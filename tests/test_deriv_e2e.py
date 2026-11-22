"""S1 proof: a person with ONLY Deriv (no MT5 key, no EA) goes from token to a closed trade. Real routes, real Deriv code, fake network only.
Run: python tests/test_deriv_e2e.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_e2e_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
os.environ.pop('DERIV_REAL', None)
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app, _scan, _paid
from backend import store as st, brokers as bk, deriv, links, bars
st.put('course_required', '0'); st.put('practice_trades_needed', '0')          # C3: this test is about something else, so the road to Real is open for its people
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []; SEEN = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def J(r): SEEN.append(r.get_data(as_text=True)); return r.get_json()
TOK, BAD = 'abcDEF1234567890', 'zzzBAD9876543210'
NOW = time.time(); D = {'bal': 1000.0, 'sold': False, 'profit': 0.0, 'buys': 0, 'real': False}

def http(m, p, t):
    if t != TOK: return 401, {}
    if m == 'GET':
        a = [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}]
        return 200, {'data': a + ([{'account_id': 'CR1', 'account_type': 'real', 'currency': 'USD'}] if D['real'] else [])}
    return 200, {'data': {'url': 'wss://fake/' + p.split('/')[-2]}}
class WS:
    def __init__(s, url): s.q = []; s.acct = url.split('/')[-1]
    def send(s, t):
        m = json.loads(t); n = m['req_id']
        if 'balance' in m: r = {'balance': {'balance': D['bal'], 'currency': 'USD'}}
        elif 'ticks_history' in m:
            g = m['granularity']; r = {'candles': [{'epoch': int(NOW // g * g) - g * i, 'open': 2000, 'high': 2001, 'low': 1999, 'close': 2000} for i in range(40, 1, -1)]}
        elif 'proposal' in m: r = {'proposal': {'id': 'q1', 'ask_price': m['amount']}}
        elif 'buy' in m: D['buys'] += 1; r = {'buy': {'contract_id': 777}}
        elif 'proposal_open_contract' in m: r = {'proposal_open_contract': {'is_sold': 1 if D['sold'] else 0, 'profit': D['profit']}}
        else: r = {'error': {'code': 'x'}}
        s.q.append(json.dumps(dict(r, req_id=n)))
    def recv(s): return s.q.pop(0)
    def close(s): pass
deriv._http = http; deriv._connect = WS
deriv.kick = lambda uid, scan, paid: deriv.run_once(uid, scan, paid)          # run the same round right away instead of in a thread

def queue(sym, uid):          # stands in for the strategies: one buy setup. (Strategy quality is covered by test_all.py, this proves the plumbing.)
    if not st.q('SELECT 1 FROM signals WHERE uid=?', (uid,), True):
        st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('XAUUSD','buy',2000,1990,2020,1,'t',2,'pending',?,?)", (int(NOW), uid))

c.get('/api/me', headers=H('zed@x.com')); U = 'dev-zed@x.com'; st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, U))
cn = J(c.get('/api/connections', headers=H('zed@x.com')))
T('1 start: nothing connected, no MT5 link', cn['state'] == 'none' and links.get(U) is None)
T('2 save token: saved, not yet checked', c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('zed@x.com')).status_code == 200 and st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'", (U,), True)['status'] == 'saved')
T('3 bot cannot start before the token is checked', c.post('/api/brokers/Deriv/bot', json={'on': True}, headers=H('zed@x.com')).status_code == 400)
v = J(c.post('/api/brokers/Deriv/verify', json={}, headers=H('zed@x.com')))
T('4 verify: ok, demo account found', v['ok'] and 'Demo' in v['message'])
t = next(b for b in J(c.get('/api/brokers', headers=H('zed@x.com')))['brokers'] if b['name'] == 'Deriv')
T('5 tile has the real balance, demo, verified', t['status'] == 'verified' and t['balance'] == 1000.0 and t['acct_demo'] is True)
cn = J(c.get('/api/connections', headers=H('zed@x.com'))); d = next(r for r in cn['rows'] if r['id'] == 'Deriv'); m = next(r for r in cn['rows'] if r['id'] == 'MT5')
T('6 Connections: Deriv ok, MT5 not set up, summary connected', d['state'] == 'ok' and m['state'] == 'none' and cn['connected'] == ['Deriv'])
T('7 Start bot works with no MT5 key and no plan problem', c.post('/api/brokers/Deriv/bot', json={'on': True}, headers=H('zed@x.com')).status_code == 200 and bk.bot_flag(U, 'Deriv') is True)
T('8 first round (real scanner, flat market): ok, no trade, no MT5 link made', bk.view(U)[0]['why_code'] == 'ok' and D['buys'] == 0 and links.get(U) is None)
T('9 real scanner ran for her and wrote a market note', json.loads(st.get('scan:%s:XAUUSD' % U) or '{}') != {})
T('10 candles were stored for her', len(bars.get('XAUUSD', 'M15', uid=U)) > 0 and len(bars.get('XAUUSD', 'H1', uid=U)) > 0)

deriv.run_once(U, queue, _paid, now=NOW)
s = st.q('SELECT * FROM signals WHERE uid=?', (U,), True)
T('11 setup became one real buy on Deriv, once', D['buys'] == 1 and s['status'] == 'open' and s['ticket'] == '777' and s['broker'] == 'Deriv')
deriv.run_once(U, queue, _paid, now=NOW)
T('12 another round never buys the same signal twice', D['buys'] == 1)
stale = dict(s, status='pending'); rq = st.q          # a second worker that read the row BEFORE the first one claimed it
st.q = lambda *x, **k: stale if (x and "status='pending' AND created>=?" in x[0]) else rq(*x, **k)
try: deriv._trade_one(deriv.Session(WS('wss://fake/VRTC1')), U, {'demo': True, 'currency': 'USD'}, 1000.0, NOW)
finally: st.q = rq
T('12b a racing second worker is stopped by the claim (still one buy)', D['buys'] == 1)
D.update(sold=True, profit=19.8, bal=1019.8); deriv.run_once(U, queue, _paid, now=NOW)
s = st.q('SELECT * FROM signals WHERE uid=?', (U,), True)
T('13 Deriv sold it: signal closed with the real profit', s['status'] == 'closed' and s['pnl'] == 19.8)
sig = J(c.get('/api/signals', headers=H('zed@x.com')))
T('14 /api/signals shows the closed trade to her', sig and sig[0]['status'] == 'closed' and sig[0]['pnl'] == 19.8)
t = next(b for b in J(c.get('/api/brokers', headers=H('zed@x.com')))['brokers'] if b['name'] == 'Deriv')
T('15 tile balance moved to 1019.8', t['balance'] == 1019.8)
T('16 profit card works for her', c.get('/api/pnl', headers=H('zed@x.com')).status_code == 200 and '19.8' in json.dumps(J(c.get('/api/pnl', headers=H('zed@x.com')))))
T('17 bot status page works', c.get('/api/botstate', headers=H('zed@x.com')).status_code == 200)

# ---- the stop rules ----
c.post('/api/brokers/Deriv/bot', json={'on': False}, headers=H('zed@x.com'))
T('18 Stop bot: next round does nothing', deriv.run_once(U, queue, _paid, now=NOW) == 'bot off')
bk.set_bot(U, 'Deriv', True); st.x('UPDATE users SET plan_until=1 WHERE uid=?', (U,))
T('19 plan ended: round refuses', deriv.run_once(U, queue, _paid, now=NOW) == 'plan ended')
st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, U))
st.x("DELETE FROM signals WHERE uid=?", (U,)); D.update(sold=False, real=True)
r = c.post('/api/brokers/Deriv/mode', json={'mode': 'real'}, headers=H('zed@x.com'))
T('20 Real mode needs the word REAL', r.status_code == 400)
c.post('/api/brokers/Deriv/mode', json={'mode': 'real', 'confirm': 'REAL'}, headers=H('zed@x.com')); bk.set_bot(U, 'Deriv', True); b0 = D['buys']
deriv.run_once(U, queue, _paid, now=NOW)
T('21 Real account is NOT traded while the owner has not set DERIV_REAL=1', D['buys'] == b0)

# ---- a wrong token never looks connected ----
c.get('/api/me', headers=H('bad@x.com')); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-bad@x.com'))
c.post('/api/brokers/Deriv', json={'token': BAD}, headers=H('bad@x.com'))
v = J(c.post('/api/brokers/Deriv/verify', json={}, headers=H('bad@x.com')))
cn = J(c.get('/api/connections', headers=H('bad@x.com')))
T('22 wrong token: rejected, never connected', v['ok'] is False and cn['state'] == 'none' and next(r for r in cn['rows'] if r['id'] == 'Deriv')['state'] == 'problem')
T('23 ...and the bot cannot be started', c.post('/api/brokers/Deriv/bot', json={'on': True}, headers=H('bad@x.com')).status_code == 400)

# ---- S1 wording: plain words, no false "connected", Binance is not called an MT5 broker ----
idx = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read(); cn = J(c.get('/api/connections', headers=H('zed@x.com')))
T('W1 MT5 popup gives three plain steps', 'Step 1 of 3' in idx and 'Connect your MT5 card' in idx)
T('W2 a saved MT5 tile says what was saved and never looks connected', 'Server name saved' in idx and 'kind!=="mt5"?" on"' in idx)
T('W3 Deriv popup has the four steps', '4. Tap Start bot' in idx)
T('W4 the MT5 card tells Deriv people to skip it', 'Using Deriv? You do not need this card' in idx)
T('W5 the MT5 card steps have the address, ServerUrl and Algo Trading', all(x in idx.split('function steps()')[1][:1800] for x in ('Allow the address', 'ServerUrl', 'Turn Algo Trading on')))
T('W6 old confusing texts are gone', 'Then make your key in the Connect MT5 card' not in idx and 'Start on a virtual account.' not in idx)
T('W7 Connection check shows an unused MT5 as one calm line', 'Skip it if you use Deriv' in idx and next(r for r in cn['rows'] if r['id'] == 'MT5')['name'].startswith('MT5 app'))
e = lambda path, body: c.post(path, json=body, headers=H('zed@x.com')).get_json()['error']
T('W8 Binance is not described as an MT5 broker', all('MT5' not in e('/api/brokers/Binance/' + w, {'on': True, 'mode': 'real'}) for w in ('bot', 'mode')) and 'does not trade yet' in e('/api/brokers/Binance/bot', {'on': True}))
T('W9 MT5 brokers still point to the MT5 card', all('MT5' in e('/api/brokers/FBS/' + w, {'on': True, 'mode': 'real'}) for w in ('bot', 'mode', 'verify')))

# ---- the token is never given back, never stored as plain text ----
raw = ' '.join(SEEN) + json.dumps(st.q('SELECT * FROM broker_links'))
T('24 the token appears in no response and not in the database', TOK not in raw and BAD not in raw)
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
if bad: sys.exit(1)
