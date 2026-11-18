"""Section S1 tests: the Deriv bot runs without an MT5 key (admins too), says why when it does nothing, and the loop reports itself.
Fake Deriv, no network. Run: python tests/test_bot1.py"""
import os, sys, json
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)), '_bot1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD,EURUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk, deriv, links
deriv.kick = lambda *a, **k: None          # the background round after Start bot would reach for the network
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
TOK = 'abcDEF1234567890'; NOW = 1700000000
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}]}
def http(m, p, t): return (200, ACC) if m == 'GET' else (200, {'data': {'url': 'wss://fake/' + p.split('/')[-2]}})
class FakeWS:
    def __init__(s, url): s.url, s.q = url, []
    def send(s, t):
        m = json.loads(t); n = m['req_id']
        r = {'balance': {'balance': 1000.5, 'currency': 'USD'}} if 'balance' in m else {'candles': []} if 'ticks_history' in m else {'error': {'code': 'x'}}
        s.q.append(json.dumps(dict(r, req_id=n)))
    def recv(s): return s.q.pop(0)
    def close(s): pass
made = []
def conn(url): w = FakeWS(url); made.append(w); return w
scans = []
def scan(sym, uid): scans.append((sym, uid))
yes, no = (lambda u: True), (lambda u: False)
def mk(email, plan=True):
    c.get('/api/me', headers=H(email)); uid = 'dev-' + email
    if plan: st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, uid))
    return uid
def bot(email, on): return c.post('/api/brokers/Deriv/bot', json={'on': on}, headers=H(email))
def tile(email): return next((b for b in c.get('/api/brokers', headers=H(email)).get_json()['brokers'] if b['name'] == 'Deriv'), {})

# ---- a Deriv-only subscriber: NO MT5 key anywhere ----
U = mk('amy@x.com')
T('no token saved -> cannot start the bot', bot('amy@x.com', True).status_code == 400)
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
T('token saved but not checked -> cannot start', bot('amy@x.com', True).status_code == 400 and tile('amy@x.com')['bot'] is False)
deriv.verify(U, http, 100)
T('the person has no MT5 link row at all', links.get(U) is None)
T('before Start: tile says the bot is off, in words', deriv.run_once(U, scan, yes, conn, http, NOW) == 'bot off' and 'off' in tile('amy@x.com')['why'].lower() and not made)
r = bot('amy@x.com', True)
T('Start bot works without an MT5 key', r.status_code == 200 and [b for b in r.get_json()['brokers'] if b['name'] == 'Deriv'][0]['bot'] is True)
made.clear(); scans.clear()
T('the loop now trades for them (round ok, scanned per symbol, for them)', deriv.run_once(U, scan, yes, conn, http, NOW) == 'ok' and scans == [('XAUUSD', U), ('EURUSD', U)])
T('tile note says running', 'running' in tile('amy@x.com')['why'].lower() and tile('amy@x.com')['why_code'] == 'ok')
T('Stop bot works and the next round does nothing', bot('amy@x.com', False).status_code == 200 and (made.clear() or deriv.run_once(U, scan, yes, conn, http, NOW)) == 'bot off' and not made)
links.new_key(U); links.set_bot(U, True)
T('once the Deriv switch was used, the old MT5 switch cannot override it', deriv.run_once(U, scan, yes, conn, http, NOW) == 'bot off')
links.set_bot(U, False)

# ---- old behaviour kept: nobody ever touched the new switch, the MT5 switch still drives Deriv ----
V = mk('bob@x.com'); c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('bob@x.com')); deriv.verify(V, http, 100)
links.new_key(V); links.set_bot(V, True)
T('legacy: MT5-link switch still turns Deriv on when the new switch was never used', deriv.run_once(V, scan, yes, conn, http, NOW) == 'ok')

# ---- the owner / an admin: link routes refuse admins, the Deriv route must not ----
A = mk('boss@x.com')
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('boss@x.com')); deriv.verify(A, http, 100)
T('admin is refused by the MT5 link switch (unchanged)', c.post('/api/link/bot', json={'on': True}, headers=H('boss@x.com')).status_code == 400)
T('admin CAN start the Deriv bot', bot('boss@x.com', True).status_code == 200 and tile('boss@x.com')['bot'] is True)
scans.clear(); T('admin round runs and scans', deriv.run_once(A, scan, yes, conn, http, NOW) == 'ok' and len(scans) == 2)

# ---- rules on starting ----
W = mk('old@x.com'); c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('old@x.com')); deriv.verify(W, http, 100)
bot('old@x.com', True); st.x('UPDATE users SET plan_until=0 WHERE uid=?', (W,))
T('plan ended -> start refused 402', bot('old@x.com', True).status_code == 402)
T('plan ended -> stop still allowed', bot('old@x.com', False).status_code == 200)
from backend import assist
X = mk('cat@x.com'); c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('cat@x.com')); deriv.verify(X, http, 100)
try: assist.save(X, on=True, balance=1000, risk=1)
except Exception as e: print('assist.save:', e)
T('Phone mode on -> Start bot refused (a signal must never be traded twice)', assist.is_on(X) and bot('cat@x.com', True).status_code == 400 and tile('cat@x.com')['bot'] is False)
assist.save(X, on=False)
T('Phone mode off -> Start bot works', bot('cat@x.com', True).status_code == 200)
T('a broker that is not Deriv is told to use the MT5 app', c.post('/api/brokers/Binance/bot', json={'on': True}, headers=H('amy@x.com')).status_code == 400)
T('route needs sign-in', c.post('/api/brokers/Deriv/bot', json={'on': True}).status_code == 401)

# ---- why notes ----
os.environ['DERIV_APP_ID'] = ''
T('no DERIV_APP_ID -> round says off and the note names DERIV_APP_ID', deriv.run_once(U, scan, yes, conn, http, NOW) == 'off' and 'DERIV_APP_ID' in tile('amy@x.com')['why'])
os.environ['DERIV_APP_ID'] = '123'
bot('amy@x.com', True)
T('plan ended -> note says so', deriv.run_once(U, scan, no, conn, http, NOW) == 'plan ended' and 'plan' in tile('amy@x.com')['why'].lower())
st.put('symbols', ''); T('empty symbols list -> note says so (not a silent ok)', deriv.run_once(U, scan, yes, conn, http, NOW) == 'no symbols' and 'symbols' in tile('amy@x.com')['why'])
st.put('symbols', 'XAUUSD,EURUSD')
def boom(*a, **k): raise ConnectionError('x')
try: deriv.run_once(U, scan, yes, boom, http, NOW)
except ConnectionError: pass
T('a crash is recorded as error and still raised', tile('amy@x.com')['why_code'] == 'error')

# ---- loop ----
for e in ('amy@x.com',): bot(e, True)
os.environ['DERIV_APP_ID'] = ''
n = deriv.round_all(scan, yes)
T('loop pass visits every verified customer even with DERIV_APP_ID missing, and writes their note', n >= 3 and 'DERIV_APP_ID' in tile('amy@x.com')['why'])
os.environ['DERIV_APP_ID'] = '123'
T('loop pass leaves a heartbeat', int(st.get('deriv:beat')) > 0)

# ---- new token resets the switch ----
bot('amy@x.com', True)
c.post('/api/brokers/Deriv', json={'token': TOK + 'X'}, headers=H('amy@x.com'))
T('saving a new token turns the bot off again and clears the note', tile('amy@x.com')['bot'] is False and 'why' not in tile('amy@x.com'))
bk.set_bot(U, 'Deriv', True); bk.set_why(U, 'Deriv', 'ok')
c.delete('/api/brokers/Deriv', headers=H('amy@x.com'))
T('removing the broker forgets the switch and the note', bk.bot_flag(U, 'Deriv') is None and st.get('why:%s:Deriv' % U) is None)

# ---- admin health ----
h = c.get('/api/admin/health', headers=H('boss@x.com')).get_json()
T('health shows loop heartbeat', h.get('deriv_loop_last'))
os.environ['DERIV_APP_ID'] = ''
h = c.get('/api/admin/health', headers=H('boss@x.com')).get_json()
T('health names a missing DERIV_APP_ID', any('DERIV_APP_ID' in p for p in h['problems']))
os.environ['DERIV_APP_ID'] = '123'

try: os.remove(os.environ['DB_PATH'])
except OSError: pass
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
