"""Section 7 backend checks: bridge.describe and GET /api/bridge. Offline. Run: python tests/test_bridge7.py (ends N/N passed)"""
import os, sys, time, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_bridge7.db'), BASE_URL='http://t')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.app import app
from backend import store as st, links, bridge

R = []
def T(n, ok): R.append((n, bool(ok)))
c = app.test_client(); SITE = 'https://x.onrender.com'
def hdr(email): return {'Authorization': 'Bearer dev:' + email}
def ea(acct, key='k'): return c.post('/api/ea/sync', json={'account': acct}, headers={'X-EA-Key': key})

r = c.get('/api/bridge'); T('signed out -> 401', r.status_code == 401)
from backend import sbauth
_v = sbauth.verify; sbauth.verify = lambda tk: dict(_v(tk), verified=False) if tk == 'dev:unv@x.com' else _v(tk)
r = c.get('/api/bridge', headers=hdr('unv@x.com')); T('email not verified -> 403, nothing is shown', r.status_code == 403)
sbauth.verify = _v
# the owner
r = c.get('/api/bridge', headers=hdr('boss@x.com')); j = r.get_json() or {}
T('owner, EA never reported -> state never with the setup checklist', r.status_code == 200 and j.get('state') == 'never' and len(j.get('help', [])) == 4)
T('the checklist names the EA_KEY and the site address', 'EA_KEY' in j['help'][1]['d'] and j['site'] in j['help'][0]['d'])
T('owner never reported: no login or balance made up', j.get('login') is None and j.get('balance') is None and j.get('age') is None)
ea({'balance': 9876.5, 'equity': 9900, 'open': 2, 'demo': True, 'allow_live': False, 'login': 12345678})
j = c.get('/api/bridge', headers=hdr('boss@x.com')).get_json()
T('owner online: state, login, balance, mode', j['state'] == 'online' and j['login'] == '12345678' and j['balance'] == 9876.5 and j['mode'] == 'demo' and j['open'] == 2)
T('online demo message says Demo and the account', 'Demo account 12345678' in j['message'] and j['age'] is not None and j['age'] < 5)
T('demo with AllowLive false says live is blocked (the safe setting)', 'blocked' in j['warn'])
T('bot off -> can_trade false and the real reason is passed on', j['bot'] is False and j['can_trade'] is False and j['why'] == 'bot off')
d = bridge.describe('', True, True, SITE, now=time.time() + 600)
T('10 minutes later -> offline with a plain "went quiet" line and 3 steps', d['state'] == 'offline' and 'quiet' in d['message'] and len(d['help']) == 3 and d['age'] >= 600)
ea({'balance': 5, 'demo': False, 'allow_live': False, 'login': 7})
j = c.get('/api/bridge', headers=hdr('boss@x.com')).get_json()
T('real account + AllowLive false -> warns that no real orders will be placed', j['mode'] == 'real' and 'no real orders' in j['warn'])
ea({'balance': 5, 'demo': False, 'allow_live': True, 'login': 7})
j = c.get('/api/bridge', headers=hdr('boss@x.com')).get_json()
T('real account + AllowLive true -> warns real money is at risk', 'Real money' in j['warn'])
ea({'balance': 5, 'login': ''})
j = c.get('/api/bridge', headers=hdr('boss@x.com')).get_json()
T('account type not reported -> mode unknown, no warning, no login', j['mode'] is None and j['warn'] == '' and j['login'] is None and j['message'].startswith('Bridge online. MT5 account.'))
# a subscriber
def user(email):
    h = hdr(email); c.get('/api/me', headers=h); return h
h = user('sub@x.com'); j = c.get('/api/bridge', headers=h).get_json()
T('subscriber without a key -> nolink, says to make the key', j['state'] == 'nolink' and 'key' in j['help'][0]['d'])
uid = st.q('SELECT uid FROM users WHERE email=?', ('sub@x.com',), True)['uid']
key = links.new_key(uid); key = key['key'] if isinstance(key, dict) else key
st.x('UPDATE users SET plan_until=? WHERE uid=?', (int(time.time()) + 86400, uid))
j = c.get('/api/bridge', headers=h).get_json()
T('subscriber with key, EA silent -> never; checklist says personal key, not EA_KEY', j['state'] == 'never' and 'personal key' in j['help'][1]['d'] and 'EA_KEY' not in j['help'][1]['d'])
ea({'balance': 100, 'demo': True, 'login': 55}, key)
j = c.get('/api/bridge', headers=h).get_json()
T('subscriber online sees their own account', j['state'] == 'online' and j['login'] == '55' and j['balance'] == 100.0)
T("the owner's numbers never leak to the subscriber", j['balance'] != 5)
st.x('UPDATE users SET plan_until=0 WHERE uid=?', (uid,))
j = c.get('/api/bridge', headers=h).get_json()
T('plan ended -> expired, no account numbers', j['state'] == 'expired' and j['balance'] is None and 'renew' in j['message'])
T('unverified/odd values never crash: a text balance and a list login', bridge.describe('', True, True, SITE)['state'] in ('online', 'offline', 'never'))
st.set_acct({'balance': 'abc', 'login': [1], 'open': 'x', 'demo': 'yes', 'allow_live': 'no'}, '')
d = bridge.describe('', True, True, SITE); T('garbage fields from the EA do not crash and give no numbers', d['balance'] is None and d['mode'] is None and d['allow_live'] is None and d['open'] == 0)
n = sum(ok for _, ok in R)
for name, ok in R:
    if not ok: print('FAIL', name)
print('%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
