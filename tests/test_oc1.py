"""OC1 checks: owner switch 'No limit on open trades'. Offline. Run: python tests/test_oc1.py (last line: N checks, M failed)"""
import os, sys, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'oc1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, limits, risk, burst
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, O = 'dev-amy@x.com', 'dev-boss@x.com'
WD = 1700000000 - (1700000000 % 86400) + 86400 * 4 + 12 * 3600
while time.gmtime(WD).tm_wday >= 4: WD += 86400
def beat(uid, n):
    a = {'balance': 1000, 'equity': 1000, 'open': n, 'demo': True, 'seen': WD}
    if uid: st.x('UPDATE links SET acct=?,seen=? WHERE uid=?', (json.dumps(a), WD, uid))
    else: st.put('acct', json.dumps(a))
links.new_key(A); links.set_bot(A, True); st.put('bot_enabled', '1')

T('default: switch off, the owner limit is the old number', limits.no_cap('') is False and limits.max_open('') == 3)
beat('', 6); T('switch off: 6 open stops the owner ("max open positions")', risk.global_gate(WD + 5, uid='') == (False, 'max open positions'))
st.put('no_open_cap', '1')
T('switch on: owner scope has no cap', limits.no_cap('') is True and limits.max_open('') == limits.UNLIMITED)
T('switch on: the owner with 6 open passes the gate', risk.global_gate(WD + 5, uid='')[0] is True)
beat('', 40); T('switch on: even 40 open passes', risk.global_gate(WD + 5, uid='')[0] is True)
T("switch on: the owner's own signed-in uid counts as owner", limits.no_cap(O) is True and limits.max_open(O) == limits.UNLIMITED)
T('switch on: a subscriber is NOT lifted (still the default 3)', limits.no_cap(A) is False and limits.max_open(A) == 3)
beat(A, 3); T('switch on: the subscriber with 3 open is still stopped', risk.global_gate(WD + 5, uid=A) == (False, 'max open positions'))
T('view says unlimited for the owner only', limits.view('')['max_open_unlimited'] is True and limits.view(A)['max_open_unlimited'] is False)
beat('', 40); st.put('burst:', json.dumps({'on': True}))
pl, why = burst.plan('', 3)
T('burst: no ceiling for the owner (40 open, a burst still gets room)', pl is not None and pl['n'] >= 2)
beat(A, 0); pa, wa = burst.plan(A, 3)
T('burst: a subscriber still has the ceiling of 15', pa is not None and pa['n'] <= 15)
st.put('no_open_cap', '0')
T('switch off again: the old limit is back at once', limits.max_open('') == 3 and risk.global_gate(WD + 5, uid='') == (False, 'max open positions'))
r = c.post('/api/admin/settings', headers=H('boss@x.com'), json={'no_open_cap': '2'})
T('admin save refuses a value that is not 0 or 1', r.status_code == 400)
r = c.post('/api/admin/settings', headers=H('boss@x.com'), json={'no_open_cap': '1'})
T('admin save accepts 1 and the gate follows', r.status_code == 200 and limits.no_cap('') is True)
r = c.post('/api/admin/settings', headers=H('amy@x.com'), json={'no_open_cap': '1'})
T('a subscriber cannot flip the owner switch', r.status_code == 403)
st.put('no_open_cap', '0')
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page: the admin checkbox and the chip text are there', '"no_open_cap"' in html and 'L.max_open_unlimited' in html)
for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]
print('%d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
