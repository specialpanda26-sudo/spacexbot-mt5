import threading, json, time
_lock = threading.Lock(); _d = {}; _tried = set(); _saved = {}
# BT10: candles used to live in server memory only, so every deploy or restart left the bot with a handful of candles ("20 of 120") and burst, which
# needs 30 (momentum) or 120 (strategies), sat idle for hours because the EA only sends 6 to 14 new candles per push after its first one.
# Now the newest 300 candles of each market and timeframe are also saved in kv (at most every 2 minutes) and put back the first time they are asked for.
SAVE_EVERY, SAVE_KEEP, SAVE_MAX_AGE = 120, 300, 12 * 3600
def _kv(key): return 'bars:%s:%s:%s' % key
def _restore(key):
    if key in _tried: return
    _tried.add(key)
    try:
        from . import store as st
        j = json.loads(st.get(_kv(key)) or 'null')
    except Exception: return
    if not isinstance(j, list): return
    ok = [r for r in j if isinstance(r, list) and len(r) >= 6 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in r[:6])]
    if not ok or max(int(r[0]) for r in ok) < time.time() - SAVE_MAX_AGE: return          # too old to trust: a gap would fool the momentum look
    with _lock:
        m = _d.setdefault(key, {})
        for r in ok: m.setdefault(int(r[0]), {'t': int(r[0]), 'o': r[1], 'h': r[2], 'l': r[3], 'c': r[4], 'v': r[5]})          # live candles win
def merge(sym, tf, rows, keep=600, uid=''):
    key = (uid, sym, tf); _restore(key); out = None
    with _lock:
        m = _d.setdefault(key, {})
        for r in rows:
            t, o, h, l, c, v = r[:6]; m[int(t)] = {'t': int(t), 'o': o, 'h': h, 'l': l, 'c': c, 'v': v}
        for t in sorted(m)[:-keep]: m.pop(t, None)
        now = time.time()
        if now - _saved.get(key, 0) >= SAVE_EVERY:
            _saved[key] = now; out = [[x['t'], x['o'], x['h'], x['l'], x['c'], x['v']] for x in (m[t] for t in sorted(m)[-SAVE_KEEP:])]
    if out is not None:
        try:
            from . import store as st
            st.put(_kv(key), json.dumps(out))
        except Exception as e: print('bars save failed', str(e)[:100])
def get(sym, tf, uid=''):
    key = (uid, sym, tf); _restore(key)
    with _lock: m = _d.get(key, {}); return [m[t] for t in sorted(m)]
