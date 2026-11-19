"""Group profit target and group loss limit (Section 3, server side). One simple set of choices per person, saved in kv 'gcap:<uid>' (uid '' = the owner's own bot).
  on          : True = the rules below apply to every GROUP of entries (a burst group, or a normal multi-entry setup of 2 or more).
  target_usd  : close the WHOLE group when its total profit reaches this many USD. 0 = no group target (a burst group then keeps its own per-entry target).
  loss_pct    : close the WHOLE group when its total loss reaches this percent of the account balance (taken when the group opens). 0 = no group loss limit.
The number of positions is NOT here: it is the person's existing 'entries' choice (prefs.py), so the card in the app (Section 5) can show all three in one place.
A single trade (a group of one) is not a group: it keeps its own stop loss and take profit only.
The server only stores and hands out the rules. The MT5 bridge does the closing (Section 4); phone-only mode cannot auto-close, it only sends signals.
Nothing here claims it makes more money. A loss limit controls how much a bad group can lose, nothing more."""
import json, time
from . import store as st

DEF = {'on': False, 'target_usd': 0.0, 'loss_pct': 0.0}
KEYS = tuple(DEF)
USD_LO, USD_HI = 0.05, 1000.0
PCT_LO, PCT_HI = 0.1, 50.0
NO_TARGET_EACH = 1000000.0        # an old EA that only knows 'each' would close a group at once if each were 0, so a group with no target sends a target it can never reach


def _raw(uid):
    try: j = json.loads(st.get('gcap:' + (uid or '')) or '{}')
    except (TypeError, ValueError): j = {}
    return j if isinstance(j, dict) else {}


def _num(v, lo, hi, d):
    if isinstance(v, bool): return d
    try: x = float(v)
    except (TypeError, ValueError, OverflowError): return d
    if x != x: return d
    return d if x == 0 else round(max(lo, min(hi, x)), 2)


def get(uid=''):
    """The person's choices, always valid (a bad saved value falls back to off)."""
    j = _raw(uid)
    return {'on': j.get('on') is True, 'target_usd': _num(j.get('target_usd'), USD_LO, USD_HI, 0.0), 'loss_pct': _num(j.get('loss_pct'), PCT_LO, PCT_HI, 0.0)}


def _check(v, lo, hi, name, unit):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('%s must be a number (0 = off)' % name)
    try: f = float(v)
    except ValueError: raise ValueError('%s must be a number (0 = off)' % name)
    if f != f or f in (float('inf'), float('-inf')): raise ValueError('%s must be a number (0 = off)' % name)
    if f != 0 and (f < lo or f > hi): raise ValueError('%s must be 0 (off) or from %g to %g %s' % (name, lo, hi, unit))
    return round(f, 2)


def save(uid, d):
    """Validate and save. Raises ValueError (nothing saved) on bad input. Returns get(uid)."""
    if not isinstance(d, dict): raise ValueError('Send the choices as an object')
    cur = _raw(uid); new = {}
    if 'on' in d:
        if not isinstance(d['on'], bool): raise ValueError('on must be true or false')
        new['on'] = d['on']
    if 'target_usd' in d: new['target_usd'] = _check(d['target_usd'], USD_LO, USD_HI, 'Group profit target', 'USD')
    if 'loss_pct' in d: new['loss_pct'] = _check(d['loss_pct'], PCT_LO, PCT_HI, 'Group loss limit', 'percent of the account')
    cur.update(new)
    st.put('gcap:' + (uid or ''), json.dumps(cur))
    return get(uid)


def rules(uid, n):
    """-> {'tgt': USD or 0, 'loss': percent or 0} for a new group of n entries, or None when no group rule applies (off, a single trade, or both numbers 0)."""
    g = get(uid)
    if not g['on'] or int(n or 0) < 2: return None
    if g['target_usd'] <= 0 and g['loss_pct'] <= 0: return None
    return {'tgt': g['target_usd'], 'loss': g['loss_pct']}


def mark(grp, uid, n, now=None):
    """A normal multi-entry setup (not a burst) that the group rules apply to: remember it as a group (kv 'bg:<id>', kind 'multi') so the EA gets it as ONE basket.
    Returns True when marked."""
    r = rules(uid, n)
    if not r: return False
    st.put('bg:%d' % int(grp), json.dumps({'k': 'multi', 'n': int(n), 'each': 0, 'gb': 0, 'tgt': r['tgt'], 'loss': r['loss'], 't': int(now or time.time())}))
    return True


def each_for(m, n=None):
    """The per-entry target an EA that only knows 'each' will use: the group target shared out, or a target it cannot reach when the group has none."""
    n = int(n or (m or {}).get('n') or 1); tgt = float((m or {}).get('tgt') or 0)
    if tgt > 0: return round(tgt / max(1, n), 4)
    if (m or {}).get('k') == 'multi': return NO_TARGET_EACH
    return (m or {}).get('each')


def view(uid=''):
    """What the app shows: the three choices (positions come from the person's existing 'entries' choice, 0 = the owner's default)."""
    from . import prefs
    return {'settings': get(uid), 'positions': prefs.get(uid)['entries']}
