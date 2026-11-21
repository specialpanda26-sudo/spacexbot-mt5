"""Section 2: Binance key check + Spot balance read (READ-ONLY, no Binance trading) and an honest "Works now / Not yet" line on every broker tile.
Adds backend/binance.py, edits backend/brokers.py, backend/app.py, static/index.html and two old tests.
Run from the repo root. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import os, sys

NEW = {
  'backend/binance.py': r'''"""Binance, Section 2: check a customer's API key and read the Spot balance. READ-ONLY. This file never trades.
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
''',
}

FILES = {
  'backend/app.py': [
    (r'''from . import lag, multi, automarkets, prefs, scale, burst, groupcap, authmail
''',
     r'''from . import lag, multi, automarkets, prefs, scale, burst, groupcap, authmail, binance
'''),
    (r'''    elif n == 'Binance': t = {'check': 'Checking Binance is not available yet.', 'switch': 'Binance does not trade yet, so it has no demo or real switch.', 'bot': 'Binance does not trade yet, so there is no bot to start.'}[what]
''',
     r'''    elif n == 'Binance': t = {'switch': 'Binance does not trade yet, so it has no demo or real switch.', 'bot': 'Binance does not trade yet, so there is no bot to start.'}[what]
'''),
    (r'''    if n != 'Deriv': return _not_deriv(n, 'check')
    ok, msg = deriv.verify(u['uid'])
''',
     r'''    if n not in ('Deriv', 'Binance'): return _not_deriv(n, 'check')
    ok, msg = deriv.verify(u['uid']) if n == 'Deriv' else binance.verify(u['uid'])
'''),
  ],
  'backend/brokers.py': [
    (r'''def catalog(): return [{'name': k, 'kind': v} for k, v in CATALOG.items()]
''',
     r'''# What each broker really does today, in plain words (shown on its tile and in its Connect card). Change these when the code changes.
ABOUT = {
    'mt5': {'tile': 'Via your MT5 app', 'works': 'Trades through your MT5 app and the SpaceXBridge EA.', 'not': 'This site does not check your key or read your balance. Your MT5 app does that.'},
    'Deriv': {'tile': 'Check, balance, demo bot', 'works': 'Token check, balance read, and the bot trading on your demo (virtual) account.', 'not': 'Real-money trading stays off unless the owner allows it and you switch to Real.'},
    'Binance': {'tile': 'Balance only, no trading', 'works': 'Key check and Spot balance read (read-only).', 'not': 'No trading. The bot never places a Binance order. A key that can withdraw is refused.'},
}
def about(name): return ABOUT.get(name) or ABOUT.get('mt5' if CATALOG.get(name) == 'mt5' else '', {})
def catalog(): return [dict({'name': k, 'kind': v}, **about(k)) for k, v in CATALOG.items()]
'''),
    (r'''    for pre in ('bot', 'why', 'mode'): st.x('DELETE FROM kv WHERE k=?', ('%s:%s:%s' % (pre, uid, n),))          # a new key starts with the bot off again (switch forgotten)
''',
     r'''    for pre in ('bot', 'why', 'mode', 'note'): st.x('DELETE FROM kv WHERE k=?', ('%s:%s:%s' % (pre, uid, n),))          # a new key starts with the bot off again (switch forgotten)
'''),
    (r'''
def mode_flag(uid, name):
''',
     r'''
def set_note(uid, name, text): st.put('note:%s:%s' % (uid, name), str(text)[:300])
def note(uid, name): return st.get('note:%s:%s' % (uid, name)) or ''

def mode_flag(uid, name):
'''),
    (r'''    return [dict({'name': r['broker'], 'kind': r['kind'], 'label': r['label'], 'mode': mode(uid, r['broker'], r['mode']), 'status': r['status'] or 'saved', 'bot': bot_flag(uid, r['broker']) is True, **_why(uid, r['broker'])},
''',
     r'''    return [dict({'name': r['broker'], 'kind': r['kind'], 'label': r['label'], 'mode': mode(uid, r['broker'], r['mode']), 'status': r['status'] or 'saved', 'bot': bot_flag(uid, r['broker']) is True, 'note': note(uid, r['broker']), 'trades': r['broker'] != 'Binance', **_why(uid, r['broker'])},
'''),
    (r'''    for pre in ('bal', 'bot', 'why', 'mode'): st.x('DELETE FROM kv WHERE k=?', ('%s:%s:%s' % (pre, uid, name),))
''',
     r'''    for pre in ('bal', 'bot', 'why', 'mode', 'note'): st.x('DELETE FROM kv WHERE k=?', ('%s:%s:%s' % (pre, uid, name),))
'''),
  ],
  'tests/test_deriv1.py': [
    (r'''T('only Deriv is checkable for now', c.post('/api/brokers/Binance/verify', headers=H('amy@x.com')).status_code == 400)
''',
     r'''T('only Deriv and Binance are checkable; an MT5 broker is told to use its MT5 app', c.post('/api/brokers/FBS/verify', headers=H('amy@x.com')).status_code == 400 and c.post('/api/brokers/Binance/verify', headers=H('amy@x.com')).status_code == 200)
'''),
  ],
  'tests/test_deriv3.py': [
    (r'''T('balance is private to its owner', 'balance' not in str(c.get('/api/brokers', headers=H('bob@x.com')).json))
''',
     r'''T('balance is private to its owner', all('balance' not in b for b in c.get('/api/brokers', headers=H('bob@x.com')).json['brokers']))
'''),
  ],
  'static/index.html': [
    (r'''inance","API key"]],CN={};
''',
     r'''inance","API key"]],CN={},CAT={};
'''),
    (r'''turn'<span class="bal x">Token rejected</span>';if(b.balance!=null&&b.st''',
     r'''turn'<span class="bal x">'+(b.name==="Binance"?"Key rejected":"Token rejected")+'</span>';if(b.name==="Binance"&&b.status==="verified")return(b.balance!=null?plB(b)+" \u00b7 ":"")+"Read-only, no trading";if(b.balance!=null&&b.st'''),
    (r'''turn'<button class="pt'+(CN[p[0]]&&CN[p[0]].status!=="rejected"&&CN[p[0]].kind!=="mt5"?" on":"")+'" data-p="'+p[0]+'">'+''',
     r'''turn'<button class="pt'+(p[0]==="Binance"?(CN.Binance&&CN.Binance.status==="verified"?" on":""):(CN[p[0]]&&CN[p[0]].status!=="rejected"&&CN[p[0]].kind!=="mt5"?" on":""))+'" data-p="'+p[0]+'">'+'''),
    (r''''+(CN[p[0]]?plT(CN[p[0]]):p[1]==="MT5 bridge"?"Via''',
     r''''+(CN[p[0]]?plT(CN[p[0]]):CAT[p[0]]&&CAT[p[0]].tile?CAT[p[0]].tile:p[1]==="MT5 bridge"?"Via'''),
    (r'''kers").then(function(j){CN={};(j.brokers||[]).forE''',
     r'''kers").then(function(j){CAT={};(j.catalog||[]).forEach(function(c){CAT[c.name]=c});CN={};(j.brokers||[]).forE'''),
    (r'''irtual) account first.":"Create an API key with trading only. Never enable withdrawals.";
  ov(XB+'<h2>Connect '+n+'</h2><p class="muted">'+tx+'</p><div class="field"><label''',
     r'''irtual) account first.":"1. In Binance open API Management and make a key. 2. Turn Enable Reading ON and Withdrawals OFF (a key that can withdraw is refused). 3. Paste the key and secret below. We check them and read your Spot balance. Binance trading is not switched on: this app never places a Binance order.";
  ov(XB+'<h2>Connect '+n+'</h2><p class="muted">'+tx+'</p>'+(CAT[n]&&CAT[n].works?'<p class="note"><b>Works now:</b> '+CAT[n].works+' <b>Not yet:</b> '+(CAT[n].not||"-")+'</p>':'')+'<div class="field"><label'''),
    (r'''onnection")+'</button>'+(cur?'<button class="btn b''',
     r'''onnection")+'</button>'+(bn&&cur?'<button class="btn block" id="pC">Check again and refresh balance</button>':'')+(cur?'<button class="btn b'''),
    (r'''.textContent=cur.why||"";
''',
     r'''.textContent=cur.why||"";var pn=$("#pE");if(bn&&cur&&cur.note&&pn)pn.textContent=cur.note;var pc2=$("#pC");if(pc2)pc2.onclick=function(){pc2.disabled=true;pn.textContent="Checking...";window.SXA.api("/api/brokers/Binance/verify",{method:"POST",body:{}}).then(function(r){pc2.disabled=false;ldB();pn.textContent=(r&&r.message)||""}).catch(function(x){pc2.disabled=false;pn.textContent=x.message||"Could not check. Try again."})};
'''),
    (r'''function(){if(n!=="Deriv"){closeOv();tst(bn?n+" saved, not checked yet":n+" server name saved. Ne''',
     r'''function(){if(n!=="Deriv"&&!bn){closeOv();tst(n+" server name saved. Ne'''),
    (r'''ow.SXA.api("/api/brokers/Deriv/verify",{method:"POST",b''',
     r'''ow.SXA.api("/api/brokers/"+n+"/verify",{method:"POST",b'''),
    (r'''f(r&&r.ok){closeOv();tst(r.message||"Deriv connect''',
     r'''f(r&&r.ok){closeOv();tst(bn?"Binance key checked. Balance read.":r.message||"Deriv connect'''),
    (r''')||"Could not check this token."}}).catch(function(x){g''',
     r''')||"Could not check this key."}}).catch(function(x){g'''),
  ],
}

def rd(p):
    with open(p, encoding='utf-8') as f: return f.read()
def main():
    if not os.path.isdir('backend'): sys.exit('Run this from the repo root (the folder that has backend/).')
    if os.path.exists('backend/binance.py'): print('Already applied. Nothing to do.'); return
    out = {}
    for path, prs in FILES.items():
        s = rd(path)
        for old, new in prs:
            if s.count(old) != 1: sys.exit('STOP: expected text not found exactly once in %s. Nothing was changed.\n%s' % (path, old[:120]))
            s = s.replace(old, new)
        out[path] = s
    out.update(NEW)
    for path, s in out.items():
        with open(path, 'w', encoding='utf-8', newline='') as f: f.write(s)
        print('wrote', path)
    print('Done. Now push it.')
main()
