"""R7 tests: a person with a Deriv token and NO MT5 key gets signals (gate, snapshot, real-mode rule, status words, EA hand-out).
Fake Deriv, no network, no temp files. Run: python tests/test_deriv7.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_deriv7_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD,EURUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app, _scan
from backend import store as st, brokers as bk, deriv, links, risk, botstate, bars
st.put('course_required', '0'); st.put('practice_trades_needed', '0')          # C3: this test is about something else, so the road to Real is open for its people
deriv.kick = lambda *a, **k: None
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
TOK = 'abcDEF1234567890'; NOW = 1700000000          # a Tuesday evening, so the weekend rule stays out of the way
class Clock:
    @staticmethod
    def time(): return NOW
real_time = risk.time
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}]}
def http(m, p, t): return (200, ACC) if m == 'GET' else (200, {'data': {'url': 'wss://fake/' + p.split('/')[-2]}})
class FakeWS:
    def __init__(s, url): s.q = []
    def send(s, t):
        m = json.loads(t); n = m['req_id']
        r = {'balance': {'balance': 1000.5, 'currency': 'USD'}} if 'balance' in m else {'candles': []} if 'ticks_history' in m else {'error': {'code': 'x'}}
        s.q.append(json.dumps(dict(r, req_id=n)))
    def recv(s): return s.q.pop(0)
    def close(s): pass
def conn(url): return FakeWS(url)
yes = lambda u: True
def mk(email):
    c.get('/api/me', headers=H(email)); uid = 'dev-' + email
    st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, uid)); return uid
def deriv_person(email):
    u = mk(email); c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H(email)); deriv.verify(u, http, 100); return u
def setacct(uid, **a): a.setdefault('seen', NOW); st.put('acct:' + uid, json.dumps(a))

# ---- the real problem: Deriv token, no MT5 key ----
U = deriv_person('amy@x.com')
T('amy has no MT5 link row', links.get(U) is None)
T('before Start: the gate says the bot is off', risk.global_gate(NOW, uid=U) == (False, 'bot off'))
c.post('/api/brokers/Deriv/bot', json={'on': True}, headers=H('amy@x.com'))
T('the Deriv round runs for her', deriv.run_once(U, lambda s, u: None, yes, conn, http, NOW) == 'ok')
a = st.acct(U)
T('her balance snapshot is saved even with no MT5 link row', a.get('balance') == 1000.5 and a.get('src') == 'deriv' and a.get('demo') is True and a.get('seen'))
T('the snapshot did not create an MT5 link row', links.get(U) is None)
risk.time = Clock
T('THE FIX: the trading gate lets a Deriv-only person trade', risk.global_gate(NOW, uid=U) == (True, 'ok'))
T('a round for one person does not open the gate for another', risk.global_gate(NOW, uid='dev-nobody') == (False, 'bot off'))
c.post('/api/brokers/Deriv/bot', json={'on': False}, headers=H('amy@x.com'))
T('after Stop the gate is closed again', risk.global_gate(NOW, uid=U) == (False, 'bot off'))
c.post('/api/brokers/Deriv/bot', json={'on': True}, headers=H('amy@x.com'))

# ---- the real scanner reaches the strategies for her (not stopped at the gate) ----
rows = [[NOW - 900 * i - 3600, 2000.0, 2000.5, 1999.5, 2000.0, 0] for i in range(60, 0, -1)]
bars.merge('XAUUSD', 'M15', rows, uid=U); bars.merge('XAUUSD', 'H1', [[NOW - 3600 * i - 7200, 2000.0, 2001.0, 1999.0, 2000.0, 0] for i in range(40, 0, -1)], uid=U)
setacct(U, balance=1000.5, equity=1000.5, open=0, demo=True, allow_live=False, src='deriv')
_scan('XAUUSD', U)
n = json.loads(st.get('scan:%s:XAUUSD' % U) or '{}')
T('the scanner looked at the market for her (note is a market note, not a gate note)', n.get('c') in ('nosetup', 'signal', 'skip'))

# ---- the person's own words ----
ex = botstate.explain(U, False, True, now=NOW)
T('Bot status speaks for Deriv and says it is watching or waiting', ex.get('broker') == 'Deriv' and ex.get('state') in ('watching', 'waiting'))
T('...and the state is not stopped', ex.get('state') != 'stopped')
setacct(U, balance=1000.5, demo=True, allow_live=False, src='deriv', seen=NOW - 500)
T('a stale Deriv snapshot closes the gate (offline)', risk.global_gate(NOW, uid=U) == (False, 'EA offline'))
setacct(U, balance=1000.5, demo=True, allow_live=False, src='deriv')

# ---- real money: each broker unlocks only itself ----
setacct(U, balance=1000.5, demo=False, allow_live=True, src='deriv')
bk.set_mode(U, 'Deriv', 'demo'); bk.set_bot(U, 'Deriv', True)
T('Deriv real account with the Deriv card on Demo: refused', risk.global_gate(NOW, uid=U)[0] is False and 'real' in risk.global_gate(NOW, uid=U)[1])
bk.set_mode(U, 'Deriv', 'real'); bk.set_bot(U, 'Deriv', True)
T('Deriv real account with the Deriv card on Real: allowed', risk.global_gate(NOW, uid=U) == (True, 'ok'))
setacct(U, balance=1000.5, demo=False, allow_live=False, src='deriv')
T('Deriv real account where live is not allowed: refused', risk.global_gate(NOW, uid=U)[0] is False)
V = mk('bob@x.com'); links.new_key(V); links.set_bot(V, True); bk.set_mode(V, 'Deriv', 'real'); bk.set_bot(V, 'Deriv', True)
st.set_acct({'balance': 500, 'demo': False, 'allow_live': True}, V); st.put('acct:%s' % V, '{}')          # an MT5 bridge snapshot of a live account (no src)
T('MT5 live account with the MT5 link on Demo: refused even when the Deriv card says Real', risk.global_gate(NOW, uid=V)[0] is False)
links.set_mode(V, 'real'); links.set_bot(V, True)
T('MT5 live account with the MT5 link on Real: allowed', risk.global_gate(NOW, uid=V) == (True, 'ok'))

# ---- old MT5 behaviour is unchanged ----
W = mk('cat@x.com'); links.new_key(W); st.set_acct({'balance': 500, 'demo': True, 'open': 0}, W)
T('MT5 person, switch off: bot off', risk.global_gate(NOW, uid=W) == (False, 'bot off'))
links.set_bot(W, True)
T('MT5 person, switch on, demo bridge: ok', risk.global_gate(NOW, uid=W) == (True, 'ok'))
T('the MT5 snapshot stays in the link row', json.loads(st.q('SELECT acct FROM links WHERE uid=?', (W,), True)['acct']).get('balance') == 500 and st.get('acct:' + W) in (None, ''))

# ---- the bot may be on only for Deriv: an MT5 bridge with its own switch off is not handed the signal ----
X = deriv_person('dan@x.com'); key = links.new_key(X); links.set_bot(X, False); bk.set_bot(X, 'Deriv', True)
sid = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('XAUUSD','buy',2000,1990,2020,1,'t',2,'pending',?,?)", (int(__import__('time').time()), X))
r = c.post('/api/ea/sync', json={'account': {'balance': 500, 'demo': True}}, headers={'X-EA-Key': key}).get_json()
T('MT5 bridge with its switch off (bot on only for Deriv) gets no signal', r['signal'] is None and r['bot'] is False)
T('...and the signal stays pending for Deriv', st.q('SELECT status FROM signals WHERE id=?', (sid,), True)['status'] == 'pending')
links.set_bot(X, True)
r = c.post('/api/ea/sync', json={'account': {'balance': 500, 'demo': True}}, headers={'X-EA-Key': key}).get_json()
T('with its own switch on the MT5 bridge gets the signal', r['signal'] and r['signal']['id'] == sid)

risk.time = real_time
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
if bad: sys.exit(1)
