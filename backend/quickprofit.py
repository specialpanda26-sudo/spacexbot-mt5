"""QP1: 'Take small profits'. One simple choice per person, saved in kv 'qp:<uid>' (uid '' = the owner's own bot).
  on  : True = every position the bot opened for this person is closed by itself as soon as its OWN profit reaches `usd`.
  usd : the profit that closes one position, in account money (0.05 to 1000). Default 0.5.
It works per position, so a trade with 6 entries closes each entry the moment that entry shows the profit, not the whole group together.
The stop loss stays on every position. A position that never reaches the profit is not touched by this switch.
The server only stores the choice and hands it out. The MT5 bridge (it checks twice a second) and the Deriv loop do the closing.
Phone-only mode cannot auto-close, it only sends signals. The owner's 'I close the profits myself' switch (manual_close.py) wins: while it is on, this switch pauses.
Nothing here claims it makes more money: small wins taken early leave the losers to run to their stop loss, and the spread and commission come out of a small profit."""
import json
from . import store as st, manual_close

USD_LO, USD_HI, USD_DEF = 0.05, 1000.0, 0.5
KEYS = ('on', 'usd')


def _raw(uid):
    try: j = json.loads(st.get('qp:' + (uid or '')) or '{}')
    except (TypeError, ValueError): j = {}
    return j if isinstance(j, dict) else {}


def _usd(v):
    if isinstance(v, bool): return USD_DEF
    try: x = float(v)
    except (TypeError, ValueError, OverflowError): return USD_DEF
    if x != x or x < USD_LO or x > USD_HI: return USD_DEF
    return round(x, 2)


def get(uid=''):
    """The person's choices, always valid (a bad saved number falls back to 0.5)."""
    j = _raw(uid)
    return {'on': j.get('on') is True, 'usd': _usd(j.get('usd'))}


def save(uid, d):
    """Validate and save. Raises ValueError (nothing saved) on bad input. Returns get(uid)."""
    if not isinstance(d, dict): raise ValueError('Send the choices as an object')
    cur = _raw(uid); new = {}
    if 'on' in d:
        if not isinstance(d['on'], bool): raise ValueError('on must be true or false')
        new['on'] = d['on']
    if 'usd' in d:
        v = d['usd']
        if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('Profit to take must be a number')
        try: f = float(v)
        except ValueError: raise ValueError('Profit to take must be a number')
        if f != f or f < USD_LO or f > USD_HI: raise ValueError('Profit to take must be from %g to %g' % (USD_LO, USD_HI))
        new['usd'] = round(f, 2)
    cur.update(new)
    st.put('qp:' + (uid or ''), json.dumps(cur))
    return get(uid)


def paused(uid=''):
    """True when the person switched it on but the owner's 'I close the profits myself' switch is holding it back."""
    return get(uid)['on'] and bool(manual_close.on(uid or ''))


def usd_for(uid=''):
    """What the closers use: the profit that closes one position, or 0.0 when it is off (or paused)."""
    g = get(uid)
    if not g['on'] or manual_close.on(uid or ''): return 0.0
    return g['usd']


def view(uid=''):
    """What the app shows."""
    return {'settings': get(uid), 'active': usd_for(uid) > 0, 'paused': paused(uid), 'min': USD_LO, 'max': USD_HI}
