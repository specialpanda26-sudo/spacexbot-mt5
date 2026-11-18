"""Section 1 tests (accounts). Run: python tests/test_accounts.py"""
import os, sys, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_acc.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

T('no token -> 401', c.get('/api/me').status_code == 401)
j = c.get('/api/me', headers=H('amy@x.com')).json
T('first sign-in creates the user', j['email'] == 'amy@x.com' and j['verified'] and not j['admin'] and j['dob'] is None and j['prof']['n']['trade'] == 1)
T('under 18 refused', c.post('/api/me/profile', json={'dob': '2015-01-01', 'gender': 'Female'}, headers=H('amy@x.com')).status_code == 400)
T('bad gender refused', c.post('/api/me/profile', json={'gender': 'x'}, headers=H('amy@x.com')).status_code == 400)
r = c.post('/api/me/profile', json={'dob': '1995-05-05', 'gender': 'Female', 'name': 'Amy W', 'user': 'Amy_fx', 'phone': '+254 700 000 000', 'exp': 'Beginner', 'n': {'daily': 1}, 'av': 3}, headers=H('amy@x.com'))
j = c.get('/api/me', headers=H('amy@x.com')).json
T('profile saved', r.status_code == 200 and j['name'] == 'Amy W' and j['age'] >= 30 and j['prof']['user'] == 'amy_fx' and j['prof']['n'] == {'quiet_start': 22, 'quiet_end': 6, 'trade': 1, 'risk': 1, 'news': 1, 'daily': 1, 'tips': 1, 'system': 1, 'billing': 1} and j['prof']['av'] == 3)
c.get('/api/me', headers=H('bob@x.com'))
r = c.post('/api/me/profile', json={'user': 'AMY_FX'}, headers=H('bob@x.com'))
T('username must be unique', r.status_code == 400 and 'taken' in r.json['error'])
T('bad username / phone refused', c.post('/api/me/profile', json={'user': 'a b'}, headers=H('bob@x.com')).status_code == 400 and c.post('/api/me/profile', json={'phone': 'abc'}, headers=H('bob@x.com')).status_code == 400)
T('unknown keys are ignored (no column injection)', c.post('/api/me/profile', json={'plan_until': 9999999999, 'name; DROP': 'x'}, headers=H('bob@x.com')).status_code == 200 and c.get('/api/me', headers=H('bob@x.com')).json['active'] is False)
T('admin email is admin', c.get('/api/me', headers=H('boss@x.com')).json['admin'])
T('admin cannot self-delete', c.delete('/api/me', headers=H('boss@x.com')).status_code == 400)
T('sign out everywhere ok', c.post('/api/me/signout-others', headers=H('amy@x.com')).json['ok'])
T('delete removes the user', c.delete('/api/me', headers=H('bob@x.com')).status_code == 200)
from backend import store as st
T('row gone', st.q("SELECT 1 FROM users WHERE uid='dev-bob@x.com'", one=True) is None)
# unverified emails: no admin, no payments
from backend import sbauth as fb
orig = fb.verify
fb.verify = lambda t: {'uid': 'u9', 'email': 'boss@x.com', 'name': '', 'verified': False}
T('unverified admin email is not admin', c.get('/api/me', headers={'Authorization': 'Bearer z'}).json['admin'] is False)
T('unverified cannot start a payment', c.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': '0712345678'}, headers={'Authorization': 'Bearer z'}).status_code == 403)
T('unverified cannot use admin api', c.post('/api/admin/grant', json={}, headers={'Authorization': 'Bearer z'}).status_code == 403)
fb.verify = orig
j = c.get('/api/me', headers=H('newbie@x.com')).json
T('a new account starts not onboarded', j['onboarded'] is False)
T('finishing onboarding is stored on the server', c.post('/api/me/profile', json={'onboarded': True}, headers=H('newbie@x.com')).status_code == 200 and c.get('/api/me', headers=H('newbie@x.com')).json['onboarded'] is True)
c.post('/api/me/profile', json={'onboarded': False}, headers=H('newbie@x.com'))
T('onboarded cannot be switched back off', c.get('/api/me', headers=H('newbie@x.com')).json['onboarded'] is True)
st.x("INSERT INTO users(uid,email,name,created) VALUES('dev-old@x.com','old@x.com','Old',1)")
T('accounts from before this change count as onboarded', c.get('/api/me', headers=H('old@x.com')).json['onboarded'] is True)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
