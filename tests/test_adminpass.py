"""Admin access pass checks (backend/adminpass.py + /api/admin/pass + the #admin pass box). Run: python tests/test_adminpass.py"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'adminpass_test.db'); ROOT = os.path.join(HERE, '..')
PASS = 'correct horse 42'
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', ADMIN_PASS=PASS)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import adminpass as ap
C = app.test_client(); R = []
def T(name, ok): R.append((name, bool(ok)))
def post(code, ip='1.1.1.1'): return C.post('/api/admin/pass', json={'code': code}, headers={'X-Forwarded-For': ip})
def H(tok): return {'X-Admin-Pass': tok}
BOSS = {'Authorization': 'Bearer dev:boss@x.com'}; JOE = {'Authorization': 'Bearer dev:joe@x.com'}
C.get('/api/me', headers=BOSS); C.get('/api/me', headers=JOE)

ap.reset()
T('admin routes refuse a visitor with no pass', C.get('/api/admin/brain').status_code == 401)
r = post('wrong pass'); T('a wrong pass is refused (401), no token given', r.status_code == 401 and 'token' not in r.json)
r = post(PASS); tok = r.json.get('token', '')
T('the right pass gives a token', r.status_code == 200 and tok.count('.') == 1 and PASS not in tok)
T('the token opens admin routes (brain, subscribers, health)', all(C.get(p, headers=H(tok)).status_code == 200 for p in ('/api/admin/brain', '/api/admin/subscribers', '/api/admin/health')))
T('the token can change things (test price, settings, plans)', C.post('/api/admin/testprice', json={'kes': 1, 'usd': 0.01}, headers=H(tok)).status_code == 200
  and C.post('/api/admin/settings', json={'risk_pct': '0.5'}, headers=H(tok)).status_code == 200 and C.post('/api/admin/testprice', json={'off': True}, headers=H(tok)).status_code == 200)
T('a made-up token is refused', C.get('/api/admin/brain', headers=H('9999999999.abcdef')).status_code == 401 and C.get('/api/admin/brain', headers=H('junk')).status_code == 401)
exp, sig = tok.split('.'); bad = exp + '.' + ('0' if sig[0] != '0' else '1') + sig[1:]
T('a token with one changed character is refused', C.get('/api/admin/brain', headers=H(bad)).status_code == 401)
T('a token with a later expiry is refused (cannot be extended)', C.get('/api/admin/brain', headers=H(str(int(exp) + 99999) + '.' + sig)).status_code == 401)
T('an expired token is refused', not ap.valid(ap.issue(now=1000)) and ap.valid(ap.issue()) and not ap.valid(tok, now=int(exp) + 1))
T('a token lasts about 12 hours', abs(int(exp) - __import__('time').time() - 12 * 3600) < 60)
T('the pass does NOT open normal user routes', C.get('/api/me', headers=H(tok)).status_code == 401 and C.get('/api/status', headers=H(tok)).status_code == 401)
T('the pass in a user route header changes nothing for a normal user', C.get('/api/admin/brain', headers={**JOE, **{'X-Admin-Pass': 'junk'}}).status_code == 403)
T('the old email admin still works (nothing removed)', C.get('/api/admin/brain', headers=BOSS).status_code == 200)
T('a normal signed-in user is still refused', C.get('/api/admin/brain', headers=JOE).status_code == 403)
T('the pass box does not return the pass anywhere', PASS not in C.get('/api/admin/health', headers=H(tok)).get_data(as_text=True))

# changing ADMIN_PASS ends passes already given
os.environ['ADMIN_PASS'] = 'a different one 99'
T('changing ADMIN_PASS ends old passes', C.get('/api/admin/brain', headers=H(tok)).status_code == 401)
os.environ['ADMIN_PASS'] = PASS
T('...and the old pass works again if it is set back (same signature)', C.get('/api/admin/brain', headers=H(tok)).status_code == 200)

# off when not set / too short
os.environ['ADMIN_PASS'] = ''
T('no ADMIN_PASS: the pass route says it is not set up', post('anything').status_code == 400 and not ap.enabled() and C.get('/api/admin/brain', headers=H(tok)).status_code == 401)
os.environ['ADMIN_PASS'] = 'short'
T('a pass under 8 characters is treated as not set', post('short').status_code == 400 and not ap.enabled())
os.environ['ADMIN_PASS'] = PASS

# lockout
ap.reset()
for i in range(5): post('nope', '2.2.2.2')
r = post(PASS, '2.2.2.2')
T('5 wrong tries lock that address, even the right pass is refused (429)', r.status_code == 429 and 'minutes' in r.json['error'])
T('another address is not locked', post(PASS, '3.3.3.3').status_code == 200)
t0 = 5000
for i in range(5): ap.attempt('nope', '4.4.4.4', now=t0)
T('the lock ends after 10 minutes', ap.attempt(PASS, '4.4.4.4', now=t0 + 599)[1] == 'locked' and ap.attempt(PASS, '4.4.4.4', now=t0 + 601)[1] == 'ok')
ap.reset()
for i in range(4): post('nope', '5.5.5.5')
post(PASS, '5.5.5.5')
for i in range(4): post('nope', '5.5.5.5')
T('a right pass clears the count of wrong tries', post(PASS, '5.5.5.5').status_code == 200)
ap.reset()
for i in range(30): ap.attempt('nope', 'ip%d' % i, now=9000)
T('30 wrong tries from many addresses lock the pass for everyone', ap.attempt(PASS, 'fresh', now=9001)[1] == 'locked')
T('...and it opens again after 10 minutes', ap.attempt(PASS, 'fresh', now=9000 + 601)[1] == 'ok')
ap.reset()
T('non-text and huge codes cannot crash it', C.post('/api/admin/pass', json={'code': {'a': 1}}).status_code == 401 and C.post('/api/admin/pass', json={'code': 'x' * 100000}).status_code == 401
  and C.post('/api/admin/pass', data='not json', content_type='text/plain').status_code == 401 and post('pässwörd').status_code == 401)

# the page itself
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read(); js = open(os.path.join(ROOT, 'static', 'live.js'), encoding='utf-8').read()
T('#admin shows a pass box in the site style (password input, .btn primary big block)', 'id="apI" type="password"' in html and 'class="btn primary big block" id="apGo"' in html and '<div class="field">' in html.split('function apGate')[1][:900])
T('the pass is kept for this tab only (sessionStorage), not forever', 'sessionStorage.setItem("sxap"' in html and 'localStorage.setItem("sxap"' not in html)
T('a stale pass is dropped and the box comes back', 'removeItem("sxap")' in html and 'apGate()' in html.split('function adm()')[1][:600])
T('a signed-in admin still opens the panel straight away', 'if(me&&me.admin){if(!U)U=me;apOpen();return}' in html)
T('the pass header is sent on /api/admin/ paths only', 'path.indexOf("/api/admin/") === 0' in js and 'h["X-Admin-Pass"]' in js)
T('.env.example documents ADMIN_PASS', 'ADMIN_PASS=' in open(os.path.join(ROOT, '.env.example'), encoding='utf-8').read())

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
