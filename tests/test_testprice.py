"""Section 1 checks: admin test price. Run: python tests/test_testprice.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'testprice_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import payments as pay
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
def mine(r): return [p for p in r.json if p['id'] == 'ptest']
C.get('/api/me', headers=A); C.get('/api/me', headers=U)
T('normal user cannot set a test price', C.post('/api/admin/testprice', json={'kes': 1, 'usd': 0.01}, headers=U).status_code == 403)
r = C.post('/api/admin/testprice', json={'kes': 1, 'usd': 0.01, 'days': 1}, headers=A)
t = mine(r) if r.status_code == 200 else []
T('admin sets KES 1 / USD 0.01', len(t) == 1 and t[0]['kes'] == 1 and abs(t[0]['usd'] - 0.01) < 1e-9 and t[0]['days'] == 1)
T('customers see the test package', any(p['id'] == 'ptest' for p in C.get('/api/plans').json))
T('the normal packages are kept', {'p1', 'p2', 'p3'} <= {p['id'] for p in C.get('/api/plans').json})
t = mine(C.post('/api/admin/testprice', json={'kes': 77, 'usd': 0.55, 'days': 2}, headers=A))
T('setting again replaces it, no duplicate', len(t) == 1 and t[0]['kes'] == 77 and abs(t[0]['usd'] - 0.55) < 1e-9 and t[0]['days'] == 2)
T('pay.plan() finds it with the new price', (pay.plan('ptest') or {}).get('kes') == 77)
for bad in ({'kes': 0, 'usd': 1}, {'kes': 5, 'usd': 0}, {'kes': 5, 'usd': 0.004}, {'kes': 'x', 'usd': 1}, {'kes': 5, 'usd': 1, 'days': 0}, {'kes': 5, 'usd': 1, 'days': 99999}, {'kes': 9999999, 'usd': 1}):
    T('refuses bad input %s' % bad, C.post('/api/admin/testprice', json=bad, headers=A).status_code == 400)
T('a refused request changes nothing', (pay.plan('ptest') or {}).get('kes') == 77)
t = mine(C.post('/api/admin/testprice', json={'kes': 77, 'usd': 1.234, 'days': 2}, headers=A))
T('USD is rounded to cents', len(t) == 1 and t[0]['usd'] == 1.23)
r = C.post('/api/admin/testprice', json={'off': True}, headers=A)
T('off removes the test package only', r.status_code == 200 and not mine(r) and {'p1', 'p2', 'p3'} <= {p['id'] for p in r.json})
T('off twice is harmless', C.post('/api/admin/testprice', json={'off': True}, headers=A).status_code == 200)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
