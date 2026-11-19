"""R6 step 1: measure why opening a position takes long. It only writes down times and shows the gaps; it never changes a trade.
One kv row per signal: lag:<id> = {"bar","got","created","sent","opened","via"} (seconds, UTC).
bar = open time of the closed candle the signal came from, so the candle closed at bar + 900. got = when that candle reached the server.
Every function here swallows its own errors: a timing note must never stop a trade."""
import json, time
from . import store as st

KEEP = 40          # how many recent signals the report reads
M15 = 900

def _now(): return int(time.time())

def _read(sid):
    try: return json.loads(st.get('lag:%d' % int(sid)) or '{}')
    except (TypeError, ValueError): return {}

def got(uid, via):
    """Call when fresh candles have just arrived for this person (via = 'ea' or 'deriv')."""
    try: st.put('lag:got:%s' % (uid or 'owner'), json.dumps({'t': _now(), 'via': via}))
    except Exception as e: print('[lag] got failed', repr(e)[:80])

def created(sid, bar, uid):
    """Call right after a signal row is made."""
    try:
        g = json.loads(st.get('lag:got:%s' % (uid or 'owner')) or '{}')
        d = {'bar': int(bar), 'created': _now(), 'via': g.get('via') or 'other'}
        if g.get('t'): d['got'] = int(g['t'])
        st.put('lag:%d' % int(sid), json.dumps(d))
    except Exception as e: print('[lag] created failed', repr(e)[:80])

def stamp(sid, what):
    """what = 'sent' (handed to the EA or claimed by Deriv) or 'opened' (the broker confirmed the position). First time wins."""
    try:
        d = _read(sid)
        if not d or what in d: return
        d[what] = _now(); st.put('lag:%d' % int(sid), json.dumps(d))
    except Exception as e: print('[lag] stamp failed', repr(e)[:80])

def gaps(d):
    """Seconds between each step, None where a step is missing. Also 'total' = candle close to open position."""
    def sub(a, b): return int(d[a] - d[b]) if a in d and b in d else None
    close = d['bar'] + M15 if 'bar' in d else None
    out = {'candle_to_server': (int(d['got'] - close) if close is not None and 'got' in d else None),
           'server_scan': sub('created', 'got'), 'signal_to_sent': sub('sent', 'created'), 'sent_to_open': sub('opened', 'sent'),
           'total': (int(d['opened'] - close) if close is not None and 'opened' in d else None)}
    return out

def report(n=KEEP):
    rows = st.q("SELECT id,symbol,side,status FROM signals ORDER BY id DESC LIMIT ?", (int(n),)) or []
    items, cols = [], {}
    for r in rows:
        d = _read(r['id'])
        if not d: continue
        g = gaps(d); items.append({'id': r['id'], 'symbol': r['symbol'], 'side': r['side'], 'status': r['status'], 'via': d.get('via'), 'gaps': g})
        for k, v in g.items():
            if v is not None: cols.setdefault(k, []).append(v)
    def med(v): v = sorted(v); return v[len(v) // 2]
    typical = {k: med(v) for k, v in cols.items()}
    steps = {k: v for k, v in typical.items() if k != 'total'}
    biggest = max(steps, key=steps.get) if steps else None
    return {'count': len(items), 'typical_seconds': typical, 'biggest': biggest, 'recent': items}
