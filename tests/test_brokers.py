"""Section 1 tests (broker vault + routes). Run: python tests/test_brokers.py"""
import os, sys, tempfile, sqlite3
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_brk.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def pay(e): c.get('/api/me', headers=H(e)); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-' + e))
TOK = 'abcDEF1234567890'; KEY = 'A' * 20 + 'k3y9'; SEC = 'S' * 24 + 'z9z9'

T('no sign-in -> 401', c.get('/api/brokers').status_code == 401 and c.post('/api/brokers/Deriv', json={'token': TOK}).status_code == 401)
c.get('/api/me', headers=H('free@x.com'))
T('no plan cannot connect -> 402', c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('free@x.com')).status_code == 402)
pay('amy@x.com')
j = c.get('/api/brokers', headers=H('amy@x.com')).json
T('list starts empty, catalog has 8 brokers, vault ready', j['brokers'] == [] and len(j['catalog']) == 8 and j['ready'] is True)
r = c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
T('Deriv token saved, shown only as a short tail', r.status_code == 200 and r.json['brokers'][0]['label'] == '...7890' and TOK not in r.get_data(as_text=True))
T('new connection starts in demo mode', r.json['brokers'][0]['mode'] == 'demo' and r.json['brokers'][0]['status'] == 'saved')
raw = sqlite3.connect(os.environ['DB_PATH']).execute('SELECT secret_enc FROM broker_links').fetchone()[0]
T('stored value is encrypted, token not in the database', raw and TOK not in raw)
T('decrypts for the trading code', bk.secret('dev-amy@x.com', 'deriv') == {'token': TOK})
T('another user cannot read it', bk.secret('dev-bob@x.com', 'Deriv') is None)
st.x("INSERT INTO broker_links(uid,broker,kind,secret_enc,label,mode,status,created,updated) SELECT 'dev-bob@x.com',broker,kind,secret_enc,label,mode,status,created,updated FROM broker_links WHERE uid='dev-amy@x.com'")
T('a copied row does not open for someone else', bk.secret('dev-bob@x.com', 'Deriv') is None)
st.x("DELETE FROM broker_links WHERE uid='dev-bob@x.com'")
r = c.post('/api/brokers/Binance', json={'key': KEY, 'secret': SEC}, headers=H('amy@x.com'))
T('Binance key + secret saved, neither returned', r.status_code == 200 and KEY not in r.get_data(as_text=True) and SEC not in r.get_data(as_text=True) and bk.secret('dev-amy@x.com', 'Binance') == {'key': KEY, 'secret': SEC})
T('bad token / bad key rejected', c.post('/api/brokers/Deriv', json={'token': 'short'}, headers=H('amy@x.com')).status_code == 400 and c.post('/api/brokers/Binance', json={'key': KEY}, headers=H('amy@x.com')).status_code == 400 and c.post('/api/brokers/Deriv', json={'token': 'bad token with spaces!!'}, headers=H('amy@x.com')).status_code == 400)
T('unknown broker rejected', c.post('/api/brokers/Nope', json={'token': TOK}, headers=H('amy@x.com')).status_code == 400)
T('junk body does not crash', c.post('/api/brokers/Deriv', data='[1]', content_type='application/json', headers=H('amy@x.com')).status_code == 400)
r = c.post('/api/brokers/IC%20Markets', json={'server': 'ICMarketsSC-Demo'}, headers=H('amy@x.com'))
T('MT5 broker keeps only the server name', r.status_code == 200 and sqlite3.connect(os.environ['DB_PATH']).execute("SELECT secret_enc FROM broker_links WHERE broker='IC Markets'").fetchone()[0] is None)
T('MT5 broker needs a sane server name', c.post('/api/brokers/FBS', json={'server': '<script>'}, headers=H('amy@x.com')).status_code == 400)
c.post('/api/brokers/Deriv', json={'token': 'zzzzYYYY99998888'}, headers=H('amy@x.com'))
T('saving again replaces, no duplicate', len([b for b in c.get('/api/brokers', headers=H('amy@x.com')).json['brokers'] if b['name'] == 'Deriv']) == 1 and bk.secret('dev-amy@x.com', 'Deriv') == {'token': 'zzzzYYYY99998888'})
pay('bob@x.com')
T('users only see their own list', c.get('/api/brokers', headers=H('bob@x.com')).json['brokers'] == [])
T('remove works, and only your own', c.delete('/api/brokers/Deriv', headers=H('bob@x.com')).status_code == 200 and bk.secret('dev-amy@x.com', 'Deriv') is not None and c.delete('/api/brokers/Deriv', headers=H('amy@x.com')).status_code == 200 and bk.secret('dev-amy@x.com', 'Deriv') is None)
T('expired plan can still remove a connection', (st.x('UPDATE users SET plan_until=0 WHERE uid=?', ('dev-amy@x.com',)), c.delete('/api/brokers/Binance', headers=H('amy@x.com')).status_code)[1] == 200)
os.environ['BROKER_KEY'] = ''
pay('amy@x.com')
r = c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
T('no BROKER_KEY: refuses to save a secret (503), nothing stored', r.status_code == 503 and bk.secret('dev-amy@x.com', 'Deriv') is None and not [b for b in bk.view('dev-amy@x.com') if b['name'] == 'Deriv'])
os.environ['BROKER_KEY'] = 'unit-test-lock-key-0123456789'
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
os.environ['BROKER_KEY'] = 'a-different-lock-key-9876543210'
T('wrong lock key cannot open saved values', bk.secret('dev-amy@x.com', 'Deriv') is None)
os.environ['BROKER_KEY'] = 'unit-test-lock-key-0123456789'
T('deleting the account erases broker keys', (c.delete('/api/me', headers=H('amy@x.com')).status_code, st.q('SELECT 1 FROM broker_links WHERE uid=?', ('dev-amy@x.com',)))[1] == [])
n = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
