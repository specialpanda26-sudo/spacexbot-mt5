"""D1 tests: Deriv switched on by DERIV_CLIENT_ID alone, and an ended login is handled (fake Deriv, no network). Run: python tests/test_d1flow.py"""
import os, sys, json, time, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_d1.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
os.environ.pop('DERIV_APP_ID', None); os.environ['DERIV_CLIENT_ID'] = 'app777'
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk, deriv, links, envcheck
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
TOK = 'abcDEF1234567890'; U = 'dev-amy@x.com'; NOW = int(time.time())
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}]}
class WS:
    def __init__(s, url): s.q = []
    def send(s, t): m = json.loads(t); s.q.append(json.dumps({'balance': {'balance': 500.0, 'currency': 'USD'}, 'req_id': m['req_id']}))
    def recv(s): return s.q.pop(0)
    def close(s): pass
conn = lambda url: WS(url)
def http_ok(m, p, t): return (200, ACC) if m == 'GET' else (200, {'data': {'url': 'wss://fake/x'}})
def http_401(m, p, t): return (401, {})
yes = lambda u: True
def scan(sym, uid): pass

# --- 1) only DERIV_CLIENT_ID is set ---
T('ON() is true with only DERIV_CLIENT_ID', deriv.ON() is True and deriv.APP() == '')
c.get('/api/me', headers=H('amy@x.com')); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, U))
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
ok, msg = deriv.verify(U, http_ok, 100, conn)
T('token check works without DERIV_APP_ID', ok and 'connected' in msg.lower())
# the header: sent only when DERIV_APP_ID itself is set (read the real request headers through a fake requests module)
import types
seen = []
class FR:
    status_code = 200
    def json(s): return ACC
def fake_request(method, url, data=None, timeout=0, headers=None): seen.append(dict(headers or {})); return FR()
sys.modules['requests'] = types.SimpleNamespace(request=fake_request)
deriv._http('GET', '/trading/v1/options/accounts', TOK)
T('no Deriv-App-ID header when DERIV_APP_ID is not set', 'Deriv-App-ID' not in seen[-1] and seen[-1]['Authorization'] == 'Bearer ' + TOK)
os.environ['DERIV_APP_ID'] = '123'; deriv._http('GET', '/x', TOK)
T('Deriv-App-ID header sent when DERIV_APP_ID is set', seen[-1].get('Deriv-App-ID') == '123')
os.environ.pop('DERIV_APP_ID')
del sys.modules['requests']

# --- 2) neither set: unchanged behaviour ---
os.environ.pop('DERIV_CLIENT_ID')
T('ON() false with neither variable', deriv.ON() is False)
ok, msg = deriv.verify(U, http_ok, 200, conn)
T('neither set -> not switched on, as before', not ok and 'not switched on' in msg)
T('run_once says off with neither set', deriv.run_once(U, scan, yes, conn, http_ok, NOW) == 'off')
os.environ['DERIV_CLIENT_ID'] = 'app777'

# --- 3) the login ended ---
deriv.verify(U, http_ok, 300, conn)
links.new_key(U); links.set_bot(U, True); bk.set_bot(U, 'Deriv', True)
T('before: round runs fine', deriv.run_once(U, scan, yes, conn, http_ok, NOW) in ('ok', 'no symbols'))
r = deriv.run_once(U, scan, yes, conn, http_401, NOW)
T('Deriv says 401 -> login ended (not "error")', r == 'login ended')
T('status is now rejected', st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'", (U,), True)['status'] == 'rejected')
T('bot switched off', bk.bot_flag(U, 'Deriv') is False)
v = next(x for x in bk.view(U) if x['name'] == 'Deriv')
T('the tile says it in plain words', v['why_code'] == 'login ended' and 'Log in with Deriv' in v['why'])
T('the minute loop skips a rejected login (no more asking Deriv)', deriv.round_all(scan, yes) == 0)
rows = envcheck.report({'BROKER_KEY': 'x' * 20, 'DERIV_CLIENT_ID': 'app777'}); lv = lambda k: next((r['level'] for r in rows if r['key'] == k), None)
T('server health does not flag Deriv when only DERIV_CLIENT_ID is set', lv('DERIV_APP_ID') is None and lv('DERIV_CLIENT_ID') == 'ok')
rows2 = envcheck.report({'BROKER_KEY': 'x' * 20}); T('neither variable set is still red', next((r['level'] for r in rows2 if r['key'] == 'DERIV_APP_ID'), None) == 'bad')
T('token never in a tile note', TOK not in json.dumps(bk.view(U)))
bad_n = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad_n), len(R))); sys.exit(1 if bad_n else 0)
