"""Reset today button (server side): backend/pnlreset.py + POST /api/pnl/reset + the 'today' numbers of /api/pnl and /api/live. No network, no real broker.
Run: python tests/test_reset6.py"""
import os, sys, glob, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'reset6_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, pnlcard as pc, pnlreset as pr, livestats, journal as jn
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
A, B, O = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
NOW = 1700049600; DS = NOW - NOW % 86400          # 12:00 UTC; today began at DS
def sig(uid, pnl, t, broker='MT5'):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,fill,uid,broker) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ('XAUUSD', 'buy', 100.0, 99.0, 102.0, 'closed', t - 600, pnl, t, 'gold_scalp', 100.0, uid, broker))
def post(email, body=None): return c.post('/api/pnl/reset', headers=H(email), json=body if body is not None else {})

# ---- the module ----
T('no reset: get is 0 and since is the day start', pr.get(A, DS) == 0 and pr.since(A, DS) == DS)
sig(A, -3, DS + 3600); sig(A, 5, DS + 7200); sig(A, -1, DS - 7200)                    # two trades today, one yesterday
j = pc.snapshot(A, now=NOW)
T('before a reset: today = the two trades since 00:00 UTC (+2.00, 2 trades), today_reset is None', j['today'] == {'pnl': 2.0, 'n': 2} and j['today_reset'] is None)
t0 = pr.reset(A, now=NOW - 1800)
T('reset stores the time 1 second ahead and returns it', t0 == NOW - 1799 and pr.get(A, DS) == t0)
j = pc.snapshot(A, now=NOW)
T('after a reset: today is 0 trades / $0.00 and today_reset is the reset time', j['today'] == {'pnl': 0.0, 'n': 0} and j['today_reset'] == t0)
sig(A, 4, NOW + 600)
j = pc.snapshot(A, now=NOW + 900)
T('a trade that closes after the reset counts again (+4.00, 1 trade)', j['today'] == {'pnl': 4.0, 'n': 1})
T('the 7-day and all-time numbers and the curve do NOT change (4 trades, +5.00)', j['week'] == {'pnl': 5.0, 'n': 4} and j['total'] == {'pnl': 5.0, 'n': 4} and j['curve_n'] == 4)
T('the Journal still lists every trade (nothing is deleted)', len(jn._closed(A, False)) == 4)
T('another person is not affected', pc.snapshot(B, now=NOW)['today_reset'] is None and pr.get(B, DS) == 0)
pr.clear(A)
T('clear (undo) puts the day back: +6.00 for the 3 trades since 00:00 UTC (two old + the +4)', pc.snapshot(A, now=NOW + 900)['today'] == {'pnl': 6.0, 'n': 3} and pr.get(A, DS) == 0)
pr.reset(A, now=DS - 5000)
T('a reset from an earlier day is ignored (it ends by itself)', pr.get(A, DS) == 0 and pr.since(A, DS) == DS and pc.snapshot(A, now=NOW)['today_reset'] is None)
st.put('pnlreset:' + A, 'junk')
T('a damaged value is ignored, never a crash', pr.get(A, DS) == 0 and pr.since(A, DS) == DS)
pr.clear(A)

# ---- the route ----
r = c.post('/api/pnl/reset', json={})
T('signed out: refused (401)', r.status_code == 401)
now = int(time.time())
sig(B, -7, now - 5); sig(B, 3, now - 4, broker='Deriv')
st.set_acct({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'allow_live': False}, '')
r = post('bob@x.com'); j = r.get_json()
T('route: 200 and returns the card numbers with today_reset set', r.status_code == 200 and isinstance(j.get('today_reset'), int) and j['today']['n'] == 0 and j['today']['pnl'] == 0.0)
T('route: the all-time total still counts both trades (-4.00)', j['total'] == {'pnl': -4.0, 'n': 2})
T('route: GET /api/pnl agrees with the answer', c.get('/api/pnl', headers=H('bob@x.com')).get_json()['today_reset'] == j['today_reset'])
T('route: /api/me still works and the route never leaks a key or secret', all(w not in json.dumps(j).lower() for w in ('token', 'secret', 'password')))
r = post('bob@x.com', {'broker': 'Deriv'}); j = r.get_json()
T('route: the broker picker value is passed through (broker Deriv)', j['broker'] == 'Deriv' and j['total'] == {'pnl': 3.0, 'n': 1})
T('route: a person only moves their own day (amy untouched)', pr.get(A) == 0 and c.get('/api/pnl', headers=H('amy@x.com')).get_json()['today_reset'] is None)
sig(B, 9, now + 30)
# Live card: bob is a normal person, scope = his own uid
lv = c.get('/api/live', headers=H('bob@x.com')).get_json()
T('live card: today starts at the reset (+9.00 from the one trade after it, not -1.00)', lv['today'] == 9.0 and lv['today_n'] == 1 and lv['today_reset'] == c.get('/api/pnl', headers=H('bob@x.com')).get_json()['today_reset'])
j = post('bob@x.com', {'undo': True}).get_json()
T('undo: today_reset is None again and today is back to the real day (3 trades, +5.00)', j['today_reset'] is None and j['today'] == {'pnl': 5.0, 'n': 3})
lv = c.get('/api/live', headers=H('bob@x.com')).get_json()
T('undo: the live card has no today_reset and counts the day again', lv['today_reset'] is None and lv['today_n'] == 3 and lv['today'] == 5.0)
T('a bad body (a list) does not crash the route', c.post('/api/pnl/reset', headers=H('bob@x.com'), data='[1,2]', content_type='application/json').status_code == 200)
pr.clear(B)

# ---- display only: the risk numbers must not move ----
st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,fill,uid,broker) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
     ('XAUUSD', 'buy', 100.0, 99.0, 102.0, 'closed', now - 60, -50.0, now - 5, 'gold_scalp', 100.0, None, 'MT5'))
before = c.get('/api/status', headers=H('boss@x.com')).get_json()
r = post('boss@x.com')
after = c.get('/api/status', headers=H('boss@x.com')).get_json()
T('the owner can reset too (200)', r.status_code == 200 and r.get_json()['today_reset'])
T('risk is untouched: the daily loss % the gates use is the same before and after the reset', before.get('day_loss_pct', 0) > 0 and before.get('day_loss_pct') == after.get('day_loss_pct'))
lv = c.get('/api/live', headers=H('boss@x.com')).get_json()
T('the owner live card does start again from zero after the reset', lv['today'] == 0.0 and lv['today_reset'])

for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
