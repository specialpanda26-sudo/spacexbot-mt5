"""BX1: live profit of every OPEN Deriv trade. Deriv has no floating figure of its own, so the phone banner and the Home card showed Floating $0.00
for normal trades (BT6 only read burst groups with a target). deriv._track already asks Deriv about every open trade each round; it now hands
the profit it just read to save(). Only a figure read in the last FRESH seconds is used; an older one is ignored, never guessed.
Words and numbers only: nothing here places or closes a trade."""
import json, time
from . import store as st

FRESH = 150          # seconds a saved figure still counts (the Deriv round runs about every 60 s)
SKEW = 5             # a reading saved up to this many seconds AFTER the caller's clock was taken still counts (a slow caller)


def _f(x):
    try: v = float(x)
    except (TypeError, ValueError): return None
    return v if v == v and abs(v) < 1e12 else None


def save(uid, live, now=None):
    """live = {signal id: profit now (USD)}. Saved as one row per person; an empty dict means 'nothing open, read just now'."""
    d = {}
    for k, v in (live or {}).items():
        f = _f(v)
        try: k = int(k)
        except (TypeError, ValueError): continue
        if f is not None: d[str(k)] = round(f, 2)
    st.put('olive:%s' % (uid or ''), json.dumps({'t': int(now or time.time()), 'p': d}))


def get(uid, now=None):
    """-> {signal id (int): profit} when it was read in the last FRESH seconds, else None."""
    now = now or time.time()
    try: j = json.loads(st.get('olive:%s' % (uid or '')) or 'null')
    except (TypeError, ValueError): return None
    if not isinstance(j, dict) or _f(j.get('t')) is None or not isinstance(j.get('p'), dict): return None
    if not -SKEW <= now - float(j['t']) <= FRESH: return None
    return {int(k): float(v) for k, v in j['p'].items() if _f(v) is not None}


def floating(uid, now=None):
    """-> the sum of the fresh live profits (USD), or None when there is no fresh reading (the caller falls back)."""
    g = get(uid, now)
    return None if g is None else round(sum(g.values()), 2)
