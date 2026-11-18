"""Section 2, step 1 tests (Deriv token check, no network). Run: python tests/test_deriv1.py"""
import os, sys, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_dv1.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk, deriv
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def pay(e): c.get('/api/me', headers=H(e)); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-' + e))
TOK = 'abcDEF1234567890'; U = 'dev-amy@x.com'
def status(): return [b['status'] for b in bk.view(U) if b['name'] == 'Deriv'][0]
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}, {'account_id': 'CR9', 'account_type': 'real', 'currency': 'USD'}]}
seen = []
def good(m, p, t): seen.append((m, p, t)); return 200, ACC
def bad(m, p, t): return 401, {}
def down(m, p, t): raise OSError('boom')

pay('amy@x.com')
T('no sign-in -> 401', c.post('/api/brokers/Deriv/verify').status_code == 401)
c.get('/api/me', headers=H('free@x.com'))
T('no plan -> 402', c.post('/api/brokers/Deriv/verify', headers=H('free@x.com')).status_code == 402)
T('only Deriv is checkable for now', c.post('/api/brokers/Binance/verify', headers=H('amy@x.com')).status_code == 400)
T('nothing saved yet -> asks to save first', deriv.verify(U, good, 1000) == (False, 'Save your Deriv token first.'))
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
ok, m = deriv.verify(U, good, 2000)
T('good token -> verified, demo found', ok and status() == 'verified' and 'Demo' in m)
T('sent the token and app id the way Deriv asks', seen and seen[0] == ('GET', '/trading/v1/options/accounts', TOK))
T('token never appears in the message', TOK not in m)
T('too-fast retry is refused', deriv.verify(U, good, 2001)[0] is False and status() == 'verified')
ok, m = deriv.verify(U, bad, 3000)
T('refused token -> rejected', not ok and status() == 'rejected' and TOK not in m)
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
T('saving again resets to saved', status() == 'saved')
ok, m = deriv.verify(U, down, 4000)
T('network failure keeps status, friendly message', not ok and status() == 'saved' and 'boom' not in m)
T('real-only token -> verified but warns, no demo', deriv.verify(U, lambda *a: (200, {'data': [{'account_id': 'CR9', 'account_type': 'real'}]}), 5000)[1].startswith('Deriv connected, but no demo'))
T('empty account list -> rejected', deriv.verify(U, lambda *a: (200, {'data': []}), 6000)[0] is False and status() == 'rejected')
T('otp link: wss only', deriv.ws_url(TOK, 'VRTC1', lambda *a: (200, {'data': {'url': 'wss://x/y?otp=1'}})) == 'wss://x/y?otp=1')
try: deriv.ws_url(TOK, 'VRTC1', lambda *a: (200, {'data': {'url': 'http://evil'}})); T('otp link: non-wss refused', False)
except ConnectionError: T('otp link: non-wss refused', True)
try: deriv.ws_url(TOK, '../x', good); T('bad account id refused', False)
except ValueError: T('bad account id refused', True)
os.environ['DERIV_APP_ID'] = ''
T('no DERIV_APP_ID -> clear message, no crash', deriv.verify(U, good, 7000)[0] is False)
os.environ['DERIV_APP_ID'] = '123'
T('route returns ok/message/brokers, no secret', (lambda r: r.status_code == 200 and 'message' in r.json and TOK not in r.get_data(as_text=True))(c.post('/api/brokers/Deriv/verify', headers=H('amy@x.com'))))
bad_n = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad_n), len(R))); sys.exit(1 if bad_n else 0)
