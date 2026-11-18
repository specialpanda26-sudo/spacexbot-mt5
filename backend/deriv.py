"""Deriv adapter, step 1: check a customer's token. READ-ONLY, it never trades.
Uses Deriv's new API: REST with the token + the Deriv-App-ID header (DERIV_APP_ID is OUR app, same for everyone; the token is the customer's own).
Reply shapes are read loosely on purpose (not yet confirmed with deriv_probe.py), and nothing here ever puts a token in a message."""
import os, re, json, time
from . import store as st, brokers as bk

BASE = lambda: os.getenv('DERIV_BASE', 'https://api.derivws.com').rstrip('/')
APP = lambda: os.getenv('DERIV_APP_ID', '').strip()
_last = {}

def _http(method, path, token):
    import requests
    r = requests.request(method, BASE() + path, data=b'' if method == 'POST' else None, timeout=15,
                         headers={'Authorization': 'Bearer ' + token, 'Deriv-App-ID': APP(), 'Accept': 'application/json'})
    try: j = r.json()
    except ValueError: j = {}
    return r.status_code, j

def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values(): yield from _walk(v)
    elif isinstance(o, list):
        for v in o: yield from _walk(v)

def accounts(token, http=None):
    """[{'id','demo','currency'}] from whatever shape Deriv returns. Raises PermissionError (token refused) or ConnectionError."""
    try: code, j = (http or _http)('GET', '/trading/v1/options/accounts', token)
    except Exception: raise ConnectionError('Could not reach Deriv. Try again in a minute.')
    if code in (401, 403): raise PermissionError('Deriv did not accept this token. Check it has Read and Trade scopes and is not expired.')
    if code != 200: raise ConnectionError('Deriv is not answering right now. Try again in a minute.')
    out, seen = [], set()
    for d in _walk(j):
        i = d.get('account_id') or d.get('id') or d.get('loginid')
        if not i or str(i) in seen: continue
        seen.add(str(i)); s = json.dumps({k: v for k, v in d.items() if not isinstance(v, (dict, list))})
        demo = bool(re.search(r'demo|virtual', s, re.I)) or str(i).upper().startswith(('VRT', 'DOT'))
        out.append({'id': str(i), 'demo': demo, 'currency': str(d.get('currency') or 'USD')})
    return out

def ws_url(token, acct, http=None):
    """A fresh one-time websocket link (valid about 2 minutes). Needed on every connect."""
    if not re.match(r'^[A-Za-z0-9_\-]{3,40}$', str(acct)): raise ValueError('bad account id')
    try: code, j = (http or _http)('POST', '/trading/v1/options/accounts/%s/otp' % acct, token)
    except Exception: raise ConnectionError('Could not reach Deriv. Try again in a minute.')
    u = (j.get('data') or {}).get('url') if isinstance(j, dict) else None
    if code != 200 or not isinstance(u, str) or not u.startswith('wss://'): raise ConnectionError('Deriv would not open a trading link for this account.')
    return u

def verify(uid, http=None, now=None):
    """Check the saved Deriv token. Sets status 'verified' or 'rejected'. Returns (ok, message). Needs DERIV_APP_ID on Render."""
    now = now or time.time()
    if now - _last.get(uid, 0) < 8: return False, 'Wait a few seconds and try again.'
    _last[uid] = now
    if not APP(): return False, 'Deriv trading is not switched on yet. Please try again soon.'
    sec = bk.secret(uid, 'Deriv')
    if not sec or not sec.get('token'): return False, 'Save your Deriv token first.'
    try:
        accts = accounts(sec['token'], http)
        if not accts: raise PermissionError('This token has no trading account. Make it on your Deriv account with Read and Trade scopes.')
    except PermissionError as e: _mark(uid, 'rejected'); return False, str(e)
    except ConnectionError as e: return False, str(e)
    _mark(uid, 'verified')
    demo = [a for a in accts if a['demo']]
    return True, 'Deriv connected. Demo account found.' if demo else 'Deriv connected, but no demo account was found. Trading stays off until you add one.'

def _mark(uid, status): st.x("UPDATE broker_links SET status=?,updated=? WHERE uid=? AND broker='Deriv'", (status, int(time.time()), uid))
