"""Section N6e: security notice (push kind 50) through a FAKE FCM and the REAL routes.
Run: python tests/test_n6e.py"""
import os, sys, json, types, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'n6e_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, security_alerts as sec, alerts
alerts.stop()          # the app starts its alert loop at import; stop it so no background job races this test on the real clock
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
QUIET = [False]; push.quiet_now = lambda *a, **k: QUIET[0]
C = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
EM = ('boss@x.com', 'joe@x.com', 'ann@x.com'); uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in EM}
for e in ('joe@x.com', 'ann@x.com'): C.post('/api/admin/grant', json={'email': e, 'days': 30}, headers=H('boss@x.com'))
who = {}
for e in EM:
    t = 'tok_%s_' % e.split('@')[0] + 'x' * 30; push.save_token(uid[e], t); who[t] = e
def call(method, e, url, body=None): SENT.clear(); return getattr(C, method)(url, json=body, headers=H(e))
def to(): return sorted(who[m['token']] for m in SENT)
def fields(m): n = m['android']['notification']; return m['notification']['title'], m['notification']['body'], n['channel_id'], n.get('tag'), m['data']['kind'], m['data']['route']
J = 'joe@x.com'; TAIL = 'If this was not you, change your password now.'
# ---- MT5 key
r = call('post', J, '/api/link/key', {}); key = r.json['key']
T('MT5 key created goes to that person only', r.status_code == 200 and to() == [J])
t, b, ch, tag, k, route = fields(SENT[0])
T('title, body, high channel, kind', t == 'Security notice' and b == 'An MT5 key was created. ' + TAIL and ch == 'sxb_high' and k == '50' and tag == 'k50')
T('the notice never carries the key', key not in json.dumps(SENT) and key[4:] not in json.dumps(SENT))
r = call('post', J, '/api/link/key', {}); T('a second key says replaced', to() == [J] and fields(SENT[0])[1].startswith('Your MT5 key was replaced.'))
r = call('post', 'free@x.com', '/api/link/key', {}); T('a refused key (no plan) sends nothing', r.status_code == 402 and SENT == [])
r = call('post', 'boss@x.com', '/api/link/key', {}); T('a refused key (owner) sends nothing', r.status_code == 400 and SENT == [])
r = call('delete', J, '/api/link'); T('MT5 link removed goes to that person', r.status_code == 200 and to() == [J] and fields(SENT[0])[1].startswith('Your MT5 link was removed.'))
call('delete', J, '/api/link'); T('removing a link that does not exist sends nothing', SENT == [])
call('delete', 'boss@x.com', '/api/link'); T('the owner delete sends nothing', SENT == [])
# ---- brokers (an MT5 broker keeps only the server name, so no vault key is needed)
r = call('post', J, '/api/brokers/IC%20Markets', {'server': 'ICMarkets-Demo'}); T('broker connected goes to that person', r.status_code == 200 and to() == [J] and fields(SENT[0])[1].startswith('IC Markets was connected.'))
r = call('post', J, '/api/brokers/IC%20Markets', {'server': ''}); T('a refused broker (bad server) sends nothing', r.status_code == 400 and SENT == [])
r = call('delete', J, '/api/brokers/IC%20Markets'); T('broker disconnected goes to that person', r.status_code == 200 and to() == [J] and fields(SENT[0])[1].startswith('IC Markets was disconnected.'))
call('delete', J, '/api/brokers/IC%20Markets'); T('disconnecting a broker that is not connected sends nothing', SENT == [])
call('delete', J, '/api/brokers/Nope'); T('an unknown broker sends nothing', SENT == [])
# ---- sign out other devices
r = call('post', J, '/api/me/signout-others', {}); T('sign out other devices goes to that person', r.status_code == 200 and to() == [J] and fields(SENT[0])[1].startswith('Your other devices were signed out.'))
orig = sec.sbauth.revoke if hasattr(sec, 'sbauth') else None
import backend.app as A; real = A.sbauth.revoke; A.sbauth.revoke = lambda u: False
call('post', J, '/api/me/signout-others', {}); T('a failed sign-out sends nothing', SENT == []); A.sbauth.revoke = real
# ---- new sign-in
sec._last.clear(); st.x("DELETE FROM kv WHERE k LIKE 'sin:%'"); T0 = 1_800_000_000
SENT.clear(); sec.signin(uid[J], '2026-11-22T10:00:00Z', T0); T('the first sign-in stamp is only remembered', SENT == [] and st.get('sin:' + uid[J]) == '2026-11-22T10:00:00Z')
sec.signin(uid[J], '2026-11-22T10:00:00Z', T0 + 10); T('the same stamp again: nothing', SENT == [])
sec.signin(uid[J], '2026-11-22T12:00:00Z', T0 + 7200); T('a new sign-in stamp goes to that person only', to() == [J] and fields(SENT[0])[1] == 'New sign-in on your account. ' + TAIL)
SENT.clear(); sec.signin(uid[J], '2026-11-22T12:30:00Z', T0 + 9000); T('a second new stamp within 6 hours: no second notice', SENT == [])
SENT.clear(); sec.signin(uid[J], '2026-11-22T20:00:00Z', T0 + 7200 + 6 * 3600 + 5); T('after 6 hours a new sign-in is noticed again', to() == [J])
sec._last.clear(); SENT.clear(); sec.signin(uid[J], '2026-11-22T20:00:00Z', T0 + 99999); T('after a restart the stored stamp is remembered (no false notice)', SENT == [])
sec._last.clear(); sec._noted.clear(); SENT.clear(); sec.signin(uid[J], '2026-11-23T08:00:00Z', T0 + 200000); T('after a restart a NEW stamp is still noticed (the old one was remembered)', to() == [J])
SENT.clear(); sec.signin(uid[J], '', T0); sec.signin(uid[J], None, T0); T('no stamp (dev, or not signed in): nothing', SENT == [])
T('the sign-in stamp comes from Supabase', "'last_sign_in': d.get('last_sign_in_at')" in open(os.path.join(ROOT, 'backend', 'sbauth.py')).read())
T('BYPASS_KINDS holds 50', 50 in push.BYPASS_KINDS)
T('app.py calls signin on every signed-in request', 'security_alerts.signin(u[' in open(os.path.join(ROOT, 'backend', 'app.py')).read())
# ---- delivery rules
QUIET[0] = True; call('post', J, '/api/link/key', {}); T('gets through quiet hours', to() == [J]); QUIET[0] = False
st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({'system': 0}), uid[J])); call('post', J, '/api/link/key', {}); T('the person System switch off = nothing', SENT == [])
st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({}), uid[J]))
A2 = 'ann@x.com'; call('post', A2, '/api/link/key', {}); T('one person action never reaches another person', to() == [A2])
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.exit(1 if bad else 0)
