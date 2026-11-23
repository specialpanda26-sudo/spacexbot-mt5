"""Losing-streak pause: request to continue + admin review (backend/streakreq.py, /api/streak*). Offline. Run: python tests/test_streakreq.py (last line: N/M passed)"""
import os, sys, time, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'streakreq_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, risk, streakreq, limits
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
U = {e: c.get('/api/me', headers=H(e)).json['uid'] for e in ('amy@x.com', 'bob@x.com', 'boss@x.com')}
A, B, O = U['amy@x.com'], U['bob@x.com'], U['boss@x.com']
NOW = time.time(); T0 = [0]
def loss(uid, ago, pnl=-5):
    T0[0] += 1; st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,closed,pnl,uid) VALUES('XAUUSD','buy',1,1,1,'closed',?,?,?,?)", (int(NOW - ago) - 60, int(NOW - ago), pnl, uid))
def refused(fn, *a):
    try: fn(*a); return False
    except ValueError: return True
st.put('max_losing_streak', 3); st.put('streak_cooldown_h', 4)

T('not paused: status says so and a request is refused', streakreq.status(A)['paused'] is False and refused(streakreq.request, A))
loss(A, 300); loss(A, 200); T('2 losses of 3: still not paused', risk.streak_state(A) is None)
loss(A, 100); s = risk.streak_state(A)
T('3 losses in a row: paused, with the count, the end time and the dollar losses', s and s['k'] == 3 and s['pnls'] == [-5, -5, -5] and int(s['until']) == int(NOW - 100) + 4 * 3600)
T('the gate text is unchanged (alerts read it)', risk.global_gate(uid=A)[1] in ('bot off', 'EA offline') or 'cooling down' in risk.global_gate(uid=A)[1])
T("someone else's pause is not affected (bob has no losses)", risk.streak_state(B) is None and streakreq.status(B)['paused'] is False)
g = c.get('/api/streak', headers=H('amy@x.com')).json
T('GET /api/streak: paused, 3 losses, no request yet', g['paused'] is True and g['k'] == 3 and g['losses'] == [-5, -5, -5] and g['request'] is None and g['owner'] is False and g['since'] == int(NOW - 100))
r = c.post('/api/streak/request', headers=H('amy@x.com'), json={})
T('POST /api/streak/request: pending', r.status_code == 200 and r.json['request']['status'] == 'pending' and r.json['request']['k'] == 3)
T('asking twice is refused', c.post('/api/streak/request', headers=H('amy@x.com'), json={}).status_code == 400)
T('bob (not paused) cannot ask', c.post('/api/streak/request', headers=H('bob@x.com'), json={}).status_code == 400)
T('the owner cannot ask (owner edits the limit directly)', c.post('/api/streak/request', headers=H('boss@x.com'), json={}).status_code == 400 and refused(streakreq.request, ''))
T('signed out: 401', c.get('/api/streak').status_code == 401)

# ---- admin review ----
T('a subscriber cannot read or decide (admin only)', c.get('/api/admin/streak', headers=H('amy@x.com')).status_code == 403 and c.post('/api/admin/streak', headers=H('amy@x.com'), json={'uid': A, 'approve': True}).status_code == 403)
l = c.get('/api/admin/streak', headers=H('boss@x.com')).json
T('admin list: amy is waiting, with email and losses', len(l['waiting']) == 1 and l['waiting'][0]['uid'] == A and l['waiting'][0]['email'] == 'amy@x.com' and l['waiting'][0]['losses'] == [-5, -5, -5] and l['recent'] == [])
T('a bad body is refused (no uid / approve not true or false)', c.post('/api/admin/streak', headers=H('boss@x.com'), json={'uid': A}).status_code == 400 and c.post('/api/admin/streak', headers=H('boss@x.com'), json={'uid': A, 'approve': 'yes'}).status_code == 400)
T('deciding for someone with no request is refused', c.post('/api/admin/streak', headers=H('boss@x.com'), json={'uid': B, 'approve': True}).status_code == 400)
d = c.post('/api/admin/streak', headers=H('boss@x.com'), json={'uid': A, 'approve': False, 'note': 'x' * 500})
T('decline: ok, note cut to 200, nothing waiting, one recent row', d.status_code == 200 and d.json['waiting'] == [] and d.json['recent'][0]['status'] == 'declined' and len(d.json['recent'][0]['note']) == 200)
T('declined: the pause stays on', risk.streak_state(A) is not None and st.get('streakok:' + A) in (None, ''))
g = c.get('/api/streak', headers=H('amy@x.com')).json
T('amy sees the declined request and the pause still on', g['paused'] is True and g['request']['status'] == 'declined')
T('amy cannot ask again for the SAME pause', c.post('/api/streak/request', headers=H('amy@x.com'), json={}).status_code == 400)
T('declining twice is refused (nothing waiting any more)', c.post('/api/admin/streak', headers=H('boss@x.com'), json={'uid': A, 'approve': True}).status_code == 400)

# ---- a NEW pause (another loss later) may be asked about again; approval restarts the count ----
loss(A, 30); T('a new loss makes a new pause', risk.streak_state(A) is not None and risk.streak_state(A)['since'] == int(NOW - 30))
r = c.post('/api/streak/request', headers=H('amy@x.com'), json={}); T('amy can ask for the new pause', r.status_code == 200 and r.json['request']['status'] == 'pending')
d = c.post('/api/admin/streak', headers=H('boss@x.com'), json={'uid': A, 'approve': True, 'note': 'ok, be careful'})
T('approve: ok, recent shows approved with the note', d.status_code == 200 and d.json['recent'][0]['status'] == 'approved' and d.json['recent'][0]['note'] == 'ok, be careful')
T('approved: the pause is OFF at once (count restarts)', risk.streak_state(A) is None and streakreq.status(A)['paused'] is False and streakreq.status(A)['request']['status'] == 'approved')
loss(A, -10); loss(A, -9)          # closed AFTER the approval moment
T('after approval 2 new losses do not pause again (needs 3)', risk.streak_state(A) is None)
loss(A, -8); T('3 new losses after approval pause again', risk.streak_state(A) is not None)
T('the other person (bob) was never changed by any of this', st.get('streakok:' + B) in (None, '') and streakreq.status(B)['request'] is None)

# ---- pause ends by itself while a request waits ----
st.x("DELETE FROM kv WHERE k LIKE 'streakok:%'"); st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'streakreq:%'")
for ago in (3 * 3600 + 3000, 3 * 3600 + 2900, 3 * 3600 + 2800): loss(B, ago)
T('bob paused (last loss 3h ago, cooldown 4h)', risk.streak_state(B) is not None)
streakreq.request(B); T('bob waits', len(streakreq.listing(NOW)['waiting']) == 1)
later = NOW + 3 * 3600
T('after the cooldown the request shows as ended and is not listed', streakreq.status(B, later)['request']['status'] == 'ended' and streakreq.listing(later)['waiting'] == [])
T('approving an ended pause is refused', refused(streakreq.decide, B, True, '', later))
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
