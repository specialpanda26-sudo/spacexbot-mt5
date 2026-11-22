"""Auto-cycle (CY1, server side): the choices for 'close the whole group at its profit target, then open the next group straight away'.
One simple set of choices per person, saved in kv 'cycle:<uid>' (uid '' = the owner's own bot). It is OFF until the person switches it on.
  on          : True = when a group reaches its profit target and is closed, the bot opens a NEW group of the same size without waiting for a new signal.
  max_per_day : the most new groups it may open this way in one day (1..100, default 10). A safety stop, so it can never loop forever.
It builds on two things that already exist and does not copy them: the group profit target (groupcap.py, e.g. 0.70 USD for the whole group) and the
number of entries per setup (prefs.py, e.g. 6). The cycle is active only when the group target is on and above 0 and the group has 2 or more entries.
Only a group that closed at its PROFIT target starts the next one. A group that ended on a stop loss, a loss limit or by hand never does.
The server only stores and hands out the rules (this section). The Deriv engine does the closing and reopening (CY2); the MT5 bridge and Binance follow (CY3).
Nothing here claims it makes more money: repeating trades also repeats losses."""
import json
from . import store as st, groupcap

DEF = {'on': False, 'max_per_day': 10}
KEYS = tuple(DEF)
MAX_LO, MAX_HI = 1, 100


def _raw(uid):
    try: j = json.loads(st.get('cycle:' + (uid or '')) or '{}')
    except (TypeError, ValueError): j = {}
    return j if isinstance(j, dict) else {}


def _day_cap(v):
    if isinstance(v, bool): return DEF['max_per_day']
    try: x = int(float(v))
    except (TypeError, ValueError, OverflowError): return DEF['max_per_day']
    return DEF['max_per_day'] if not MAX_LO <= x <= MAX_HI else x


def get(uid=''):
    """The person's choices, always valid (a bad saved value falls back to the default)."""
    j = _raw(uid)
    return {'on': j.get('on') is True, 'max_per_day': _day_cap(j.get('max_per_day', DEF['max_per_day']))}


def save(uid, d):
    """Validate and save. Raises ValueError (nothing saved) on bad input. Returns get(uid)."""
    if not isinstance(d, dict): raise ValueError('Send the choices as an object')
    cur = _raw(uid); new = {}
    if 'on' in d:
        if not isinstance(d['on'], bool): raise ValueError('on must be true or false')
        new['on'] = d['on']
    if 'max_per_day' in d:
        v = d['max_per_day']
        if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('New groups per day must be a whole number from %d to %d' % (MAX_LO, MAX_HI))
        try: f = float(v)
        except ValueError: raise ValueError('New groups per day must be a whole number from %d to %d' % (MAX_LO, MAX_HI))
        if f != f or f != int(f) or not MAX_LO <= f <= MAX_HI: raise ValueError('New groups per day must be a whole number from %d to %d' % (MAX_LO, MAX_HI))
        new['max_per_day'] = int(f)
    cur.update(new)
    st.put('cycle:' + (uid or ''), json.dumps(cur))
    return get(uid)


def rules(uid, n):
    """-> {'tgt': USD for the whole group, 'n': entries, 'max_per_day': int} for a group of n entries, or None when the cycle does not apply
    (switched off, a single trade, or no group profit target to cycle on)."""
    c = get(uid)
    if not c['on']: return None
    g = groupcap.rules(uid, n)
    if not g or g['tgt'] <= 0: return None
    return {'tgt': g['tgt'], 'n': int(n), 'max_per_day': c['max_per_day']}


def why_not(uid, n):
    """Plain words for the app: why the cycle is not running although it is switched on. '' when it is running or switched off."""
    c = get(uid)
    if not c['on']: return ''
    g = groupcap.get(uid)
    if not g['on']: return 'Switch on the group profit target first. The cycle starts a new group each time the target is reached.'
    if g['target_usd'] <= 0: return 'Set a group profit target above 0 USD. The cycle needs it to know when to close.'
    if int(n or 0) < 2: return 'Choose 2 or more entries per setup. A single trade is not a group.'
    return ''


def view(uid=''):
    """What the app shows: the cycle choices, the group target it builds on, the entries per setup, and a plain-words reason when it is not running."""
    gv = groupcap.view(uid); pos = gv['positions']
    return {'settings': get(uid), 'group': gv['settings'], 'positions': pos, 'note': why_not(uid, pos if pos else 2),
            'limits': {'max_per_day': [MAX_LO, MAX_HI]}}
