"""Section 6 checks: the real Journal and Stats. GET /api/journal + backend/journal.py and the broker label on every trade. No network, no real broker. Run: python tests/test_jour6.py"""
import os, sys, re, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'jour6_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, journal as jn, deriv
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
A, B, O = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
NOW = int(time.time())
def sig(uid, status='closed', pnl=None, t=NOW, sym='XAUUSD', side='buy', strat='gold_scalp', broker=None, note=None):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,fill,uid,broker,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sym, side, 100.0, 99.0, 102.0, status, t - 600, pnl, t if status == 'closed' else None, strat, 100.0, uid or None, broker, note))
def J(email, q=''): return c.get('/api/journal' + q, headers=H(email)).get_json()

# ---- nothing yet: honest zeros, never sample rows ----
j = J('amy@x.com')
T('no trades: empty list, zero numbers, no brokers (never sample rows)', j['rows'] == [] and j['total'] == 0 and j['stats']['trades'] == 0 and j['stats']['net'] == 0 and j['pairs'] == [] and j['brokers'] == [])
T('no trades: profit factor is null, not a made-up number', j['stats']['profit_factor'] is None and j['stats']['win_rate'] == 0)
T('GET /api/journal needs a sign-in', c.get('/api/journal').status_code == 401)
from backend import sbauth
_v = sbauth.verify; sbauth.verify = lambda t: {'uid': 'dev-ghost', 'email': 'ghost@x.com', 'name': 'g', 'verified': False}
T('GET /api/journal needs a verified email (403)', c.get('/api/journal', headers=H('ghost@x.com')).status_code == 403); sbauth.verify = _v

# ---- which rows count ----
sig(A, 'closed', 10.0, NOW - 50, 'XAUUSD', 'buy', 'gold_scalp', 'MT5'); sig(A, 'closed', -4.0, NOW - 40, 'EURUSD', 'sell', 'ma_cross', 'MT5')
sig(A, 'closed', 6.0, NOW - 30, 'XAUUSD', 'buy', 'gold_scalp', 'Deriv'); sig(A, 'closed', -2.0, NOW - 20, 'XAUUSD', 'sell', 'gold_scalp', 'Deriv')
sig(A, 'open'); sig(A, 'pending'); sig(A, 'rejected', note='bad'); sig(A, 'expired'); sig(A, 'closed', None, NOW)            # none of these is a closed trade with a result
j = J('amy@x.com'); r = j['rows']
T('only closed trades with a profit figure are listed (open, pending, rejected, expired and no-result rows are left out)', j['total'] == 4 and len(r) == 4)
T('newest first', [x['pnl'] for x in r] == [-2.0, 6.0, -4.0, 10.0])
x = r[0]
T('a row has time, symbol, side, readable strategy name, pnl, result, broker, entry, sl, tp', x['t'] == NOW - 20 and x['symbol'] == 'XAUUSD' and x['side'] == 'sell' and x['strategy_name'] == 'Liquidity sweep scalp' and x['pnl'] == -2.0 and x['result'] == 'loss' and x['broker'] == 'Deriv' and x['entry'] == 100.0 and x['sl'] == 99.0 and x['tp'] == 102.0)
T('a win is a win and a loss is a loss', [y['result'] for y in r] == ['loss', 'win', 'loss', 'win'])

# ---- the numbers ----
s = j['stats']
T('count, wins, losses, win rate, net', s['trades'] == 4 and s['wins'] == 2 and s['losses'] == 2 and s['win_rate'] == 50.0 and s['net'] == 10.0)
T('profit factor = gross win / gross loss (16 / 6)', s['profit_factor'] == 2.67)
T('best, worst, per trade', s['best'] == 10.0 and s['worst'] == -4.0 and s['per_trade'] == 2.5)
T('break-even win rate from the average win and loss (8 and 3 -> 27.3%)', s['break_even'] == 27.3)
T('max drawdown walks the trades oldest first (10, 6, 12, 10 -> deepest dip 4)', s['max_drawdown'] == 4.0)
T('loss streak counts the longest run of losses oldest first', s['loss_streak'] == 1)
sig(A, 'closed', -1.0, NOW + 1); sig(A, 'closed', -1.0, NOW + 2); sig(A, 'closed', -1.0, NOW + 3)
T('the earlier -2 loss and three new losses after it = a streak of 4', J('amy@x.com')['stats']['loss_streak'] == 4)
st.x("DELETE FROM signals WHERE uid=? AND pnl=-1.0", (A,))
p = {o['symbol']: o for o in j['pairs']}
T('by pair: XAUUSD 3 trades, 2 won, net 14; EURUSD 1 trade net -4; most trades first', [o['symbol'] for o in j['pairs']] == ['XAUUSD', 'EURUSD'] and p['XAUUSD']['n'] == 3 and p['XAUUSD']['wins'] == 2 and p['XAUUSD']['pnl'] == 14.0 and p['XAUUSD']['win_rate'] == 67 and p['EURUSD']['pnl'] == -4.0)

# ---- the filters ----
j = J('amy@x.com', '?result=win')
T('Wins: only winning trades in the list, the numbers still cover every trade', j['total'] == 2 and all(y['result'] == 'win' for y in j['rows']) and j['stats']['trades'] == 4)
j = J('amy@x.com', '?result=loss')
T('Losses: only losing trades in the list', j['total'] == 2 and all(y['result'] == 'loss' for y in j['rows']))
T('a strange result value means All', J('amy@x.com', '?result=zzz')['total'] == 4 and J('amy@x.com', '?result=zzz')['result'] == 'all')
j = J('amy@x.com', '?broker=Deriv')
T('broker picker: Deriv only, and the numbers follow the broker (6 - 2 = 4)', j['total'] == 2 and all(y['broker'] == 'Deriv' for y in j['rows']) and j['stats']['trades'] == 2 and j['stats']['net'] == 4.0 and j['broker'] == 'Deriv')
j = J('amy@x.com', '?broker=mt5')
T('broker names are not case sensitive (mt5 = MT5): net 10 - 4 = 6', j['total'] == 2 and j['stats']['net'] == 6.0 and j['broker'] == 'MT5')
T('the list of brokers always shows every broker this person traded with (so the picker stays)', j['brokers'] == ['Deriv', 'MT5'] and J('amy@x.com', '?broker=Deriv')['brokers'] == ['Deriv', 'MT5'])
j = J('amy@x.com', '?broker=Nonsense')
T('a broker with no trades: an empty list and zero numbers, never all trades', j['total'] == 0 and j['rows'] == [] and j['stats']['trades'] == 0)
T('both filters together (Deriv + Wins = one trade)', J('amy@x.com', '?broker=Deriv&result=win')['total'] == 1)

# ---- old rows with no broker column value ----
sig(B, 'closed', 3.0, NOW, broker=None, note='x20'); sig(B, 'closed', 2.0, NOW - 5, broker=None, note=None); sig(B, 'closed', 1.0, NOW - 9, broker='MT5', note='x20')
b = {y['pnl']: y['broker'] for y in J('bob@x.com')['rows']}
T("older rows: the note 'x20' means Deriv, no note means MT5, and a saved broker always wins", b == {3.0: 'Deriv', 2.0: 'MT5', 1.0: 'MT5'})

# ---- whose trades ----
T("bob sees only bob's trades", J('bob@x.com')['total'] == 3 and J('bob@x.com')['stats']['net'] == 6.0)
T("amy never sees bob's trades", all(y['pnl'] not in (3.0, 2.0, 1.0) for y in J('amy@x.com')['rows']))
sig('', 'closed', 50.0, NOW, broker='MT5'); sig(O, 'closed', 5.0, NOW - 1, broker='Deriv')
j = J('boss@x.com')
T("the owner sees the owner's EA trades (scope '') and their own Deriv trades, nothing of amy or bob", j['total'] == 2 and sorted(y['pnl'] for y in j['rows']) == [5.0, 50.0] and j['brokers'] == ['Deriv', 'MT5'])
T("a normal person never sees the owner's EA trades", all(y['pnl'] != 50.0 for y in J('amy@x.com')['rows']) and all(y['pnl'] != 50.0 for y in J('bob@x.com')['rows']))
T('the answer carries no key, token or secret', not re.search(r'token|secret|key', json.dumps(J('amy@x.com')).lower()))

# ---- the row limit only trims the list ----
for i in range(jn.LIMIT + 20): sig(O, 'closed', 1.0, NOW - 1000 - i, broker='MT5')
j = J('boss@x.com')
T('the list is capped at LIMIT rows, the count and the numbers still cover every trade', len(j['rows']) == jn.LIMIT and j['total'] == jn.LIMIT + 22 and j['stats']['trades'] == jn.LIMIT + 22)

# ---- every trade that opens says which broker opened it ----
sid = sig(A, 'sent'); c.post('/api/ea/report', json={'id': sid, 'status': 'open', 'ticket': 9, 'lots': 0.1, 'price': 100.5}, headers={'X-EA-Key': 'k'})   # owner EA
T("the owner's EA open report cannot touch someone else's row", st.q('SELECT broker FROM signals WHERE id=?', (sid,), True)['broker'] is None)
import backend.links as links
key = links.new_key(A) if hasattr(links, 'new_key') else None
if key:
    c.post('/api/ea/report', json={'id': sid, 'status': 'open', 'ticket': 9, 'lots': 0.1, 'price': 100.5}, headers={'X-EA-Key': key})
    T("a subscriber's EA reporting a trade open labels it MT5", st.q('SELECT broker,status FROM signals WHERE id=?', (sid,), True) == {'broker': 'MT5', 'status': 'open'})
    c.post('/api/ea/report', json={'id': sid, 'status': 'closed', 'pnl': 7.5}, headers={'X-EA-Key': key})
    T('and when it closes it shows in her Journal with the MT5 label', [(y['pnl'], y['broker']) for y in J('amy@x.com')['rows'] if y['id'] == sid] == [(7.5, 'MT5')])
sid2 = sig('', 'pending')
c.post('/api/ea/report', json={'id': sid2, 'status': 'open', 'ticket': 1, 'lots': 0.1, 'price': 100}, headers={'X-EA-Key': 'k'})
T("the owner's EA open report labels the trade MT5", st.q('SELECT broker FROM signals WHERE id=?', (sid2,), True)['broker'] == 'MT5')
sid3 = sig(B, 'pending', t=NOW + 600)      # created = NOW, so it is fresh enough to trade
_p, _b, _r, _s = deriv._place, deriv._bot, deriv._report, deriv._resnap
deriv._place = lambda sess, s, bal, cur: ('open', {'contract_id': 555, 'stake': 5.0, 'mult': 20}); deriv._bot = lambda uid: True; deriv._report = lambda *a, **k: None; deriv._resnap = lambda *a, **k: None
deriv._trade(None, B, {'demo': True, 'currency': 'USD'}, 1000.0, NOW)
deriv._place, deriv._bot, deriv._report, deriv._resnap = _p, _b, _r, _s
T('a trade Deriv opens is labelled Deriv', st.q('SELECT broker,status,note FROM signals WHERE id=?', (sid3,), True) == {'broker': 'Deriv', 'status': 'open', 'note': 'x20'})
T('the broker column exists in the Postgres schema too', 'ADD COLUMN IF NOT EXISTS broker TEXT' in open(os.path.join(ROOT, 'backend', 'store.py')).read() and 'ADD COLUMN IF NOT EXISTS broker TEXT' in open(os.path.join(ROOT, 'supabase_schema.sql')).read())

bad_n = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad_n), len(R)))
for f in glob.glob(DB + '*'): os.remove(f)
sys.exit(1 if bad_n else 0)
