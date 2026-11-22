"""Checks Section 5B-2a: the Binance SPOT bot engine (backend/binance_bot.py) against a fake Binance (no network, testnet address fixed). Run: python tests/test_bb2.py"""
import os, sys, json, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_bb2.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from urllib.parse import parse_qs
from backend.app import app
from backend import store as st, brokers as bk, binance_bot as bb, binance_trade as bt, tradeon
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
NOW = 1700000000; U = 'dev-amy@x.com'; KEY, SEC = 'k' * 24, 's' * 24
yes, no = (lambda u: True), (lambda u: False)
S = {'price': 95000.0, 'bal': '1000', 'can': True, 'boom_post': False, 'calls': []}
def posts(): return [x for x in S['calls'] if x[0] == 'POST']
def http(method, path, key, qs):
    S['calls'].append((method, path, qs)); q = {k: v[0] for k, v in parse_qs(qs).items()}
    if (method, path) not in bt.ALLOWED: raise AssertionError('call outside ALLOWED: %s %s' % (method, path))
    if path == '/api/v3/exchangeInfo': return 200, {'symbols': [{'symbol': q['symbol'], 'status': 'TRADING', 'baseAsset': q['symbol'][:-4], 'quoteAsset': 'USDT',
            'filters': [{'filterType': 'LOT_SIZE', 'minQty': '0.00001', 'stepSize': '0.00001'}, {'filterType': 'NOTIONAL', 'minNotional': '5.0'}]}]}
    if path == '/api/v3/ticker/price': return 200, {'symbol': q['symbol'], 'price': str(S['price'])}
    if path == '/api/v3/account': return 200, {'canTrade': S['can'], 'balances': [{'asset': 'USDT', 'free': S['bal'], 'locked': '0'}]}
    if path == '/api/v3/klines':
        g = {'5m': 300, '15m': 900, '1h': 3600}[q['interval']]; last = NOW - NOW % g
        return 200, [[(last - g * k) * 1000, '1', '2', '0.5', '1.5', '1'] for k in range(9, -1, -1)]
    if path == '/api/v3/order' and method == 'POST':
        if S['boom_post']: raise RuntimeError('network ' + KEY)
        qty = float(q['quantity']); px = S['price']; quote = round(qty * px, 8)
        fee = {'commission': str(round(qty * 0.001, 8)), 'commissionAsset': q['symbol'][:-4]} if q['side'] == 'BUY' else {'commission': str(round(quote * 0.001, 8)), 'commissionAsset': 'USDT'}
        return 200, {'orderId': 500 + len(posts()), 'status': 'FILLED', 'executedQty': q['quantity'], 'cummulativeQuoteQty': str(quote), 'fills': [dict(fee, price=str(px), qty=q['quantity'])]}
    return 404, {}
scans = []
def scan(sym, uid): scans.append((sym, uid))
def sig(side='buy', sym='BTCUSD', entry=95000, sl=94000, tp=97000, risk=0.1, status='pending'):
    return st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)', (sym, side, entry, sl, tp, risk, 'test', 2, status, NOW, U))
def row(i): return st.q('SELECT * FROM signals WHERE id=?', (i,), True)
def reset():
    S.update(price=95000.0, bal='1000', can=True, boom_post=False, calls=[]); scans.clear()
    st.x("UPDATE signals SET status='closed' WHERE status IN ('open','closing','sent','pending')")          # start each case with no trade open

c.get('/api/me', headers=H('amy@x.com')); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, U))
st.put('symbols', 'BTCUSD,XAUUSD')
T('no Binance key saved -> not verified', bb.run_once(U, scan, yes, http, NOW) == 'not verified')
c.post('/api/brokers/Binance', json={'key': KEY, 'secret': SEC}, headers=H('amy@x.com'))
T('a saved but unchecked key -> not verified, nothing called', bb.run_once(U, scan, yes, http, NOW) == 'not verified' and not S['calls'])
st.x("UPDATE broker_links SET status='verified' WHERE uid=? AND broker='Binance'", (U,))
T('Binance never chosen as the platform -> other platform, nothing called', bb.run_once(U, scan, yes, http, NOW) == 'other platform' and not S['calls'])
tradeon.set_(U, False, 'Binance')
T('chosen but the bot switch is off -> bot off, nothing called', bb.run_once(U, scan, yes, http, NOW) == 'bot off' and not S['calls'])
bk.set_bot(U, 'Binance', True)
T('plan ended -> plan ended, nothing called', bb.run_once(U, scan, no, http, NOW) == 'plan ended' and not S['calls'])
bk.set_mode(U, 'Binance', 'real'); bk.set_bot(U, 'Binance', True)
T('Real mode is not available yet -> real not ready, nothing called', bb.run_once(U, scan, yes, http, NOW) == 'real not ready' and not S['calls'])
bk.set_mode(U, 'Binance', 'demo'); bk.set_bot(U, 'Binance', True)
st.put('symbols', 'XAUUSD,EURUSD')
T('no crypto market in the list -> no crypto symbols', bb.run_once(U, scan, yes, http, NOW) == 'no crypto symbols' and not [x for x in S['calls'] if x[1] == '/api/v3/klines'])
st.put('symbols', 'BTCUSD,XAUUSD'); reset()
T('pair(): BTCUSD and BTCUSDT map, gold and forex do not', bb.pair('BTCUSD') == 'BTCUSDT' and bb.pair('ethusdt') == 'ETHUSDT' and bb.pair('XAUUSD') is None and bb.pair('EURUSD') is None)

# --- happy path: one BUY signal
i = sig()
T('a round runs ok', bb.run_once(U, scan, yes, http, NOW) == 'ok')
T('only the crypto market was scanned', scans == [('BTCUSD', U)])
T('candles were read for BTCUSDT only (public prices)', all('BTCUSDT' in x[2] for x in S['calls'] if x[1] == '/api/v3/klines') and any(x[1] == '/api/v3/klines' for x in S['calls']))
p = posts(); r = row(i)
T('exactly one BUY MARKET was sent with a client id', len(p) == 1 and 'side=BUY' in p[0][2] and 'type=MARKET' in p[0][2] and 'newClientOrderId=sxb-%d&' % i in p[0][2])
T('stake from the risk percent: 95 USDT -> 0.001 BTC', 'quantity=0.001&' in p[0][2])
T('the signal is open on Binance with its order id and net amount', r['status'] == 'open' and r['broker'] == 'Binance' and r['ticket'] == '501' and abs(r['lots'] - 0.000999) < 1e-9 and r['note'] == 'spot')
pos = json.loads(st.get('bnpos:%d' % i)); T('the position (amount, cost) is saved', pos['pair'] == 'BTCUSDT' and pos['qty'] == '0.000999' and float(pos['cost']) == 95.0)
T('the balance is shown on the tile as a testnet (demo) balance', json.loads(st.get('bal:%s:Binance' % U))['demo'] is True)
n = len(posts()); bb.run_once(U, scan, yes, http, NOW)
T('another round does not buy the same signal again', len(posts()) == n)
T('the balance counts the free USDT plus what the open trade cost: 1000 + 95', st.acct(U).get('balance') == 1095.0)

# --- following the trade
S['price'] = 96000.0; n = len(posts()); bb.run_once(U, scan, yes, http, NOW)
T('price between the stop and the target: nothing is sold', len(posts()) == n and row(i)['status'] == 'open')
S['price'] = 97000.0; bb.run_once(U, scan, no, http, NOW)          # the plan has ended: an open trade is still closed
p = posts(); r = row(i)
T('target reached: one SELL of the held amount (floored to the step), even with the plan ended', len(p) == 2 and 'side=SELL' in p[1][2] and 'quantity=0.00099&' in p[1][2])
T('closed with a profit worked out after the fee: 96.03 - 0.09603 - 95 = 0.93', r['status'] == 'closed' and r['pnl'] == 0.93)
T('closed by the target', st.get('closedby:%d' % i) == 'tp' and float(st.get('exitpx:%d' % i)) == 97000.0)
n = len(posts()); bb.run_once(U, scan, yes, http, NOW)
T('a closed trade is never sold twice', len(posts()) == n)

# --- stop loss, with the bot switched OFF
reset(); bk.set_bot(U, 'Binance', True); i2 = sig(); bb.run_once(U, scan, yes, http, NOW); bk.set_bot(U, 'Binance', False)
S['price'] = 93900.0; bb.run_once(U, scan, yes, http, NOW); r = row(i2)
T('stop loss reached with the bot OFF: still sold, closed by the stop, a loss', r['status'] == 'closed' and r['pnl'] < 0 and st.get('closedby:%d' % i2) == 'sl')

# --- skipped signals
reset(); bk.set_bot(U, 'Binance', True); a = sig(side='sell'); b = sig(sym='XAUUSD'); bb.run_once(U, scan, yes, http, NOW)
T('a SELL signal is skipped (spot cannot short) and nothing is sent', row(a)['status'] == 'rejected' and 'short' in row(a)['note'] and not posts())
T('a gold signal is skipped (crypto only)', row(b)['status'] == 'rejected' and 'crypto' in row(b)['note'])

# --- strong setup stake
reset(); k = sig(); st.put('stake:%d' % k, 40); bb.run_once(U, scan, yes, http, NOW)
T('a strong setup uses 40% of the balance: 400 USDT -> 0.00421 BTC', 'quantity=0.00421&' in posts()[0][2])
reset(); k = sig(risk=5); bb.run_once(U, scan, yes, http, NOW)
T('a big risk percent is capped at half the balance: 500 USDT -> 0.00526 BTC', 'quantity=0.00526&' in posts()[0][2])

# --- not enough money / no trade permission
reset(); S['bal'] = '50'; k = sig(); bb.run_once(U, scan, yes, http, NOW)
T('not enough USDT: the signal is rejected with a plain note and nothing is sent', row(k)['status'] == 'rejected' and not posts())
reset(); S['can'] = False; k = sig(); r = bb.run_once(U, scan, yes, http, NOW)
T('a key that cannot trade -> cannot trade, nothing sent', r == 'cannot trade' and not posts())

# --- unconfirmed orders are never repeated
reset(); k = sig(); S['boom_post'] = True; bb.run_once(U, scan, yes, http, NOW); S['boom_post'] = False
T('a buy that could not be confirmed stays sent with a note', row(k)['status'] == 'sent' and 'not confirmed' in row(k)['note'])
n = len(posts()); bb.run_once(U, scan, yes, http, NOW)
T('and it is never retried', len(posts()) == n)
reset(); k = sig(); bb.run_once(U, scan, yes, http, NOW); S['price'] = 97000.0; S['boom_post'] = True; bb.run_once(U, scan, yes, http, NOW); S['boom_post'] = False
T('a sell that could not be confirmed stays closing with a note', row(k)['status'] == 'closing' and 'not confirmed' in row(k)['note'])
n = len(posts()); bb.run_once(U, scan, yes, http, NOW)
T('and it is never sold twice', len(posts()) == n)
T('the key never appears in the Binance tile note', KEY not in (st.get('why:%s:Binance' % U) or ''))
T('every call stayed inside the allowed list and every POST was an order', all((m, pth) in bt.ALLOWED for m, pth, _ in S['calls']) and all(x[1] == '/api/v3/order' for x in posts()))
src = open(os.path.join(os.path.dirname(__file__), '..', 'backend', 'app.py'), encoding='utf-8').read()
T('the app does not start this bot yet (5B-2b)', 'binance_bot' not in src)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
