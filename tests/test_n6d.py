"""Section N6d: setup nudges (push kinds 45-49) through a FAKE FCM. Checks who is nudged, the payload, once-ever, one-a-day and the daytime window.
Run: python tests/test_n6d.py"""
import os, sys, json, types, threading, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'n6d_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, alerts, nudge_alerts as na
alerts.stop()          # stop the background alert loop so it cannot race this test
R = []
def T(name, ok): R.append((name, bool(ok))); print('PASS' if ok else 'FAIL', name)
SENT = []
class Resp:
    status_code = 200; text = '{}'
    def json(self): return {}
class FakeReq:
    def post(self, url, json=None, headers=None, data=None, timeout=None):
        if 'messages:send' in url: SENT.append(json['message'])
        return Resp()
push.requests = FakeReq(); push._access_token = lambda: 'fake'
push._account = lambda: {'project_id': 'p', 'client_email': 'e@p.iam', 'private_key': 'k'}
class SyncThread:
    def __init__(self, target=None, daemon=None): self.t = target
    def start(self): self.t()
push.threading = types.SimpleNamespace(Thread=SyncThread, Lock=threading.Lock)
push.quiet_now = lambda *a, **k: False
C = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
EAT = dt.timezone(dt.timedelta(hours=3)); DAY = 86400
def at(y, mo, d, h, mi=0): return dt.datetime(y, mo, d, h, mi, tzinfo=EAT).timestamp()
NOW = at(2026, 12, 10, 12)
who = {}; uid = {}
def mk(e, plan=True, created=10, notif='{"trade": 1}', prof=True, link='risk', tok=10):
    """A person who has done every step, then change one thing. created/tok are days ago. link: 'risk' (default), 'norisk' or None for no MT5 key (made 10 days ago)."""
    uid[e] = C.get('/api/me', headers=H(e)).json['uid']
    if plan: C.post('/api/admin/grant', json={'email': e, 'days': 3650}, headers=H('boss@x.com'))
    t = 'tok_%s_' % e.split('@')[0] + 'x' * 30; push.save_token(uid[e], t); who[t] = e
    st.x('UPDATE push_tokens SET created=? WHERE uid=?', (int(NOW - tok * DAY), uid[e]))
    st.x('UPDATE users SET created=?,notif=?,username=?,phone=?,country=? WHERE uid=?', (int(NOW - created * DAY), notif, 'n_' + e.split('@')[0] if prof else None, '0700' if prof else '', 'KE' if prof else '', uid[e]))
    if link: st.x('INSERT INTO links(uid,key_hash,mode,bot,risk,created) VALUES(?,?,?,?,?,?)', (uid[e], 'h_' + e, 'demo', 0, None if link == 'norisk' else 1.0, int(NOW - 10 * DAY)))
def go(now=NOW):
    SENT.clear(); na._tried.clear(); st.x('DELETE FROM push_log'); na.nudge_job(now); return sorted((who[m['token']], m['data']['kind']) for m in SENT)
def fields(m): n = m['android']['notification']; return m['notification']['title'], m['notification']['body'], n['channel_id'], n.get('tag'), m['data']['kind'], m['data']['route']
C.get('/api/me', headers=H('boss@x.com'))
push.save_token(C.get('/api/me', headers=H('boss@x.com')).json['uid'], 'tok_boss_' + 'x' * 30)
mk('done@x.com'); T('a person who finished every step gets nothing', go() == [])
# ---- 45 verify email (the server learns it from /api/me, here called directly with a fixed clock)
U = 'done@x.com'; na._unv.clear()
na.seen(uid[U], False, NOW - 3 * 3600); na.seen(uid[U], False, NOW - 600)
T('45: unverified 3 h, seen 10 min ago: nudged', go() == [(U, '45')])
t, b, ch, tag, k, route = fields(SENT[0])
T('45: title, body, low channel, kind, route', t == 'Verify your email' and 'keeps your account safe' in b and ch == 'sxb_low' and k == '45' and route == '#profile')
na._unv.clear(); na.seen(uid[U], False, NOW - 3600); na.seen(uid[U], False, NOW - 600); T('45: not before 2 hours unverified', go() == [])
na._unv.clear(); na.seen(uid[U], False, NOW - 9 * 3600); na.seen(uid[U], False, NOW - 4 * 3600); T('45: not for someone not seen in the app for a while', go() == [])
na._unv.clear(); na.seen(uid[U], False, NOW - 3 * 3600); na.seen(uid[U], False, NOW - 600); na.seen(uid[U], True, NOW - 60); T('45: nothing once verified (even though seen in the app minutes ago)', go() == [])
na._unv.clear()
T('/api/me reports the person to the nudges (app.py hook)', 'nudge_alerts.seen(u[' in open(os.path.join(ROOT, 'backend', 'app.py')).read())
# ---- 46 connect broker
mk('nomt@x.com', link=None, created=2); T('46: plan, 2 days old, nothing connected: nudged', go() == [('nomt@x.com', '46')])
t, b, ch, tag, k, route = fields(SENT[0]); T('46: title, body, kind, route', t == 'Connect your MT5' and 'Open Connect' in b and k == '46' and route == '#profile')
mk('young@x.com', link=None, created=0); T('46: not on the first day', 'young@x.com' not in [w for w, _ in go()])
mk('noplan@x.com', link=None, plan=False, created=2); T('46: not without a plan', 'noplan@x.com' not in [w for w, _ in go()])
mk('hasmt@x.com', created=2); T('46: not with an MT5 key', 'hasmt@x.com' not in [w for w, _ in go()])
mk('deriv@x.com', link=None, created=2); st.x("INSERT INTO broker_links(uid,broker,kind,secret_enc,label,mode,status,created,updated) VALUES(?,?,?,?,?,?,?,?,?)", (uid['deriv@x.com'], 'Deriv', 'token', 'x', 'd', 'demo', 'verified', 1, 1))
T('46: not with a saved Deriv broker', 'deriv@x.com' not in [w for w, _ in go()])
mk('phone@x.com', link=None, created=2); st.x('INSERT INTO assist(uid,enabled,balance,risk,updated) VALUES(?,?,?,?,?)', (uid['phone@x.com'], 1, 1000, 1.0, 1))
T('46: not with Phone mode on', 'phone@x.com' not in [w for w, _ in go()])
T('46: the admin is never nudged', 'boss@x.com' not in [w for w, _ in go()])
# ---- 47 risk
mk('norisk@x.com', link='norisk'); T('47: an MT5 key with no risk chosen: nudged', ('norisk@x.com', '47') in go())
t, b, ch, tag, k, route = fields([m for m in SENT if who[m['token']] == 'norisk@x.com'][0]); T('47: title, body', t == 'Set your risk' and 'risk percent' in b and k == '47')
st.x('UPDATE links SET created=? WHERE uid=?', (int(NOW - 3600), uid['norisk@x.com'])); T('47: not within a day of making the key', ('norisk@x.com', '47') not in go())
st.x('UPDATE links SET created=?,risk=? WHERE uid=?', (int(NOW - 10 * DAY), 2.0, uid['norisk@x.com'])); T('47: not once a risk is saved', ('norisk@x.com', '47') not in go())
# ---- 48 alerts
mk('noalert@x.com', notif=None); T('48: alerts never chosen, phone 10 days old: nudged', ('noalert@x.com', '48') in go())
t, b, ch, tag, k, route = fields([m for m in SENT if who[m['token']] == 'noalert@x.com'][0]); T('48: title, body', t == 'Choose your alerts' and 'Profile' in b and k == '48')
mk('newphone@x.com', notif=None, tok=1); T('48: not within 2 days of the first phone', 'newphone@x.com' not in [w for w, _ in go()])
mk('emptyalert@x.com', notif='{}'); T('48: an empty {} counts as never chosen', ('emptyalert@x.com', '48') in go())
# ---- 49 profile
mk('noprof@x.com', prof=False, created=4); T('49: profile unfinished, 4 days old: nudged', ('noprof@x.com', '49') in go())
t, b, ch, tag, k, route = fields([m for m in SENT if who[m['token']] == 'noprof@x.com'][0]); T('49: title, body', t == 'Finish your profile' and 'symbols' in b and k == '49')
mk('halfprof@x.com', created=4); st.x('UPDATE users SET country=NULL WHERE uid=?', (uid['halfprof@x.com'],)); T('49: one missing field (country) is enough', ('halfprof@x.com', '49') in go())
mk('newprof@x.com', prof=False, created=1); T('49: not within 3 days of sign-up', 'newprof@x.com' not in [w for w, _ in go()])
# ---- one a day, once ever
mk('two@x.com', link=None, created=2, notif=None); SENT.clear(); st.x('DELETE FROM push_log'); na._tried.clear(); na.nudge_job(NOW)
T('one a day: a person with two open steps (46 and 48) gets only the first today', sorted(k for w, k in [(who[m['token']], m['data']['kind']) for m in SENT] if w == 'two@x.com') == ['46'])
SENT.clear(); na._tried.clear(); na.nudge_job(NOW + 600); T('one a day: still nothing more the same day', 'two@x.com' not in [who[m['token']] for m in SENT])
st.x('UPDATE push_log SET ts=ts-86400')          # push.allowed counts 'today' on the real clock, so move yesterday's sends back one day
SENT.clear(); na._tried.clear(); na.nudge_job(NOW + DAY)
T('once ever: tomorrow the other step (48) comes, 46 never repeats', sorted(m['data']['kind'] for m in SENT if who[m['token']] == 'two@x.com') == ['48'])
st.x('UPDATE push_log SET ts=ts-86400')
SENT.clear(); na._tried.clear(); na.nudge_job(NOW + 2 * DAY); T('once ever: after both, nothing', 'two@x.com' not in [who[m['token']] for m in SENT])
# ---- daytime, switch, loop
T('window: nothing at 08:59 EAT', go(at(2026, 12, 10, 8, 59)) == [])
T('window: nothing from 20:00 EAT', go(at(2026, 12, 10, 20, 0)) == [])
st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({'tips': 0}), uid['nomt@x.com'])); T('the person Tips switch off = no nudge', 'nomt@x.com' not in [w for w, _ in go()])
na.register(); T('loop: the job is on the alerts loop', 'nudge_alerts' in alerts._jobs); T('loop: it runs on its own', alerts._jobs['nudge_alerts']['func']() is None)
T('startup: app.py registers the nudges', 'nudge_alerts.register()' in open(os.path.join(ROOT, 'backend', 'app.py')).read())
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.exit(1 if bad else 0)
