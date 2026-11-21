"""Piece 1 tests: balance on the broker tiles (fake Deriv, no network). Run: python tests/test_deriv3.py"""
import os, sys, json, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_dv3.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk, deriv, links
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
TOK = 'abcDEF1234567890'; U = 'dev-amy@x.com'; V = 'dev-bob@x.com'
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}]}
def http(m, p, t): return (200, ACC) if m == 'GET' else (200, {'data': {'url': 'wss://fake'}})
class FW:
    def __init__(s, u): s.q = []
    def send(s, t): m = json.loads(t); s.q.append(json.dumps({'balance': {'balance': 250.75, 'currency': 'USD'}, 'req_id': m['req_id']}))
    def recv(s): return s.q.pop(0)
    def close(s): pass
for e in ('amy@x.com', 'bob@x.com'): c.get('/api/me', headers=H(e)); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-' + e))
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
def mine(): return [b for b in c.get('/api/brokers', headers=H('amy@x.com')).json['brokers'] if b['name'] == 'Deriv'][0]
T('saved, no balance yet', 'balance' not in mine())
ok, m = deriv.verify(U, http, 100, FW)
T('verify shows the balance right away', ok and mine().get('balance') == 250.75 and mine()['acct_demo'] is True and mine()['currency'] == 'USD')
T('balance is private to its owner', all('balance' not in b for b in c.get('/api/brokers', headers=H('bob@x.com')).json['brokers']))
T('balance failure never breaks verify', deriv.verify(U, http, 200, lambda u: 1 / 0)[0] is True)
bk.set_bal(U, 'Deriv', 300, '<b>x</b>', False); b = mine()
T('currency is sanitised, real flag kept', b['currency'] == 'USD' and b['acct_demo'] is False and b['balance'] == 300.0)
c.post('/api/brokers/Deriv', json={'token': 'zzzzYYYY99998888'}, headers=H('amy@x.com'))
T('new token forgets the old balance', 'balance' not in mine())
bk.set_bal(U, 'Deriv', 5, 'USD', True); c.delete('/api/brokers/Deriv', headers=H('amy@x.com'))
T('remove deletes the balance too', st.q("SELECT k FROM kv WHERE k LIKE 'bal:%'") == [])
html = open(os.path.join(os.path.dirname(__file__), '..', 'static', 'index.html')).read()
T('tile code + style present', 'function plB' in html and '.pt small .bal.r' in html and 'setInterval(function(){if(!document.hidden)ldB()},60000)' in html)
bad_n = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad_n), len(R))); sys.exit(1 if bad_n else 0)
