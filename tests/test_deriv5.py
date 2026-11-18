"""Section 2, step 3 tests: place and follow Deriv trades (fake Deriv, no network). Run: python tests/test_deriv5.py"""
import os, sys, json, time, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_dv5.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
os.environ.pop('DERIV_REAL', None)
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk, deriv, links
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
TOK = 'abcDEF1234567890'; U = 'dev-amy@x.com'; V = 'dev-bob@x.com'; NOW = int(time.time())
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}, {'account_id': 'CR9', 'account_type': 'real', 'currency': 'USD'}]}
def http(m, p, t): return (200, ACC) if m == 'GET' else (200, {'data': {'url': 'wss://fake/' + p.split('/')[-2]}})
class FakeWS:
    bad_mults = set(); proposal_err = False; buy_err = False; sold = {}; buys = []; seen = []
    def __init__(s, url): s.url, s.q = url, []
    def send(s, t):
        m = json.loads(t); FakeWS.seen.append(m); n = m['req_id']
        if 'balance' in m: r = {'balance': {'balance': 1000.0, 'currency': 'USD'}}
        elif 'ticks_history' in m: r = {'error': {'code': 'none'}}
        elif 'proposal' in m and 'contract_type' in m:
            if FakeWS.proposal_err or m['multiplier'] in FakeWS.bad_mults: r = {'error': {'message': 'Multiplier not allowed'}}
            else: r = {'proposal': {'id': 'P%d' % m['multiplier'], 'ask_price': m['amount']}}
        elif 'buy' in m:
            if FakeWS.buy_err: r = {'error': {'message': 'Insufficient balance'}}
            else: FakeWS.buys.append(m); r = {'buy': {'contract_id': 777000 + len(FakeWS.buys), 'buy_price': m['price']}}
        elif 'proposal_open_contract' in m:
            cid = m['contract_id']; r = {'proposal_open_contract': {'contract_id': cid, 'is_sold': 1 if cid in FakeWS.sold else 0, 'profit': FakeWS.sold.get(cid, 0)}}
        else: r = {'error': {'code': 'unknown'}}
        s.q.append(json.dumps(dict(r, req_id=n)))
    def recv(s): return s.q.pop(0)
    def close(s): pass
made = []
def conn(url): w = FakeWS(url); made.append(w); return w
def scan(sym, uid): pass
yes = lambda u: True
def sig(uid, side='buy', entry=2000.0, sl=1994.0, tp=2012.0, age=0, status='pending'):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('XAUUSD',?,?,?,?,1.0,'t',1,?,?,?)", (side, entry, sl, tp, status, NOW - age, uid))
def row(i): return st.q('SELECT * FROM signals WHERE id=?', (i,), True)
def rnd(uid=U): return deriv.run_once(uid, scan, yes, conn, http, NOW)

# --- sizing maths ---
z = deriv._size(2000, 1994, 2012, 1000, 1.0, 100)
T('stake: losing at the stop = 1% of 1000 -> stake 33.33, stop $10, target $20 (RR 2)', z == (33.33, 10.0, 20.0))
T('sell side uses distances, same numbers', deriv._size(2000, 2006, 1988, 1000, 1.0, 100) == (33.33, 10.0, 20.0))
T('stake too big for the account -> no', deriv._size(2000, 1999.9, 2000.2, 1000, 1.0, 5) is None)
T('stake below Deriv minimum -> no', deriv._size(2000, 1900, 2200, 20, 0.1, 100) is None)
T('junk numbers -> no, no crash', deriv._size(None, 1, 2, 1000, 1, 100) is None and deriv._size(5, 5, 6, 1000, 1, 100) is None)

# --- set up a verified, paid, bot-on customer ---
for e in ('amy@x.com', 'bob@x.com'): c.get('/api/me', headers=H(e)); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-' + e))
for e in ('amy@x.com', 'bob@x.com'):
    c.post('/api/brokers/Deriv', json={'token': TOK + e[:3]}, headers=H(e)); deriv.verify('dev-' + e, http, 100)
    links.new_key('dev-' + e); links.set_bot('dev-' + e, True)

a = sig(U)
T('a fresh signal is bought once', rnd() == 'ok' and len(FakeWS.buys) == 1 and row(a)['status'] == 'open')
b = FakeWS.buys[0]; prop = [m for m in FakeWS.seen if 'contract_type' in m][0]
T('buy side -> MULTUP on the Deriv gold symbol, demo account', prop['contract_type'] == 'MULTUP' and prop['underlying_symbol'] == 'frxXAUUSD' and made[-1].url == 'wss://fake/VRTC1')
T('stake, multiplier, stop and target amounts sent', prop['amount'] == 33.33 and prop['multiplier'] == 100 and prop['limit_order'] == {'stop_loss': 10.0, 'take_profit': 20.0} and prop['basis'] == 'stake')
T('bought by the quote id with a price cap', b['buy'] == 'P100' and b['price'] == 33.33)
r = row(a); T('trade recorded: ticket, stake, note', r['ticket'] == '777001' and r['lots'] == 33.33 and r['note'] == 'x100')
n = len(FakeWS.buys); rnd(); rnd()
T('running again never buys the same signal twice', len(FakeWS.buys) == n)
T('open count shown to the gates', st.acct(U)['open'] == 1)

# --- following the trade ---
FakeWS.sold = {}; rnd()
T('still running -> stays open', row(a)['status'] == 'open')
FakeWS.sold = {777001: 20.0}; rnd()
r = row(a); T('sold at profit -> closed with pnl +20', r['status'] == 'closed' and r['pnl'] == 20.0 and r['closed'])
T('open count back to 0 after close', st.acct(U)['open'] == 0)
rep = sum(1 for x in [row(a)] if x['pnl'] == 20.0); n = len(FakeWS.buys); rnd()
T('closing is recorded once', row(a)['pnl'] == 20.0 and len(FakeWS.buys) == n)

# --- losing trade, sell side, other customer isolation ---
a2 = sig(U, 'sell', 2000.0, 2006.0, 1988.0); sig(V)
FakeWS.buys.clear(); FakeWS.seen.clear(); rnd(); rnd(V)
T('sell side -> MULTDOWN', any(m.get('contract_type') == 'MULTDOWN' for m in FakeWS.seen))
T("each customer's signal went to their own connection", len(FakeWS.buys) == 2)
FakeWS.sold = {int(row(a2)['ticket']): -10.0}; rnd()
T('loss recorded as -10', row(a2)['status'] == 'closed' and row(a2)['pnl'] == -10.0)
T("bob's trade untouched by amy's round", st.q("SELECT status FROM signals WHERE uid=? ORDER BY id DESC LIMIT 1", (V,), True)['status'] == 'open')

# --- failures ---
FakeWS.sold = {}; deriv._mult_ok.clear(); FakeWS.bad_mults = {100, 200}; FakeWS.seen.clear(); FakeWS.buys.clear()
a3 = sig(U); rnd()
T('multiplier refused -> tries the next one that fits', row(a3)['status'] == 'open' and row(a3)['note'] == 'x50' and deriv._mult_ok['XAUUSD'] == 50)
FakeWS.bad_mults = set(); a4 = sig(U); FakeWS.seen.clear(); rnd()
T('remembers the multiplier that worked', [m for m in FakeWS.seen if 'contract_type' in m][0]['multiplier'] == 50)
FakeWS.proposal_err = True; a5 = sig(U); rnd(); r = row(a5)
T('no quote at all -> rejected with a reason, nothing bought', r['status'] == 'rejected' and 'Multiplier' in r['note'])
FakeWS.proposal_err = False; FakeWS.buy_err = True; a6 = sig(U); rnd(); r = row(a6)
T('buy refused -> rejected with Deriv reason', r['status'] == 'rejected' and 'Insufficient' in r['note'])
FakeWS.buy_err = False
a7 = sig(U, age=300)
rnd(); T('stale signal is never traded', row(a7)['status'] == 'expired')
links.set_bot(U, False); a8 = sig(U); FakeWS.buys.clear(); rnd()
T('bot off -> nothing bought', not FakeWS.buys and row(a8)['status'] == 'pending')
links.set_bot(U, True)

# --- real money guard ---
links.set_mode(U, 'real'); links.set_bot(U, True); st.x("UPDATE signals SET status='expired' WHERE uid=?", (U,)); a9 = sig(U); FakeWS.buys.clear(); made.clear(); rnd()
T('real account without DERIV_REAL=1 -> no trade, signal left alone', made[-1].url == 'wss://fake/CR9' and not FakeWS.buys and row(a9)['status'] == 'pending')
os.environ['DERIV_REAL'] = '1'; rnd()
T('with DERIV_REAL=1 and Real mode -> trades on the real account', len(FakeWS.buys) == 1 and row(a9)['status'] == 'open')
os.environ.pop('DERIV_REAL')
T('token never stored in the trade notes', all(TOK not in (x['note'] or '') for x in st.q('SELECT note FROM signals')))
bad_n = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad_n), len(R))); sys.exit(1 if bad_n else 0)
