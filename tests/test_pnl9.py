"""Section 9A checks: the Profit and loss card numbers. GET /api/pnl + backend/pnlcard.py. No network, no real broker. Run: python tests/test_pnl9.py"""
import os, sys, glob, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'pnl9_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, pnlcard as pc, livestats, sbauth
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
A, B, O, D = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com', 'dev-dan@x.com'
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com', 'dan@x.com'): c.get('/api/me', headers=H(e))
NOW = 1700049600                      # 12:00 UTC, so today started at NOW - 43200
DS = NOW - NOW % 86400; DAY = 86400
def sig(uid, pnl, t, broker='MT5', status='closed', sym='XAUUSD'):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,fill,uid,broker) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sym, 'buy', 100.0, 99.0, 102.0, status, t - 600, pnl, t if status == 'closed' else None, 'gold_scalp', 100.0, uid, broker))
def P(email, q=''): return c.get('/api/pnl' + q, headers=H(email)).get_json()

# ---- nothing yet: honest zeros ----
j = pc.snapshot(A, now=NOW)
T('no trades: every amount 0, no curve, no brokers (never sample numbers)', j['today'] == {'pnl': 0.0, 'n': 0} and j['week'] == {'pnl': 0.0, 'n': 0} and j['total'] == {'pnl': 0.0, 'n': 0} and j['curve'] == [] and j['curve_n'] == 0 and j['brokers'] == [])
T('no trades: win rate 0, not a made-up number', j['stats']['win_rate'] == 0 and j['stats']['trades'] == 0)

# ---- amy: five trades (oldest first: +20 Deriv 10d, -2 Deriv 6.5d, +6 MT5 2d, -4 MT5 5h, +10 MT5 100s) ----
for pnl, t, b in ((20.0, NOW - 10 * DAY, 'Deriv'), (-2.0, NOW - int(6.5 * DAY), 'Deriv'), (6.0, NOW - 2 * DAY, 'MT5'), (-4.0, NOW - 5 * 3600, 'MT5'), (10.0, NOW - 100, 'MT5')):
    sig(A, pnl, t, b)
sig(A, None, NOW, 'MT5', 'open'); sig(A, None, NOW, 'MT5', 'pending'); sig(A, None, NOW, 'MT5', 'rejected'); sig(A, None, NOW, 'MT5', 'expired'); sig(A, None, NOW)   # none of these is a closed trade with a result
sig(A, float('inf'), NOW, 'MT5')                                                                                                                              # a broken profit figure never counts
j = pc.snapshot(A, now=NOW)
T('only closed trades with a real profit figure count (open, pending, rejected, expired, no result, infinite are left out)', j['total']['n'] == 5)
T('today = trades closed since 00:00 UTC (+10, -4 -> 6.00, 2 trades)', j['today'] == {'pnl': 6.0, 'n': 2})
T('last 7 days = rolling 7 days (+10, -4, +6, -2 -> 10.00, 4 trades; the 10-day-old +20 is out)', j['week'] == {'pnl': 10.0, 'n': 4})
T('all time = every closed trade (30.00, 5 trades)', j['total'] == {'pnl': 30.0, 'n': 5})
s = j['stats']
T('win rate and counts (3 wins, 2 losses, 60%)', s['trades'] == 5 and s['wins'] == 3 and s['losses'] == 2 and s['win_rate'] == 60.0)
T('best, worst and the biggest drop (20, -4, 4)', s['best'] == 20.0 and s['worst'] == -4.0 and s['max_drawdown'] == 4.0)
T('the curve is the running total, OLDEST first, ending on the all-time number', [p['v'] for p in j['curve']] == [20.0, 18.0, 24.0, 20.0, 30.0] and j['curve'][-1]['v'] == j['total']['pnl'] and j['curve_n'] == 5)
T('every curve point carries the time the trade closed, and times only go forward', [p['t'] for p in j['curve']] == sorted(p['t'] for p in j['curve']) and j['curve'][-1]['t'] == NOW - 100)
T('brokers lists only brokers that have trades, known ones in order', j['brokers'] == ['Deriv', 'MT5'] and j['broker'] == '')

# ---- the edges of today and of the week ----
sig(B, 1.0, DS, 'MT5'); sig(B, 2.0, DS - 1, 'MT5'); sig(B, 4.0, NOW - 7 * DAY, 'MT5'); sig(B, 8.0, NOW - 7 * DAY - 1, 'MT5')
j = pc.snapshot(B, now=NOW)
T('a trade closed exactly at 00:00 UTC is today; one second before is not', j['today'] == {'pnl': 1.0, 'n': 1})
T('a trade closed exactly 7 days ago is in the week; one second earlier is not (1 + 2 + 4 = 7.00)', j['week'] == {'pnl': 7.0, 'n': 3} and j['total'] == {'pnl': 15.0, 'n': 4})

# ---- the broker picker ----
j = pc.snapshot(A, broker='Deriv', now=NOW)
T('?broker=Deriv: only Deriv trades (+20, -2 -> 18.00); the broker list still shows both', j['total'] == {'pnl': 18.0, 'n': 2} and j['today']['n'] == 0 and j['brokers'] == ['Deriv', 'MT5'] and j['broker'] == 'Deriv' and [p['v'] for p in j['curve']] == [20.0, 18.0])
j = pc.snapshot(A, broker='mt5', now=NOW)
T('?broker=mt5 (any capitals): only MT5 trades (+6, -4, +10 -> 12.00, today 6.00)', j['total'] == {'pnl': 12.0, 'n': 3} and j['today'] == {'pnl': 6.0, 'n': 2} and j['broker'] == 'MT5' and j['stats']['win_rate'] == 66.7)
j = pc.snapshot(A, broker='Nobody', now=NOW)
T('an unknown broker shows nothing (not everything)', j['total']['n'] == 0 and j['curve'] == [])

# ---- whose trades ----
sig(None, 100.0, NOW - 50, 'MT5')                                  # the owner's own EA (scope '')
T("a normal person never sees another person's trades or the owner's EA trades", pc.snapshot(A, now=NOW)['total']['pnl'] == 30.0 and pc.snapshot(B, now=NOW)['total']['pnl'] == 15.0)
sig(O, 5.0, NOW - 40, 'Deriv')
jo = pc.snapshot(O, admin=True, now=NOW)
T("the owner sees the owner's EA trades + their own Deriv trades, and nobody else's (100 + 5)", jo['total'] == {'pnl': 105.0, 'n': 2})

# ---- a long history is thinned but stays true ----
for i in range(200): sig(D, 1.0 if i % 3 else -0.5, NOW - (200 - i) * 60, 'MT5')
j = pc.snapshot(D, now=NOW)
true = []; run = 0.0
for i in range(200): run += 1.0 if i % 3 else -0.5; true.append(round(run, 2))
T('200 trades: the curve is thinned to at most %d points, curve_n still says 200' % pc.MAXP, len(j['curve']) == pc.MAXP and j['curve_n'] == 200)
T('thinning keeps the first and the last point, and every point is a real running total', j['curve'][0]['v'] == true[0] and j['curve'][-1]['v'] == true[-1] == j['total']['pnl'] and all(p['v'] in true for p in j['curve']))
T('thinned points stay in time order', [p['t'] for p in j['curve']] == sorted(p['t'] for p in j['curve']))
T('a short history is not thinned', len(pc._thin([{'t': i, 'v': i} for i in range(pc.MAXP)])) == pc.MAXP)

# ---- agrees with the Live card on Home ----
now = int(time.time())
for e, uid in (('amy@x.com', A),):
    sig(uid, 3.0, now - 5, 'MT5'); sig(uid, -1.25, now - 3, 'Deriv')
lv = livestats.snapshot(A)['today']; pn = pc.snapshot(A)['today']['pnl']
T('the P&L card "Today" and the Live card "Today" are the same number', lv == pn and lv != 0)

# ---- the route ----
T('GET /api/pnl needs a sign-in', c.get('/api/pnl').status_code == 401)
_v = sbauth.verify; sbauth.verify = lambda t: {'uid': 'dev-ghost', 'email': 'ghost@x.com', 'name': 'g', 'verified': False}
T('GET /api/pnl needs a verified email (403)', c.get('/api/pnl', headers=H('ghost@x.com')).status_code == 403); sbauth.verify = _v
r = c.get('/api/pnl', headers=H('amy@x.com')); j = r.get_json()
T("the route answers with the person's own numbers", r.status_code == 200 and j['total']['n'] == 7 and set(j) >= {'today', 'week', 'total', 'stats', 'curve', 'curve_n', 'brokers', 'broker', 'ts'})
T("bob's route shows bob's numbers, not amy's", P('bob@x.com')['total']['pnl'] == 15.0)
T('the owner route uses the owner scope', P('boss@x.com')['total']['pnl'] == 105.0)
T('?broker=Deriv on the route filters', P('amy@x.com', '?broker=Deriv')['broker'] == 'Deriv' and P('amy@x.com', '?broker=Deriv')['total']['n'] == 3)
T('the route never carries a token, key or secret', all(w not in json.dumps(P('amy@x.com')).lower() for w in ('token', 'secret', 'password', 'key')))
T('a person with no trades gets zeros from the route', P('dan@x.com')['total']['n'] == 200 and c.get('/api/me', headers=H('eve@x.com')).status_code == 200 and P('eve@x.com')['total']['n'] == 0 and P('eve@x.com')['curve'] == [])

for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
