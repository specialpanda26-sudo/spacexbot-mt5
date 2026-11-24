"""Per-person trading limits that the SERVER enforces: max trades a day and the loss-streak stop.
Before this, the two boxes in the app (Session limits card) only changed the page on the phone; the server used one global setting for everybody.
Rules:
 - Owner (uid ''): the boxes write the global settings max_trades_day and max_losing_streak (same keys the admin settings already use).
 - A subscriber saves their own numbers, kept per person. 0 or empty = use the owner's setting.
 - A subscriber can only be STRICTER than the owner, never looser: trades = the smaller of the two (when the owner has a cap), streak the same.
   The owner's 0 means 'no limit' for trades and 'switched off' for the streak stop, so then the subscriber's own number applies on its own.
The risk gate (risk.global_gate) asks trades(uid) and streak(uid) every time, so a change applies on the very next signal."""
import json, os
from . import store as st

MAX_TRADES, MAX_STREAK, MAX_OPEN_HI = 100, 10, 50          # MAX_OPEN_HI: the most the owner can ever set as the ceiling

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
    from . import userlim          # RS5: the person's own number; the owner's setting is for the owner's own bot
    return int(userlim.val(uid, 'max_trades'))

def streak(uid=''):
    """Effective loss-streak stop for the gate. 0 = off."""
    from . import userlim          # RS5
    return int(userlim.val(uid, 'streak'))

UNLIMITED = 1000          # OC1: what 'no limit' counts as in the room sums

def _owner(uid):
    """OC1: the owner's own scope ('') or a signed-in admin's uid (the owner's Deriv / Binance bot runs under the owner's own uid)."""
    if not uid: return True
    r = st.q('SELECT email FROM users WHERE uid=?', (uid,), True)
    adm = {e.strip().lower() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()}
    return bool(r) and (r['email'] or '').lower() in adm

def no_cap(uid=''):
    """OC1: True when the owner switched 'No limit on open trades' on (setting no_open_cap = 1). It applies to the OWNER only; every subscriber keeps the ceiling."""
    return st.get('no_open_cap') == '1' and _owner(uid)

def ceiling():
    """R4: the highest 'positions at once' a subscriber may pick. The owner sets it (setting max_open_ceiling, default 6). Never below 1."""
    return max(1, min(MAX_OPEN_HI, _g('max_open_ceiling') or 6))

def max_open(uid=''):
    """R4: how many positions the bot may hold at once for this person. The owner's own scope uses the global setting max_open. A subscriber uses the number
    they picked (kept per person, never above the owner's ceiling, even if the ceiling was lowered later); with no pick they get the owner's default."""
    if no_cap(uid): return UNLIMITED          # OC1
    base = max(1, _g('max_open') or 3)
    try:
        from . import automode
        if automode.on(): base = max(base, automode.positions())          # auto mode: always room for one whole trade
    except Exception: pass
    if not uid or _owner(uid): return base
    from . import userlim          # RS5: the person's own number (0 = off = the owner's server ceiling)
    own = int(userlim.val(uid, 'max_open'))
    return min(own, ceiling()) if own > 0 else ceiling()

def view(uid=''):
    """What the app shows: the person's OWN saved numbers (0 = none) and the owner's caps."""
    mo = {'max_open_unlimited': no_cap(uid), 'max_open': _num(_mine(uid).get('mo')) if uid else max_open(''), 'max_open_now': max_open(uid), 'max_open_default': max(1, _g('max_open') or 3), 'max_open_ceiling': ceiling()}
    if not uid: return dict({'max_trades': _g('max_trades_day'), 'streak': _g('max_losing_streak'), 'cap_trades': 0, 'cap_streak': 0}, **mo)
    m = _mine(uid); ct, cs = _g('max_trades_day'), _g('max_losing_streak')
    return dict(mo, **{'max_trades': _num(m.get('mt')), 'streak': _num(m.get('ks')), 'cap_trades': 0, 'cap_streak': 0})          # RS5: the owner's numbers no longer cut a person's own

def _int(v, hi, name):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('%s must be a whole number' % name)
    try: f = float(v)
    except ValueError: raise ValueError('%s must be a whole number' % name)
    if f != int(f) or f < 0 or f > hi: raise ValueError('%s must be a whole number from 0 to %d (0 = use the default)' % (name, hi))
    return int(f)

def _open_pick(v, hi):
    """A pick for 'positions at once': a whole number from 1 to hi, or 0 = use the owner's default."""
    if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('Positions at once must be a whole number')
    try: f = float(v)
    except ValueError: raise ValueError('Positions at once must be a whole number')
    if f != f or f != int(f) or f < 0 or f > hi: raise ValueError('Positions at once must be a whole number from 1 to %d (0 = use the default)' % hi)
    return int(f)

def save(uid, max_trades=None, streak=None, max_open=None, ceiling=None):
    """Save one or more numbers. Raises ValueError (nothing is saved) on bad input. Returns view(uid).
    max_open: a subscriber picks 1..ceiling (0 = the owner's default); the owner sets the global default 1..50. ceiling: owner only (1..50)."""
    mt = _int(max_trades, MAX_TRADES, 'Max trades a day') if max_trades is not None else None
    ks = _int(streak, MAX_STREAK, 'Loss streak stop') if streak is not None else None
    mo = _open_pick(max_open, globals()['ceiling']() if uid else MAX_OPEN_HI) if max_open is not None else None
    if mo == 0 and not uid: raise ValueError('Positions at once must be a whole number from 1 to %d' % MAX_OPEN_HI)
    cl = None
    if ceiling is not None:
        if uid: raise ValueError('Only the owner can set the ceiling')
        cl = _open_pick(ceiling, MAX_OPEN_HI)
        if cl < 1: raise ValueError('The ceiling must be 1 or more')
    if mt is None and ks is None and mo is None and cl is None: raise ValueError('Nothing to save')
    if not uid:
        if mo is not None: st.put('max_open', mo)
        if cl is not None: st.put('max_open_ceiling', cl)
        if mt is not None: st.put('max_trades_day', mt)
        if ks is not None: st.put('max_losing_streak', ks)
    else:
        m = _mine(uid)
        if mt is not None: m['mt'] = mt
        if ks is not None: m['ks'] = ks
        if mo is not None:
            if mo: m['mo'] = mo
            else: m.pop('mo', None)
        st.put('lim:' + uid, json.dumps(m))
    return view(uid)
