"""Account profile: validation + storage. The browser never decides who a user is; the signed-in token does."""
import re, json, sqlite3, datetime as dt
from . import store as st

EXP = {'Beginner', 'Intermediate', 'Advanced'}; GOAL = {'Learn', 'Steady', 'Active'}; RISK = {'Low', 'Medium', 'High'}
GENDER = {'Female', 'Male', 'Non-binary', 'Prefer not to say'}
NOTIF = ('trade', 'risk', 'news', 'daily', 'tips', 'system', 'billing')
DEF_NOTIF = {'trade': 1, 'risk': 1, 'news': 1, 'daily': 1, 'tips': 1, 'system': 1, 'billing': 1}

def age_of(dob):
    y, m, d = map(int, dob.split('-')); t = dt.date.today()
    return t.year - y - ((t.month, t.day) < (m, d))

def view(uid):
    r = st.q('SELECT * FROM users WHERE uid=?', (uid,), True) or {}
    try: n = {**DEF_NOTIF, **json.loads(r.get('notif') or '{}')}
    except ValueError: n = dict(DEF_NOTIF)
    return {'name': r.get('name') or '', 'created': r.get('created') or 0, 'onboarded': r.get('onboarded') != 0, 'dob': r.get('dob'), 'gender': r.get('gender'),
            'age': age_of(r['dob']) if r.get('dob') else None,
            'prof': {'user': r.get('username') or '', 'phone': r.get('phone') or '', 'country': r.get('country') or '', 'bio': r.get('bio') or '',
                     'exp': r.get('exp_level') or '', 'goal': r.get('goal') or '', 'risk': r.get('risk_pref') or '', 'av': r.get('av') or 0, 'n': n}}

def _s(v, mx): return str(v if v is not None else '').strip()[:mx]

def update(uid, j):
    """Only keys present in j change. Raises ValueError(message) on bad input."""
    sets = {}
    if 'name' in j:
        v = _s(j['name'], 60)
        if len(v) < 2: raise ValueError('Enter your full name.')
        sets['name'] = v
    if 'user' in j:
        v = _s(j['user'], 20)
        if v and not re.fullmatch(r'[A-Za-z0-9_]{3,20}', v): raise ValueError('Username: 3 to 20 letters, numbers or underscores.')
        sets['username'] = v.lower() or None
    if 'phone' in j:
        v = _s(j['phone'], 18)
        if v and not re.fullmatch(r'\+?[0-9 ()-]{7,18}', v): raise ValueError('Enter a valid phone number, for example +254 700 000 000.')
        sets['phone'] = v
    if 'country' in j: sets['country'] = _s(j['country'], 60)
    if 'bio' in j: sets['bio'] = _s(j['bio'], 120)
    for key, col, ok in (('exp', 'exp_level', EXP), ('goal', 'goal', GOAL), ('risk', 'risk_pref', RISK)):
        if key in j:
            v = _s(j[key], 20)
            if v and v not in ok: raise ValueError('Bad ' + key)
            sets[col] = v
    if 'av' in j:
        try: a = int(j['av'])
        except (TypeError, ValueError): raise ValueError('Bad avatar')
        if not 0 <= a <= 5: raise ValueError('Bad avatar')
        sets['av'] = a
    if 'n' in j:
        if not isinstance(j['n'], dict): raise ValueError('Bad notifications')
        cur = view(uid)['prof']['n']
        sets['notif'] = json.dumps({k: (1 if j['n'].get(k) else 0) if k in j['n'] else (1 if cur.get(k) else 0) for k in NOTIF})
    if j.get('onboarded'): sets['onboarded'] = 1          # one way only: it can be set, never switched back off
    if 'gender' in j:
        if str(j['gender']) not in GENDER: raise ValueError('Pick an option for gender.')
        sets['gender'] = str(j['gender'])
    if 'dob' in j:
        try: d = dt.date.fromisoformat(str(j['dob']))
        except ValueError: raise ValueError('Enter a valid date of birth.')
        a = age_of(d.isoformat())
        if a < 18: raise ValueError('You must be 18 or older to use spaceXBot.')
        if a > 100: raise ValueError('Enter a valid date of birth.')
        sets['dob'] = d.isoformat()
    if not sets: return
    cols = ','.join(k + '=?' for k in sets)          # keys come from the whitelist above, never from the request
    try: st.x(f'UPDATE users SET {cols} WHERE uid=?', (*sets.values(), uid))
    except sqlite3.IntegrityError: raise ValueError('That username is taken.')

def erase(uid):
    """Delete the person. Payment rows stay (accounting) but lose the link to a profile."""
    st.x('DELETE FROM users WHERE uid=?', (uid,))
