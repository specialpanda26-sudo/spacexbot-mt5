"""Section 9B checks: the chart pop-up data for one closed trade. GET /api/trade/<id> + backend/tradeview.py. No network, no real broker. Run: python tests/test_trade9b.py"""
import os, sys, glob, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'trade9b_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, bars, tradeview as tv, pnlcard as pc
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
A, B, O = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
T0 = 1700000000 - 1700000000 % 900          # a quarter-hour boundary
def sig(uid, pnl=5.0, opened=T0, closed=T0 + 3600, status='closed', sym='XAUUSD', entry=100.0, sl=99.0, tp=102.0, fill=100.2, lots=0.1, broker='MT5', side='buy'):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,fill,lots,uid,broker) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sym, side, entry, sl, tp, status, opened, pnl, closed if status == 'closed' else None, 'gold_scalp', fill, lots, uid, broker))
def G(email, tid): return c.get('/api/trade/%s' % tid, headers=H(email))
def J(email, tid): return G(email, tid).get_json()
def candle_rows(sym, uid, start, n, step=900, base=100.0):
    return [[start + i * step, base + i * 0.01, base + i * 0.01 + 0.5, base + i * 0.01 - 0.5, base + i * 0.01 + 0.1, 1] for i in range(n)]

# ---- who may ask, and what counts as a trade ----
t1 = sig(A)
T('signed out: refused, nothing leaks', c.get('/api/trade/%d' % t1).status_code == 401)
d = J('amy@x.com', t1)
T('own closed trade: 200 with its id, symbol, side, broker and strategy', G('amy@x.com', t1).status_code == 200 and d['id'] == t1 and d['symbol'] == 'XAUUSD' and d['side'] == 'buy' and d['broker'] == 'MT5' and d['strategy'] == 'gold_scalp')
T("someone else's trade: 404, same as a trade that does not exist (no way to probe other people's ids)", G('bob@x.com', t1).status_code == 404 and G('amy@x.com', 999999).status_code == 404 and G('bob@x.com', t1).get_json() == G('amy@x.com', 999999).get_json())
T('a trade that is not closed (open, pending, rejected, expired) is never shown, even if it carries a floating profit figure', all(G('amy@x.com', sig(A, 1.5, status=s)).status_code == 404 for s in ('open', 'pending', 'sent', 'rejected', 'expired')))
T('a closed trade with no profit figure, or a broken one, is never shown', G('amy@x.com', sig(A, None)).status_code == 404 and G('amy@x.com', sig(A, float('inf'))).status_code == 404)
T('an id that is not a number: 404, not a crash', c.get('/api/trade/abc', headers=H('amy@x.com')).status_code == 404 and tv.detail(A, False, 'abc') is None and tv.detail(A, False, None) is None)

# ---- what the server really stored ----
T('prices are exactly the stored ones (planned entry, fill, stop loss, take profit)', d['levels'] == {'entry': 100.0, 'fill': 100.2, 'sl': 99.0, 'tp': 102.0})
T('lots, profit, win/loss, opened and closed come from the row', d['lots'] == 0.1 and d['pnl'] == 5.0 and d['result'] == 'win' and d['opened'] == T0 and d['closed'] == T0 + 3600)
T('a losing trade says loss', J('amy@x.com', sig(A, -3.5))['result'] == 'loss' and J('amy@x.com', sig(A, -3.5))['pnl'] == -3.5)
T('NO exit price and NO close reason: the server never stored them, and the answer says so in plain words', d['exit']['recorded'] is False and d['exit']['price'] is None and d['exit']['reason'] is None and 'not recorded' in d['exit']['note'])
T('there is no key in the answer that could carry an exit price, a close reason or a guess', not any(k in d for k in ('exit_price', 'close_price', 'close', 'reason', 'result_reason', 'hit_tp', 'hit_sl')) and 'exit_price' not in d['exit'] and 'tp_hit' not in d['exit'])
T('a missing, zero, negative or broken price is left out (None), never invented', J('amy@x.com', sig(A, entry=None, sl=0.0, tp=-1.0, fill=None))['levels'] == {'entry': None, 'fill': None, 'sl': None, 'tp': None})
T('lots missing or 0: None', J('amy@x.com', sig(A, lots=None))['lots'] is None and J('amy@x.com', sig(A, lots=0))['lots'] is None)
T('decimals follow the stored prices (gold 2, forex 5)', d['dec'] == 2 and J('amy@x.com', sig(A, entry=1.08512, sl=1.08, tp=1.09, fill=1.08515))['dec'] == 5)
T("Deriv trades say Deriv (their note starts with x<multiplier>, old rows carry no broker)", J('amy@x.com', st.x("INSERT INTO signals(symbol,side,entry,status,created,pnl,closed,note,uid) VALUES('R_100','buy',100,'closed',?,1.0,?,'x100','dev-amy@x.com')", (T0, T0 + 60)))['broker'] == 'Deriv')
T('the answer carries no account, secret or other person details', set(d) == {'id', 'symbol', 'side', 'strategy', 'strategy_name', 'broker', 'lots', 'pnl', 'result', 'opened', 'closed', 'levels', 'dec', 'exit', 'candles'} and all(w not in json.dumps(d).lower() for w in ('token', 'secret', 'password', 'email', '"uid"', 'dev-amy')))

# ---- candles: only what the server still holds ----
T('no candles held: an empty list and both coverage flags false (the page then draws only the price levels)', d['candles']['rows'] == [] and d['candles']['covers_open'] is False and d['candles']['covers_close'] is False)
bars.merge('XAUUSD', 'M15', candle_rows('XAUUSD', A, T0 - 30 * 900, 60), uid=A)      # 30 bars before the open, the trade (4 bars), and after
d = J('amy@x.com', t1); cn = d['candles']
T('candles held around the trade: sent, M15, with both times covered', len(cn['rows']) >= 5 and cn['tf'] == 'M15' and cn['secs'] == 900 and cn['covers_open'] is True and cn['covers_close'] is True and cn['merged'] == 1)
T('only the window around the trade is sent (24 bars before the open, 8 after the close), oldest first', cn['rows'][0][0] == T0 - 24 * 900 and cn['rows'][-1][0] <= T0 + 3600 + 8 * 900 and [r[0] for r in cn['rows']] == sorted(r[0] for r in cn['rows']))
T('each candle is [time, open, high, low, close] straight from what was stored', cn['rows'][0] == [T0 - 24 * 900, 100.0 + 6 * 0.01, 100.0 + 6 * 0.01 + 0.5, 100.0 + 6 * 0.01 - 0.5, 100.0 + 6 * 0.01 + 0.1])
T("another person's candles are never used for my trade", J('bob@x.com', sig(B))['candles']['rows'] == [])
T('a different market has none', J('amy@x.com', sig(A, sym='EURUSD'))['candles']['rows'] == [])
bars.merge('GBPUSD', 'M15', candle_rows('GBPUSD', A, T0 + 900, 40), uid=A)          # starts after the trade opened
p = J('amy@x.com', sig(A, sym='GBPUSD'))['candles']
T('candles that start after the trade opened: covers_open false (the page says only some candles are held)', p['rows'] and p['covers_open'] is False)
bars.merge('USDJPY', 'M15', candle_rows('USDJPY', A, T0 - 5 * 900, 3), uid=A)       # too few to draw
T('fewer than 5 candles counts as none', J('amy@x.com', sig(A, sym='USDJPY'))['candles']['rows'] == [])
bars.merge('AUDUSD', 'M15', [[T0 - 900 * i, float('nan'), 1, 1, 1, 1] for i in range(1, 12)] + [[T0 + 900 * i, 0, 0, 0, 0, 1] for i in range(1, 12)] + [[T0 - 900 * 30, -1, 2, 1, 1, 1]], uid=A)
T('broken candles (nan, zero, negative) are dropped, never drawn', J('amy@x.com', sig(A, sym='AUDUSD'))['candles']['rows'] == [])
DAY5 = 5 * 86400
bars.merge('XAGUSD', 'M15', [[T0 - 900 * 24 + 900 * i, 10 + i, 20 + i, 5 + i, 11 + i, 1] for i in range(600)], uid=A)
q = J('amy@x.com', sig(A, sym='XAGUSD', closed=T0 + DAY5))['candles']
T('a long trade: candles are merged into bigger ones (at most 90), honest: first open, highest high, lowest low, last close', 1 < q['merged'] and len(q['rows']) <= 90 and q['secs'] == 900 * q['merged'] and q['rows'][0][1] == 10 and q['rows'][0][2] == max(20 + i for i in range(q['merged'])) and q['rows'][0][3] == 5 and q['rows'][0][4] == 11 + q['merged'] - 1)
T('the merged chart still covers both times', q['covers_open'] is True and q['covers_close'] is True)

# ---- the owner ----
sig(O, 2.0, sym='XAUUSD'); o_ea = sig('', 3.0); o_dv = sig(O, 4.0, broker='Deriv'); other = sig(B, 9.0)
T("the owner sees their own EA trade (scope ''), their own Deriv trade, and never another person's", G('boss@x.com', o_ea).status_code == 200 and G('boss@x.com', o_dv).status_code == 200 and G('boss@x.com', other).status_code == 404)
T("a normal person can never open the owner's EA ('' scope) trade", G('amy@x.com', o_ea).status_code == 404)

# ---- the profit curve points can open their trade ----
j = pc.snapshot(A)
T('every profit curve point carries the id of its trade, and that trade opens', j['curve'] and all(isinstance(p['id'], int) for p in j['curve']) and all(G('amy@x.com', p['id']).status_code == 200 for p in j['curve']))
many = [sig(B, 1.0, opened=T0 + 10000 + i, closed=T0 + 10060 + i) for i in range(200)]
bids = {r['id'] for r in st.q("SELECT id FROM signals WHERE uid=?", (B,))}
jb = pc.snapshot(B)
T('a long history is thinned but the points that stay keep their own id (first and last included)', jb['curve_n'] > pc.MAXP and len(jb['curve']) <= pc.MAXP and all(p['id'] in bids for p in jb['curve']) and jb['curve'][-1]['id'] == many[-1])

for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
