"""Deriv adapter, step 1: check a customer's token. READ-ONLY, it never trades.
Uses Deriv's new API: REST with the token + the Deriv-App-ID header (DERIV_APP_ID is OUR app, same for everyone; the token is the customer's own).
Reply shapes are read loosely on purpose (not yet confirmed with deriv_probe.py), and nothing here ever puts a token in a message."""
import os, re, json, time
import threading
from . import store as st, brokers as bk, bars, links

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

def _mark(uid, status): st.x("UPDATE broker_links SET status=?,updated=? WHERE uid=? AND broker='Deriv'", (status, int(time.time()), uid))

# ---------------- step 2: candles + account snapshot + scan (still NO trading) ----------------
GRAN = {'M15': 900, 'H1': 3600}
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

def _pick(accts, want_real):
    return next((a for a in accts if a['demo'] != want_real), None)

def run_once(uid, scan, paid, connect=None, http=None, now=None):
    """One round for one customer: only if plan active, bot on, token verified. Reads candles, refreshes the account snapshot, runs the scan."""
    now = now or time.time()
    if not APP(): return 'off'
    if not paid(uid): return 'plan ended'
    l = links.get(uid)
    if not l or not l['bot']: return 'bot off'
    r = st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'", (uid,), True)
    if not r or r['status'] != 'verified': return 'not verified'
    sec = bk.secret(uid, 'Deriv')
    if not sec or not sec.get('token'): return 'no token'
    real = links.mode(uid) == 'real'
    acct = _pick(accounts(sec['token'], http), real)
    if not acct: return 'no real account' if real else 'no demo account'
    sess = Session((connect or _connect)(ws_url(sec['token'], acct['id'], http)))
    try:
        bal = balance(sess)
        if bal is None: return 'no balance'
        n_open = st.q("SELECT COUNT(*) n FROM signals WHERE status='open' AND COALESCE(uid,'')=?", (uid,), True)['n']
        st.set_acct({'balance': bal, 'equity': bal, 'open': n_open, 'demo': acct['demo'], 'allow_live': real}, uid)
        bk.set_bal(uid, 'Deriv', bal, acct['currency'], acct['demo'])
        for sym in [x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()][:8]:
            try:
                for tf in ('M15', 'H1'):
                    rows = candles(sess, sym, tf, 300 if tf == 'M15' else 200, now)
                    if rows: bars.merge(sym, tf, rows, uid=uid)
                scan(sym, uid)
            except ConnectionError: raise
            except Exception as e: print('[deriv] symbol failed', sym, repr(e)[:100])
        st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent') AND created<? AND uid=?", (int(now) - 180, uid))
    finally: sess.close()
    return 'ok'

_started = False
def start(scan, paid):
    """Background round for every verified Deriv customer. Starts quietly; does nothing until DERIV_APP_ID is set."""
    global _started
    if _started: return
    _started = True
    def loop():
        while True:
            time.sleep(max(30, int(os.getenv('DERIV_EVERY', '60'))))
            if not APP(): continue
            try: ids = [x['uid'] for x in st.q("SELECT uid FROM broker_links WHERE broker='Deriv' AND status='verified' LIMIT 200")]
            except Exception as e: print('[deriv] list failed', repr(e)[:100]); continue
            for uid in ids:
                try: run_once(uid, scan, paid)
                except Exception as e: print('[deriv] round failed', repr(e)[:100])
    threading.Thread(target=loop, daemon=True).start()
