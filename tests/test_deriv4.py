"""Wrong token must never look connected (fake Deriv, no network). Run: python tests/test_deriv4.py"""
import os, sys, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_dv4.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk, deriv
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c.get('/api/me', headers=H('amy@x.com')); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-amy@x.com'))
U = 'dev-amy@x.com'
def status(): return [b['status'] for b in bk.view(U) if b['name'] == 'Deriv'][0]
c.post('/api/brokers/Deriv', json={'token': 'wrongWRONG12345678'}, headers=H('amy@x.com'))
T('a saved token starts as "saved", not verified', status() == 'saved')
for i, code in enumerate((400, 401, 403)):
    c.post('/api/brokers/Deriv', json={'token': 'wrongWRONG12345678'}, headers=H('amy@x.com'))
    ok, m = deriv.verify(U, lambda *a, code=code: (code, {}), 1000 * (i + 1))
    T('Deriv says HTTP %d -> rejected' % code, not ok and status() == 'rejected')
html = open(os.path.join(os.path.dirname(__file__), '..', 'static', 'index.html')).read()
T('tile says "Not checked"/"Token rejected", never plain Connected for a saved key', 'function plT' in html and 'Saved, not checked' in html and 'Token rejected' in html and 'plT(CN[p[0]])' in html)
T('wrong token keeps the box open with the error', 'go.disabled=false;er.textContent=(r&&r.message)' in html)
T('no more "connected" toast for unchecked brokers', 'tst(n+" connected")' not in html)
bad_n = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad_n), len(R))); sys.exit(1 if bad_n else 0)
