"""Section N4: trade and risk alerts (kinds 5, 6, 9, 10, 11-18) through a FAKE FCM: who gets each kind, the payload (title, body, channel_id, tag, data.kind/route), once per day / per event.
Run: python tests/test_n4.py"""
import os, sys, time, json, types, threading, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'n4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend import app as appmod
from backend.app import app
from backend import store as st, push, bars, risk, alerts, brain, limits, risk_alerts as ra
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
QUIET = [False]; push.quiet_now = lambda *a, **k: QUIET[0]

C = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in ('boss@x.com', 'joe@x.com')}
C.post('/api/admin/grant', json={'email': 'joe@x.com', 'days': 30}, headers=H('boss@x.com'))
who = {}
for e in uid:
    t = 'tok_%s_' % e.split('@')[0] + 'x' * 30; push.save_token(uid[e], t); who[t] = e
JOE = uid['joe@x.com']
def to(): return sorted(who[m['token']] for m in SENT)
def fields(m): n = m['android']['notification']; return m['notification']['title'], m['notification']['body'], n['channel_id'], n.get('tag'), m['data']['kind'], m['data']['route']
def fresh(): SENT.clear(); ra._tried.clear(); st.x('DELETE FROM push_log')
def gate(u, why, now=None, sym=''): fresh(); return ra.gate(u, why, sym, now)
NOW = time.time()

# ---- 11 / 12 loss limits
T('11: returns the kind', gate('', 'daily loss limit hit') == 11)
t, b, ch, tag, k, route = fields(SENT[0])
T('11: the owner scope goes to the admin phone only', to() == ['boss@x.com'])
T('11: title, body with the real limit, high channel, tag, route', t == 'Daily loss limit reached' and '3% limit' in b and ch == 'sxb_high' and tag == 'k11' and k == '11' and route == '#home')
gate(JOE, 'daily loss limit hit'); T('11: a subscriber gets their own alert, nobody else', to() == ['joe@x.com'])
SENT.clear(); ra._tried.clear(); ra.gate(JOE, 'daily loss limit hit', '', NOW + 600); T('11: once a day per person', SENT == [])
SENT.clear(); ra._tried.clear(); ra.gate(JOE, 'daily loss limit hit', '', NOW + 86400); T('11: sent again the next day', to() == ['joe@x.com'])
QUIET[0] = True; gate('', 'daily loss limit hit'); T('11: a risk alert ignores quiet hours', len(SENT) == 1); QUIET[0] = False
gate('', 'weekly loss limit hit'); T('12: weekly limit', fields(SENT[0])[0] == 'Weekly loss limit reached' and '6% limit' in fields(SENT[0])[1] and fields(SENT[0])[4] == '12')

fresh(); ra.gate('', 'weekly loss limit hit', '', NOW); SENT.clear(); ra._tried.clear(); ra.gate('', 'weekly loss limit hit', '', NOW + 3600)
T('12: once a week, not once a day or hour', SENT == [])
ra._tried.clear(); ra.gate('', 'weekly loss limit hit', '', NOW + 8 * 86400); T('12: sent again the next week', len(SENT) == 1)
fresh(); ra.gate('', 'USD exposure already at limit (x)', 'EURUSD', NOW); SENT.clear(); ra._tried.clear(); ra.gate('', 'GBP exposure already at limit (x)', 'GBPUSD', NOW)
T('17: a second currency the same day is its own alert', len(SENT) == 1 and fields(SENT[0])[0] == 'GBP exposure limit')
calls = []; real_n = push.notify; push.notify = lambda *a, **k: calls.append(a); fresh()
ra.gate('', 'max open positions', '', NOW); ra.gate('', 'max open positions', '', NOW + 60); push.notify = real_n
T('retry: the same alert is not even tried again within the hour', len(calls) == 1)

# ---- 13 streak pause, 14 resumed
st.x('DELETE FROM signals'); st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,closed,pnl,uid) VALUES('XAUUSD','buy',1,1,1,'closed',?,?,-5,'')", (int(NOW) - 600, int(NOW) - 300))
gate('', '3 losses in a row: cooling down', NOW)
t, b, ch, tag, k, route = fields(SENT[0]); until = int(NOW) - 300 + 4 * 3600
T('13: losing-streak pause with the count and the resume time', t == 'Losing-streak pause' and b.startswith('3 losses in a row') and dt.datetime.fromtimestamp(until, ra.EAT).strftime('%H:%M') + ' EAT' in b and k == '13')
T('13: the resume time is remembered', float(st.get('ra14:owner')) == until)
fresh(); ra.resume_job(NOW); T('14: nothing before the pause ends', SENT == [])
ra.resume_job(until + 5); T('14: trading resumed once the pause is over, admin phone', to() == ['boss@x.com'] and fields(SENT[0])[0] == 'Trading resumed' and fields(SENT[0])[4] == '14')
T('14: the reminder row is gone', st.get('ra14:owner') in (None, ''))
SENT.clear(); ra._tried.clear(); ra.resume_job(until + 400); T('14: sent only once', SENT == [])

# ---- 15 / 16 / 17
gate('', 'max open positions'); T('15: max open trades with the real number', fields(SENT[0])[0] == 'Max open trades reached' and fields(SENT[0])[1].startswith('%d trades' % limits.max_open('')) and fields(SENT[0])[4] == '15')
st.put('max_trades_day', 5); gate('', 'max trades today'); T('16: max trades for the day with the real number', fields(SENT[0])[0] == 'Max trades for today reached' and fields(SENT[0])[1].startswith('5 trades') and fields(SENT[0])[4] == '16'); st.put('max_trades_day', 0)
gate('', 'USD exposure already at limit (correlated trades)', sym='EURUSD'); T('17: currency exposure names the currency and the market', fields(SENT[0])[0] == 'USD exposure limit' and 'EURUSD' in fields(SENT[0])[1] and fields(SENT[0])[4] == '17')
for why in ('bot off', 'EA offline', 'weekend/Friday-night risk', 'symbol cooldown', 'ok'): T('no alert for the reason "%s"' % why, gate('', why) is None and SENT == [])

# ---- 18 half of the daily limit
st.set_acct({'balance': 1000, 'seen': time.time()}, '')
def loss(x): st.x('DELETE FROM signals'); st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,closed,pnl,uid) VALUES('XAUUSD','buy',1,1,1,'closed',?,?,?,'')", (int(time.time()), int(time.time()), -x)); fresh()
loss(20); ra.watch('', time.time())
T('18: 2% lost of a 3% limit is sent', to() == ['boss@x.com'] and fields(SENT[0])[0] == 'Half of the daily limit used' and "2% of the 3% limit" in fields(SENT[0])[1] and fields(SENT[0])[4] == '18')
loss(5); ra.watch('', time.time()); T('18: 0.5% lost is not half yet', SENT == [])
loss(40); ra.watch('', time.time()); T('18: at or over the limit it is kind 11 territory, not 18', SENT == [])
loss(20); ra.watch('', time.time()); SENT.clear(); ra._tried.clear(); ra.watch('', time.time()); T('18: once a day', SENT == [])
st.x('DELETE FROM signals')

# ---- 10 long open
def opened(hours_ago, u=''):
    st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,uid) VALUES('XAUUSD','buy',1,1,1,'open',?,?)", (int(NOW), u))
    i = st.q('SELECT MAX(id) AS i FROM signals', (), True)['i']; st.put('lag:%d' % i, json.dumps({'opened': int(NOW - hours_ago * 3600)})); return i
i = opened(7); fresh(); ra.long_open_job(NOW)
t, b, ch, tag, k, route = fields(SENT[0])
T('10: a trade open 7 hours, admin phone, with the time open and no made-up profit', to() == ['boss@x.com'] and t == 'XAUUSD is still open' and b == 'Open for 7h 00m.' and k == '10')
T('10: the tag carries the trade id', tag == 'k10-sig%d-long' % i)
SENT.clear(); ra._tried.clear(); ra.long_open_job(NOW + 3000); T('10: once per trade', SENT == [])
st.x('DELETE FROM signals'); opened(2); fresh(); ra.long_open_job(NOW); T('10: not for a trade open only 2 hours', SENT == [])
st.x('DELETE FROM signals'); opened(8, JOE); fresh(); ra.long_open_job(NOW); T("10: a subscriber's trade goes to that subscriber", to() == ['joe@x.com'])
st.x('DELETE FROM signals')

# ---- 5 / 6 / 9 from the EA report route
def newsig():
    st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('XAUUSD','buy',2000,1990,2020,1,'gold_scalp',2,'open',?,'')", (int(time.time()),))
    return st.q('SELECT MAX(id) AS i FROM signals', (), True)['i']
def rep(sid, **d): SENT.clear(); return C.post('/api/ea/report', json=dict(id=sid, **d), headers={'X-EA-Key': 'k'}).status_code
sid = newsig(); st.x('DELETE FROM push_log')
rep(sid, status='be'); t, b, ch, tag, k, route = fields(SENT[0])
T('5: breakeven goes to the admin phone with the trade tag', to() == ['boss@x.com'] and t == 'XAUUSD stop moved to breakeven' and k == '5' and tag == 'k5-sig%d-be' % sid and route == '#signals' and ch == 'sxb_high')
rep(sid, status='partial', pnl=3.5); t, b, ch, tag, k, route = fields(SENT[0])
T('6: partial close with the profit so far', t == 'XAUUSD partly closed' and '+3.50' in b and k == '6')
rep(sid, status='pending', state='placed'); T('9: pending order with its state', fields(SENT[0])[0] == 'XAUUSD pending order placed' and fields(SENT[0])[4] == '9')
T('5/6/9: the trade row itself is not changed', st.q('SELECT status FROM signals WHERE id=?', (sid,), True)['status'] == 'open')
rep(sid, status='be'); T('5: a second breakeven report for the same trade is not sent twice', SENT == [])
T('5/6/9: an unknown id is ignored quietly', rep(999999, status='be') == 200 and SENT == [])

# ---- the scan hooks (the real _scan_tf, with the gates stubbed to give each reason)
rows = [(int(NOW) - 900 * 3 + 900 * i, 2000, 2001, 1999, 2000, 1) for i in range(3)]
bars.merge('XAUUSD', 'M15', rows, uid=''); bars.merge('XAUUSD', 'M15', rows, uid=JOE); bars.merge('XAUUSD', 'H1', rows, uid=''); bars.merge('XAUUSD', 'H1', rows, uid=JOE)
real_gg, real_sg, real_ev = risk.global_gate, risk.symbol_gate, brain.evaluate
step = [0]
def scan(u): step[0] += 1; fresh(); st.x('DELETE FROM kv WHERE k LIKE ?', ('lastbar:%',)); appmod._last_scan.clear(); appmod._scan_tf('XAUUSD', u, 'M15', 'H1')
risk.global_gate = lambda *a, **k: (False, 'daily loss limit hit')
scan(''); T('hook: a scan stopped by the global gate sends the risk alert (owner = admin phone)', [fields(m)[4] for m in SENT] == ['11'] and to() == ['boss@x.com'])
scan(JOE); T('hook: the same for a subscriber, to that subscriber', [fields(m)[4] for m in SENT] == ['11'] and to() == ['joe@x.com'])
risk.global_gate = lambda *a, **k: (True, 'ok')
brain.evaluate = lambda *a, **k: {'side': 'buy', 'score': 2, 'strategy': 'x', 'entry': 1, 'sl': 1, 'tp': 1, 'adx': 1, 'why': {}}
risk.symbol_gate = lambda *a, **k: (False, 'GBP exposure already at limit (correlated trades)')
scan(''); T('hook: a signal stopped by the symbol gate sends the exposure alert', [fields(m)[4] for m in SENT] == ['17'])
risk.global_gate, risk.symbol_gate, brain.evaluate = real_gg, real_sg, real_ev
T('hook: the scan also calls watch() once the gate has passed', 'risk_alerts.watch(uid)' in open(os.path.join(ROOT, 'backend', 'app.py')).read())

# ---- the loop
ra.register()
T('loop: resume and long-open jobs are on the alerts loop', {'resume_alerts', 'long_open_alerts'} <= set(alerts._jobs))
T('loop: the app registers them at startup', 'risk_alerts.register()' in open(os.path.join(ROOT, 'backend', 'app.py')).read())

bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.exit(1 if bad else 0)
