"""C3: the road to Real. Real money opens after ALL lessons (backend/course.py) AND `practice_trades_needed` closed trades (owner setting, default 5, 0 to 100).
Demo is always open. The owner/admins and the owner's own EA (uid '') are exempt. Milestones are worked out from real data, nothing is stored except what the person has already seen (kv 'pathseen:<uid>').
This file must not import risk (risk imports it)."""
import os, json
from . import store as st, course

DEFAULT_NEEDED = 5

def needed():
    """Practice trades required, 0 to 100. A bad value falls back to 5."""
    try: n = int(float(st.get('practice_trades_needed')))
    except (TypeError, ValueError): return DEFAULT_NEEDED
    return n if 0 <= n <= 100 else DEFAULT_NEEDED

def exempt(uid, admin=False):
    """The owner side never has to walk the road: the owner's own EA (uid ''), a signed-in admin, or an email in ADMIN_EMAILS."""
    if admin or not uid: return True
    r = st.q('SELECT email FROM users WHERE uid=?', (uid,), True)
    adm = {e.strip().lower() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()}
    return bool(r) and (r['email'] or '').strip().lower() in adm

def closed(uid):
    """Closed trades of this person. Entries opened together for one setup count once."""
    return st.q("SELECT COUNT(DISTINCT COALESCE(grp,id)) n FROM signals WHERE status='closed' AND COALESCE(uid,'')=?", (uid,), True)['n']

def _lessons_ok(uid): return (not course.required()) or course.complete(uid)

def real_allowed(uid, admin=False):
    if exempt(uid, admin): return True
    return _lessons_ok(uid) and closed(uid) >= needed()

def why(uid, admin=False):
    """Plain words for what is still missing, or '' when Real is open."""
    if real_allowed(uid, admin): return ''
    bits = []
    left = len(course.LESSONS) - len(course.done(uid))
    if not _lessons_ok(uid): bits.append('finish the %d lesson%s still open' % (left, '' if left == 1 else 's'))
    n = needed() - closed(uid)
    if n > 0: bits.append('close %d more practice trade%s' % (n, '' if n == 1 else 's'))
    return 'Real trading is not open yet. To unlock it: %s. Demo trading is open any time.' % ' and '.join(bits)

def _has_broker(uid):
    if not uid: return False
    if st.q("SELECT 1 FROM broker_links WHERE uid=? AND status='verified'", (uid,), True): return True
    r = st.q('SELECT 1 FROM links WHERE uid=?', (uid,), True)
    return bool(r)

M = [  # id, title, text, art
 ('first', 'First lesson done', 'You passed your first lesson. Nice start.', 'yay'),
 ('three', 'Halfway through the lessons', 'Three lessons done. Half way there.', 'doc'),
 ('lessons', 'All lessons done', 'You know the basics: signals, risk and safety rules.', 'shield'),
 ('broker', 'Broker connected', 'Your bot has a place to trade (demo or real).', 'plug'),
 ('trade1', 'First trade closed', 'Your first trade is closed. Look at it in the Journal.', 'coin'),
 ('practice', 'Practice finished', 'You closed all the practice trades asked of you.', 'ok'),
 ('real', 'Real trading unlocked', 'The road is finished. Real mode is open: type REAL to switch, and check which mode you are in first.', 'rocket'),
 ('ten', '10 trades closed', 'A record of ten closed trades. Learn from each one, wins and losses.', 'lock'),
]

def _done(uid):
    d = len(course.done(uid)); c = closed(uid)
    return {'first': d >= 1, 'three': d >= 3, 'lessons': d >= len(course.LESSONS), 'broker': _has_broker(uid), 'trade1': c >= 1,
            'practice': (c >= needed()) if needed() > 0 else d >= len(course.LESSONS),          # nothing to practise: it opens with the lessons
            'real': real_allowed(uid), 'ten': c >= 10}

def _seen(uid):
    try: s = json.loads(st.get('pathseen:%s' % uid) or '[]')
    except ValueError: s = []
    return [x for x in s if isinstance(x, str)] if isinstance(s, list) else []

def view(uid, admin=False):
    dn = _done(uid); sn = set(_seen(uid)); c = closed(uid); nd = needed(); ld = len(course.done(uid)); tot = len(course.LESSONS)
    ms = [{'id': i, 'title': t, 'text': x, 'art': a, 'done': dn[i], 'new': dn[i] and i not in sn} for i, t, x, a in M]
    ex = exempt(uid, admin)
    return {'exempt': ex, 'real_open': real_allowed(uid, admin), 'why': why(uid, admin),
            'lessons': {'done': ld, 'total': tot, 'required': course.required()},
            'practice': {'done': min(c, nd) if nd else 0, 'needed': nd, 'closed': c},
            'milestones': ms, 'earned': sum(1 for m in ms if m['done']), 'total': len(ms)}

def seen(uid):
    """Mark every milestone reached so far as seen (the pop-up shows once). Returns the new view's earned list."""
    dn = _done(uid); st.put('pathseen:%s' % uid, json.dumps(sorted(k for k, v in dn.items() if v)))
    return [k for k, v in dn.items() if v]
