"""Phone notifications through Firebase Cloud Messaging (HTTP v1). Facts only: never a promise of profit, never advice.
Env: FCM_SERVICE_ACCOUNT = the service-account JSON (raw or base64). Without it every send is a quiet no-op."""
import os, time, json, base64, threading, datetime as dt
import requests
from . import store as st

CAT = ('trade', 'risk', 'news', 'daily', 'tips', 'system', 'billing')
BYPASS_CATS = {'risk', 'billing'}            # always get through quiet hours and the daily cap
BYPASS_KINDS = {27}                          # EA offline too
NUDGE_KINDS = set(range(45, 50))
_T = [
 (1,'trade','hi','Trade opened'),(2,'trade','hi','Take-profit hit'),(3,'trade','hi','Stop-loss hit'),(4,'trade','hi','Trade closed'),
 (5,'trade','hi','Stop moved to breakeven'),(6,'trade','hi','Partial close'),(7,'trade','hi','Signal found'),(8,'trade','lo','Signal skipped'),
 (9,'trade','hi','Pending order update'),(10,'trade','lo','Trade open a long time'),
 (11,'risk','hi','Daily loss limit reached'),(12,'risk','hi','Weekly loss limit reached'),(13,'risk','hi','Losing-streak pause'),(14,'risk','hi','Trading resumed'),
 (15,'risk','hi','Max open trades reached'),(16,'risk','hi','Max trades for the day reached'),(17,'risk','hi','Currency exposure limit'),(18,'risk','hi','Half of daily loss limit used'),
 (19,'news','hi','High-impact news soon'),(20,'news','hi','News lock started'),(21,'news','lo','News lock ended'),(22,'news','lo','Session opening'),
 (23,'news','hi','Large move on XAUUSD'),(24,'news','lo','Market closed'),(25,'news','lo','Spread too wide'),
 (26,'system','hi','MT5 EA connected'),(27,'system','hi','MT5 EA offline'),(28,'system','hi','EA back online'),(29,'system','lo','Server updated'),
 (30,'system','hi','Monitor mode changed'),(31,'system','hi','Account type changed'),
 (32,'daily','lo','Daily summary'),(33,'daily','lo','Weekly report'),(34,'daily','lo','Monthly report'),(35,'daily','lo','Brain update'),
 (36,'daily','lo','Winning streak'),(37,'daily','lo','Review your trades'),
 (38,'billing','hi','Payment received'),(39,'billing','hi','M-Pesa prompt sent'),(40,'billing','hi','Payment not completed'),(41,'billing','hi','PayPal payment confirmed'),
 (42,'billing','hi','Plan ends in 3 days'),(43,'billing','hi','Plan ends tomorrow'),(44,'billing','hi','Plan ended'),
 (45,'tips','lo','Verify your email'),(46,'tips','lo','Connect your MT5'),(47,'tips','lo','Set your risk'),(48,'tips','lo','Choose your alerts'),(49,'tips','lo','Finish your profile'),
 (50,'system','hi','Security notice')]
KINDS = {k: {'cat': c, 'ch': h, 'title': t} for k, c, h, t in _T}
CHANNEL = {'hi': 'sxb_high', 'lo': 'sxb_low'}
ROUTE = {'trade': '#signals', 'risk': '#home', 'news': '#home', 'daily': '#stats', 'tips': '#profile', 'system': '#home', 'billing': '#plans'}   # screen opened on tap
MAX_PER_DAY = int(os.getenv('PUSH_DAILY_CAP', '12'))
QUIET = (22, 6)                              # East Africa time (UTC+3)
EAT = dt.timezone(dt.timedelta(hours=3))

# ---------- who wants what ----------
def prefs(uid):
    from . import accounts
    r = st.q('SELECT notif FROM users WHERE uid=?', (uid,), True) or {}
    try: n = json.loads(r.get('notif') or '{}')
    except ValueError: n = {}
    return {k: n.get(k, accounts.DEF_NOTIF.get(k, 1)) not in (0, False, '0') for k in CAT}

def quiet_now(now=None):
    h = dt.datetime.fromtimestamp(now or time.time(), EAT).hour
    return h >= QUIET[0] or h < QUIET[1]

def _day0(now=None):
    d = dt.datetime.fromtimestamp(now or time.time(), EAT).replace(hour=0, minute=0, second=0, microsecond=0); return int(d.timestamp())

def allowed(uid, kind, now=None):
    """(ok, reason). One place decides: category switch, quiet hours, 1 nudge a day, daily cap."""
    k = KINDS.get(kind)
    if not k: return False, 'unknown kind'
    if not prefs(uid).get(k['cat'], True): return False, 'category off'
    free = k['cat'] in BYPASS_CATS or kind in BYPASS_KINDS
    if not free and quiet_now(now): return False, 'quiet hours'
    d0 = _day0(now)
    if kind in NUDGE_KINDS and (st.q('SELECT COUNT(*) AS n FROM push_log WHERE uid=? AND kind>=45 AND kind<=49 AND ts>=?', (uid, d0), True) or {}).get('n', 0) >= 1:
        return False, 'nudge limit'
    if not free and (st.q('SELECT COUNT(*) AS n FROM push_log WHERE uid=? AND ts>=?', (uid, d0), True) or {}).get('n', 0) >= MAX_PER_DAY:
        return False, 'daily cap'
    return True, ''

# ---------- the one entry point ----------
def send(uid, kind, body, title=None, key=None, force=False):
    """Send one notification kind to one person. key makes it idempotent per person. Returns (sent_count, reason)."""
    if not configured(): return 0, 'FCM not configured'
    k = KINDS.get(kind)
    if not k: return 0, 'unknown kind'
    if key and st.q('SELECT 1 FROM push_log WHERE uid=? AND k=?', (uid, key), True): return 0, 'duplicate'
    if not force:
        ok, why = allowed(uid, kind)
        if not ok: return 0, why
    tk = tokens(uid)
    if not tk: return 0, 'no device'
    title = title or k['title']; ch = CHANNEL[k['ch']]
    data = {'kind': kind, 'cat': k['cat'], 'route': ROUTE[k['cat']], 'tag': 'k%s' % kind}; n = 0; last = ''
    for t in tk:
        try: ok, why = _fcm(t, title, body, ch, data)
        except Exception as e: ok, why = False, str(e)[:120]
        if ok: n += 1
        else: last = why
    if n: st.x('INSERT INTO push_log(uid,kind,k,ts) VALUES(?,?,?,?)', (uid, kind, key, int(time.time())))
    return n, last

def recipients():
    """Subscribers and admins that have a phone registered."""
    admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}; now = time.time(); out = []
    for r in st.q('SELECT DISTINCT u.uid AS uid,u.email AS email,u.plan_until AS pu FROM users u JOIN push_tokens t ON t.uid=u.uid'):
        if (r['pu'] or 0) > now or (r['email'] or '').lower() in admins: out.append(r['uid'])
    return out

def broadcast(kind, body, title=None, key=None):
    """Send in the background so a trade route is never slowed down. Returns immediately."""
    if not configured(): return
    def run():
        for uid in recipients():
            try: send(uid, kind, body, title, (key + '/' + uid) if key else None)
            except Exception as e: print('[push] failed', e)
    threading.Thread(target=run, daemon=True).start()
