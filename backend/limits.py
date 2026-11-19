"""Per-person trading limits that the SERVER enforces: max trades a day and the loss-streak stop.
Before this, the two boxes in the app (Session limits card) only changed the page on the phone; the server used one global setting for everybody.
Rules:
 - Owner (uid ''): the boxes write the global settings max_trades_day and max_losing_streak (same keys the admin settings already use).
 - A subscriber saves their own numbers, kept per person. 0 or empty = use the owner's setting.
 - A subscriber can only be STRICTER than the owner, never looser: trades = the smaller of the two (when the owner has a cap), streak the same.
   The owner's 0 means 'no limit' for trades and 'switched off' for the streak stop, so then the subscriber's own number applies on its own.
The risk gate (risk.global_gate) asks trades(uid) and streak(uid) every time, so a change applies on the very next signal."""
import json
from . import store as st

MAX_TRADES, MAX_STREAK = 100, 10

def _g(k):
    try: return max(0, int(float(st.get(k) or 0)))
    except (TypeError, ValueError): return 0

def _mine(uid):
    if not uid: return {}
    try: j = json.loads(st.get('lim:' + uid) or '{}')
    except ValueError: j = {}
    return j if isinstance(j, dict) else {}

def _num(v):
    try: return max(0, int(v))
    except (TypeError, ValueError): return 0

def _cap(own, owner):
    """The smaller of the person's number and the owner's, where 0 means 'not set'."""
    if own <= 0: return owner
    if owner <= 0: return own
    return min(own, owner)

def trades(uid=''):
    """Effective max trades per day for the gate. 0 = no limit."""
    return _g('max_trades_day') if not uid else _cap(_num(_mine(uid).get('mt')), _g('max_trades_day'))

def streak(uid=''):
    """Effective loss-streak stop for the gate. 0 = off."""
    return _g('max_losing_streak') if not uid else _cap(_num(_mine(uid).get('ks')), _g('max_losing_streak'))

def view(uid=''):
    """What the app shows: the person's OWN saved numbers (0 = none) and the owner's caps."""
    if not uid: return {'max_trades': _g('max_trades_day'), 'streak': _g('max_losing_streak'), 'cap_trades': 0, 'cap_streak': 0}
    m = _mine(uid); ct, cs = _g('max_trades_day'), _g('max_losing_streak')
    return {'max_trades': _cap(_num(m.get('mt')), ct) if _num(m.get('mt')) else 0, 'streak': _cap(_num(m.get('ks')), cs) if _num(m.get('ks')) else 0, 'cap_trades': ct, 'cap_streak': cs}

def _int(v, hi, name):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('%s must be a whole number' % name)
    try: f = float(v)
    except ValueError: raise ValueError('%s must be a whole number' % name)
    if f != int(f) or f < 0 or f > hi: raise ValueError('%s must be a whole number from 0 to %d (0 = use the default)' % (name, hi))
    return int(f)

def save(uid, max_trades=None, streak=None):
    """Save one or both numbers. Raises ValueError (nothing is saved) on bad input. Returns view(uid)."""
    mt = _int(max_trades, MAX_TRADES, 'Max trades a day') if max_trades is not None else None
    ks = _int(streak, MAX_STREAK, 'Loss streak stop') if streak is not None else None
    if mt is None and ks is None: raise ValueError('Nothing to save')
    if not uid:
        if mt is not None: st.put('max_trades_day', mt)
        if ks is not None: st.put('max_losing_streak', ks)
    else:
        m = _mine(uid)
        if mt is not None: m['mt'] = mt
        if ks is not None: m['ks'] = ks
        st.put('lim:' + uid, json.dumps(m))
    return view(uid)
