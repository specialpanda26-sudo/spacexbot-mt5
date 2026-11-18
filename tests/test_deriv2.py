"""Section 2, step 2 tests (Deriv candles + snapshot + scan, fake Deriv, no network). Run: python tests/test_deriv2.py"""
import os, sys, json, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_dv2.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD,EURUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk, deriv, bars, links
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
TOK = 'abcDEF1234567890'; U = 'dev-amy@x.com'; NOW = 1700000000
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}, {'account_id': 'CR9', 'account_type': 'real', 'currency': 'USD'}]}
def http(m, p, t):
    if m == 'GET': return 200, ACC
    return 200, {'data': {'url': 'wss://fake/' + p.split('/')[-2]}}
class FakeWS:
    plain_ok = True
    def __init__(s, url): s.url, s.q, s.sent = url, [], []
    def send(s, t):
        m = json.loads(t); s.sent.append(m); n = m['req_id']
        if 'balance' in m: r = {'balance': {'balance': 1000.5, 'currency': 'USD'}}
        elif 'ticks_history' in m:
            if not FakeWS.plain_ok and 'underlying_symbol' not in m: r = {'error': {'code': 'x'}}
            else:
                g = m['granularity']; last = NOW - NOW % g
                r = {'candles': [{'epoch': last - g * k, 'open': 1.0, 'high': 2.0, 'low': 0.5, 'close': 1.5} for k in range(9, -1, -1)]}
        else: r = {'error': {'code': 'unknown'}}
        s.q.append(json.dumps(dict(r, req_id=n)))
    def recv(s): return s.q.pop(0)
    def close(s): s.closed = True
made = []
def conn(url): w = FakeWS(url); made.append(w); return w
scans = []
def scan(sym, uid): scans.append((sym, uid))
yes, no = (lambda u: True), (lambda u: False)

c.get('/api/me', headers=H('amy@x.com')); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, U))
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
T('not verified yet -> nothing happens', deriv.run_once(U, scan, yes, conn, http, NOW) == 'bot off')
links.new_key(U)
T('bot off -> no connection made', deriv.run_once(U, scan, yes, conn, http, NOW) == 'bot off' and not made)
links.set_bot(U, True)
T('bot on but token not verified -> skipped', deriv.run_once(U, scan, yes, conn, http, NOW) == 'not verified' and not made)
deriv.verify(U, http, 100)
T('plan ended -> skipped, no connection', deriv.run_once(U, scan, no, conn, http, NOW) == 'plan ended' and not made)
T('verified + bot + plan -> ok', deriv.run_once(U, scan, yes, conn, http, NOW) == 'ok')
w = made[0]
T('used the demo account link (default mode demo)', w.url == 'wss://fake/VRTC1')
T('scan ran once per symbol, for this user', scans == [('XAUUSD', U), ('EURUSD', U)])
T('account snapshot saved: balance, demo, fresh', (lambda a: a['balance'] == 1000.5 and a['demo'] is True and a['allow_live'] is False and a['seen'] > 0)(st.acct(U)))
m15 = bars.get('XAUUSD', 'M15', U); h1 = bars.get('XAUUSD', 'H1', U)
T('candles stored for the user, forming candle dropped', len(m15) == 9 and len(h1) == 9 and m15[-1]['t'] + 900 <= NOW and m15[-1]['c'] == 1.5)
T('candles are private to the user', bars.get('XAUUSD', 'M15', '') == [])
T('asked Deriv for 15 min and 1 hour candles', {m.get('granularity') for m in w.sent if 'ticks_history' in m} == {900, 3600})
T('connection closed after the round', getattr(w, 'closed', False))
made.clear(); scans.clear(); FakeWS.plain_ok = False
T('works when Deriv wants underlying_symbol (fallback spelling)', deriv.run_once(U, scan, yes, conn, http, NOW) == 'ok' and len(bars.get('EURUSD', 'M15', U)) == 9)
FakeWS.plain_ok = True
made.clear(); links.set_mode(U, 'real'); links.set_bot(U, True)
T('Real mode picks the real account and allows live', deriv.run_once(U, scan, yes, conn, http, NOW) == 'ok' and made[0].url == 'wss://fake/CR9' and st.acct(U)['demo'] is False and st.acct(U)['allow_live'] is True)
made.clear(); links.set_mode(U, 'demo'); links.set_bot(U, True)
T('demo again -> demo account', deriv.run_once(U, scan, yes, conn, http, NOW) == 'ok' and made[0].url == 'wss://fake/VRTC1')
now = int(__import__('time').time())
st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('XAUUSD','buy',1,0.9,1.2,1,'t',1,'pending',?,?)", (now - 400, U))
st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('EURUSD','buy',1,0.9,1.2,1,'t',1,'pending',?,?)", (now, U))
deriv.run_once(U, scan, yes, conn, http, now)
T('old pending signal expires, fresh one stays', [r['status'] for r in st.q("SELECT status FROM signals WHERE uid=? ORDER BY created", (U,))] == ['expired', 'pending'])
os.environ['DERIV_APP_ID'] = ''
T('no DERIV_APP_ID -> off', deriv.run_once(U, scan, yes, conn, http, NOW) == 'off')
os.environ['DERIV_APP_ID'] = '123'
bad_n = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad_n), len(R))); sys.exit(1 if bad_n else 0)
