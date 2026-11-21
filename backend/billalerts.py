"""Section N3: billing alerts that are not tied to one request.
Plan ends in 3 days (kind 42), plan ends tomorrow (43), plan ended (44). run() is one timed job in backend/alerts.py (every 10 minutes while the server is awake).
Each message is sent once per person per plan end date (push key plan<kind>-<plan_until>); extending a plan gives a new end date, so the cycle starts again.
Payment alerts (38 received, 39 prompt sent, 40 not completed, 41 PayPal) are sent from backend/payments.py through push.notify_user.
Facts only: no promise of profit."""
import os, time, datetime as dt
from . import store as st

DAY = 86400
def which(left):
    """Seconds left on the plan (negative = already ended) -> push kind, or None.
    More than 3 days: nothing. 1 to 3 days: 42. Under 1 day: 43. Ended up to 2 days ago: 44. Longer ago: nothing."""
    if left > 3 * DAY: return None
    if left > DAY: return 42
    if left > 0: return 43
    if left >= -2 * DAY: return 44
    return None

def until_text(ts):
    """Plan end as '21 Nov 2026' (East Africa time, the app's own clock)."""
    return dt.datetime.fromtimestamp(int(ts), dt.timezone(dt.timedelta(hours=3))).strftime('%d %b %Y').lstrip('0')

def until_for(uid):
    r = st.q('SELECT plan_until FROM users WHERE uid=?', (uid,), True)
    return until_text(r['plan_until']) if r and r['plan_until'] else ''

def run(now=None, send=None):
    """Send the plan-ending alerts that are due. Returns how many phones were reached. Never raises. Admins have no plan end, so they get none."""
    n = 0
    try:
        from . import push
        from .pushcopy import compose
        send = send or push.send
        now = int(now or time.time())
        admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}
        rows = st.q('SELECT DISTINCT u.uid AS uid,u.email AS email,u.plan_until AS pu FROM users u JOIN push_tokens t ON t.uid=u.uid WHERE u.plan_until>? AND u.plan_until<=?', (now - 2 * DAY, now + 3 * DAY))
        for r in rows:
            if (r['email'] or '').lower() in admins: continue
            k = which(int(r['pu']) - now)
            if not k: continue
            try:
                t, b, i = compose(k, until=until_text(r['pu']))
                sent, _ = send(r['uid'], k, b, t, 'plan%d-%d' % (k, int(r['pu'])), img=i); n += sent
            except Exception as e: print('[billalerts] failed', r['uid'], e)
    except Exception as e: print('[billalerts] run failed', e)
    return n
