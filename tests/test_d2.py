"""D2 tests: Deriv MT5 as a broker next to FBS. Run: python tests/test_d2.py"""
import os, sys, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_d2.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, brokers as bk
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
HTML = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()

T('Deriv MT5 is an MT5 broker', bk.CATALOG.get('Deriv MT5') == 'mt5')
T('plain Deriv is still the token bot', bk.CATALOG.get('Deriv') == 'token')
T('names match without case or spaces trouble', bk.canon('deriv mt5') == 'Deriv MT5' and bk.canon(' Deriv ') == 'Deriv')
a = bk.about('Deriv MT5')
T('its note says no EA and no key are needed', 'No EA and no key needed' in a['works'] and 'MT5 phone app' in a['works'])
T('its note warns about market names', 'name markets differently' in a['not'])
T('catalog lists it with its note', any(x['name'] == 'Deriv MT5' and x['kind'] == 'mt5' and x.get('works') for x in bk.catalog()))
c.get('/api/me', headers=H('amy@x.com')); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-amy@x.com'))
r = c.post('/api/brokers/Deriv%20MT5', json={'server': ''}, headers=H('amy@x.com'))
T('empty server is refused with the Deriv hint, no made-up name', r.status_code == 400 and 'Copy it exactly' in r.get_json()['error'] and 'Deriv MT5-Demo' not in r.get_json()['error'])
r = c.post('/api/brokers/Deriv%20MT5', json={'server': 'DerivTest-Server'}, headers=H('amy@x.com'))
T('server name saves, no secret kept', r.status_code == 200 and bk.secret('dev-amy@x.com', 'Deriv MT5') is None)
r = c.post('/api/brokers/FBS', json={'server': 'FBS-Demo'}, headers=H('amy@x.com'))
names = [b['name'] for b in r.get_json()['brokers']]
T('FBS and Deriv MT5 sit side by side', sorted(names) == ['Deriv MT5', 'FBS'])
T('both start in demo mode', all(b['mode'] == 'demo' for b in r.get_json()['brokers']))
T('the token bot did not appear', 'Deriv' not in names)
T('Connect row names Deriv MT5', "MT5 app (FBS, Deriv MT5...)" in open(os.path.join(ROOT, 'backend', 'connwhy.py'), encoding='utf-8').read())
T('removing Deriv MT5 leaves FBS', c.delete('/api/brokers/Deriv%20MT5', headers=H('amy@x.com')).status_code == 200 and [b['name'] for b in bk.view('dev-amy@x.com')] == ['FBS'])
T('tile is on the Connect tab', '["Deriv MT5","MT5 bridge"]' in HTML)
T('logo alias points to the Deriv logo', 'derivmt5:"deriv"' in HTML)
T('server box has its own placeholder', 'n==="Deriv MT5"?"Your Deriv MT5 server name"' in HTML)
T('onboarding offers it, MT5 demo or real account', '["derivmt5","Deriv MT5","MT5 demo or real account","D"]' in HTML)
T('setup list offers it', '["derivmt5","Deriv MT5","your Deriv MT5 server name"]' in HTML)
n = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
