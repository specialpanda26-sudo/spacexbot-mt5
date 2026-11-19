"""R4 checks: each person picks how many positions the bot may hold at once. backend/limits.py (max_open, ceiling, save), risk.open_count + the gate, GET/POST /api/limits,
GET /api/status. Offline. Run: python tests/test_open4.py (last line: N checks, M failed)"""
import os, sys, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'open4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, limits, risk
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, B, O = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'
WD = 1700000000 - (1700000000 % 86400) + 86400 * 4 + 12 * 3600
while time.gmtime(WD).tm_wday >= 4: WD += 86400
def beat(uid, n, t=WD):
    a = {'balance': 1000, 'equity': 1000, 'open': n, 'demo': True, 'seen': t}
    if uid: st.x('UPDATE links SET acct=?,seen=? WHERE uid=?', (json.dumps(a), t, uid))
    else: st.put('acct', json.dumps(a))
def sig(uid, status, broker=None):
    return st.x("INSERT INTO signals(symbol,side,entry,status,created,uid,broker) VALUES('XAUUSD','buy',1,?,?,?,?)", (status, WD, uid or None, broker))
def gate(uid): return risk.global_gate(WD + 5, uid=uid)

# ---- the numbers ----
T('default: the owner number 3, ceiling 6', limits.max_open('') == 3 and limits.max_open(A) == 3 and limits.ceiling() == 6)
T('a subscriber picks 5: it applies to them and nobody else', limits.save(A, max_open=5)['max_open_now'] == 5 and limits.max_open(A) == 5 and limits.max_open(B) == 3 and limits.max_open('') == 3)
T('a subscriber may pick MORE than the owner default (not only stricter)', limits.max_open(A) > limits.max_open(''))
for bad in (7, 0.5, -1, 'x', True, None.__class__, [3], float('nan')):
    try: limits.save(A, max_open=bad); ok = False
    except ValueError: ok = True
    T('a bad pick is refused and nothing changes: %r' % (bad,), ok and limits.max_open(A) == 5)
T('0 puts the person back on the owner default', limits.save(A, max_open=0)['max_open'] == 0 and limits.max_open(A) == 3)
limits.save(A, max_open=6); limits.save('', ceiling=4)
T('the owner lowers the ceiling: the pick of 6 is cut to 4 at once, the saved pick is kept', limits.max_open(A) == 4 and limits.view(A)['max_open'] == 6)
try: limits.save(A, max_open=5); ok = False
except ValueError: ok = True
T('under the lowered ceiling 5 is refused', ok)
limits.save('', ceiling=6)
try: limits.save(A, ceiling=9); ok = False
except ValueError: ok = True
T('a subscriber trying to set the ceiling is refused', ok)
for bad in (0, 51, 'x'):
    try: limits.save('', ceiling=bad); ok = False
    except ValueError: ok = True
    T('the owner ceiling must be 1 to 50: %r refused' % (bad,), ok and limits.ceiling() == 6)
T('the owner sets the default number for everybody who did not pick', limits.save('', max_open=4)['max_open_now'] == 4 and limits.max_open(B) == 4 and limits.max_open(A) == 6)
try: limits.save('', max_open=0); ok = False
except ValueError: ok = True
T('the owner cannot set the default to 0', ok)
limits.save('', max_open=3)
T("saving positions does not touch the person's other numbers", (limits.save(B, max_trades=7), limits.save(B, max_open=2), limits.view(B))[-1]['max_trades'] == 7)

# ---- counting ----
links.new_key(A); links.set_bot(A, True); links.new_key(B); links.set_bot(B, True)
limits.save(A, max_open=2); limits.save(B, max_open=0)
beat(A, 0); T('nothing open: counted 0, the gate passes', risk.open_count(A) == 0 and gate(A)[0] is True)
beat(A, 1); sig(A, 'open', 'Deriv')
T('one position the EA reports plus one Deriv trade we recorded: the larger of the two (1) is used, not added', risk.open_count(A) == 1)
sig(A, 'open', 'Deriv'); T('two Deriv trades: 2 counted, the gate stops at the limit of 2', risk.open_count(A) == 2 and gate(A) == (False, 'max open positions'))
st.x("DELETE FROM signals WHERE uid=?", (A,)); beat(A, 0)
sig(A, 'pending'); sig(A, 'sent')
T('signals about to open (pending and sent) count too, so a burst cannot slip past', risk.open_count(A) == 2 and gate(A) == (False, 'max open positions'))
st.x("DELETE FROM signals WHERE uid=?", (A,)); sig(A, 'closed'); sig(A, 'rejected'); sig(A, 'expired'); beat(A, 0)
T('closed, rejected and expired never count', risk.open_count(A) == 0 and gate(A)[0] is True)
beat(A, 5); T('the EA reporting 5 open positions (some by hand) is respected', risk.open_count(A) == 5 and gate(A)[1] == 'max open positions')
beat(A, 'abc'); T('a broken open count counts as 0, no crash', risk.open_count(A) == 0)
st.x("DELETE FROM signals WHERE uid=?", (A,)); beat(A, 0)
sig(B, 'open'); sig(B, 'open'); sig(B, 'open'); beat(B, 3)
T("another person's trades never count: amy 0, bob 3 (his limit is the default 3)", risk.open_count(A) == 0 and risk.open_count(B) == 3 and gate(B)[1] == 'max open positions' and gate(A)[0] is True)
limits.save(B, max_open=5); T("bob's own higher pick lets him go on", gate(B)[0] is True)
st.x("DELETE FROM signals WHERE uid=?", (B,)); st.x("DELETE FROM signals WHERE uid IS NULL")
st.put('bot_enabled', '1'); beat('', 3); T("the owner scope uses the owner's default and the EA count", gate('') == (False, 'max open positions'))
limits.save('', max_open=4); T('the owner raises the default: the owner gate opens', gate('')[0] is True); limits.save('', max_open=3); beat('', 0)

# ---- routes ----
T('GET /api/limits needs a sign-in', c.get('/api/limits').status_code == 401)
j = c.get('/api/limits', headers=H('amy@x.com')).get_json()
T('GET returns the pick, the number in force, the default and the ceiling', j['max_open'] == 2 and j['max_open_now'] == 2 and j['max_open_default'] == 3 and j['max_open_ceiling'] == 6)
r = c.post('/api/limits', headers=H('amy@x.com'), json={'max_open': 5}); T('POST saves the pick and answers with the new numbers', r.status_code == 200 and r.get_json()['max_open_now'] == 5)
r = c.post('/api/limits', headers=H('amy@x.com'), json={'max_open': 9}); T('POST above the ceiling: 400 with a plain message, nothing saved', r.status_code == 400 and '1 to 6' in r.get_json()['error'] and limits.max_open(A) == 5)
r = c.post('/api/limits', headers=H('amy@x.com'), json={'ceiling': 2}); T('a subscriber cannot change the ceiling through the route (ignored)', limits.ceiling() == 6 and r.status_code == 400)
r = c.post('/api/limits', headers=H('boss@x.com'), json={'ceiling': 8}); T('the owner can change the ceiling through the route', r.status_code == 200 and r.get_json()['max_open_ceiling'] == 8 and limits.ceiling() == 8)
c.post('/api/limits', headers=H('boss@x.com'), json={'ceiling': 6})
T("amy's pick never changes bob's", limits.max_open(B) == 5 and c.get('/api/limits', headers=H('bob@x.com')).get_json()['max_open_now'] == 5)
c.post('/api/limits', headers=H('amy@x.com'), json={'max_trades': 4}); T('saving other limits keeps the position pick', limits.max_open(A) == 5)
st.x("UPDATE users SET plan_until=? WHERE uid=?", (int(time.time()) + 86400, A)); links.new_key(A); links.set_bot(A, True)
j = c.get('/api/status', headers=H('amy@x.com')).get_json()
T('GET /api/status shows the person\'s own limit and open count', j['max_open'] == 5 and 'open' in j)
for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]; print('%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
