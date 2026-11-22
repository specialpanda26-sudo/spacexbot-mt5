"""Checks Section 5B-1: the Binance SPOT order layer (backend/binance_trade.py). Testnet only, no network (a fake Binance is used).
Run: python tests/test_bt1.py"""
import os, sys, hmac, hashlib
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, ROOT)
from decimal import Decimal as D
from backend import binance_trade as bt
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
KEY, SEC = 'KEYKEYKEY123', 'SECRETSECRET456'

def fake(bal='1000', can=True, order=None, status=200, sym_status='TRADING', quote='USDT', price='95000', calls=None):
    calls = calls if calls is not None else []
    def http(method, path, key, qs):
        calls.append((method, path, key, qs))
        if path == '/api/v3/exchangeInfo':
            return 200, {'symbols': [{'symbol': 'BTCUSDT', 'status': sym_status, 'baseAsset': 'BTC', 'quoteAsset': quote, 'filters': [
                {'filterType': 'LOT_SIZE', 'minQty': '0.00001', 'stepSize': '0.00001'}, {'filterType': 'NOTIONAL', 'minNotional': '5.0'}]}]}
        if path == '/api/v3/ticker/price': return 200, {'symbol': 'BTCUSDT', 'price': price}
        if path == '/api/v3/account': return 200, {'canTrade': can, 'balances': [{'asset': 'USDT', 'free': bal, 'locked': '0'}]}
        if path == '/api/v3/order' and method == 'POST':
            if order is not None: return status, order
            return 200, {'orderId': 77, 'status': 'FILLED', 'executedQty': '0.00105', 'cummulativeQuoteQty': '99.75',
                         'fills': [{'price': '95000', 'qty': '0.00105', 'commission': '0.00000105', 'commissionAsset': 'BTC'}]}
        return 404, {}
    return http, calls
def posts(calls): return [c for c in calls if c[0] == 'POST']

T('address is the TESTNET', bt.BASE() == 'https://testnet.binance.vision')
os.environ['BINANCE_BASE'] = 'https://evil.example'
T('an env var cannot change the address', bt.BASE() == 'https://testnet.binance.vision')
bad = 0
for m, p in (('DELETE', '/api/v3/order'), ('POST', '/sapi/v1/capital/withdraw/apply'), ('GET', '/sapi/v1/account/apiRestrictions'), ('POST', '/api/v3/order/oco'), ('POST', '/sapi/v1/margin/order'), ('GET', '/fapi/v1/order')):
    try: bt._call(m, p, KEY, SEC, http=fake()[0]); bad += 1
    except ValueError: pass
T('no withdraw, transfer, margin, futures or DELETE call can be made', bad == 0)
T('only 7 method+path pairs are allowed', len(bt.ALLOWED) == 7 and all(p.startswith('/api/v3/') for _, p in bt.ALLOWED))
src = open(os.path.join(ROOT, 'backend', 'binance.py'), encoding='utf-8').read()
T('the Section 2 file binance.py is still read-only (no POST, no orders)', 'requests.post' not in src and "'POST'" not in src and 'requests.get' in src)

h, c = fake(); bt._call('POST', '/api/v3/order', KEY, SEC, {'symbol': 'BTCUSDT'}, h, now_ms=1700000000000)
qs = c[0][3]; body, sig = qs.rsplit('&signature=', 1)
T('the request is signed with HMAC-SHA256 over the query', sig == hmac.new(SEC.encode(), body.encode(), hashlib.sha256).hexdigest() and 'timestamp=1700000000000' in body)
T('the secret is never sent, only the key header value', SEC not in qs and c[0][2] == KEY)

T('floor_qty rounds DOWN to the step', bt.floor_qty('0.123456', '0.001') == D('0.123') and bt.floor_qty('2.9', '1') == D('2') and bt.floor_qty('0.0009', '0.001') == D('0'))
T('fmt gives plain text', bt.fmt(D('0.00105000')) == '0.00105' and bt.fmt(D('100')) == '100')

r, w = bt.rules('BTCUSDT', fake()[0])
T('rules read the step, minimum and notional', r and r['step'] == D('0.00001') and r['min_notional'] == D('5.0') and r['base'] == 'BTC')
T('a bad name is refused', bt.rules('btc usdt!', fake()[0])[0] is None and bt.rules('', fake()[0])[0] is None)
T('a market that is not trading is refused', bt.rules('BTCUSDT', fake(sym_status='BREAK')[0])[0] is None)
T('a non-USDT market is refused', bt.rules('BTCUSDT', fake(quote='BTC')[0])[0] is None)
q, w = bt.plan_buy('100', '95000', r)
T('plan_buy: 100 USDT at 95000 = 0.00105 BTC (floored)', q == D('0.00105'))
q, w = bt.plan_buy('3', '95000', r)
T('plan_buy: 3 USDT is too small and says why', q is None and 'too small' in w)

h, c = fake(); o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'sxb-1', h, now_ms=1)
p = posts(c)
T('open_long sends exactly one BUY MARKET with the client id and FULL response', len(p) == 1 and 'side=BUY' in p[0][3] and 'type=MARKET' in p[0][3] and 'quantity=0.00105' in p[0][3] and 'newClientOrderId=sxb-1' in p[0][3] and 'newOrderRespType=FULL' in p[0][3])
T('open_long result: average price, and the fee paid in BTC is taken off', o['ok'] and o['avg'] == D('95000') and o['fee_base'] == D('0.00000105') and o['net_qty'] == D('0.00104895'))
h, c = fake(bal='50'); o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'sxb-2', h)
T('not enough USDT: refused and NOTHING is sent', not o['ok'] and 'Not enough USDT' in o['msg'] and not posts(c))
h, c = fake(can=False); o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'sxb-3', h)
T('a key that cannot trade: refused and nothing sent', not o['ok'] and not posts(c))
h, c = fake(); o = bt.open_long(KEY, SEC, 'BTCUSDT', '2', 'sxb-4', h)
T('stake below the minimum: refused and nothing sent', not o['ok'] and not posts(c))
h, c = fake(price='0'); o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'sxb-5', h)
T('no price: refused and nothing sent', not o['ok'] and not posts(c))
h, c = fake(); o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'x' * 80, h)
T('a long client id is cut to 36 characters', 'newClientOrderId=' + 'x' * 36 + '&' in posts(c)[0][3])

h, c = fake(); o = bt.close_long(KEY, SEC, 'BTCUSDT', '0.00104895', 'sxb-6', h)
T('close_long sells the held amount floored to the step, SELL MARKET', o['ok'] and 'side=SELL' in posts(c)[0][3] and 'quantity=0.00104' in posts(c)[0][3])
h, c = fake(); o = bt.close_long(KEY, SEC, 'BTCUSDT', '0.000001', 'sxb-7', h)
T('dust below the minimum: not sold, nothing sent', not o['ok'] and 'Too little' in o['msg'] and not posts(c))
h, c = fake(); o = bt.close_long(KEY, SEC, 'BTCUSDT', '0.5', 'sxb-8', h)
T('close_long never sends more than the amount given', 'quantity=0.5' in posts(c)[0][3] and 'quantity=0.50001' not in posts(c)[0][3])

for code, j, want in ((400, {'code': -2010, 'msg': 'Duplicate order sent.'}, 'already sent'), (400, {'code': -2010, 'msg': 'Account has insufficient balance'}, 'not enough balance'),
                      (400, {'code': -1013, 'msg': 'Filter failure: LOT_SIZE'}, 'size'), (401, {'code': -2015, 'msg': 'Invalid API-key'}, 'did not accept'),
                      (429, {}, 'slow down'), (503, {}, 'not answering'), (451, {}, 'blocks')):
    h, c = fake(order=j, status=code); o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'sxb-9', h)
    T('error %s %s -> plain words' % (code, j.get('code', '')), not o['ok'] and want in o['msg'])
    if KEY in o['msg'] or SEC in o['msg']: T('key leaked in a message', False)
h, c = fake(order={'orderId': 1, 'status': 'NEW', 'executedQty': '0', 'cummulativeQuoteQty': '0'}); o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'sxb-10', h)
T('an order that did not fill is reported as not ok', not o['ok'])
def boom(*a): raise RuntimeError('network ' + KEY + SEC)
o = bt.open_long(KEY, SEC, 'BTCUSDT', '100', 'sxb-11', boom)
T('a network failure never raises and never shows the key', not o['ok'] and KEY not in o['msg'] and SEC not in o['msg'])
h, c = fake(); ok, m = bt.check_key(KEY, SEC, h)
T('check_key reads the account and shows the test balance', ok and '1000' in m and not posts(c))
h, c = fake(can=False); ok, m = bt.check_key(KEY, SEC, h)
T('check_key: a key that cannot trade is not ok', not ok)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
