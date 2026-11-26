"""Phone notifications through Firebase Cloud Messaging (HTTP v1). Facts only: never a promise of profit, never advice.
Env: FCM_SERVICE_ACCOUNT = the service-account JSON (raw or base64). Without it every send is a quiet no-op."""
import os, time, json, base64, threading, datetime as dt
import requests
from . import store as st

CAT = ('trade', 'risk', 'news', 'daily', 'tips', 'system', 'billing')
BYPASS_CATS = {'risk', 'billing'}            # always get through quiet hours and the daily cap
BYPASS_KINDS = {27, 30, 31, 50}                          # EA offline too
NUDGE_KINDS = set(range(45, 50))
TRADE_TAG_KINDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}         # the banner's tag carries the trade id, so two trades never replace each other
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
MAX_PER_DAY = int(os.getenv('PUSH_DAILY_CAP', '30'))
QUIET = (22, 6)                              # East Africa time (UTC+3)
EAT = dt.timezone(dt.timedelta(hours=3))

# ---------- who wants what ----------
def prefs(uid):
    from . import accounts
    r = st.q('SELECT notif FROM users WHERE uid=?', (uid,), True) or {}
    try: n = json.loads(r.get('notif') or '{}')
    except ValueError: n = {}
    return {k: n.get(k, accounts.DEF_NOTIF.get(k, 1)) not in (0, False, '0') for k in CAT}

def quiet_now(user_notif=None, kind=None, now=None):
    if kind in [2, 3, 4]:
        return False
    notif = user_notif or {}
    start_hour = notif.get("quiet_start", QUIET[0])
    end_hour = notif.get("quiet_end", QUIET[1])
    h = dt.datetime.fromtimestamp(now or time.time(), EAT).hour
    if start_hour > end_hour:
        return (h >= start_hour) or (h < end_hour)
    return start_hour <= h < end_hour

def _day0(now=None):
    d = dt.datetime.fromtimestamp(now or time.time(), EAT).replace(hour=0, minute=0, second=0, microsecond=0); return int(d.timestamp())

def allowed(uid, kind, now=None):
    """(ok, reason). One place decides: category switch, quiet hours, 1 nudge a day, daily cap."""
    k = KINDS.get(kind)
    if not k: return False, 'unknown kind'
    if not prefs(uid).get(k['cat'], True): return False, 'category off'
    free = k['cat'] in BYPASS_CATS or kind in BYPASS_KINDS
    if not free and quiet_now(prefs(uid), kind, now): return False, 'quiet hours'
    d0 = _day0(now)
    if kind in NUDGE_KINDS and (st.q('SELECT COUNT(*) AS n FROM push_log WHERE uid=? AND kind>=45 AND kind<=49 AND ts>=?', (uid, d0), True) or {}).get('n', 0) >= 1:
        return False, 'nudge limit'
    if not free and (st.q('SELECT COUNT(*) AS n FROM push_log WHERE uid=? AND ts>=?', (uid, d0), True) or {}).get('n', 0) >= MAX_PER_DAY:
        return False, 'daily cap'
    return True, ''

# ---------- tokens ----------
def save_token(uid, token, platform='android'):
    token = str(token or '').strip()
    if not 20 <= len(token) <= 4096: raise ValueError('Bad token')
    now = int(time.time())
    st.x('INSERT INTO push_tokens(token,uid,platform,created,seen) VALUES(?,?,?,?,?) ON CONFLICT(token) DO UPDATE SET uid=excluded.uid,platform=excluded.platform,seen=excluded.seen',
         (token, uid, str(platform)[:20], now, now))

def drop_token(token): st.x('DELETE FROM push_tokens WHERE token=?', (token,))
def tokens(uid): return [r['token'] for r in st.q('SELECT token FROM push_tokens WHERE uid=?', (uid,))]

# ---------- FCM HTTP v1 ----------
_acc = None; _tok = {'v': None, 'exp': 0}; _lk = threading.Lock()
def _account():
    global _acc
    if _acc is None:
        raw = os.getenv('FCM_SERVICE_ACCOUNT', '').strip()
        if not raw: _acc = {}
        else:
            try: _acc = json.loads(raw if raw.startswith('{') else base64.b64decode(raw).decode('utf-8'))
            except Exception as e: print('[push] FCM_SERVICE_ACCOUNT unreadable:', e); _acc = {}
    return _acc
def configured(): a = _account(); return bool(a.get('private_key') and a.get('client_email') and a.get('project_id'))

def _b64(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def _access_token():
    with _lk:
        if _tok['v'] and _tok['exp'] > time.time() + 60: return _tok['v']
        a = _account(); now = int(time.time())
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        head = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
        claim = _b64(json.dumps({'iss': a['client_email'], 'scope': 'https://www.googleapis.com/auth/firebase.messaging',
                                 'aud': 'https://oauth2.googleapis.com/token', 'iat': now, 'exp': now + 3600}).encode())
        key = serialization.load_pem_private_key(a['private_key'].encode(), password=None)
        sig = key.sign((head + '.' + claim).encode(), padding.PKCS1v15(), hashes.SHA256())
        r = requests.post('https://oauth2.googleapis.com/token', data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': head + '.' + claim + '.' + _b64(sig)}, timeout=15)
        r.raise_for_status(); j = r.json(); _tok['v'] = j['access_token']; _tok['exp'] = now + int(j.get('expires_in', 3600)); return _tok['v']

def _fcm(token, title, body, channel, data):
    a = _account()
    msg = {'message': {'token': token, 'notification': {'title': title, 'body': body},
           'data': {k: str(v) for k, v in data.items()},
           'android': {'priority': 'HIGH' if channel == 'sxb_high' else 'NORMAL', 'notification': {'channel_id': channel, 'icon': 'ic_stat_sxb', 'tag': data.get('tag', '')[:60] or None}}}}
    if not msg['message']['android']['notification']['tag']: del msg['message']['android']['notification']['tag']
    if data.get('img'): msg['message']['notification']['image'] = data['img']
    r = requests.post('https://fcm.googleapis.com/v1/projects/%s/messages:send' % a['project_id'], json=msg,
                      headers={'Authorization': 'Bearer ' + _access_token()}, timeout=15)
    if r.status_code == 200: return True, ''
    if r.status_code in (404, 400) and ('UNREGISTERED' in r.text or 'INVALID_ARGUMENT' in r.text and 'token' in r.text.lower()): drop_token(token); return False, 'dead token removed'
    return False, 'FCM %s %s' % (r.status_code, r.text[:160])

def tag_for(kind, key=None):
    """Android replaces a banner that has the same tag. Trade kinds carry the trade id (key 'sig12-open', without the '/<uid>' that broadcast adds), others share one tag per kind."""
    if kind in TRADE_TAG_KINDS and key: return ('k%s-%s' % (kind, str(key).split('/')[0]))[:60]
    return 'k%s' % kind

# ---------- the one entry point ----------
def send(uid, kind, body, title=None, key=None, force=False, img=None):
    """Send one notification kind to one person. key makes it idempotent per person. Returns (sent_count, reason)."""
    k0 = KINDS.get(kind)          # TB1: the in-app inbox keeps it too (unless that category is switched off)
    if k0:
        try:
            from . import inbox
            if prefs(uid).get(k0['cat'], True): inbox.add(uid, kind, title or k0['title'], body, k0['cat'], key)
        except Exception as e: print('[push] inbox failed', str(e)[:80])
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
    data = {'kind': kind, 'cat': k['cat'], 'route': '#connect' if kind == 7 else ROUTE[k['cat']], 'tag': tag_for(kind, key)}; n = 0; last = ''
    if img: data['img'] = img
    for t in tk:
        try: ok, why = _fcm(t, title, body, ch, data)
        except Exception as e: ok, why = False, str(e)[:120]
        if ok: n += 1
        else: last = why
    if n: st.x('INSERT INTO push_log(uid,kind,k,ts) VALUES(?,?,?,?)', (uid, kind, key, int(time.time())))
    return n, last

WHY = {'no device': 'No phone is registered for your account. Open the app on your phone, sign in as admin, allow notifications, then try again.',
       'FCM not configured': 'The server has no FCM_SERVICE_ACCOUNT yet, so it cannot send phone alerts.',
       'category off': 'Trade alerts are switched off in your alert settings.'}
def explain(why):
    """A reason code from send() in plain words for the admin screen."""
    return WHY.get(why) or ('Not sent: %s' % why if why else 'Not sent.')

def recipients(admins_only=False):
    """Subscribers and admins that have a phone registered. admins_only: just the admins (ADMIN_EMAILS)."""
    admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}; now = time.time(); out = []
    for r in st.q('SELECT DISTINCT u.uid AS uid,u.email AS email,u.plan_until AS pu FROM users u JOIN push_tokens t ON t.uid=u.uid'):
        is_admin = (r['email'] or '').lower() in admins
        if is_admin or (not admins_only and (r['pu'] or 0) > now): out.append(r['uid'])
    return out

def broadcast(kind, body, title=None, key=None, img=None, only=None, admins=False):
    """Send in the background so a trade route is never slowed down. Returns immediately. only = one person; admins = admins only; neither = every subscriber."""
    if not configured(): return
    def run():
        for uid in recipients(admins):
            if only and uid != only: continue
            try: send(uid, kind, body, title, (key + '/' + uid) if key else None, img=img)
            except Exception as e: print('[push] failed', e)
    threading.Thread(target=run, daemon=True).start()

def notify(kind, key=None, **facts):
    """Write the message for this kind from the facts and send it to everyone who should get it. Never raises."""
    try:
        from .pushcopy import compose
        only = facts.pop('only', None); admins = bool(facts.pop('admins', False)); t, b, i = compose(kind, **facts); broadcast(kind, b, t, key, i, only, admins)
    except Exception as e: print('[push] notify failed', kind, e)

def notify_user(uid, kind, key=None, **facts):
    """Billing alerts for ONE person, whatever their plan state. broadcast() only reaches paid people and admins, but "prompt sent", "payment did not go through" and "plan ended" belong to people who have no plan right now. Background thread, never raises. key makes it once per person."""
    if not configured(): return
    try:
        from .pushcopy import compose
        t, b, i = compose(kind, **facts)
    except Exception as e: print('[push] notify_user failed', kind, e); return
    def run():
        try: send(uid, kind, b, t, key, img=i)
        except Exception as e: print('[push] failed', e)
    threading.Thread(target=run, daemon=True).start()

def send_data(uid, data):
    """Silent data message: no banner of its own. The app's native service turns it into the live 'Bot running' notification."""
    if not configured(): return 0
    n = 0
    for t in tokens(uid):
        try:
            a = _account()
            msg = {'message': {'token': t, 'data': {k: str(v) for k, v in data.items()}, 'android': {'priority': 'HIGH', 'ttl': '120s'}}}
            r = requests.post('https://fcm.googleapis.com/v1/projects/%s/messages:send' % a['project_id'], json=msg,
                              headers={'Authorization': 'Bearer ' + _access_token()}, timeout=15)
            if r.status_code == 200: n += 1
            elif r.status_code in (404, 400) and 'UNREGISTERED' in r.text: drop_token(t)
        except Exception as e: print('[push] data send failed', str(e)[:120])
    return n
