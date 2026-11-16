"""Supabase Auth. The browser signs in (Google, or email + 6-digit code sent through Resend) and sends us its access token.
We never trust the browser: every request's token is checked with Supabase, which also rejects signed-out sessions."""
import os, time, hashlib, threading
import requests
_cache = {}; _cl = threading.Lock()
def _url(): return os.getenv('SUPABASE_URL', '').rstrip('/')
def _anon(): return os.getenv('SUPABASE_ANON_KEY', '')
def _svc(): return os.getenv('SUPABASE_SERVICE_KEY', '')
def configured(): return bool(_url() and _anon())
def public_config():
    """Safe to send to the browser (the anon key is public by design; data is protected by the server, not by this key)."""
    return {'url': _url(), 'key': _anon()}

def verify(token):
    """-> {'uid','email','name','verified'} or None. Cached 60 s per token."""
    if os.getenv('DEV_AUTH') == '1' and token.startswith('dev:'):
        em = token[4:]; return {'uid': 'dev-' + em, 'email': em, 'name': em.split('@')[0], 'verified': True}
    if not configured(): return None
    k = hashlib.sha256(token.encode()).hexdigest(); now = time.time()
    with _cl:
        hit = _cache.get(k)
        if hit and hit[0] > now: return dict(hit[1])
        if len(_cache) > 2000: _cache.clear()
    try:
        r = requests.get(_url() + '/auth/v1/user', headers={'Authorization': 'Bearer ' + token, 'apikey': _anon()}, timeout=8)
        if r.status_code != 200: return None
        d = r.json(); m = d.get('user_metadata') or {}
        u = {'uid': d['id'], 'email': d.get('email') or '', 'name': m.get('full_name') or m.get('name') or '',
             'verified': bool(d.get('email_confirmed_at') or d.get('confirmed_at'))}
    except Exception as e:
        print('verify failed:', e); return None
    with _cl: _cache[k] = (now + 60, u)
    return dict(u)

def revoke(uid):
    """Sign the person out of every other device (this one stays signed in)."""
    if os.getenv('DEV_AUTH') == '1' and uid.startswith('dev-'): return True
    if not configured(): return False
    try:
        from flask import request
        tok = request.headers.get('Authorization', '')[7:]
        r = requests.post(_url() + '/auth/v1/logout?scope=others', headers={'Authorization': 'Bearer ' + tok, 'apikey': _anon()}, timeout=8)
        with _cl: _cache.clear()
        return r.status_code in (200, 204)
    except Exception as e: print('revoke failed:', e); return False

def delete_user(uid):
    if os.getenv('DEV_AUTH') == '1' and uid.startswith('dev-'): return True
    if not (_url() and _svc()): return False
    try:
        r = requests.delete(_url() + '/auth/v1/admin/users/' + uid, headers={'Authorization': 'Bearer ' + _svc(), 'apikey': _svc()}, timeout=8)
        return r.status_code in (200, 204)
    except Exception as e: print('supabase delete failed:', e); return False

def notify(title, body, key=None):
    """Trade alerts: logged, and emailed through Resend to subscribers who kept Trade alerts on."""
    print('[alert]', title, body)
    try:
        from . import mailer; mailer.trade_alert(title, body, key)
    except Exception as e: print('alert mail failed', e)
