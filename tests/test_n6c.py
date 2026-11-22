"""Section N6c: report alerts (push kinds 32, 33, 34, 36, 37) through a FAKE FCM and real closed trades.
Run: python tests/test_n6c.py"""
import os, sys, json, types, threading, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'n6c_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, alerts, report_alerts as ra
alerts.stop()          # stop the background alert loop so it cannot race this test
R = []
def T(name, ok): R.append((name, bool(ok))); print('PASS' if ok else 'FAIL', name)
SENT = []
class Resp:
    status_code = 200; text = '{}'
    def json(self): return {}
class FakeReq:
    def post(self, url, json=None, headers=None, data=None, timeout=None):
        if 'messages:send' in url: SENT.append(json['message'])
        return Resp()
push.requests = FakeReq(); push._access_token = lambda: 'fake'
push._account = lambda: {'project_id': 'p', 'client_email': 'e@p.iam', 'private_key': 'k'}
class SyncThread:
    def __init__(self, target=None, daemon=None): self.t = target
    def start(self): self.t()
push.threading = types.SimpleNamespace(Thread=SyncThread, Lock=threading.Lock)
push.quiet_now = lambda *a, **k: False
C = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
EM = ('boss@x.com', 'joe@x.com', 'ann@x.com', 'free@x.com', 'win@x.com', 'old@x.com'); uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in EM}
for e in ('joe@x.com', 'ann@x.com', 'win@x.com', 'old@x.com'): C.post('/api/admin/grant', json={'email': e, 'days': 3650}, headers=H('boss@x.com'))
who = {}
for e in EM:
    t = 'tok_%s_' % e.split('@')[0] + 'x' * 30; push.save_token(uid[e], t); who[t] = e
EAT = dt.timezone(dt.timedelta(hours=3))
def at(y, mo, d, h, mi=0): return dt.datetime(y, mo, d, h, mi, tzinfo=EAT).timestamp()
def trade(e, pnl, t, sym='XAUUSD'): st.x("INSERT INTO signals(symbol,side,strategy,status,created,pnl,closed,uid,broker) VALUES(?,?,?,?,?,?,?,?,?)", (sym, 'buy', 'x', 'closed', int(t) - 60, pnl, int(t), uid[e], 'MT5'))
def go(fn, now): SENT.clear(); ra._tried.clear(); st.x('DELETE FROM push_log'); fn(now); return SENT
def to(kind=None): return sorted(who[m['token']] for m in SENT if kind is None or m['data']['kind'] == str(kind))
def fields(m): n = m['android']['notification']; return m['notification']['title'], m['notification']['body'], n['channel_id'], n.get('tag'), m['data']['kind'], m['data']['route']
def kind(k): return [m for m in SENT if m['data']['kind'] == str(k)]
# ---- data: Wednesday 18 Nov 2026
J, A, B, F = 'joe@x.com', 'ann@x.com', 'boss@x.com', 'free@x.com'
trade(J, 10, at(2026, 11, 18, 10)); trade(J, -4, at(2026, 11, 18, 12)); trade(J, 6, at(2026, 11, 18, 14), 'EURUSD'); trade(J, -1, at(2026, 11, 18, 11))
trade(A, -5, at(2026, 11, 18, 9)); trade(A, -3, at(2026, 11, 18, 11))
st.x("INSERT INTO signals(symbol,side,strategy,status,created,pnl,closed,uid,broker) VALUES(?,?,?,?,?,?,?,?,?)", ('XAUUSD', 'buy', 'x', 'closed', 1, -2.5, int(at(2026, 11, 18, 13)), '', 'MT5'))      # the owner's own EA trade (scope '')
trade(F, 50, at(2026, 11, 18, 13))
WED = at(2026, 11, 18, 21, 10)

# ---- 32 daily
go(ra.report_job, WED)
T('32: sent to people with trades today and a plan (and the owner admin), not to no-plan', to(32) == sorted(['ann@x.com', 'boss@x.com', 'joe@x.com']))
m = [x for x in kind(32) if who[x['token']] == J][0]; t, b, ch, tag, k, route = fields(m)
T('32: title and body carry the real money, trades and win rate', t == 'Hooray! Today: +11.00 USD' and b == '4 trades, 50% wins.' and k == '32' and route == '#stats')
m = [x for x in kind(32) if who[x['token']] == A][0]
T('32: a losing day says so', fields(m)[0] == 'Oops, today: -8.00 USD' and '2 trades, 0% wins' in fields(m)[1])
m = [x for x in kind(32) if who[x['token']] == B][0]
T('32: the owner reads the owner trades (scope), not the other people', fields(m)[0] == 'Oops, today: -2.50 USD')
T('33 and 34 are not sent on a Wednesday', kind(33) == [] and kind(34) == [])
T('37: only a person with 2+ losses AND a net loss gets it (not net-positive joe with 2 losses, not net-loss boss with 1 loss)', to(37) == [A] and fields(kind(37)[0])[0] == "Review today's trades")
SENT.clear(); ra.report_job(WED + 60); T('32: the same day is never sent twice (no second send even after 10 min)', (ra._tried.clear(), ra.report_job(WED + 900), SENT)[2] == [])
T('32: nothing before 21:00', go(ra.report_job, at(2026, 11, 18, 20, 59)) == [])
T('32: nothing from 22:00', go(ra.report_job, at(2026, 11, 18, 22, 0)) == [])
T('32: a day with no closed trades sends nothing', go(ra.report_job, at(2026, 11, 19, 21, 10)) == [])
st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({'daily': 0}), uid[J]))
T('32: the person Daily switch off = nothing for that person', J not in [who[x['token']] for x in go(ra.report_job, WED)]); st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({}), uid[J]))

# ---- 33 weekly (Sunday 22 Nov)
SUN = at(2026, 11, 22, 21, 10)
go(ra.report_job, SUN)
T('33: weekly goes to people with trades in the last 7 days', to(33) == sorted(['ann@x.com', 'boss@x.com', 'joe@x.com']))
m = [x for x in kind(33) if who[x['token']] == J][0]
T('33: title, body with the best market, route', fields(m)[0] == 'Hooray! Weekly report: +11.00 USD' and fields(m)[1] == '4 trades, 50% wins. Best: XAUUSD.' and fields(m)[5] == '#stats')
T('33: a loss week says Oops', fields([x for x in kind(33) if who[x['token']] == A][0])[0] == 'Oops, Weekly report: -8.00 USD')
T('32: no daily on a day without trades (Sunday)', kind(32) == [])
trade(J, 1, at(2026, 11, 14, 12)); T('33: trades older than 7 days are not counted', fields([x for x in go(ra.report_job, SUN) if x['data']['kind'] == '33' and who[x['token']] == J][0])[1].startswith('4 trades'))

# ---- 34 monthly (1 Dec 2026, 09:10)
trade(J, 100, at(2026, 12, 1, 8)); DEC = at(2026, 12, 1, 9, 10)
go(ra.report_job, DEC); m = [x for x in kind(34) if who[x['token']] == J][0]
T('34: monthly goes out on the 1st at 09:00 for the month that ended (this month is not counted)', fields(m)[0] == 'Hooray! Monthly report: +12.00 USD' and fields(m)[1].startswith('5 trades'))
T('34: not on the 2nd', go(ra.report_job, at(2026, 12, 2, 9, 10)) == [])
T('34: not at 08:30 on the 1st', go(ra.report_job, at(2026, 12, 1, 8, 30)) == [])
go(ra.report_job, DEC); T('34: the same month is not sent twice', (SENT.clear(), ra._tried.clear(), ra.report_job(DEC + 1800), SENT)[3] == [])

# ---- 36 winning streak
W, O = 'win@x.com', 'old@x.com'; D = at(2026, 12, 3, 0)
for i in range(3): trade(W, 5, D + 36000 + i * 1800); trade(O, 5, D + 21600 + i * 1800)      # win: 10:00-11:00, old: 06:00-07:00
NOW = D + 41400                                                                                # 11:30
go(ra.streak_job, NOW)
T('36: 3 wins in a row goes to that person only, not to the one whose streak is old', to(36) == [W])
t, b, ch, tag, k, route = fields(SENT[0])
T('36: title, body, low channel, kind, route', t == 'Hooray! 3 wins in a row' and 'winning streak' in b and ch == 'sxb_low' and k == '36' and route == '#stats')
SENT.clear(); ra._tried.clear(); ra.streak_job(NOW + 700); T('36: the same streak is not sent twice', SENT == [])
trade(W, 5, D + 43200); SENT.clear(); ra._tried.clear(); ra.streak_job(NOW + 2000); T('36: 4 in a row is not a milestone', SENT == [])
trade(W, 5, D + 43500); SENT.clear(); ra._tried.clear(); ra.streak_job(NOW + 2300); T('36: 5 in a row is', to(36) == [W] and fields(SENT[0])[0] == 'Hooray! 5 wins in a row')
trade(W, -2, D + 44000); T('36: a loss ends the streak', go(ra.streak_job, NOW + 2600) == [])

# ---- loop
ra.register(); T('loop: both jobs are on the alerts loop', {'report_alerts', 'streak_alerts'} <= set(alerts._jobs))
T('loop: the jobs run on their own', alerts._jobs['report_alerts']['func']() is None and alerts._jobs['streak_alerts']['func']() is None)
T('startup: app.py registers the report alerts', 'report_alerts.register()' in open(os.path.join(ROOT, 'backend', 'app.py')).read())
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.exit(1 if bad else 0)
