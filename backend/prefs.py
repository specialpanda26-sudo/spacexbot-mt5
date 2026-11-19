"""Per-person trading choices the SERVER enforces (saved in kv 'pref:<uid>', uid '' = the owner's own bot).
  strategies : names the person allows. Empty = all of them (normal confluence).
  alone      : True = any ONE allowed strategy may trade by itself (use with a short list, or one name = 'use only this strategy').
  min_conf   : how many strategies must agree, 1..5. 0 = use the owner's setting.
  entries    : entries opened per setup, 1..ceiling. 0 = use the owner's setting (multi.py).
  scale      : True = the bot may open MORE entries (up to `entries`) only while its recent setups are winning (see scale.py).
The person can only choose things the owner's ceiling allows. Nothing here claims more entries make more money: they share one trade's risk."""
import json
from . import store as st, limits

def _raw(uid):
    try: j = json.loads(st.get('pref:' + (uid or '')) or '{}')
    except (TypeError, ValueError): j = {}
    return j if isinstance(j, dict) else {}

def _known():
    from . import strategies as S
    return [f.__name__ for f in S.ALL]

def get(uid=''):
    j = _raw(uid); ok = set(_known())
    return {'strategies': [x for x in (j.get('strategies') or []) if x in ok], 'alone': j.get('alone') is True,
            'min_conf': _i(j.get('min_conf'), 0, 5), 'entries': min(_i(j.get('entries'), 0, 10), limits.ceiling()), 'scale': j.get('scale') is True}

def _i(v, lo, hi):
    try: return max(lo, min(hi, int(float(v))))
    except (TypeError, ValueError): return lo

def save(uid, d):
    """Validate and save. Raises ValueError (nothing saved) on bad input. Returns get(uid)."""
    if not isinstance(d, dict): raise ValueError('Send the choices as an object')
    cur = _raw(uid); ok = set(_known())
    if 'strategies' in d:
        s = d['strategies']
        if not isinstance(s, list) or len(s) > 40 or any(not isinstance(x, str) for x in s): raise ValueError('strategies must be a list of names')
        bad = [x for x in s if x not in ok]
        if bad: raise ValueError('Unknown strategy: %s' % bad[0][:30])
        cur['strategies'] = list(dict.fromkeys(s))
    for k, hi in (('min_conf', 5), ('entries', min(10, limits.ceiling()))):
        if k in d:
            v = d[k]
            if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('%s must be a whole number' % k)
            try: f = float(v)
            except ValueError: raise ValueError('%s must be a whole number' % k)
            if f != int(f) or f < 0 or f > hi: raise ValueError('%s must be a whole number from 0 to %d (0 = use the default)' % (k, hi))
            cur[k] = int(f)
    for k in ('alone', 'scale'):
        if k in d:
            if not isinstance(d[k], bool): raise ValueError('%s must be true or false' % k)
            cur[k] = d[k]
    st.put('pref:' + (uid or ''), json.dumps(cur))
    return get(uid)

def apply(uid, off, solo, min_conf):
    """-> (off, solo, min_conf) after this person's choices. Only ever NARROWS what the owner allows: an owner-off strategy stays off."""
    p = get(uid); off = set(off); solo = set(solo)
    if p['strategies']:
        off |= set(_known()) - set(p['strategies'])
        if p['alone']: solo |= set(p['strategies']) - off
    if p['min_conf']: min_conf = p['min_conf']
    return off, solo, min_conf
