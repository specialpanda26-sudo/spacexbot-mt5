import threading
_lock = threading.Lock(); _d = {}
def merge(sym, tf, rows, keep=600):
    with _lock:
        m = _d.setdefault((sym, tf), {})
        for r in rows:
            t, o, h, l, c, v = r[:6]; m[int(t)] = {'t': int(t), 'o': o, 'h': h, 'l': l, 'c': c, 'v': v}
        for t in sorted(m)[:-keep]: m.pop(t, None)
def get(sym, tf):
    with _lock: m = _d.get((sym, tf), {}); return [m[t] for t in sorted(m)]
