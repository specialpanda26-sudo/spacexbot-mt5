"""Test Lab 1 checks: owner-only, TEST_LAB=1 only, never writes, messages equal the real ones. No network. Run: python tests/test_testlab.py"""
import os, sys, glob, sqlite3
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_testlab_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD', DERIV_APP_ID='1')
os.environ.pop('TEST_LAB', None)
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import testlab, alerts
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
for e in ('amy@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
def dump():
    d = sqlite3.connect(DB); out = {}
    for (t,) in d.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        out[t] = d.execute('SELECT * FROM "%s"' % t).fetchall()
    d.close(); return out
def run(who, case): return c.post('/api/admin/testlab/run', json={'case': case}, headers=H(who))
IDS = [r[0] for r in testlab._ROWS]

# switch OFF (default)
r = c.get('/api/admin/testlab', headers=H('boss@x.com')).get_json()
T('switch off: the owner sees on=false and no cases', r['on'] is False and r['cases'] == [])
T('switch off: running a case is refused (403)', run('boss@x.com', 'pay_ok').status_code == 403)
os.environ['TEST_LAB'] = '0'
T('TEST_LAB=0 is also off', run('boss@x.com', 'pay_ok').status_code == 403)
os.environ['TEST_LAB'] = '1'

# switch ON
T('a normal customer cannot list', c.get('/api/admin/testlab', headers=H('amy@x.com')).status_code == 403)
T('a normal customer cannot run', run('amy@x.com', 'pay_ok').status_code == 403)
T('no sign-in cannot list or run', c.get('/api/admin/testlab').status_code == 401 and c.post('/api/admin/testlab/run', json={'case': 'pay_ok'}).status_code == 401)
r = c.get('/api/admin/testlab', headers=H('boss@x.com')).get_json()
T('the owner sees the Deriv login and payment cases', r['on'] is True and {x['group'] for x in r['cases']} == {'Deriv login', 'Payment'} and len(r['cases']) == 8)
T('unknown case is a 400', run('boss@x.com', 'nope').status_code == 400)
before = dump(); ok = True; seen = {}
for i in IDS:
    x = run('boss@x.com', i); j = x.get_json(); seen[i] = j
    ok = ok and x.status_code == 200 and j.get('fake') is True and j.get('case') == i
T('every case runs and says fake=true', ok)
T('running every case changed NOTHING in the database', dump() == before)
T('success cases are ok, the others are not', seen['deriv_ok']['ok'] and seen['pay_ok']['ok'] and not any(seen[k]['ok'] for k in IDS if k not in ('deriv_ok', 'pay_ok')))
src = open(os.path.join(ROOT, 'backend', 'deriv_oauth.py'), encoding='utf-8').read() + open(os.path.join(ROOT, 'backend', 'deriv.py'), encoding='utf-8').read()
T('every Deriv message is the real one (found in deriv_oauth.py / deriv.py)', all(seen[k]['msg'] in src for k in IDS if k.startswith('deriv_')))
T('the lab file never touches the store, money or trades', not any(w in open(os.path.join(ROOT, 'backend', 'testlab.py'), encoding='utf-8').read().split('"""', 2)[2] for w in ('import store', 'st.put', 'st.x(', 'requests', 'payments', 'signals')))
print('%d/%d' % (sum(R), len(R))); [os.remove(f) for f in glob.glob(DB + '*')]; sys.exit(0 if all(R) else 1)
