"""LIVE1 tests. Run: python tests/test_live1.py"""
import os, sys, tempfile, json
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_live1.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, live, push
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
j = c.get('/api/me', headers=H('boss@x.com')).json
T('live status is ON by default for the owner', j['prof']['n'].get('live') == 1)
r = c.post('/api/me/profile', json={'n': {'live': 0}}, headers=H('boss@x.com')); j = c.get('/api/me', headers=H('boss@x.com')).json
T('switching it off is saved', r.status_code == 200 and j['prof']['n']['live'] == 0)
T('saving another switch keeps live off', c.post('/api/me/profile', json={'n': {'tips': 0}}, headers=H('boss@x.com')).status_code == 200 and c.get('/api/me', headers=H('boss@x.com')).json['prof']['n']['live'] == 0)
c.post('/api/me/profile', json={'n': {'live': 1}}, headers=H('boss@x.com'))
T('switching it on is saved', c.get('/api/me', headers=H('boss@x.com')).json['prof']['n']['live'] == 1)
T('other switches untouched', c.get('/api/me', headers=H('boss@x.com')).json['prof']['n']['trade'] == 1)
uid = c.get('/api/me', headers=H('boss@x.com')).json['uid'] if 'uid' in c.get('/api/me', headers=H('boss@x.com')).json else 'dev-boss@x.com'
st.x("INSERT OR REPLACE INTO push_tokens(token,uid,platform,created,seen) VALUES('tok1',?, 'android',1,1)", (uid,))
sent = []; push.send_data = lambda u, d: sent.append((u, d)) or 1
live.snapshot = lambda now=None, uid='': {'on': True, 'a': {'balance': 100, 'equity': 101}, 'today': 1.5, 'open': [], 'now': 1000}
live._last.clear(); live.tick(1000)
T('switch ON: the owner phone gets the notification', len(sent) == 1 and sent[0][1].get('title', '').startswith('Bot running'))
c.post('/api/me/profile', json={'n': {'live': 0}}, headers=H('boss@x.com')); sent.clear(); live._last.clear(); live.tick(2000)
T('switch OFF: nothing is sent', sent == [])
html = open(os.path.join(os.path.dirname(__file__), '..', 'static', 'index.html'), encoding='utf-8').read()
T('Profile > Notifications shows the Live bot status row', 'pfT("n.live","Live bot status"' in html)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
