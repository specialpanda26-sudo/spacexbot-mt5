"""Losing-streak pause: ask the admin to let me continue (per person).
The pause itself is unchanged (risk.streak_state: N losses in a row stop NEW trades for STREAK_COOLDOWN_H hours). This adds:
 - request(uid): a person whose bot is paused by the streak asks the admin to let it trade again. One request per pause; kv 'streakreq:<uid>'.
 - decide(uid, approve, note): the admin reviews. Approve = the streak counter for that person starts again from now (kv 'streakok:<uid>'; only losses
   AFTER that moment count), so the bot trades again at once. Decline = the pause stays until it ends by itself; the person cannot ask again for the SAME pause.
 - Nothing else is loosened: daily and weekly loss limits, max open trades, Real-mode gates all still apply. Owner scope is refused (the owner edits the limits directly).
Request states: pending, approved, declined. 'ended' is shown (not stored) when a pending pause finished by itself.
Nothing here claims it makes money: it only lets a person, with the admin's OK, trade before the cooldown ends."""
import json, time
from . import store as st, risk, limits

NOTE_MAX = 200


def _key(uid): return 'streakreq:' + uid


def _get(uid):
    try: j = json.loads(st.get(_key(uid)) or 'null')
    except (TypeError, ValueError): j = None
    return j if isinstance(j, dict) and j.get('status') in ('pending', 'approved', 'declined') else None


def _put(uid, r): st.put(_key(uid), json.dumps(r))


def _person(uid): return bool(uid) and not limits._owner(uid)


def status(uid, now=None):
    """What the card needs: is this person paused, why (the last losses, in dollars), when it ends by itself, and their request."""
    now = now or time.time(); s = risk.streak_state(uid, now) if _person(uid) else None
    r = _get(uid) if _person(uid) else None
    if r and r['status'] == 'pending' and not s: r = dict(r, status='ended')
    return {'owner': not _person(uid), 'paused': bool(s), 'k': s['k'] if s else 0, 'until': int(s['until']) if s else 0, 'since': int(s['since']) if s else 0,
            'losses': [round(p, 2) for p in s['pnls']] if s else [], 'request': r}


def request(uid, now=None):
    """The person asks to continue. ValueError (nothing changed) when not paused, already asked, or the admin already declined THIS pause."""
    now = now or time.time()
    if not _person(uid): raise ValueError('The owner changes the loss-streak limit in the admin settings.')
    s = risk.streak_state(uid, now)
    if not s: raise ValueError('Your bot is not paused by a losing streak right now.')
    r = _get(uid)
    if r and r['status'] == 'pending' and r.get('since') == s['since']: raise ValueError('Your request is already with the admin.')
    if r and r['status'] == 'declined' and r.get('since') == s['since']: raise ValueError('The admin declined this one. The pause ends by itself at the time shown.')
    _put(uid, {'status': 'pending', 't': int(now), 'k': s['k'], 'since': s['since'], 'losses': [round(p, 2) for p in s['pnls']], 'note': ''})
    return status(uid, now)


def decide(uid, approve, note='', now=None):
    """Admin only (the route checks). Raises ValueError when there is nothing pending for this person or the pause already ended."""
    now = now or time.time(); r = _get(uid) if uid else None
    if not r or r['status'] != 'pending': raise ValueError('There is no waiting request from this person.')
    if not risk.streak_state(uid, now): raise ValueError('That pause already ended by itself.')
    note = (note if isinstance(note, str) else '').strip()[:NOTE_MAX]
    if approve is True: st.put('streakok:' + uid, int(now))
    _put(uid, dict(r, status='approved' if approve is True else 'declined', decided=int(now), note=note))
    return listing(now)


def listing(now=None):
    """For the admin: requests still waiting (oldest first) and the last decisions."""
    now = now or time.time(); wait, done = [], []
    for row in st.q("SELECT k,v FROM kv WHERE k LIKE 'streakreq:%'"):
        uid = row['k'][len('streakreq:'):]; r = _get(uid)
        if not r or not _person(uid): continue
        u = st.q('SELECT email,name FROM users WHERE uid=?', (uid,), True) or {}
        item = dict(r, uid=uid, email=u.get('email') or '', name=u.get('name') or '')
        if r['status'] == 'pending':
            if risk.streak_state(uid, now): wait.append(item)
        else: done.append(item)
    wait.sort(key=lambda x: x['t']); done.sort(key=lambda x: x.get('decided', 0), reverse=True)
    return {'waiting': wait, 'recent': done[:10]}
