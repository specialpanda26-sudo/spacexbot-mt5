"""Section 2: Binance key check + balance read (read-only). Binance is faked, no network. Run: python tests/test_binance.py"""
import os, sys, json, hmac, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'bn_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', BROKER_KEY='0123456789abcdef0123')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import store as st, brokers as bk, binance as B
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
H = lambda e: {'Authorization': 'Bearer dev:' + e}
KEY = 'K' * 64; SEC = 'S' * 64
c = app.test_client(); U = 'dev-amy@x.com'
st.x('INSERT OR REPLACE INTO users(uid,email,name,plan_until,created) VALUES(?,?,?,?,?)', (U, 'amy@x.com', 'Amy', 4102444800, 1))
c.get('/api/me', headers=H('amy@x.com'))
st.x('UPDATE users SET plan_until=4102444800 WHERE uid=?', (U,))

calls = []
state = {'restr': {'enableReading': True, 'enableWithdrawals': False, 'enableSpotAndMarginTrading': True},
         'acct': (200, {'balances': [{'asset': 'USDT', 'free': '100.50', 'locked': '0'}, {'asset': 'BTC', 'free': '0.01', 'locked': '0.01'}, {'asset': 'ZZZ', 'free': '5', 'locked': '0'}, {'asset': 'ETH', 'free': '0', 'locked': '0'}]}),
         'restr_code': 200}
PRICES = [{'symbol': 'BTCUSDT', 'price': '50000'}, {'symbol': 'ETHUSDT', 'price': '3000'}]
def fake(path, key, params):
    calls.append((path, key, dict(params)))
    if path == '/api/v3/time': return 200, {'serverTime': 1700000000000}
    if path == '/api/v3/ticker/price': return 200, PRICES
    if path == '/sapi/v1/account/apiRestrictions': return state['restr_code'], state['restr']
    if path == '/api/v3/account': return state['acct']
    return 404, {}
T('nothing saved yet -> asks to save first', B.verify(U, fake, 1000) == (False, 'Save your Binance key and secret first.'))
r = c.post('/api/brokers/Binance', json={'key': KEY, 'secret': SEC}, headers=H('amy@x.com'))
T('save works and returns no secret', r.status_code == 200 and KEY not in r.get_data(as_text=True) and SEC not in r.get_data(as_text=True))
T('saved key is not checked yet', next(b for b in bk.view(U) if b['name'] == 'Binance')['status'] == 'saved')

ok, msg = B.verify(U, fake, 2000)
T('good key -> ok, balance read', ok and 'Spot balance' in msg)
v = next(b for b in bk.view(U) if b['name'] == 'Binance')
T('status verified, balance = 100.50 + 0.02 BTC x 50000 = 1100.50 (unpriced ZZZ skipped)', v['status'] == 'verified' and v['balance'] == 1100.5 and v['currency'] == 'USD' and v['acct_demo'] is False)
T('the note says one asset could not be priced', '1 small asset' in v['note'])
T('the real-key read-only check still says it never orders (5B-2b: the demo check is binance_bot.verify)', v['trades'] is True and 'never places a Binance order' in v['note'])
T('key goes in a header, secret is never sent', all(k in (None, KEY) for _, k, _ in calls) and all(SEC not in json.dumps(p) for _, _, p in calls))
acc = next(x for x in calls if x[0] == '/api/v3/account'); p = dict(acc[2]); sig = p.pop('signature')
q = '&'.join('%s=%s' % (k, p[k]) for k in p)
T('signature is HMAC-SHA256 of the query with the secret', sig == hmac.new(SEC.encode(), q.encode(), hashlib.sha256).hexdigest())
T('uses Binance server time', p['timestamp'] == 1700000000000)
T('only read addresses were called, only through the one door', {x[0] for x in calls} <= set(B.ALLOWED) and not any('order' in x[0] for x in calls))
try: B._get('/api/v3/order', KEY, SEC, http=fake); T('an order address is refused', False)
except ValueError: T('an order address is refused', True)
T('too fast -> asked to wait', B.verify(U, fake, 2001) == (False, 'Wait a few seconds and try again.'))

state['restr'] = dict(state['restr'], enableWithdrawals=True)
ok, msg = B.verify(U, fake, 3000)
T('key that can withdraw is refused and marked rejected', not ok and 'WITHDRAW' in msg and next(b for b in bk.view(U) if b['name'] == 'Binance')['status'] == 'rejected')
state['restr'] = {'enableReading': False, 'enableWithdrawals': False}
ok, msg = B.verify(U, fake, 4000); T('key without Enable Reading is refused', not ok and 'Enable Reading' in msg)
state['restr'] = {'enableReading': True, 'enableWithdrawals': False}
state['restr_code'] = 401; state['restr'] = {'code': -2015, 'msg': 'Invalid API-key, IP, or permissions'}
ok, msg = B.verify(U, fake, 5000)
T('wrong key (-2015) -> rejected with plain words', not ok and 'did not accept' in msg and next(b for b in bk.view(U) if b['name'] == 'Binance')['status'] == 'rejected')
state['restr_code'] = 400; state['restr'] = {'code': -1022}
ok, msg = B.verify(U, fake, 6000); T('bad signature (-1022) -> secret does not match', not ok and 'secret does not match' in msg)
state['restr_code'] = 451; state['restr'] = {}
before = next(b for b in bk.view(U) if b['name'] == 'Binance')['status']
ok, msg = B.verify(U, fake, 7000)
T('country block (451) -> explained, BINANCE_BASE named, status not changed', not ok and 'BINANCE_BASE' in msg and next(b for b in bk.view(U) if b['name'] == 'Binance')['status'] == before)
state['restr_code'] = 503; state['restr'] = {}
ok, msg = B.verify(U, fake, 8000); T('Binance down -> try later, no crash', not ok and 'not answering' in msg)
def boom(path, key, params): raise RuntimeError('secret ' + SEC + ' key ' + KEY)
ok, msg = B.verify(U, boom, 9000); T('network error is explained and never shows the key or secret', not ok and KEY not in msg and SEC not in msg)

# recovered key works again; a good re-check clears the old reject
state['restr_code'] = 200; state['restr'] = {'enableReading': True, 'enableWithdrawals': False}
ok, msg = B.verify(U, fake, 10000); T('good key after a bad one -> verified again', ok and next(b for b in bk.view(U) if b['name'] == 'Binance')['status'] == 'verified')
st.x("DELETE FROM kv WHERE k LIKE 'bal:%'")
state['acct'] = (200, {'balances': []})
ok, msg = B.verify(U, fake, 11000)
T('empty wallet reads as $0.00, not as fake money', ok and next(b for b in bk.view(U) if b['name'] == 'Binance')['balance'] == 0)

# routes
T('route: no sign-in -> 401', c.post('/api/brokers/Binance/verify').status_code == 401)
B._last.clear()
import backend.binance as BB; BB._http = fake
state['acct'] = (200, {'balances': [{'asset': 'USDT', 'free': '7', 'locked': '0'}]})
bk.set_mode(U, 'Binance', 'real')          # 5B-2b: demo = testnet key (test_bn2b.py); real keeps this read-only check
r = c.post('/api/brokers/Binance/verify', headers=H('amy@x.com')).get_json()
T('route: verify returns ok + the tile row with balance 7', r['ok'] and next(b for b in r['brokers'] if b['name'] == 'Binance')['balance'] == 7)
T('route: Binance bot is refused until it is chosen and checked, and it has no demo/real switch', c.post('/api/brokers/Binance/bot', json={'on': True}, headers=H('amy@x.com')).status_code == 400 and c.post('/api/brokers/Binance/mode', json={'mode': 'real', 'confirm': 'REAL'}, headers=H('amy@x.com')).status_code == 400)
T('route: an MT5 broker is still told to use the MT5 app', 'MT5' in c.post('/api/brokers/FBS/verify', headers=H('amy@x.com')).get_json()['error'])
cat = {x['name']: x for x in c.get('/api/brokers', headers=H('amy@x.com')).get_json()['catalog']}
T('every broker says exactly what works and what does not', all(cat[n].get('tile') and cat[n].get('works') and cat[n].get('not') for n in cat))
T('Binance says read-only / no trading, Deriv says demo bot, MT5 says via MT5 app', 'testnet' in cat['Binance']['tile'].lower() and 'demo' in cat['Deriv']['tile'].lower() and 'MT5' in cat['FBS']['tile'])
T('saving a new key forgets the old balance and note', (c.post('/api/brokers/Binance', json={'key': 'A' * 40, 'secret': 'B' * 40}, headers=H('amy@x.com')), next(b for b in bk.view(U) if b['name'] == 'Binance'))[1].get('balance') is None)
other = c.get('/api/brokers', headers=H('bob@x.com')).get_json()['brokers']
T("one person never sees another person's Binance row", other == [])
src = open(os.path.join(HERE, '..', 'backend', 'binance.py')).read()
T('the Binance file has no order, trade, withdraw, post or delete call', not any(w in src.lower().replace('withdrawals', '').replace('withdraw money', '').replace('can withdraw', '') for w in ('requests.post', 'requests.delete', '/api/v3/order', 'order/test', 'method=\'post\'')))
idx = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('page: Binance help says Withdrawals OFF and no Binance orders', 'Withdrawals OFF' in idx and 'testnet.binance.vision' in idx and 'never places a Binance order' not in idx and 'Create an API key with trading only' not in idx)
T('page: Binance key is checked after saving, and can be checked again', '"/api/brokers/"+n+"/verify"' in idx and 'id="pC"' in idx and 'Testnet demo' in idx)
T('page: tiles and Connect card show the Works now / Not yet lines', 'Works now:' in idx and 'Not yet:' in idx and 'CAT[p[0]].tile' in idx)
print('\n%d/%d passed' % (sum(R), len(R))); os.path.exists(DB) and os.remove(DB); sys.exit(0 if all(R) else 1)
