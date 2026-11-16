"""Firebase Admin: verify Google sign-in tokens + send push (FCM). Lazy so the app boots without it."""
import os, json
_ready = None
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
    """-> {'uid','email','name'} or None"""
    if os.getenv('DEV_AUTH') == '1' and token.startswith('dev:'):
        em = token[4:]; return {'uid': 'dev-' + em, 'email': em, 'name': em.split('@')[0]}
    if not _init(): return None
    try:
        from firebase_admin import auth
        d = auth.verify_id_token(token); return {'uid': d['uid'], 'email': d.get('email', ''), 'name': d.get('name', '')}
    except Exception as e:
        print('verify failed:', e); return None
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
