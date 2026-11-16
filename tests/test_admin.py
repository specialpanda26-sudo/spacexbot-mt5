"""Section 5 checks: admin user list, grant, revoke. Run: python tests/test_admin.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'admin_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import store as st
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
C.get('/api/me', headers=U); C.get('/api/me', headers=A)
T('normal user cannot list or revoke', C.get('/api/admin/subscribers', headers=U).status_code == 403 and C.post('/api/admin/revoke', json={'email': 'joe@x.com'}, headers=U).status_code == 403)
r = C.get('/api/admin/subscribers', headers=A)
T('admin sees both users', r.status_code == 200 and {x['email'] for x in r.json} >= {'boss@x.com', 'joe@x.com'})
T('grant gives days', C.post('/api/admin/grant', json={'email': 'joe@x.com', 'days': 7}, headers=A).status_code == 200)
joe = [x for x in C.get('/api/admin/subscribers', headers=A).json if x['email'] == 'joe@x.com'][0]
T('list shows about 7 days', 6 * 86400 < joe['plan_until'] - time.time() <= 7 * 86400 + 5)
T('grant unknown user fails', C.post('/api/admin/grant', json={'email': 'nobody@x.com', 'days': 7}, headers=A).status_code == 400)
T('revoke clears access', C.post('/api/admin/revoke', json={'email': 'joe@x.com'}, headers=A).status_code == 200)
joe = [x for x in C.get('/api/admin/subscribers', headers=A).json if x['email'] == 'joe@x.com'][0]
T('revoked user has no plan', joe['plan_until'] == 0 and C.get('/api/status', headers=U).status_code == 402)
T('revoke unknown user fails', C.post('/api/admin/revoke', json={'email': 'nobody@x.com'}, headers=A).status_code == 400)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
