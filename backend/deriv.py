"""Deriv adapter, step 1: check a customer's token. READ-ONLY, it never trades.
Uses Deriv's new API: REST with the token + the Deriv-App-ID header (DERIV_APP_ID is OUR app, same for everyone; the token is the customer's own).
Reply shapes are read loosely on purpose (not yet confirmed with deriv_probe.py), and nothing here ever puts a token in a message."""
import os, re, json, time
import threading
from . import store as st, brokers as bk, bars, links, push, sbauth, learn, lag

BASE = lambda: os.getenv('DERIV_BASE', 'https://api.derivws.com').rstrip('/')
APP = lambda: os.getenv('DERIV_APP_ID', '').strip()
_last = {}

def _http(method, path, token):
    import requests
    r = requests.request(method, BASE() + path, data=b'' if method == 'POST' else None, timeout=15,
                         headers={'Authorization': 'Bearer ' + token, 'Deriv-App-ID': APP(), 'Accept': 'application/json'})
    try: j = r.json()
    except ValueError: j = {}
    return r.status_code, j

def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values(): yield from _walk(v)
    elif isinstance(o, list):
        for v in o: yield from _walk(v)

def accounts(token, http=None):
    """[{'id','demo','currency'}] from whatever shape Deriv returns. Raises PermissionError (token refused) or ConnectionError."""
    try: code, j = (http or _http)('GET', '/trading/v1/options/accounts', token)
    except Exception: raise ConnectionError('Could not reach Deriv. Try again in a minute.')
    if code in (400, 401, 403):
        print('[deriv] token refused, HTTP', code)          # for the owner's log: 400 can also mean a wrong DERIV_APP_ID
        raise PermissionError('Deriv did not accept this token. Check it has Read and Trade scopes and is not expired.')
    if code != 200: raise ConnectionError('Deriv is not answering right now. Try again in a minute.')
    out, seen = [], set()
    for d in _walk(j):
        i = d.get('account_id') or d.get('id') or d.get('loginid')
        if not i or str(i) in seen: continue
        seen.add(str(i)); s = json.dumps({k: v for k, v in d.items() if not isinstance(v, (dict, list))})
        demo = bool(re.search(r'demo|virtual', s, re.I)) or str(i).upper().startswith(('VRT', 'DOT'))
        out.append({'id': str(i), 'demo': demo, 'currency': str(d.get('currency') or 'USD')})
    return out

def ws_url(token, acct, http=None):
    """A fresh one-time websocket link (valid about 2 minutes). Needed on every connect."""
    if not re.match(r'^[A-Za-z0-9_\-]{3,40}$', str(acct)): raise ValueError('bad account id')
    try: code, j = (http or _http)('POST', '/trading/v1/options/accounts/%s/otp' % acct, token)
    except Exception: raise ConnectionError('Could not reach Deriv. Try again in a minute.')
    u = (j.get('data') or {}).get('url') if isinstance(j, dict) else None
    if code != 200 or not isinstance(u, str) or not u.startswith('wss://'): raise ConnectionError('Deriv would not open a trading link for this account.')
    return u

def verify(uid, http=None, now=None, connect=None):
    """Check the saved Deriv token. Sets status 'verified' or 'rejected'. Returns (ok, message). Needs DERIV_APP_ID on Render."""
    now = now or time.time()
    if now - _last.get(uid, 0) < 8: return False, 'Wait a few seconds and try again.'
    _last[uid] = now
    if not APP(): return False, 'Deriv trading is not switched on yet. Please try again soon.'
    sec = bk.secret(uid, 'Deriv')
    if not sec or not sec.get('token'): return False, 'Save your Deriv token first.'
    try:
        accts = accounts(sec['token'], http)
        if not accts: raise PermissionError('This token has no trading account. Make it on your Deriv account with Read and Trade scopes.')
    except PermissionError as e: _mark(uid, 'rejected'); return False, str(e)
    except ConnectionError as e: return False, str(e)
    _mark(uid, 'verified')
    demo = [a for a in accts if a['demo']]
    try: _snapshot(uid, sec['token'], demo[0] if demo else None, http, connect)          # show the balance right away; never blocks the check
    except Exception: pass
    return True, 'Deriv connected. Demo account found.' if demo else 'Deriv connected, but no demo account was found. Trading stays off until you add one.'

def _snapshot(uid, token, acct, http=None, connect=None):
    if not acct: return
    sess = Session((connect or _connect)(ws_url(token, acct['id'], http)))
    try:
        bal = balance(sess)
        if bal is not None: bk.set_bal(uid, 'Deriv', bal, acct['currency'], acct['demo'])
    finally: sess.close()

def refresh(uid, http=None, connect=None):
    """Read the balance of the account type the person picked (Demo or Real) so the Account card shows it. Never trades. True if it worked."""
    if not APP(): return False
    r = st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'", (uid,), True)
    sec = bk.secret(uid, 'Deriv') if r and r['status'] == 'verified' else None
    if not sec or not sec.get('token'): return False
    try:
        acct = _pick(accounts(sec['token'], http), bk.mode(uid, 'Deriv') == 'real')
        if not acct: return False
        _snapshot(uid, sec['token'], acct, http, connect)
    except Exception: return False
    return True

def _mark(uid, status): st.x("UPDATE broker_links SET status=?,updated=? WHERE uid=? AND broker='Deriv'", (status, int(time.time()), uid))

# ---------------- step 2: candles + account snapshot + scan (still NO trading) ----------------
GRAN = {'M5': 300, 'M15': 900, 'H1': 3600}
def _frx(sym): return 'frx' + str(sym).upper()          # XAUUSD -> frxXAUUSD (what Deriv calls it)

def _connect(url):
    import websocket
    return websocket.create_connection(url, timeout=15)

class Session:
    """One websocket conversation. Every question carries a req_id and we wait for the matching answer."""
    def __init__(s, ws): s.ws, s.n = ws, 0
    def ask(s, msg):
        s.n += 1; s.ws.send(json.dumps(dict(msg, req_id=s.n)))
        for _ in range(12):
            d = json.loads(s.ws.recv())
            if isinstance(d, dict) and (d.get('req_id') == s.n or (d.get('echo_req') or {}).get('req_id') == s.n): return d
        raise ConnectionError('Deriv did not answer.')
    def close(s):
        try: s.ws.close()
        except Exception: pass

def candles(sess, sym, tf, count=300, now=None):
    """Closed candles as [epoch,o,h,l,c,0] rows. The candle still forming is dropped, so signals use finished candles only."""
    now = now or time.time(); g = GRAN[tf]
    for extra in ({}, {'underlying_symbol': _frx(sym)}):            # the probe will tell us which spelling Deriv wants; try both
        d = sess.ask(dict({'ticks_history': _frx(sym), 'style': 'candles', 'granularity': g, 'count': count, 'end': 'latest'}, **extra))
        c = d.get('candles')
        if isinstance(c, list) and c: break
    else: return []
    rows = []
    for x in c:
        try: t = int(x['epoch']); rows.append([t, float(x['open']), float(x['high']), float(x['low']), float(x['close']), 0])
        except (KeyError, TypeError, ValueError): continue
    return sorted(r for r in rows if r[0] + g <= now)

def balance(sess):
    d = sess.ask({'balance': 1}); b = d.get('balance')
    try: return float(b.get('balance') if isinstance(b, dict) else b)
    except (TypeError, ValueError): return None

def _bot(uid):
    """Is the bot on for this person's Deriv trading? The Deriv switch (set from the Deriv tile) wins once used;
    until then the old MT5-link switch still counts, so nothing that worked before stops working."""
    from . import tradeon
    if not tradeon.allows(uid, 'Deriv'): return False          # 5A: another platform was chosen
    f = bk.bot_flag(uid, 'Deriv')
    return f if f is not None else links.bot_on(uid)

def _pick(accts, want_real):
    return next((a for a in accts if a['demo'] != want_real), None)

def run_once(uid, scan, paid, connect=None, http=None, now=None):
    """One round for one customer (see _run_once). The result is also saved as a plain-words note on the Deriv tile, so a bot that
    does nothing always says why."""
    now = now or time.time()
    try: r = _run_once(uid, scan, paid, connect, http, now)
    except Exception: bk.set_why(uid, 'Deriv', 'error', now); raise
    bk.set_why(uid, 'Deriv', r, now); return r

def _run_once(uid, scan, paid, connect, http, now):
    """One round for one customer: only if plan active, bot on, token verified. Reads candles, refreshes the account snapshot, runs the scan."""
    if not APP(): return 'off'
    if not paid(uid): return 'plan ended'
    from . import tradeon
    if not tradeon.allows(uid, 'Deriv'): return 'other platform'          # 5A
    if not _bot(uid): return 'bot off'
    r = st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'", (uid,), True)
    if not r or r['status'] != 'verified': return 'not verified'
    sec = bk.secret(uid, 'Deriv')
    if not sec or not sec.get('token'): return 'no token'
    real = bk.mode(uid, 'Deriv') == 'real'
    acct = _pick(accounts(sec['token'], http), real)
    if not acct: return 'no real account' if real else 'no demo account'
    sess = Session((connect or _connect)(ws_url(sec['token'], acct['id'], http)))
    try:
        bal = balance(sess)
        if bal is None: return 'no balance'
        n_open = st.q("SELECT COUNT(*) n FROM signals WHERE status='open' AND COALESCE(uid,'')=?", (uid,), True)['n']
        st.set_acct({'balance': bal, 'equity': bal, 'open': n_open, 'demo': acct['demo'], 'allow_live': real, 'src': 'deriv'}, uid)
        bk.set_bal(uid, 'Deriv', bal, acct['currency'], acct['demo'])
        try: _track(sess, uid, acct)
        except ConnectionError: raise
        except Exception as e: print('[deriv] track failed', repr(e)[:100])
        syms = [x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()][:8]
        for sym in syms:
            try:
                from . import prefs
                for tf in (('M5', 'M15', 'H1') if prefs.get(uid)['fast'] else ('M15', 'H1')):
                    rows = candles(sess, sym, tf, 200 if tf == 'H1' else 300, now)
                    if rows: bars.merge(sym, tf, rows, uid=uid)
                lag.got(uid, 'deriv')
                scan(sym, uid)
            except ConnectionError: raise
            except Exception as e: print('[deriv] symbol failed', sym, repr(e)[:100])
        try: _trade(sess, uid, acct, bal, now)
        except ConnectionError: raise
        except Exception as e: print('[deriv] trade failed', repr(e)[:100])
        st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent') AND created<? AND uid=?", (int(now) - 180, uid))
    finally: sess.close()
    return 'ok' if syms else 'no symbols'

_started = False
def round_all(scan, paid):
    """One pass over every verified Deriv customer. Runs even when DERIV_APP_ID is missing, so each customer's tile can say so."""
    try: ids = [x['uid'] for x in st.q("SELECT uid FROM broker_links WHERE broker='Deriv' AND status='verified' LIMIT 200")]
    except Exception as e: print('[deriv] list failed', repr(e)[:100]); return 0
    for uid in ids:
        try: run_once(uid, scan, paid)
        except Exception as e: print('[deriv] round failed', repr(e)[:100])
    st.put('deriv:beat', int(time.time()))          # the loop's heartbeat (shown in the owner's health)
    return len(ids)

def kick(uid, scan, paid):
    """Run one round for one person right now (after Start bot), instead of waiting up to a minute."""
    def go():
        try: run_once(uid, scan, paid)
        except Exception as e: print('[deriv] kick failed', repr(e)[:100])
    threading.Thread(target=go, daemon=True).start()

def start(scan, paid):
    """Background round for every verified Deriv customer. Starts quietly; does nothing until DERIV_APP_ID is set."""
    global _started
    if _started: return
    _started = True
    def loop():
        while True:
            time.sleep(max(30, int(os.getenv('DERIV_EVERY', '60'))))
            round_all(scan, paid)
    threading.Thread(target=loop, daemon=True).start()

# ---------------- step 3: place and follow trades (multiplier contracts). Demo accounts always; a real account also needs DERIV_REAL=1 ----------------
MULTS = lambda: [int(x) for x in os.getenv('DERIV_MULTS', '100,200,50,30,20,10,5').split(',') if x.strip().isdigit()]
_mult_ok = {}          # symbol -> the multiplier Deriv accepted last time

def _why(d):
    e = d.get('error') if isinstance(d, dict) else None
    return (str((e.get('message') or e.get('code')) if isinstance(e, dict) else 'no answer from Deriv'))[:100]

def _size(entry, sl, tp, bal, risk_pct, mult):
    """Stake and the two money limits so that hitting the stop loses about risk_pct of the balance and the target wins RR times that.
    Multiplier maths: profit = stake x multiplier x price change. Returns (stake, stop_loss_money, take_profit_money) or None."""
    try: entry, sl, tp, bal = float(entry), float(sl), float(tp), float(bal)
    except (TypeError, ValueError): return None
    if not entry or entry == sl or entry == tp: return None
    frac = abs(entry - sl) / entry
    risk = bal * float(risk_pct or 1) / 100.0
    stake = round(risk / (mult * frac), 2)
    if stake < 1 or stake > bal * 0.5 or risk >= stake: return None        # too small for Deriv, too big for the account, or the stop would be wider than the stake
    return stake, round(risk, 2), round(risk * abs(tp - entry) / abs(entry - sl), 2)

def _place(sess, sig, bal, cur):
    """Quote, then buy by the quote's own id (so one signal can never buy twice). Returns ('open', info) or ('rejected', reason)."""
    from . import stake as stk
    ct = 'MULTUP' if sig['side'] == 'buy' else 'MULTDOWN'; sym = sig['symbol']
    order = ([_mult_ok[sym]] if sym in _mult_ok else []) + [m for m in MULTS() if m != _mult_ok.get(sym)]
    last = 'no multiplier fits this balance and stop distance'
    want = stk.pct(sig['id'])          # Section 1: the stake share set for this signal (0 = normal sizing)
    for m in order:
        z = (want and stk.size(sig['entry'], sig['sl'], sig['tp'], bal, want, m)) or _size(sig['entry'], sig['sl'], sig['tp'], bal, sig['risk_pct'], m)
        if not z: continue
        stake, slm, tpm = z
        p = sess.ask({'proposal': 1, 'contract_type': ct, 'underlying_symbol': _frx(sym), 'currency': cur, 'amount': stake, 'basis': 'stake',
                      'multiplier': m, 'limit_order': {'stop_loss': slm, 'take_profit': tpm}})
        q = p.get('proposal')
        if not isinstance(q, dict) or not q.get('id'): last = _why(p); continue
        b = sess.ask({'buy': q['id'], 'price': q.get('ask_price', stake)})
        by = b.get('buy')
        if not isinstance(by, dict) or not by.get('contract_id'): return 'rejected', _why(b)
        _mult_ok[sym] = m
        return 'open', {'contract_id': by['contract_id'], 'stake': stake, 'mult': m}
    return 'rejected', last

def _report(uid, sid, stt, reason=''):
    """Same alerts the EA path sends: opened, closed (win/loss), skipped. Only to this customer."""
    s = st.q('SELECT * FROM signals WHERE id=?', (sid,), True)
    if not s: return
    if stt == 'closed': learn.log(uid, 'closed', s['strategy'], s['symbol'], s['side'], s['pnl'], {'reason': reason})
    if stt in ('open', 'closed'):
        sbauth.notify('%s %s' % (s['symbol'], 'opened' if stt == 'open' else 'closed'), ('%s stake %s' % (s['side'].upper(), s['lots'])) if stt == 'open' else 'P/L %s' % s['pnl'], key='sig%s-%s' % (sid, stt), only=uid)
        if stt == 'open': push.notify(1, 'sig%s-open' % sid, sym=s['symbol'], side=s['side'], entry=s['fill'] or s['entry'], sl=s['sl'], tp=s['tp'], risk=s['risk_pct'], strategy=s['strategy'], only=uid)
        else: push.notify({'tp': 2, 'sl': 3}.get(reason, 4), 'sig%s-closed' % sid, sym=s['symbol'], pnl=s['pnl'], only=uid)
    elif stt == 'rejected': push.notify(8, 'sig%s-skipped' % sid, sym=s['symbol'], reason=str(reason)[:80], only=uid)

def _resnap(sess, uid, acct):
    b = balance(sess)
    if b is None: return
    n = st.q("SELECT COUNT(*) n FROM signals WHERE status='open' AND COALESCE(uid,'')=?", (uid,), True)['n']
    st.set_acct({'balance': b, 'equity': b, 'open': n, 'demo': acct['demo'], 'allow_live': bk.mode(uid, 'Deriv') == 'real', 'src': 'deriv'}, uid)
    bk.set_bal(uid, 'Deriv', b, acct['currency'], acct['demo'])

def _trade_one(sess, uid, acct, bal, now):
    if not acct['demo'] and os.getenv('DERIV_REAL') != '1': return          # real money needs the owner's switch as well as the customer's Real mode
    s = st.q("SELECT * FROM signals WHERE uid=? AND status='pending' AND created>=? ORDER BY id LIMIT 1", (uid, int(now) - 120), True)
    if not s or not _bot(uid): return
    if not st.x("UPDATE signals SET status='sent' WHERE id=? AND status='pending'", (s['id'],), True): return      # claimed: nobody else can buy this signal
    lag.stamp(s['id'], 'sent')
    try: kind, r = _place(sess, s, bal, acct['currency'])
    except Exception as e:
        st.x("UPDATE signals SET note=? WHERE id=?", ('buy not confirmed, check Deriv', s['id'])); print('[deriv] buy unconfirmed', repr(e)[:100]); return
    if kind == 'open':
        lag.stamp(s['id'], 'opened')
        st.x("UPDATE signals SET status='open',ticket=?,lots=?,fill=?,note=?,broker='Deriv' WHERE id=?", (str(r['contract_id']), r['stake'], s['entry'], 'x%s' % r['mult'], s['id']))
        _report(uid, s['id'], 'open')
    else:
        st.x("UPDATE signals SET status='rejected',note=? WHERE id=?", (r[:120], s['id'])); _report(uid, s['id'], 'rejected', r)
    _resnap(sess, uid, acct)

def _trade(sess, uid, acct, bal, now):
    """R8: open every entry that is waiting (up to 12), one after the other, so a multi-entry setup is not spread over minutes.
    Stops at once if one buy could not be confirmed (it stays 'sent') or nothing moved."""
    for _ in range(12):
        pend = lambda: st.q("SELECT COUNT(*) n FROM signals WHERE uid=? AND status='pending'", (uid,), True)['n']
        before = pend()
        if not before: return
        _trade_one(sess, uid, acct, bal, now)
        if pend() >= before or st.q("SELECT COUNT(*) n FROM signals WHERE uid=? AND status='sent'", (uid,), True)['n']: return

def _closed_by(r, pnl):
    """'sl' or 'tp' only when the profit is within 5% of the loss/gain the stop or target should give (stake x multiplier x distance);
    anything else, or anything it cannot work out, is 'other'. Deriv reports only the profit, so this is an inference, never a guess from the sign alone."""
    try:
        stake = float(r['lots']); mult = float(str(r['note']).lstrip('x')); e = float(r['entry']); sl = float(r['sl']); tp = float(r['tp'])
        if min(stake, mult, e) <= 0 or e == sl: return 'other'
        risk = stake * mult * abs(e - sl) / e; gain = risk * abs(tp - e) / abs(e - sl)
    except (KeyError, TypeError, ValueError): return 'other'
    if pnl < 0 and abs(-pnl - risk) <= max(0.05 * risk, 0.02): return 'sl'
    if pnl > 0 and abs(pnl - gain) <= max(0.05 * gain, 0.02): return 'tp'
    return 'other'

def _track(sess, uid, acct):
    """Ask Deriv about every open trade of this customer; when one has been sold (stop, target or by hand) record the result."""
    done = False
    for r in st.q("SELECT id,ticket,lots,note,entry,sl,tp FROM signals WHERE uid=? AND status='open' AND ticket IS NOT NULL ORDER BY id LIMIT 20", (uid,)):
        try: cid = int(r['ticket'])
        except (TypeError, ValueError): continue
        p = sess.ask({'proposal_open_contract': 1, 'contract_id': cid}).get('proposal_open_contract')
        if not isinstance(p, dict) or str(p.get('is_sold')).lower() not in ('1', 'true'): continue
        try: pnl = round(float(p.get('profit')), 2)
        except (TypeError, ValueError): continue
        if st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=? AND status='open'", (pnl, int(time.time()), r['id']), True):
            st.put('closedby:%d' % r['id'], _closed_by(r, pnl))          # Section 3: shown as "Closed by" in the trade detail
            for k in ('sell_spot', 'exit_tick'):          # Section 4: only a price Deriv really sent
                try: x = float(p.get(k))
                except (TypeError, ValueError): continue
                if 0 < x < 1e9: st.put('exitpx:%d' % r['id'], x); break
            _report(uid, r['id'], 'closed', 'tp' if pnl > 0 else 'sl' if pnl < 0 else 'other'); done = True
    if done: _resnap(sess, uid, acct)
