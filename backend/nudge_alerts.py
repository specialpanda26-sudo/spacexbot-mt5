"""Section N6d: setup nudges, push kinds 45 to 49. One gentle reminder per step, ONCE EVER per person (push_log key n<kind>-<uid>), only to a person who really has not done the step.
push.allowed already limits nudges to ONE a day per person, so a person with two open steps gets the second one the next day.
45 verify your email (the server does not store 'verified', so app.py's /api/me tells seen() and the nudge goes to someone who is in the app unverified),
46 connect your broker, 47 set your risk, 48 choose your alerts, 49 finish your profile. Sent only between FROM_H and TO_H EAT. Admins get none.
One job on the ONE loop in backend/alerts.py (register() below). It takes `now` so a test can fix the clock.
Tunables (assumptions, change here):"""
import time, datetime as dt
from . import store as st, push

EAT = push.EAT
FROM_H, TO_H = 9, 20            # nudges only in the daytime (EAT)
UNVERIFIED_AFTER = 2 * 3600     # 45: unverified for this long ...
UNVERIFIED_FRESH = 3600         # ... and seen in the app within this long (so someone who verified elsewhere is not nudged)
CONNECT_AFTER = 86400           # 46: a person with a plan and no broker connected, one day after sign-up
RISK_AFTER = 86400              # 47: a made MT5 key with no risk chosen, one day after it was made
ALERTS_AFTER = 2 * 86400        # 48: alerts never chosen, two days after the first phone registered
PROFILE_AFTER = 3 * 86400       # 49: profile unfinished, three days after sign-up
PROFILE_FIELDS = ('username', 'phone', 'country')
RETRY_SEC = 1800
_unv = {}; _tried = {}

def seen(uid, verified, now=None):
    """Called from /api/me. Remembers (first seen, last seen) of a person who is in the app with an unverified email; forgets them once verified."""
    now = now or time.time()
    if verified: _unv.pop(uid, None)
    else: _unv[uid] = (_unv.get(uid, (now, now))[0], now)

def _fire(uid, kind, now):
    key = 'n%d-%s' % (kind, uid)
    if now - _tried.get(key, 0) < RETRY_SEC: return False
    _tried[key] = now
    for k in [k for k, t in _tried.items() if now - t > 86400]: _tried.pop(k, None)
    push.notify_user(uid, kind, key); return True

def _connected(uid):
    """A broker is connected in some way: an MT5 key, a saved broker (Deriv), or Phone mode."""
    return bool(st.q('SELECT 1 FROM links WHERE uid=?', (uid,), True) or st.q('SELECT 1 FROM broker_links WHERE uid=?', (uid,), True)
                or (st.q('SELECT enabled FROM assist WHERE uid=?', (uid,), True) or {}).get('enabled'))

def nudge_job(now=None):
    now = now or time.time()
    if not (FROM_H <= dt.datetime.fromtimestamp(now, EAT).hour < TO_H): return
    admins = set(push.recipients(True))
    for r in st.q('SELECT u.uid AS uid,u.plan_until AS pu,u.created AS created,u.notif AS notif,u.username AS username,u.phone AS phone,u.country AS country,'
                  'MIN(t.created) AS tok FROM users u JOIN push_tokens t ON t.uid=u.uid GROUP BY u.uid,u.plan_until,u.created,u.notif,u.username,u.phone,u.country') or []:
        uid = r['uid']
        if uid in admins: continue
        age = now - (r['created'] or now); u = _unv.get(uid)
        if u and now - u[0] >= UNVERIFIED_AFTER and now - u[1] <= UNVERIFIED_FRESH: _fire(uid, 45, now)
        if (r['pu'] or 0) > now and age >= CONNECT_AFTER and not _connected(uid): _fire(uid, 46, now)
        l = st.q('SELECT risk,created FROM links WHERE uid=?', (uid,), True)
        if (r['pu'] or 0) > now and l and l.get('risk') is None and now - (l.get('created') or now) >= RISK_AFTER: _fire(uid, 47, now)
        if str(r['notif'] or '').strip() in ('', '{}', 'null') and now - (r['tok'] or now) >= ALERTS_AFTER: _fire(uid, 48, now)
        if any(not r.get(f) for f in PROFILE_FIELDS) and age >= PROFILE_AFTER: _fire(uid, 49, now)

def register():
    """Put the job on the alerts loop. Safe to call twice."""
    from . import alerts
    alerts.register_job('nudge_alerts', 1800, nudge_job)
