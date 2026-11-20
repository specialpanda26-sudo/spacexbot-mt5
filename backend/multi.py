"""R8 multi-entry: on a strong, clean setup the bot may open several entries at once. The OWNER decides how many.
Settings (owner, /api/admin/settings): multi_entries = most entries per setup, 1..10 (1 = off, the default); multi_min_score = how many strategies must agree, default 3.
The entries SHARE the normal risk of one trade (each gets base / n), so a setup that fails loses what one trade would have lost, not n times that.
Always held back by the person's max positions at once, the owner's ceiling and the max trades a day: the count never goes above the room left.
Nothing here claims it makes more money. Only tools/backtest.py on real data can say that."""
from . import store as st, limits, risk, prefs, scale, automode

HI = 10

def _g(k, d):
    try: return int(float(st.get(k)))
    except (TypeError, ValueError): return d

def cap(uid=''):
    p = prefs.get(uid)
    return max(1, min(HI, p['entries'] or _g('multi_entries', 1)))

def min_score():
    return max(1, _g('multi_min_score', 3))

def entries(uid, score, strategy=''):
    if automode.on(): return 1
    c = cap(uid); p = prefs.get(uid)
    try: sc = int(score or 0)
    except (TypeError, ValueError): sc = 0
    if c <= 1: return 1
    if p['scale']:
        if not scale.hot(uid, strategy)[0]: return 1
    elif sc < min_score() and not p['entries']: return 1
    room = limits.max_open(uid) - risk.open_count(uid)
    return max(1, min(c, room))          # the daily limit counts setups, not entries (risk.global_gate): one setup of n entries is one trade

def share(base, n):
    """Risk percent for each entry. One entry keeps the exact normal number."""
    return float(base) if n <= 1 else round(float(base) / n, 4)
