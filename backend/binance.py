"""Binance, Section 2: check a customer's API key and read the Spot balance. READ-ONLY. This file never trades.
Only three Binance addresses can ever be called (see ALLOWED), only with GET, so no order can be placed from here.
Uses Binance's free API: the key goes in a header, the request is signed with the secret (HMAC-SHA256). Neither is ever put in a message or a log.
A key that can WITHDRAW money is refused on purpose. BINANCE_BASE (Render env, optional) changes the address if Binance blocks this server's country."""
import os, re, hmac, hashlib, time, json
from . import store as st, brokers as bk

BASE = lambda: os.getenv('BINANCE_BASE', 'https://api.binance.com').rstrip('/')
ALLOWED = ('/api/v3/time', '/api/v3/ticker/price', '/api/v3/account', '/sapi/v1/account/apiRestrictions')
STABLE = {'USDT', 'USDC', 'FDUSD', 'BUSD', 'TUSD', 'USD', 'DAI'}
_last = {}

def _http(path, key, params):
    import requests
    h = {'Accept': 'application/json'}
    if key: h['X-MBX-APIKEY'] = key
    r = requests.get(BASE() + path, params=params, headers=h, timeout=12)
    try: j = r.json()
    except ValueError: j = {}
    return r.status_code, j

def _get(path, key=None, secret=None, params=None, http=None, now_ms=None):
    """The one door to Binance. GET only, and only the paths in ALLOWED."""
    if path not in ALLOWED: raise ValueError('not allowed')
    p = dict(params or {})
    if secret:
        p['timestamp'] = int(now_ms or time.time() * 1000); p['recvWindow'] = 10000
        q = '&'.join('%s=%s' % (k, p[k]) for k in p)
        p['signature'] = hmac.new(secret.encode('utf-8'), q.encode('utf-8'), hashlib.sha256).hexdigest()
    return (http or _http)(path, key, p)

def _fail(code, j):
    """-> (message, is_the_keys_fault). Binance's own error number is in j['code']."""
    c = j.get('code') if isinstance(j, dict) else None
    if c in (-2014, -2015, -2008): return 'Binance did not accept this key. Check the key and secret, that Enable Reading is on, and that the key has no IP limit (or allow this server).', True
    if c == -1022: return 'The secret does not match this key. Copy both again.', True
    if c == -1021: return 'Binance says this server clock is off. Try again in a minute.', False
    if code in (451, 403): return "Binance blocks requests from this server's location. The owner can set BINANCE_BASE on Render.", False
    if code in (418, 429): return 'Binance asked us to slow down. Try again in a minute.', False
    if code >= 500: return 'Binance is not answering right now. Try again in a minute.', False
    return 'Binance said no (HTTP %s). Try again.' % code, False

def _server_ms(http):
    try:
        code, j = _get('/api/v3/time', http=http)
        if code == 200 and isinstance(j, dict) and j.get('serverTime'): return int(j['serverTime'])
    except Exception: pass
    return None

def _prices(http):
    try: code, j = _get('/api/v3/ticker/price', http=http)
    except Exception: return {}
    if code != 200 or not isinstance(j, list): return {}
    out = {}
    for x in j:
        try: out[str(x['symbol'])] = float(x['price'])
        except (KeyError, TypeError, ValueError): continue
    return out

def usd_total(balances, prices):
    """-> (total in USD, how many held assets could not be priced). Stable coins count 1:1; others go through USDT, then USDC, then BTC."""
    tot, skip = 0.0, 0
    for b in balances if isinstance(balances, list) else []:
        try: a = str(b['asset']).upper(); n = float(b.get('free') or 0) + float(b.get('locked') or 0)
        except (KeyError, TypeError, ValueError): continue
        if n <= 0: continue
        if a in STABLE: tot += n; continue
        p = prices.get(a + 'USDT') or prices.get(a + 'USDC')
        if not p and prices.get(a + 'BTC') and prices.get('BTCUSDT'): p = prices[a + 'BTC'] * prices['BTCUSDT']
        if p: tot += n * p
        else: skip += 1
    return round(tot, 2), skip

def _mark(uid, status): st.x("UPDATE broker_links SET status=?,updated=? WHERE uid=? AND broker='Binance'", (status, int(time.time()), uid))

def verify(uid, http=None, now=None):
    """Check the saved key and read the balance. Sets status verified / rejected and a plain note. Returns (ok, message). Never trades."""
    now = now or time.time()
    if now - _last.get(uid, 0) < 8: return False, 'Wait a few seconds and try again.'
    _last[uid] = now
    sec = bk.secret(uid, 'Binance')
    if not sec or not sec.get('key') or not sec.get('secret'): return False, 'Save your Binance key and secret first.'
    key, sk = sec['key'], sec['secret']
    ms = _server_ms(http)
    try:
        code, j = _get('/sapi/v1/account/apiRestrictions', key, sk, http=http, now_ms=ms)
        if code != 200 or not isinstance(j, dict):
            msg, bad = _fail(code, j)
            if bad: _mark(uid, 'rejected'); bk.set_note(uid, 'Binance', msg)
            return False, msg
        if not j.get('enableReading', True): return _reject(uid, 'This key cannot read your account. Make a new key with Enable Reading on.')
        if j.get('enableWithdrawals'): return _reject(uid, 'This key can WITHDRAW money. For your safety it is refused. Make a new key with Withdrawals turned OFF.')
        code, a = _get('/api/v3/account', key, sk, params={'omitZeroBalances': 'true'}, http=http, now_ms=ms)
        if code != 200 or not isinstance(a, dict) or not isinstance(a.get('balances'), list):
            msg, bad = _fail(code, a)
            if bad: _mark(uid, 'rejected'); bk.set_note(uid, 'Binance', msg)
            return False, msg
    except Exception as e:
        print('[binance] check failed:', type(e).__name__)         # the type only: a message could hold the key
        return False, 'Could not reach Binance. Try again in a minute.'
    total, skip = usd_total(a['balances'], _prices(http))
    _mark(uid, 'verified'); bk.set_bal(uid, 'Binance', total, 'USD', demo=False, now=now)
    note = 'Key checked. Spot balance about $%s (read-only).%s Binance trading is off: this app never places a Binance order.' % (format(total, ',.2f'), (' %d small asset(s) could not be priced.' % skip) if skip else '')
    bk.set_note(uid, 'Binance', note); return True, note

def _reject(uid, msg):
    _mark(uid, 'rejected'); bk.set_note(uid, 'Binance', msg); return False, msg
