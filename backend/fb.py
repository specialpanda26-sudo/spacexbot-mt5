"""Firebase Admin: verify Google/email sign-in tokens, revoke sessions, delete users, send push (FCM). Lazy so the app boots without it."""
import os, json, time, hashlib, threading
_ready = None; _cache = {}; _cl = threading.Lock()
def _init():
    global _ready
    if _ready is not None: return _ready
    raw = os.getenv('FIREBASE_SERVICE_ACCOUNT')
    if not raw: _ready = False; return False
    try:
        import firebase_admin
        from firebase_admin import credentials
        firebase_admin.initialize_app(credentials.Certificate(json.loads(raw))); _ready = True
    except Exception as e:
        print('firebase init failed:', e); _ready = False
    return _ready
def verify(token):
    """-> {'uid','email','name','verified'} or None. Revocation is checked, results cached 60 s per token."""
    if os.getenv('DEV_AUTH') == '1' and token.startswith('dev:'):
        em = token[4:]; return {'uid': 'dev-' + em, 'email': em, 'name': em.split('@')[0], 'verified': True}
    if not _init(): return None
    k = hashlib.sha256(token.encode()).hexdigest(); now = time.time()
    with _cl:
        hit = _cache.get(k)
        if hit and hit[0] > now: return dict(hit[1])
        if len(_cache) > 2000: _cache.clear()
    try:
        from firebase_admin import auth
        d = auth.verify_id_token(token, check_revoked=True)
        u = {'uid': d['uid'], 'email': d.get('email', ''), 'name': d.get('name', ''), 'verified': bool(d.get('email_verified'))}
    except Exception as e:
        print('verify failed:', e); return None
    with _cl: _cache[k] = (now + 60, u)
    return dict(u)
def revoke(uid):
    """Sign the person out everywhere (their refresh tokens stop working; cached checks expire within 60 s)."""
    if os.getenv('DEV_AUTH') == '1' and uid.startswith('dev-'): return True
    if not _init(): return False
    try:
        from firebase_admin import auth
        auth.revoke_refresh_tokens(uid)
        with _cl: _cache.clear()
        return True
    except Exception as e: print('revoke failed:', e); return False
def delete_user(uid):
    if os.getenv('DEV_AUTH') == '1' and uid.startswith('dev-'): return True
    if not _init(): return False
    try:
        from firebase_admin import auth
        auth.delete_user(uid); return True
    except Exception as e: print('firebase delete failed:', e); return False
def push(tokens, title, body):
    tokens = [t for t in tokens if t]
    if not tokens: return 0
    if not _init(): print('[push disabled]', title, body); return 0
    from firebase_admin import messaging
    ok = 0
    for t in tokens:
        try: messaging.send(messaging.Message(token=t, notification=messaging.Notification(title=title, body=body))); ok += 1
        except Exception as e: print('push fail:', e)
    return ok
