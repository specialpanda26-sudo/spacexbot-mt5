"""Section 9a checks: welcome email on first sign-in. No network. Run: python tests/test_welcome9.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'welcome9_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', RESEND_API_KEY='re_test', MAIL_FROM='spaceXBot <a@b.com>', MAIL_ALERT_CAP='1', MAIL_HARD_CAP='9')
os.environ.pop('MAIL_WELCOME', None)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import store as st, mailer as M
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
class Resp:
    status_code = 200
    def json(s): return {'id': 'em_1'}
calls = []
M.requests.post = lambda url, json=None, headers=None, timeout=None: (calls.append((json, headers)) or Resp())
def wait(n):
    for _ in range(100):
        if len(calls) >= n: break
        time.sleep(0.05)
    time.sleep(0.15)
H = lambda e: {'Authorization': 'Bearer dev:' + e}; C = app.test_client()
C.get('/api/me', headers=H('ann.lee@x.com')); wait(1)
T('first sign-in sends one welcome email to that address', len(calls) == 1 and calls[0][0]['to'] == ['ann.lee@x.com'])
b = calls[0][0] if calls else {'subject': '', 'html': '', 'text': ''}
T('subject and heading greet the person by first name', b['subject'] == 'Welcome to spaceXBot' and 'Welcome to spaceXBot, ann.lee!' in b['text'])
T('the three steps are in the text and the html', all(s in b['text'] and s in b['html'] for s in ('Choose a plan', 'Connect Deriv or MT5', 'Start the bot on the Bot tab')))
T('uses an existing picture (alert.gif), not a missing one', '/static/email/alert.gif' in b['html'] and os.path.exists(os.path.join(HERE, '..', 'static', 'email', 'alert.gif')))
T('idempotency key is welcome/<uid>', calls[0][1]['Idempotency-Key'] == 'welcome/dev-ann.lee@x.com')
C.get('/api/me', headers=H('ann.lee@x.com')); C.get('/api/me', headers=H('ann.lee@x.com')); wait(2)
T('later sign-ins send nothing more', len(calls) == 1)
C.get('/api/me', headers=H('bob@x.com')); wait(2)
T('the alert cap (1) does not block a welcome', len(calls) == 2 and calls[1][0]['to'] == ['bob@x.com'])
T('the welcome is counted as a receipt-kind email (day count 2)', int(st.get(M._day_key()) or 0) == 2)
st.x('INSERT INTO users(uid,email,name,created,onboarded) VALUES(?,?,?,?,0)', ('dev-old@x.com', 'old@x.com', 'Old', int(time.time())))
n = len(calls); C.get('/api/me', headers=H('old@x.com')); time.sleep(0.4)
T('a person who already has a row gets nothing (no email to existing people)', len(calls) == n)
import backend.app as A
real_v = A.sbauth.verify; A.sbauth.verify = lambda t: {'uid': 'u-unv', 'email': 'unv@x.com', 'name': 'U', 'verified': False}
n = len(calls); r = C.get('/api/me', headers={'Authorization': 'Bearer x'}); time.sleep(0.4)
T('an unverified email gets no welcome, sign-in still works', len(calls) == n and r.status_code == 200 and st.q('SELECT 1 FROM users WHERE uid=?', ('u-unv',), True))
A.sbauth.verify = real_v
os.environ['MAIL_WELCOME'] = '0'; n = len(calls); C.get('/api/me', headers=H('cat@x.com')); time.sleep(0.4)
T('MAIL_WELCOME=0 turns it off', len(calls) == n)
os.environ.pop('MAIL_WELCOME'); os.environ['RESEND_API_KEY'] = ''; n = len(calls); r = C.get('/api/me', headers=H('dan@x.com')); time.sleep(0.4)
T('email not set up: nothing sent and sign-in still works', len(calls) == n and r.status_code == 200)
os.environ['RESEND_API_KEY'] = 're_test'
T('no email address: nothing sent', M._welcome_now('nope') is False)
st.x('UPDATE users SET email=? WHERE uid=?', ('', 'dev-dan@x.com')); T('empty email on file: nothing sent', M._welcome_now('dev-dan@x.com') is False)
real = M.welcome; M.welcome = lambda uid: (_ for _ in ()).throw(RuntimeError('boom'))
r = C.get('/api/me', headers=H('eve@x.com')); T('a crash in welcome never breaks sign-in', r.status_code == 200)
M.welcome = real
print('\n%d/%d passed' % (sum(R), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(0 if all(R) else 1)
