"""C-AUTH 1: "Log in with Deriv" on the server. OAuth 2.0 Authorization Code + PKCE (Deriv's own login page; the person never copies a token).
Flow: start(uid) -> person approves on Deriv -> finish(state, code) swaps the code for an access token (server side), saves it in the same vault as a pasted token,
then runs the normal Deriv check. Deriv gives NO refresh token: when the token ends (expires_in) the person logs in again. We ask for the 'trade' scope only.
Nothing here ever prints or returns a token or a code."""
import os, json, time, hashlib, base64, secrets, string
from urllib.parse import urlencode
from . import store as st, brokers as bk

AUTH = 'https://auth.deriv.com/oauth2/auth'
TOKEN = 'https://auth.deriv.com/oauth2/token'
SCOPE = 'trade'
KEEP = 600                      # a login attempt is good for 10 minutes
_ABC = string.ascii_letters + string.digits + '-._~'

def client_id(): return (os.getenv('DERIV_CLIENT_ID') or os.getenv('DERIV_APP_ID') or '').strip()
def base(): return (os.getenv('BASE_URL') or os.getenv('PUBLIC_URL') or '').strip().rstrip('/')
def redirect_uri(): return base() + '/auth/deriv/callback'
def _b64(b): return base64.urlsafe_b64encode(b).decode('ascii').rstrip('=')

def start(uid, now=None):
    """-> (url, None) or (None, plain-words reason)."""
    now = int(now or time.time())
    if not client_id(): return None, 'Deriv login is not switched on yet. The owner must set DERIV_APP_ID on Render.'
    if not base().startswith('https://') and not base().startswith('http://localhost'): return None, 'Deriv login needs the site address. The owner must set BASE_URL on Render (https).'
    if not bk.ready(): return None, 'Broker linking is not switched on yet. Please try again soon.'
    old = st.get('dauthp:%s' % uid)
    if old: st.x('DELETE FROM kv WHERE k=?', ('dauth:%s' % old,))          # one login attempt at a time per person
    verifier = ''.join(secrets.choice(_ABC) for _ in range(64)); state = secrets.token_hex(16)
    st.put('dauth:%s' % state, json.dumps({'u': uid, 'v': verifier, 'e': now + KEEP})); st.put('dauthp:%s' % uid, state)
    q = {'response_type': 'code', 'client_id': client_id(), 'redirect_uri': redirect_uri(), 'scope': SCOPE, 'state': state,
         'code_challenge': _b64(hashlib.sha256(verifier.encode('ascii')).digest()), 'code_challenge_method': 'S256'}
    return AUTH + '?' + urlencode(q), None

def _http(url, data):
    import requests
    r = requests.post(url, data=data, headers={'Accept': 'application/json'}, timeout=15)
    try: j = r.json()
    except ValueError: j = {}
    return r.status_code, j

def _say(uid, ok, msg):
    if uid: st.put('dmsg:%s' % uid, json.dumps({'ok': bool(ok), 'msg': msg, 't': int(time.time())}))
    return bool(ok), msg

def finish(state, code, error='', http=None, verify=None, now=None):
    """The callback. -> (ok, plain message). The attempt is single use, whatever happens next."""
    now = int(now or time.time()); k = 'dauth:%s' % str(state or '')[:80]
    raw = st.get(k) if state else None
    if not raw or not st.x('DELETE FROM kv WHERE k=?', (k,), True): return False, 'This login link is not valid any more. Tap Log in with Deriv again.'
    try: rec = json.loads(raw); uid = rec['u']; ver = rec['v']
    except Exception: return False, 'This login link is not valid any more. Tap Log in with Deriv again.'
    if st.get('dauthp:%s' % uid) == str(state): st.x('DELETE FROM kv WHERE k=?', ('dauthp:%s' % uid,))
    if now > rec.get('e', 0): return _say(uid, False, 'The login took too long. Tap Log in with Deriv again.')
    if error or not code: return _say(uid, False, 'Deriv login was cancelled. Nothing was connected.')
    try: status, j = (http or _http)(TOKEN, {'grant_type': 'authorization_code', 'client_id': client_id(), 'code': str(code), 'code_verifier': ver, 'redirect_uri': redirect_uri()})
    except Exception: return _say(uid, False, 'Could not reach Deriv. Try again in a minute.')
    tok = j.get('access_token') if isinstance(j, dict) else None
    if status != 200 or not isinstance(tok, str) or not tok: return _say(uid, False, 'Deriv did not accept the login. Tap Log in with Deriv again.')
    try: bk.save(uid, 'Deriv', {'token': tok})
    except (ValueError, RuntimeError): return _say(uid, False, 'Deriv sent a login we could not keep safely. Tap Log in with Deriv again, or paste a token instead.')
    try: life = int(j.get('expires_in'))
    except (TypeError, ValueError): life = 86400
    st.put('dexp:%s' % uid, now + max(60, min(life, 90 * 86400)))
    if verify is None:
        from . import deriv
        verify = deriv.verify
    try: ok, msg = verify(uid)
    except Exception: ok, msg = False, 'Saved, but Deriv could not be checked just now.'
    return _say(uid, ok, msg)

def status(uid, now=None):
    """For the app: how long the login lasts, and what the last attempt said."""
    now = int(now or time.time()); e = st.get('dexp:%s' % uid); m = st.get('dmsg:%s' % uid)
    try: left = max(0, int(e) - now)
    except (TypeError, ValueError): left = None
    try: last = json.loads(m) if m else None
    except ValueError: last = None
    return {'on': bool(client_id()) and bk.ready(), 'seconds_left': left, 'days_left': None if left is None else left // 86400, 'last': last}
