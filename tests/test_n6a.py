"""Section N6a: system alerts (push kinds 26-29) through a FAKE FCM. Checks who gets each kind, the payload and that each goes out once.
Run: python tests/test_n6a.py"""
import os, sys, time, json, types, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'n6a_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None); os.environ.pop('RENDER_GIT_COMMIT', None); os.environ.pop('BUILD_ID', None)
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, alerts, system_alerts as sa
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
EM = ('boss@x.com', 'joe@x.com', 'ann@x.com'); uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in EM}
for e in ('joe@x.com',): C.post('/api/admin/grant', json={'email': e, 'days': 30}, headers=H('boss@x.com'))
who = {}
for e in EM:
    t = 'tok_%s_' % e.split('@')[0] + 'x' * 30; push.save_token(uid[e], t); who[t] = e
st.x("INSERT INTO links(uid,key_hash,mode,bot,created) VALUES(?,?,?,?,?)", (uid['joe@x.com'], 'h1', 'demo', 0, 1))
def beat(scope, seen, **extra):
    a = dict(extra, seen=seen)
    if scope: st.x('UPDATE links SET acct=?,seen=? WHERE uid=?', (json.dumps(a), seen, scope))
    else: st.put('acct', json.dumps(a))
def run(fn, now): SENT.clear(); fn(now); return SENT
def to(): return sorted(who[m['token']] for m in SENT)
def fields(m): n = m['android']['notification']; return m['notification']['title'], m['notification']['body'], n['channel_id'], n.get('tag'), m['data']['kind'], m['data']['route']
NOW = 1_800_000_000

T('nothing is sent while no EA ever reported', run(sa.ea_job, NOW) == [])
beat('', NOW - 10)
T('26: the owner EA first seen goes to the admin only', (run(sa.ea_job, NOW), to())[1] == ['boss@x.com'])
t, b, ch, tag, k, route = fields(SENT[0])
T('26: title, body, high channel, tag, kind, route', t == 'MT5 connected' and 'Your EA is online' in b and ch == 'sxb_high' and tag == 'k26' and k == '26' and route == '#home')
T('26: second run says nothing more', run(sa.ea_job, NOW + 30) == [])
beat('', NOW - 10); T('27: a 4-minute silence is not an alert', run(sa.ea_job, NOW - 10 + 240) == [])
r = run(sa.ea_job, NOW - 10 + 360)
T('27: offline after 5+ minutes goes to the admin', to() == ['boss@x.com'])
t, b, ch, tag, k, route = fields(SENT[0])
T('27: title and the real minutes in the body', t == 'MT5 is offline' and 'for 6 minutes' in b and k == '27')
T('27: said once only', run(sa.ea_job, NOW - 10 + 900) == [])
beat('', NOW + 2000)
T('28: back online goes to the admin', (run(sa.ea_job, NOW + 2010), to())[1] == ['boss@x.com'] and fields(SENT[0])[0] == 'MT5 is back online')
T('28: said once only', run(sa.ea_job, NOW + 2020) == [])
beat('', NOW + 2000); run(sa.ea_job, NOW + 2000 + 400)
T('a second outage sends a new 27', len(SENT) == 1 and fields(SENT[0])[4] == '27')
st.put('acct', json.dumps({'seen': NOW + 5000, 'src': 'deriv'}));
st.put('ea26:', 'up'); T('a Deriv snapshot is not MT5: nothing sent', run(sa.ea_job, NOW + 9000) == [])
push.quiet_now = lambda *a, **k: True
beat('', NOW + 9000); st.put('ea26:', 'up'); run(sa.ea_job, NOW + 9000 + 400)
T('27 gets through quiet hours', to() == ['boss@x.com'])
push.quiet_now = lambda *a, **k: False

st.x("DELETE FROM kv WHERE k='acct'"); st.x("DELETE FROM kv WHERE k='ea26:'")          # the owner EA is out of the picture for the subscriber checks
j = uid['joe@x.com']; beat(j, NOW - 5)
T('26: a subscriber EA goes to that subscriber only', (run(sa.ea_job, NOW), to())[1] == ['joe@x.com'] and fields(SENT[0])[3] == 'k26')
beat(j, NOW - 5); run(sa.ea_job, NOW + 400)
T('27: a subscriber EA offline goes to that subscriber only', to() == ['joe@x.com'])
beat(j, NOW + 800); run(sa.ea_job, NOW + 805)
T('28: a subscriber EA back goes to that subscriber only', to() == ['joe@x.com'] and fields(SENT[0])[4] == '28')

# ---- 29
sa._booted = False; os.environ.pop('RENDER_GIT_COMMIT', None); st.x("DELETE FROM kv WHERE k='boot29'")
T('29: no version known = nothing', run(sa.boot_job, NOW) == [])
sa._booted = False; os.environ['RENDER_GIT_COMMIT'] = 'abc123def4567890'
T('29: the very first start only remembers', run(sa.boot_job, NOW) == [] and st.get('boot29') == 'abc123def456')
sa._booted = False; T('29: same version again (a wake-up) sends nothing', run(sa.boot_job, NOW) == [])
sa._booted = False; os.environ['RENDER_GIT_COMMIT'] = 'zzz999yyy8887777'
run(sa.boot_job, NOW)
T('29: a new version goes to the admin only', to() == ['boss@x.com'])
t, b, ch, tag, k, route = fields(SENT[0])
T('29: title, low channel, kind', t == 'spaceXBot was updated' and ch == 'sxb_low' and k == '29')
T('29: runs once per start', run(sa.boot_job, NOW) == [])

# ---- startup
sa.register()
T('loop: both jobs are on the alerts loop', {'ea_alerts', 'boot_alerts'} <= set(alerts._jobs))
T('loop: the jobs run on their own', alerts._jobs['ea_alerts']['func']() is None and alerts._jobs['boot_alerts']['func']() is None)
T('startup: app.py registers the system alerts', 'system_alerts.register()' in open(os.path.join(ROOT, 'backend', 'app.py')).read())
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.exit(1 if bad else 0)
