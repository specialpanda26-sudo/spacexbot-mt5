"""Section N6b: kinds 30 (monitor mode) and 31 (account type) through a FAKE FCM and the REAL routes.
Run: python tests/test_n6b.py"""
import os, sys, json, types, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'n6b_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, alerts
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
QUIET = [False]; push.quiet_now = lambda *a, **k: QUIET[0]
C = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
EM = ('boss@x.com', 'joe@x.com', 'ann@x.com'); uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in EM}
for e in ('joe@x.com', 'ann@x.com'): C.post('/api/admin/grant', json={'email': e, 'days': 30}, headers=H('boss@x.com'))
who = {}
for e in EM:
    t = 'tok_%s_' % e.split('@')[0] + 'x' * 30; push.save_token(uid[e], t); who[t] = e
def post(e, url, body): SENT.clear(); r = C.post(url, json=body, headers=H(e)); return r
def to(): return sorted(who[m['token']] for m in SENT)
def fields(m): n = m['android']['notification']; return m['notification']['title'], m['notification']['body'], n['channel_id'], n.get('tag'), m['data']['kind'], m['data']['route']
J = 'joe@x.com'
# ---- 31 MT5 link
post(J, '/api/link/key', {})
r = post(J, '/api/link/mode', {'mode': 'real', 'confirm': 'REAL'})
T('31: Demo to Real works and goes to that person only', r.status_code == 200 and to() == [J])
t, b, ch, tag, k, route = fields(SENT[0])
T('31: title, body, high channel, tag, kind, route', t == 'Switched to Real account' and 'Real account' in b and ch == 'sxb_high' and tag == 'k31' and k == '31' and route == '#home')
T('31: the same mode again sends nothing', (post(J, '/api/link/mode', {'mode': 'real', 'confirm': 'REAL'}), SENT)[1] == [])
r = post(J, '/api/link/mode', {'mode': 'demo'}); T('31: Real back to Demo says Demo', to() == [J] and fields(SENT[0])[0] == 'Switched to Demo account')
r = post(J, '/api/link/mode', {'mode': 'real'}); T('31: a refused switch (REAL not typed) sends nothing', r.status_code == 400 and SENT == [])
r = post('free@x.com', '/api/link/mode', {'mode': 'demo'}); T('31: a person with no key (refused) sends nothing', r.status_code == 400 and SENT == [])
r = post('boss@x.com', '/api/link/mode', {'mode': 'real', 'confirm': 'REAL'}); T('31: the owner (refused by the link route) sends nothing', r.status_code == 400 and SENT == [])
QUIET[0] = True; post(J, '/api/link/mode', {'mode': 'real', 'confirm': 'REAL'}); T('31: gets through quiet hours', to() == [J]); QUIET[0] = False
st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({'system': 0}), uid[J])); post(J, '/api/link/mode', {'mode': 'demo'})
T('31: the person System switch off = nothing', SENT == []); st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({}), uid[J]))
# ---- 31 Deriv
A = 'ann@x.com'
st.x("INSERT INTO broker_links(uid,broker,kind,secret_enc,label,mode,status,created,updated) VALUES(?,?,?,?,?,?,?,?,?)", (uid[A], 'Deriv', 'token', 'x', 'd', 'demo', 'verified', 1, 1))
r = post(A, '/api/brokers/Deriv/mode', {'mode': 'real', 'confirm': 'REAL'})
T('31: Deriv Demo to Real goes to that person only', r.status_code == 200 and to() == [A] and fields(SENT[0])[4] == '31')
T('31: Deriv same mode again sends nothing', (post(A, '/api/brokers/Deriv/mode', {'mode': 'real', 'confirm': 'REAL'}), SENT)[1] == [])
# ---- 30 monitor (phone) mode
r = post(J, '/api/assist/settings', {'on': True, 'balance': 1000})
T('30: Phone mode on goes to that person only', r.status_code == 200 and to() == [J])
t, b, ch, tag, k, route = fields(SENT[0])
T('30: title, body, kind, route', t == 'Monitor mode on' and 'wait for you' in b and k == '30' and tag == 'k30' and route == '#home')
T('30: on again sends nothing', (post(J, '/api/assist/settings', {'on': True}), SENT)[1] == [])
T('30: changing only the balance sends nothing', (post(J, '/api/assist/settings', {'balance': 2000}), SENT)[1] == [])
post(J, '/api/assist/settings', {'on': False}); T('30: off says Monitor mode off', to() == [J] and fields(SENT[0])[0] == 'Monitor mode off' and 'by itself' in fields(SENT[0])[1])
r = post(J, '/api/assist/settings', {'on': True, 'balance': 'abc'}); T('30: a refused change (bad balance) sends nothing', r.status_code == 400 and SENT == [])
r = post('boss@x.com', '/api/assist/settings', {'on': True, 'balance': 1000}); T('30: the owner is refused and nothing is sent', r.status_code == 400 and SENT == [])
QUIET[0] = True; post(J, '/api/assist/settings', {'on': True, 'balance': 1000}); T('30: gets through quiet hours', to() == [J]); QUIET[0] = False
T('startup: BYPASS_KINDS holds 30 and 31', {27, 30, 31} <= push.BYPASS_KINDS)
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.exit(1 if bad else 0)
