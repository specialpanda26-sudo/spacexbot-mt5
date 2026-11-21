"""Section N5: market alerts (push kinds 19-25) through a FAKE FCM. Checks who gets it, the payload (title, body, channel_id, tag, data.kind/route) and that each alert goes out once.
Run: python tests/test_n5.py"""
import os, sys, time, json, types, threading, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'n5_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, news, bars, risk, alerts, market_alerts as ma
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
EM = ('boss@x.com', 'joe@x.com', 'ann@x.com', 'free@x.com', 'off@x.com')
uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in EM}
for e in ('joe@x.com', 'ann@x.com', 'off@x.com'): C.post('/api/admin/grant', json={'email': e, 'days': 30}, headers=H('boss@x.com'))
who = {}
for e in EM:
    t = 'tok_%s_' % e.split('@')[0] + 'x' * 30; push.save_token(uid[e], t); who[t] = e
st.x('UPDATE users SET notif=? WHERE uid=?', (json.dumps({'news': 0}), uid['off@x.com']))      # off@ switched the news category off
def go(fn, now):
    SENT.clear(); ma._tried.clear(); st.x('DELETE FROM push_log'); fn(now); return SENT          # a clean slate each time, so an earlier send never hides a wrong send
def to(): return sorted(who[m['token']] for m in SENT)
def fields(m): n = m['android']['notification']; return m['notification']['title'], m['notification']['body'], n['channel_id'], n.get('tag'), m['data']['kind'], m['data']['route']
BOTH = ['ann@x.com', 'boss@x.com', 'joe@x.com']          # every subscriber and the admin; not the person without a plan, not the person with news off

def utc(y, mo, d, h, mi=0): return dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc).timestamp()
NOW = utc(2026, 11, 18, 12, 0)                           # a Wednesday, midday
def ev(mins, ccy='USD', title='CPI', t0=NOW): return {'date': dt.datetime.fromtimestamp(t0 + mins * 60, dt.timezone.utc).isoformat(), 'country': ccy, 'title': title, 'impact': 'High'}

# ---- 19 news soon
news.set_rows([ev(45)])
go(ma.news_job, NOW)
T('19: sent to subscribers and admins, not to no-plan or news-off', to() == BOTH)
t, b, ch, tag, k, route = fields(SENT[0])
T('19: title carries the real minutes', t == 'CPI in 45 minutes')
T('19: body, high channel, tag, kind and route', 'Big news for USD' in b and ch == 'sxb_high' and tag == 'k19' and k == '19' and route == '#home')
SENT.clear(); ma._tried.clear(); ma.news_job(NOW + 700)
T('19: the same event is never sent twice to a person', SENT == [])
news.set_rows([ev(90)]); T('19: nothing when the release is more than 60 min away', go(ma.news_job, NOW) == [])
news.set_rows([ev(45, ccy='NZD')]); T('19: nothing for a currency the bot does not trade', go(ma.news_job, NOW) == [])
news.set_rows([ev(-10)]); T('19: nothing for a release that already happened', [m for m in go(ma.news_job, NOW) if m['data']['kind'] == '19'] == [])

# ---- 20 / 21 lock
news.set_rows([ev(20)]); r = go(ma.news_job, NOW)
T('20: lock started (inside the 30 minutes before) is sent', sorted(m['data']['kind'] for m in r).count('20') == 3)
T('20: wording', [fields(m)[0] for m in r if m['data']['kind'] == '20'][0] == 'News lock started')
news.set_rows([ev(40)]); T('20: not yet when the release is 40 min away', [m for m in go(ma.news_job, NOW) if m['data']['kind'] == '20'] == [])
news.set_rows([ev(-35)]); r = go(ma.news_job, NOW)
T('21: lock ended 5 minutes ago is sent', [m['data']['kind'] for m in r] == ['21'] * 3 and fields(r[0])[0] == 'News lock ended')
news.set_rows([ev(-80)]); T('21: not sent hours late', go(ma.news_job, NOW) == [])
news.set_rows([ev(-20)]); T('21: not sent while the lock still runs', [m for m in go(ma.news_job, NOW) if m['data']['kind'] == '21'] == [])
st.put('news_lock', '0'); news.set_rows([ev(20, title='GDP'), ev(-35, title='NFP')])
T('20/21: no lock alerts when the news lock is switched off', [m for m in go(ma.news_job, NOW) if m['data']['kind'] in ('20', '21')] == [])
st.put('news_lock', '1')

# ---- 22 session opening (daylight saving: London 08:00 is 07:00 UTC in July, 08:00 UTC in November)
r = go(ma.session_job, utc(2026, 11, 23, 8, 3))
T('22: London opens Monday 08:03 (winter, UTC)', to() == BOTH and fields(r[0])[0] == 'London session is opening' and fields(r[0])[2] == 'sxb_low' and fields(r[0])[4] == '22')
T('22: not London 08:03 UTC in summer (that is 09:03 there)', [m for m in go(ma.session_job, utc(2026, 7, 15, 8, 3)) if 'London' in m['notification']['title']] == [])
T('22: London opens at 07:03 UTC in summer', [fields(m)[0] for m in go(ma.session_job, utc(2026, 7, 15, 7, 3))].count('London session is opening') == 3)
T('22: New York opens 13:02 UTC in winter', [fields(m)[0] for m in go(ma.session_job, utc(2026, 11, 23, 13, 2))][0] == 'New York session is opening')
T('22: Tokyo opens 00:01 UTC', [fields(m)[0] for m in go(ma.session_job, utc(2026, 11, 23, 0, 1))][0] == 'Tokyo session is opening')
T('22: nothing on a Saturday', go(ma.session_job, utc(2026, 11, 21, 8, 3)) == [])
T('22: nothing 20 minutes after the open', go(ma.session_job, utc(2026, 11, 23, 8, 20)) == [])
go(ma.session_job, utc(2026, 11, 23, 8, 3)); SENT.clear(); ma._tried.clear(); ma.session_job(utc(2026, 11, 23, 8, 6))
T('22: the same session on the same day is sent once', SENT == [])

# ---- 23 large gold move
def candles(start, closes, step=900):
    rows = []; prev = closes[0]
    for i, c in enumerate(closes): rows.append((start + i * step, prev, max(prev, c), min(prev, c), c, 1)); prev = c
    bars._d.pop(('', 'XAUUSD', 'M15'), None); bars.merge('XAUUSD', 'M15', rows, uid='')
base = 2000.0
candles(NOW - 3600 + 900, [2000, 2005, 2010, 2016])           # +0.8% over the window, last candle fresh
r = go(ma.move_job, NOW)
T('23: a rise of 0.8% in an hour is sent', to() == BOTH and fields(r[0])[0] == 'XAUUSD moved +0.80%' and fields(r[0])[4] == '23')
T('23: body gives minutes and price', 'in 60 minutes' in fields(r[0])[1] and '2016' in fields(r[0])[1] and fields(r[0])[2] == 'sxb_high')
candles(NOW - 3600 + 900, [2000, 1995, 1990, 1984]); r = go(ma.move_job, NOW)
T('23: a fall shows a minus sign', fields(r[0])[0] == 'XAUUSD moved -0.80%')
candles(NOW - 3600 + 900, [2000, 2001, 2002, 2003]); T('23: a small move (0.15%) is not sent', go(ma.move_job, NOW) == [])
candles(NOW - 3500, [2000, 2016], step=900); T('23: candles whose newest bar is older than 30 minutes are not sent', go(ma.move_job, NOW) == [])
candles(NOW - 3600 + 900, [2000, 2005, 2010, 2016]); st.put('symbols', 'EURUSD,GBPUSD'); T('23: nothing when gold is not one of the markets', go(ma.move_job, NOW) == [])
st.put('symbols', 'XAUUSD,EURUSD,GBPUSD,USDJPY')
go(ma.move_job, NOW); SENT.clear(); ma._tried.clear(); candles(NOW + 600 - 3600 + 900, [2000, 2005, 2010, 2016]); ma.move_job(NOW + 600)
T('23: the same move is not sent again within the 2 hour gap', SENT == [])

# ---- 24 market closed
fri = utc(2026, 11, 20, 20, 30)
r = go(ma.closed_job, fri)
T('24: Friday 20:30 UTC is sent once the weekend rule starts', to() == BOTH and fields(r[0])[0] == 'Market is closed' and fields(r[0])[4] == '24' and fields(r[0])[2] == 'sxb_low')
T('24: not after the 3 hour window (Friday 23:30)', go(ma.closed_job, utc(2026, 11, 20, 23, 30)) == [])
T('24: not before the cutoff (Friday 19:00)', go(ma.closed_job, utc(2026, 11, 20, 19, 0)) == [])
T('24: not on Sunday (not a late surprise)', go(ma.closed_job, utc(2026, 11, 22, 12, 0)) == [])
st.put('symbols', 'XAUUSD,BTCUSD'); T('24: not sent while a BTC market keeps the bot looking', go(ma.closed_job, utc(2026, 11, 20, 21, 0)) == [])
st.put('symbols', 'XAUUSD,EURUSD,GBPUSD,USDJPY')

# ---- 25 spread too wide, through the real EA report route
def newsig():
    st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('XAUUSD','buy',2000,1990,2020,1,'gold_scalp',2,'sent',?,'')", (int(time.time()),))
    return st.q('SELECT MAX(id) AS i FROM signals', (), True)['i']
def rep(reason):
    SENT.clear(); return C.post('/api/ea/report', json=dict(id=newsig(), status='rejected', reason=reason), headers={'X-EA-Key': 'k'}).status_code
rep('spread too wide')
T('25: the EA phrase "spread too wide" sends kind 25 to the admin only (owner EA)', to() == ['boss@x.com'] and [fields(m)[4] for m in SENT] == ['25'])
t, b, ch, tag, k, route = fields(SENT[0])
T('25: title, body, channel, tag, route', t == 'Spread too wide on XAUUSD' and 'trade was skipped' in b and ch == 'sxb_low' and tag == 'k25' and route == '#home')
time.sleep(1.1); rep('spread too wide'); T('25: a second one within 10 minutes for the same market is not sent', SENT == [])
rep('spread'); T('25: any other reason (even "spread") is still the old kind 8', [fields(m)[4] for m in SENT] == ['8'])
rep('news: USD CPI'); T('25: a news rejection is kind 8', [fields(m)[4] for m in SENT] == ['8'])

# ---- once per key: a job run again a minute later does not even try
calls = []; real = push.notify; push.notify = lambda *a, **k: calls.append(a)
ma._tried.clear(); news.set_rows([ev(45)]); ma.news_job(NOW); ma.news_job(NOW + 60)
push.notify = real
T('retry: the same key is not attempted again for 10 minutes', len(calls) == 1)
T('startup: the app puts the market jobs on the loop', 'market_alerts.register()' in open(os.path.join(ROOT, 'backend', 'app.py')).read())

# ---- the loop
ma.register()
T('loop: the four jobs are registered on the alerts loop', {'news_alerts', 'session_alerts', 'move_alerts', 'closed_alerts'} <= set(alerts._jobs))
T('loop: every job runs on its own without a clock argument', all(alerts._jobs[n]['func']() is None for n in ('news_alerts', 'session_alerts', 'move_alerts', 'closed_alerts')))

bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.exit(1 if bad else 0)
