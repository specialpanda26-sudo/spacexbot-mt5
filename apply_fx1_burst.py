"""FX1: burst stuck on 'Not enough candle history (18 of 120)'.
Run from the repo folder: python3 apply_fx1_burst.py"""
import re, sys

def rep(path, old, new, count=1):
    s = open(path, encoding='utf-8').read()
    if s.count(old) != count:
        sys.exit('STOP: %s: expected %d match(es), found %d for: %s' % (path, count, s.count(old), old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new))
    print('ok', path)

BARS = '''"""Candle store. The newest ~600 candles per person, market and timeframe, kept in server memory for speed.
FX1: they are also saved in the database (kv 'bars:<uid>:<symbol>:<tf>', at most once every SAVE_EVERY seconds per key) and loaded back the first time a key is
used after a restart. Before, every restart or Render sleep threw the history away, and the MT5 bridge only sends a few new candles a minute afterwards, so burst
mode waited hours for its 30 to 120 candles. Nothing here is invented: only candles the broker or feed really sent."""
import json, threading, time
_lock = threading.Lock(); _d = {}; _tried = set(); _saved = {}
SAVE_EVERY = 300          # seconds between database saves of one key
KEEP_AGE = 14 * 86400     # saved candles older than this are not loaded back


def _kv(uid, sym, tf): return 'bars:%s:%s:%s' % (uid or '', sym, tf)


def _num(x): return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x


def _restore(uid, sym, tf):
    """Load the saved candles of this key, once per process. Never raises: nothing saved, or a database hiccup, just means an empty start like before."""
    k = (uid, sym, tf)
    with _lock:
        if k in _tried: return
        _tried.add(k)
    rows = []
    try:
        from . import store as st
        j = json.loads(st.get(_kv(uid, sym, tf)) or '[]'); now = time.time()
        for r in (j if isinstance(j, list) else []):
            if isinstance(r, list) and len(r) >= 6 and all(_num(x) for x in r[:6]) and 0 <= now - r[0] <= KEEP_AGE: rows.append(r)
    except Exception as e:
        print('bars restore failed', sym, tf, str(e)[:80]); return
    with _lock:
        m = _d.setdefault(k, {})
        for r in rows: m.setdefault(int(r[0]), {'t': int(r[0]), 'o': r[1], 'h': r[2], 'l': r[3], 'c': r[4], 'v': r[5]})          # a candle that already arrived wins


def _save(uid, sym, tf, now):
    k = (uid, sym, tf)
    with _lock:
        if now - _saved.get(k, 0) < SAVE_EVERY: return
        _saved[k] = now; m = _d.get(k, {})
        rows = [[m[t]['t'], m[t]['o'], m[t]['h'], m[t]['l'], m[t]['c'], m[t]['v']] for t in sorted(m)]
    try:
        from . import store as st
        st.put(_kv(uid, sym, tf), json.dumps(rows))
    except Exception as e: print('bars save failed', sym, tf, str(e)[:80])


def merge(sym, tf, rows, keep=600, uid=''):
    _restore(uid, sym, tf)
    with _lock:
        m = _d.setdefault((uid, sym, tf), {})
        for r in rows:
            t, o, h, l, c, v = r[:6]; m[int(t)] = {'t': int(t), 'o': o, 'h': h, 'l': l, 'c': c, 'v': v}
        for t in sorted(m)[:-keep]: m.pop(t, None)
    _save(uid, sym, tf, time.time())


def get(sym, tf, uid=''):
    _restore(uid, sym, tf)
    with _lock: m = _d.get((uid, sym, tf), {}); return [m[t] for t in sorted(m)]
'''
open('backend/bars.py', 'w', encoding='utf-8').write(BARS); print('ok backend/bars.py (whole file)')

rep('backend/burst_free.py', "HOUR = 3600\n", "HOUR = 3600\nMIN_MINUTE = 10          # FX1: 'trade every minute' needs only this many candles; a no-signal burst without it still needs 30\n")
rep('backend/burst_free.py',
    '''def side_any(m):
    """BT7: the direction of the last 5 candles, however small ('buy' up, 'sell' down). None only when the price did not move at all."""
    if not m or len(m) < 30: return None''',
    '''def side_any(m, need=30):
    """BT7: the direction of the last 5 candles, however small ('buy' up, 'sell' down). None only when the price did not move at all."""
    if not m or len(m) < max(7, need): return None''')
rep('backend/burst_free.py', "sd = side(m) or (side_any(m) if minute else None)", "sd = side(m) or (side_any(m, MIN_MINUTE) if minute else None)")
rep('backend/burst_look.py',
    "    if bf.side(m) is None and not (minute and bf.side_any(m)): return 'No clear price move either.'",
    "    need = bf.MIN_MINUTE if minute else 30          # FX1\n"
    "    if len(m or []) < need: return 'Only %d candles so far; a chance without a strategy signal needs %d.' % (len(m or []), need)\n"
    "    if bf.side(m) is None and not (minute and bf.side_any(m, bf.MIN_MINUTE)): return 'No clear price move either.'")
print('FX1 done')
