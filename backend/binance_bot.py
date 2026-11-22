"""Binance SPOT bot, Section 5B-2a: the ENGINE. TESTNET ONLY (it only talks through binance_trade.py, whose address is fixed to Binance's testnet).
NOT started by the app yet: 5B-2b starts the loop and adds the screens. It follows the Deriv bot: read candles, run the scan, open pending BUY signals, follow open trades.
Rules: Binance trades only when the person CHOSE Binance as the platform (never by default), the bot switch is on, the key is verified, the plan is active and the mode is demo
(= testnet). Spot is long-only: a SELL signal is skipped. Only crypto markets (BTC, ETH, BNB, SOL, XRP, ADA, DOGE, LTC against USDT). Size: a strong setup uses its stake share
of the balance (stake.py), otherwise the stop loses about the signal's risk percent; never more than half of the balance. The stop loss and take profit are checked by this
bot about once a minute (spot has no stop built into a market order), so a fast move can pass them: said plainly in the app in 5B-2b. Open trades are followed even if the bot is switched off."""
import os, time, json, threading
from decimal import Decimal
from . import store as st, brokers as bk, bars, tradeon, binance_trade as bt

CRYPTO = ('BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'LTC')
IV = {'M5': '5m', 'M15': '15m', 'H1': '1h'}; SEC = {'M5': 300, 'M15': 900, 'H1': 3600}

def pair(sym):
    """App market name -> Binance spot name, or None (not a crypto market we trade). BTCUSD and BTCUSDT both -> BTCUSDT."""
    s = str(sym or '').upper().strip()
    for b in CRYPTO:
        if s in (b + 'USD', b + 'USDT'): return b + 'USDT'
    return None

def candles(p, tf, http=None, now=None, count=300):
    """Closed candles as [epoch,o,h,l,c,0] rows (the one still forming is dropped). Public prices, no key."""
    now = now or time.time()
    try: code, j = bt._call('GET', '/api/v3/klines', params={'symbol': p, 'interval': IV[tf], 'limit': count}, http=http)
    except Exception: return []
    if code != 200 or not isinstance(j, list): return []
    rows = []
    for x in j:
        try: rows.append([int(x[0]) // 1000, float(x[1]), float(x[2]), float(x[3]), float(x[4]), 0])
        except (IndexError, TypeError, ValueError): continue
    return sorted(r for r in rows if r[0] + SEC[tf] <= now)

def _price(p, http):
    try: code, j = bt._call('GET', '/api/v3/ticker/price', params={'symbol': p}, http=http)
    except Exception: return None
    try: return float(j['price']) if code == 200 and isinstance(j, dict) else None
    except (KeyError, TypeError, ValueError): return None

def _free(key, secret, http, now_ms):
    code, a = bt._call('GET', '/api/v3/account', key, secret, http=http, now_ms=now_ms)
    if code != 200 or not isinstance(a, dict): raise ConnectionError(bt._fail(code, a if isinstance(a, dict) else {}))
    return float(bt._free(a, 'USDT')), bool(a.get('canTrade'))

def _pos(sid):
    try: j = json.loads(st.get('bnpos:%d' % sid) or '')
    except ValueError: return None
    return j if isinstance(j, dict) else None

def _held_cost(uid):
    tot = 0.0
    for r in st.q("SELECT id FROM signals WHERE uid=? AND status='open' AND broker='Binance'", (uid,)):
        p = _pos(r['id'])
        if p:
            try: tot += float(p['cost'])
            except (KeyError, TypeError, ValueError): pass
    return tot

def _stake(sig, bal):
    """USDT to spend. Strong setup = its share of the balance; otherwise the stop loses about risk_pct of the balance. Never over half of the balance. None if it cannot be worked out."""
    from . import stake as stk
    cap = bal * 0.5
    want = stk.pct(sig['id'])
    if want: return round(min(bal * want / 100.0, cap), 2)
    try: e, s = float(sig['entry']), float(sig['sl']); d = abs(e - s) / e; risk = bal * float(sig['risk_pct'] or 1) / 100.0
    except (TypeError, ValueError, ZeroDivisionError): return None
    return round(min(risk / d, cap), 2) if d > 0 else None

def _report(uid, sid, stt, reason=''):
    from . import deriv
    try: deriv._report(uid, sid, stt, reason)
    except Exception as e: print('[binance_bot] report failed', repr(e)[:80])

def _reject(uid, sid, why):
    st.x("UPDATE signals SET status='rejected',note=? WHERE id=?", (str(why)[:120], sid)); _report(uid, sid, 'rejected', why)

def _open_one(uid, key, secret, bal, now, http):
    """Claim ONE pending signal (nobody else can buy it) and buy it. True if a signal was handled."""
    s = st.q("SELECT * FROM signals WHERE uid=? AND status='pending' AND created>=? ORDER BY id LIMIT 1", (uid, int(now) - 120), True)
    if not s: return False
    if not st.x("UPDATE signals SET status='sent' WHERE id=? AND status='pending'", (s['id'],), True): return False
    p = pair(s['symbol'])
    if not p: _reject(uid, s['id'], 'Binance trades only crypto markets'); return True
    if s['side'] != 'buy': _reject(uid, s['id'], 'Binance spot cannot sell short, so a SELL signal is skipped'); return True
    stake = _stake(s, bal)
    if not stake: _reject(uid, s['id'], 'Could not work out a stake for this signal'); return True
    out = bt.open_long(key, secret, p, str(stake), 'sxb-%d' % s['id'], http, int(now * 1000))
    if out.get('ok'):
        st.x("UPDATE signals SET status='open',ticket=?,lots=?,fill=?,note='spot',broker='Binance' WHERE id=?", (str(out['order_id']), float(out['net_qty']), float(out['avg']), s['id']))
        st.put('bnpos:%d' % s['id'], json.dumps({'pair': p, 'qty': format(out['net_qty'].normalize(), 'f'), 'cost': str(out['quote']), 'fee_q': str(out['fee_quote'])}))
        _report(uid, s['id'], 'open')
    elif 'may or may not' in str(out.get('msg')):
        st.x("UPDATE signals SET note=? WHERE id=?", ('buy not confirmed, check Binance', s['id']))          # stays 'sent': never retried, so it can never buy twice
    else: _reject(uid, s['id'], out.get('msg') or 'Binance refused the order')
    return True

def _track(uid, key, secret, http, now):
    """Follow every open Binance trade of this person: price at or past the take profit / stop loss -> sell what we hold and record the result."""
    for r in st.q("SELECT id,sl,tp FROM signals WHERE uid=? AND status='open' AND broker='Binance' ORDER BY id LIMIT 20", (uid,)):
        pos = _pos(r['id'])
        if not pos: continue
        px = _price(pos['pair'], http)
        try: sl, tp = float(r['sl']), float(r['tp'])
        except (TypeError, ValueError): continue
        if px is None: continue
        why = 'tp' if px >= tp else 'sl' if px <= sl else None
        if not why: continue
        if not st.x("UPDATE signals SET status='closing' WHERE id=? AND status='open'", (r['id'],), True): continue          # claimed: one sell only
        out = bt.close_long(key, secret, pos['pair'], pos['qty'], 'sxb-%d-c' % r['id'], http, int(now * 1000))
        if not out.get('ok'):
            m = str(out.get('msg'))
            if 'already sent' in m or 'may or may not' in m: st.x("UPDATE signals SET note=? WHERE id=?", ('sell not confirmed, check Binance', r['id']))          # stays 'closing': never sold twice
            else: st.x("UPDATE signals SET status='open',note=? WHERE id=?", (m[:120], r['id']))
            continue
        pnl = round(float(out['quote'] - out['fee_quote'] - Decimal(pos['cost']) - Decimal(pos.get('fee_q') or 0)), 2)
        st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=?", (pnl, int(time.time()), r['id']))
        st.put('closedby:%d' % r['id'], why); st.put('exitpx:%d' % r['id'], float(out['avg']))
        _report(uid, r['id'], 'closed', why)

def _bot(uid): return bk.bot_flag(uid, 'Binance') is True

def run_once(uid, scan, paid, http=None, now=None):
    """One round for one person. The result is saved as a plain-words note on the Binance tile (bk.set_why), like Deriv."""
    now = now or time.time()
    try: r = _run_once(uid, scan, paid, http, now)
    except Exception as e:
        print('[binance_bot] round failed', type(e).__name__); bk.set_why(uid, 'Binance', 'error', now); raise
    bk.set_why(uid, 'Binance', r, now); return r

def _run_once(uid, scan, paid, http, now):
    row = st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Binance'", (uid,), True)
    if not row or row['status'] != 'verified': return 'not verified'
    sec = bk.secret(uid, 'Binance')
    if not sec or not sec.get('key') or not sec.get('secret'): return 'no key'
    key, secret = sec['key'], sec['secret']
    ms = int(now * 1000)
    if st.q("SELECT 1 FROM signals WHERE uid=? AND status='open' AND broker='Binance'", (uid,), True): _track(uid, key, secret, http, now)          # always, even if the bot is off
    if not paid(uid): return 'plan ended'
    if tradeon.get(uid) != 'Binance': return 'other platform'          # Binance trades only when it was chosen on purpose
    if not _bot(uid): return 'bot off'
    if bk.mode(uid, 'Binance') == 'real': return 'real not ready'          # 5B-3
    free, can = _free(key, secret, http, ms)
    if not can: return 'cannot trade'
    bal = free + _held_cost(uid)
    n_open = st.q("SELECT COUNT(*) n FROM signals WHERE status='open' AND COALESCE(uid,'')=?", (uid,), True)['n']
    st.set_acct({'balance': bal, 'equity': bal, 'open': n_open, 'demo': True, 'allow_live': False, 'src': 'binance'}, uid)
    bk.set_bal(uid, 'Binance', bal, 'USD', demo=True, now=now)
    syms = [x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()][:8]
    mine = [s for s in syms if pair(s)]
    if not mine: return 'no crypto symbols'
    for sym in mine:
        try:
            from . import prefs
            for tf in (('M5', 'M15', 'H1') if prefs.get(uid)['fast'] else ('M15', 'H1')):
                rows = candles(pair(sym), tf, http, now, 200 if tf == 'H1' else 300)
                if rows: bars.merge(sym, tf, rows, uid=uid)
            scan(sym, uid)
        except Exception as e: print('[binance_bot] symbol failed', sym, type(e).__name__)
    for _ in range(12):
        if not _open_one(uid, key, secret, bal, now, http): break
    st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent') AND created<? AND uid=?", (int(now) - 180, uid))
    return 'ok'

_started = False
def round_all(scan, paid):
    try: ids = [x['uid'] for x in st.q("SELECT uid FROM broker_links WHERE broker='Binance' AND status='verified' LIMIT 200")]
    except Exception as e: print('[binance_bot] list failed', repr(e)[:100]); return 0
    for uid in ids:
        try: run_once(uid, scan, paid)
        except Exception as e: print('[binance_bot] round failed', type(e).__name__)
    st.put('binance:beat', int(time.time())); return len(ids)

def kick(uid, scan, paid):
    def go():
        try: run_once(uid, scan, paid)
        except Exception as e: print('[binance_bot] kick failed', type(e).__name__)
    threading.Thread(target=go, daemon=True).start()

def start(scan, paid):
    global _started
    if _started: return
    _started = True
    def loop():
        while True:
            time.sleep(max(30, int(os.getenv('BINANCE_EVERY', '60'))))
            round_all(scan, paid)
    threading.Thread(target=loop, daemon=True).start()
