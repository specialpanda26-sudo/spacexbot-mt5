"""Binance SPOT trading, Section 5B-1: the ORDER LAYER only. TESTNET ONLY. Nothing in the app calls this file yet (5B-2 wires the bot, 5B-3 adds Real).
Safety, on purpose: (1) the address is fixed to Binance's TESTNET (testnet.binance.vision, fake money); no env var can change it. (2) Only the 7 (method, path) pairs in ALLOWED
can ever be called: no DELETE, no /sapi, so no withdrawal, transfer or margin call exists here. (3) Spot is long-only: BUY opens, SELL closes what we hold; no shorting.
(4) Every order carries a client id, so a repeated send is refused by Binance instead of buying twice. (5) Keys are only used to sign; they are never put in a message or a log.
binance.py (the Section 2 key check) stays read-only and is untouched."""
import re, hmac, hashlib, time
from decimal import Decimal, ROUND_DOWN, InvalidOperation

TEST_BASE = 'https://testnet.binance.vision'
BASE = lambda: TEST_BASE                                    # fixed: 5B-3 is where a Real address may ever be added
ALLOWED = (('GET', '/api/v3/time'), ('GET', '/api/v3/exchangeInfo'), ('GET', '/api/v3/ticker/price'), ('GET', '/api/v3/account'),
           ('POST', '/api/v3/order'), ('GET', '/api/v3/order'), ('GET', '/api/v3/klines'))
SYM = re.compile(r'^[A-Z0-9]{5,12}$')

def _http(method, path, key, qs):
    import requests
    h = {'Accept': 'application/json'}
    if key: h['X-MBX-APIKEY'] = key
    r = requests.request(method, BASE() + path + ('?' + qs if qs else ''), headers=h, timeout=12)
    try: j = r.json()
    except ValueError: j = {}
    return r.status_code, j

def _call(method, path, key=None, secret=None, params=None, http=None, now_ms=None):
    """The one door to Binance. Only the pairs in ALLOWED; signed when a secret is given."""
    if (method, path) not in ALLOWED: raise ValueError('not allowed')
    p = dict(params or {})
    if secret:
        p['timestamp'] = int(now_ms or time.time() * 1000); p['recvWindow'] = 10000
    qs = '&'.join('%s=%s' % (k, p[k]) for k in p)
    if secret: qs += ('&' if qs else '') + 'signature=' + hmac.new(secret.encode('utf-8'), qs.encode('utf-8'), hashlib.sha256).hexdigest()
    return (http or _http)(method, path, key, qs)

def _d(v):
    try: return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError): return Decimal(0)

def fmt(x):
    """Decimal -> plain text without exponent or trailing zeros (what Binance wants in quantity)."""
    s = format(x.normalize(), 'f')
    return s

def floor_qty(q, step):
    step = _d(step)
    if step <= 0: return _d(q)
    return (_d(q) / step).to_integral_value(ROUND_DOWN) * step

def _fail(code, j):
    """-> a plain message. Binance's own error number is in j['code']."""
    c = j.get('code') if isinstance(j, dict) else None
    m = str(j.get('msg') or '') if isinstance(j, dict) else ''
    if c in (-2014, -2015, -2008): return 'Binance did not accept this test key. Check the key and secret (testnet keys only work on the testnet).'
    if c == -1022: return 'The secret does not match this key.'
    if c == -1021: return 'Binance says this server clock is off. Try again in a minute.'
    if c == -2010 and 'uplicate' in m: return 'This order was already sent, so it was not sent again.'
    if c == -2010: return 'Binance refused the order: not enough balance.'
    if c in (-1013, -1111, -1100): return 'Binance refused the order size (below its minimum or the wrong step).'
    if code in (418, 429): return 'Binance asked us to slow down. Try again in a minute.'
    if code in (451, 403): return "Binance blocks requests from this server's location."
    if code >= 500: return 'Binance is not answering right now. Try again in a minute.'
    return 'Binance said no (HTTP %s).' % code

def rules(symbol, http=None):
    """-> (rules dict, '') or (None, why). USDT markets that are trading only."""
    s = str(symbol or '').upper()
    if not SYM.match(s): return None, 'That market name is not valid.'
    try: code, j = _call('GET', '/api/v3/exchangeInfo', params={'symbol': s}, http=http)
    except Exception: return None, 'Could not reach Binance. Try again in a minute.'
    if code != 200 or not isinstance(j, dict) or not j.get('symbols'): return None, 'Binance does not list %s.' % s
    x = j['symbols'][0]
    if x.get('status') != 'TRADING': return None, '%s is not trading right now.' % s
    if x.get('quoteAsset') != 'USDT': return None, 'Only USDT markets for now (%s is not).' % s
    f = {a.get('filterType'): a for a in x.get('filters', []) if isinstance(a, dict)}
    lot = f.get('LOT_SIZE') or {}; nt = f.get('NOTIONAL') or f.get('MIN_NOTIONAL') or {}
    return {'symbol': s, 'base': x.get('baseAsset'), 'quote': 'USDT', 'step': _d(lot.get('stepSize')), 'min_qty': _d(lot.get('minQty')), 'min_notional': _d(nt.get('minNotional'))}, ''

def plan_buy(stake, price, r):
    """-> (quantity as Decimal, '') or (None, why). Spend at most `stake` USDT."""
    stake, price = _d(stake), _d(price)
    if stake <= 0 or price <= 0: return None, 'No stake or no price.'
    q = floor_qty(stake / price, r['step'])
    if q < r['min_qty'] or q <= 0 or q * price < r['min_notional']:
        need = max(r['min_notional'], r['min_qty'] * price)
        return None, 'Stake too small for %s: Binance needs about %s USDT per order.' % (r['symbol'], fmt(need.quantize(Decimal('0.01'), ROUND_DOWN)) if need else '--')
    return q, ''

def _result(j, base):
    ex = _d(j.get('executedQty')); cq = _d(j.get('cummulativeQuoteQty'))
    fee = sum((_d(x.get('commission')) for x in (j.get('fills') or []) if x.get('commissionAsset') == base), Decimal(0))
    feeq = sum((_d(x.get('commission')) for x in (j.get('fills') or []) if x.get('commissionAsset') == 'USDT'), Decimal(0))
    return {'ok': True, 'order_id': j.get('orderId'), 'status': j.get('status'), 'qty': ex, 'net_qty': ex - fee, 'quote': cq,
            'avg': (cq / ex) if ex > 0 else Decimal(0), 'fee_base': fee, 'fee_quote': feeq}

def market(key, secret, r, side, qty, cid, http=None, now_ms=None):
    """One MARKET order. -> result dict (ok True/False, plain `msg` when not ok). A refused or failed send never raises."""
    p = {'symbol': r['symbol'], 'side': side, 'type': 'MARKET', 'quantity': fmt(qty), 'newClientOrderId': str(cid)[:36], 'newOrderRespType': 'FULL'}
    try: code, j = _call('POST', '/api/v3/order', key, secret, p, http, now_ms)
    except Exception as e:
        print('[binance_trade] order failed:', type(e).__name__)          # the type only: a message could hold the key
        return {'ok': False, 'msg': 'Could not reach Binance. The order may or may not have gone; check before trying again.'}
    if code != 200 or not isinstance(j, dict) or j.get('status') not in ('FILLED', 'PARTIALLY_FILLED', 'EXPIRED'):
        return {'ok': False, 'msg': _fail(code, j if isinstance(j, dict) else {})}
    out = _result(j, r['base'])
    if out['qty'] <= 0: return {'ok': False, 'msg': 'Binance did not fill the order.'}
    return out

def _free(a, asset):
    for b in a.get('balances', []) if isinstance(a, dict) else []:
        if b.get('asset') == asset: return _d(b.get('free'))
    return Decimal(0)

def check_key(key, secret, http=None, now_ms=None):
    """Testnet key can trade? -> (ok, message). Reads the account only."""
    try: code, a = _call('GET', '/api/v3/account', key, secret, http=http, now_ms=now_ms)
    except Exception: return False, 'Could not reach Binance. Try again in a minute.'
    if code != 200 or not isinstance(a, dict): return False, _fail(code, a if isinstance(a, dict) else {})
    if not a.get('canTrade'): return False, 'This key cannot trade. Make a testnet key with trading allowed.'
    return True, 'Testnet key works. Test balance %s USDT.' % fmt(_free(a, 'USDT').quantize(Decimal('0.01'), ROUND_DOWN))

def open_long(key, secret, symbol, stake, cid, http=None, now_ms=None):
    """Spot BUY of about `stake` USDT. Checks market rules, price and balance first; sends nothing if any check fails."""
    r, why = rules(symbol, http)
    if not r: return {'ok': False, 'msg': why}
    try:
        c1, t = _call('GET', '/api/v3/ticker/price', params={'symbol': r['symbol']}, http=http)
        c2, a = _call('GET', '/api/v3/account', key, secret, http=http, now_ms=now_ms)
    except Exception: return {'ok': False, 'msg': 'Could not reach Binance. Try again in a minute.'}
    if c2 != 200 or not isinstance(a, dict): return {'ok': False, 'msg': _fail(c2, a if isinstance(a, dict) else {})}
    if not a.get('canTrade'): return {'ok': False, 'msg': 'This key cannot trade. Make a testnet key with trading allowed.'}
    price = _d(t.get('price')) if c1 == 200 and isinstance(t, dict) else Decimal(0)
    q, why = plan_buy(stake, price, r)
    if q is None: return {'ok': False, 'msg': why}
    if _free(a, 'USDT') < q * price: return {'ok': False, 'msg': 'Not enough USDT: the order needs about %s and the test account has %s.' % (fmt((q * price).quantize(Decimal('0.01'), ROUND_DOWN)), fmt(_free(a, 'USDT').quantize(Decimal('0.01'), ROUND_DOWN)))}
    out = market(key, secret, r, 'BUY', q, cid, http, now_ms); out['symbol'] = r['symbol']; return out

def close_long(key, secret, symbol, held_qty, cid, http=None, now_ms=None):
    """Spot SELL of what we hold (the net quantity from open_long). Never sells more than the amount given."""
    r, why = rules(symbol, http)
    if not r: return {'ok': False, 'msg': why}
    q = floor_qty(held_qty, r['step'])
    if q <= 0 or q < r['min_qty']: return {'ok': False, 'msg': 'Too little %s left to sell (below Binance\'s minimum).' % r['base']}
    out = market(key, secret, r, 'SELL', q, cid, http, now_ms); out['symbol'] = r['symbol']; return out
