"""C-AUTH 1 checks: Log in with Deriv (backend/deriv_oauth.py, GET /api/deriv/login, GET /auth/deriv/callback). Fake Deriv, no network. Run: python tests/test_ca1.py"""
import os, sys, glob, io, re, json, time, base64, hashlib, contextlib
from urllib.parse import urlparse, parse_qs
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_ca1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='https://bot.example.com', SYMBOLS='XAUUSD', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='app123')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import deriv_oauth as do, alerts, store as st, brokers as bk
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'bob@x.com'): c.get('/api/me', headers=H(e))
UA, UB = 'dev-amy@x.com', 'dev-bob@x.com'
TOKEN = 'ory_at_' + 'A' * 40 + '.' + 'b' * 43; CODE = 'the-one-time-code-xyz'
def q(url): return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
def verifier(state): return json.loads(st.get('dauth:' + state))['v']
sent = []
def fake(status=200, body=None):
    def h(url, data): sent.append((url, dict(data))); return status, (body if body is not None else {'access_token': TOKEN, 'expires_in': 2592000})
    return h
ok_verify = lambda uid: (True, 'Deriv connected. Demo account found.')
# --- start
os.environ['DERIV_APP_ID'] = ''; u, why = do.start(UA); T('no DERIV_APP_ID: no link, plain reason names it', u is None and 'DERIV_APP_ID' in why)
os.environ['DERIV_APP_ID'] = 'app123'; os.environ['BASE_URL'] = ''; u, why = do.start(UA); T('no BASE_URL: no link, plain reason names it', u is None and 'BASE_URL' in why)
os.environ['BASE_URL'] = 'http://bot.example.com'; u, why = do.start(UA); T('a plain http site address is refused', u is None)
os.environ['BASE_URL'] = 'https://bot.example.com/'
url, why = do.start(UA); p = q(url); state = p['state']
T('link goes to Deriv login with the standard parameters', url.startswith('https://auth.deriv.com/oauth2/auth?') and p['response_type'] == 'code' and p['client_id'] == 'app123' and p['code_challenge_method'] == 'S256')
T('return address is exactly the site + /auth/deriv/callback', p['redirect_uri'] == 'https://bot.example.com/auth/deriv/callback')
T('only the trade scope is asked for (no payment, no account management)', p['scope'] == 'trade')
T('code_challenge is the SHA-256 of the stored verifier', p['code_challenge'] == base64.urlsafe_b64encode(hashlib.sha256(verifier(state).encode()).digest()).decode().rstrip('='))
T('verifier is 43 to 128 safe characters and state is long and random', 43 <= len(verifier(state)) <= 128 and len(state) >= 32 and do.start(UA)[0] and True)
T('a new attempt cancels the earlier one for that person', do.finish(state, CODE, http=fake(), verify=ok_verify)[0] is False)
# --- finish
url, _ = do.start(UA); state = url and q(url)['state']; v = verifier(state); sent.clear()
ok, msg = do.finish(state, CODE, http=fake(), verify=ok_verify, now=time.time())
T('good login: ok and the verify message comes back', ok and 'Deriv connected' in msg)
T('code, verifier, client id and return address went to Deriv token address', sent and sent[0][0] == do.TOKEN and sent[0][1] == {'grant_type': 'authorization_code', 'client_id': 'app123', 'code': CODE, 'code_verifier': v, 'redirect_uri': 'https://bot.example.com/auth/deriv/callback'})
sec = bk.secret(UA, 'Deriv'); T('the token is in the vault under that person, like a pasted token', sec and sec.get('token') == TOKEN)
T('the other person has nothing', bk.secret(UB, 'Deriv') is None)
T('expiry is kept from expires_in', abs(int(st.get('dexp:' + UA)) - (time.time() + 2592000)) < 20 and do.status(UA)['days_left'] in (29, 30))
T('the attempt is single use', do.finish(state, CODE, http=fake(), verify=ok_verify)[0] is False)
for bad, n in (('', 'empty state'), ('nope', 'unknown state'), ('x' * 500, 'huge state')): T('a ' + n + ' is refused and saves nothing', do.finish(bad, CODE, http=fake(), verify=ok_verify)[0] is False)
url, _ = do.start(UB); sb = q(url)['state']; ok, msg = do.finish(sb, '', 'access_denied', http=fake(), verify=ok_verify)
T('cancelled on Deriv: not ok, plain words, nothing saved, no token call', not ok and 'cancelled' in msg and bk.secret(UB, 'Deriv') is None)
url, _ = do.start(UB); sb = q(url)['state']; sent.clear(); ok, msg = do.finish(sb, CODE, http=fake(), verify=ok_verify, now=time.time() + 601)
T('an attempt older than 10 minutes is refused before Deriv is called', not ok and 'too long' in msg and not sent and bk.secret(UB, 'Deriv') is None)
url, _ = do.start(UB); sb = q(url)['state']; ok, msg = do.finish(sb, CODE, http=fake(400, {'error': 'invalid_grant'}), verify=ok_verify)
T('Deriv refuses the code: not ok, nothing saved', not ok and bk.secret(UB, 'Deriv') is None)
def boom(u, d): raise OSError('down')
url, _ = do.start(UB); sb = q(url)['state']; ok, msg = do.finish(sb, CODE, http=boom, verify=ok_verify); T('Deriv unreachable: plain message, nothing saved', not ok and 'reach Deriv' in msg and bk.secret(UB, 'Deriv') is None)
url, _ = do.start(UB); sb = q(url)['state']; ok, msg = do.finish(sb, CODE, http=fake(200, {'access_token': 'ory_at_' + 'z' * 200}), verify=ok_verify)
T('a token the vault cannot keep is refused in plain words', not ok and 'paste a token' in msg and bk.secret(UB, 'Deriv') is None)
url, _ = do.start(UB); sb = q(url)['state']; do.finish(sb, CODE, http=fake(200, {'access_token': TOKEN}), verify=ok_verify)
T('no expires_in: a safe default is kept (one day)', 80000 < int(st.get('dexp:' + UB)) - time.time() < 90000)
url, _ = do.start(UB); sb = q(url)['state']; buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf): do.finish(sb, CODE, http=fake(), verify=ok_verify)
T('no token and no code is ever printed', TOKEN not in buf.getvalue() and CODE not in buf.getvalue())
T('the saved status and message never hold the token', TOKEN not in json.dumps(do.status(UA)) and TOKEN not in str(st.get('dmsg:' + UA)))
# --- routes
T('login address needs a signed-in person', c.get('/api/deriv/login').status_code == 401)
r = c.get('/api/deriv/login', headers=H('amy@x.com')); T('signed in gets a Deriv link', r.status_code == 200 and r.get_json()['url'].startswith('https://auth.deriv.com/oauth2/auth?'))
os.environ['DERIV_APP_ID'] = ''; r = c.get('/api/deriv/login', headers=H('amy@x.com')); T('not switched on: plain 503', r.status_code == 503 and 'DERIV_APP_ID' in r.get_json()['error']); os.environ['DERIV_APP_ID'] = 'app123'
r = c.get('/auth/deriv/callback?state=bad&code=abc'); T('callback with a bad state goes back to the app as a failure, no token or code in the address', r.status_code == 302 and r.headers['Location'] == '/?deriv=fail#connect')
r = c.get('/auth/deriv/callback?error=access_denied&state=bad'); T('callback with an error goes back as a failure', r.status_code == 302 and 'fail' in r.headers['Location'])
T('status needs sign-in and answers when signed in', c.get('/api/deriv/login-status').status_code == 401 and 'on' in c.get('/api/deriv/login-status', headers=H('amy@x.com')).get_json())
src = open(os.path.join(ROOT, 'backend', 'deriv_oauth.py'), encoding='utf-8').read()
T('no payment or account_manage scope anywhere in the file', not re.search(r"scope.{0,40}(payment|account_manage)", src, re.I) and "SCOPE = 'trade'" in src)
T('no profit promise in the messages', not re.search(r'guarantee|risk.free|sure profit', src, re.I))
for f in glob.glob(DB + '*'): os.remove(f)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
