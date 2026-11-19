"""R6 step 1 tests: timing notes (candle arrived, signal made, handed out, position open) and the owner's gap report.
No network. Run: python tests/test_lag6.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_lag6_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, lag, brain, risk, bars
c = A.app.test_client(); H = {'X-EA-Key': 'k'}; ADM = {'Authorization': 'Bearer dev:boss@x.com'}; USR = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

brain.evaluate = lambda *a, **k: {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 't', 'score': 3, 'adx': 20}
risk.global_gate = lambda uid='': (True, ''); risk.symbol_gate = lambda *a, **k: (True, '')
BAR = int(time.time()) // 900 * 900 - 900
rows = [[BAR - 900 * i, 2000, 2001, 1999, 2000, 1] for i in range(130)]
r = c.post('/api/ea/sync', json={'account': {'balance': 1000, 'demo': True}, 'bars': {'XAUUSD': {'M15': rows, 'H1': rows[:10]}}}, headers=H)
T('sync with candles works', r.status_code == 200)
T('the same sync that carried the candles also hands the new signal out (no extra wait)', (r.get_json().get('signal') or {}).get('id'))
sid = st.q('SELECT id FROM signals ORDER BY id DESC LIMIT 1', (), True)['id']
d = json.loads(st.get('lag:%d' % sid))
T('signal remembers the candle it came from', d.get('bar') == BAR)
T('signal remembers when the candles arrived and the way they came', d.get('got') and d.get('via') == 'ea')
T('signal remembers when it was made', d.get('created') and d['created'] >= d['got'])
T('the sent time is noted when it is handed out, and it is not open yet', 'sent' in d and 'opened' not in d)
first_sent = d['sent']

c.post('/api/ea/report', json={'id': sid, 'status': 'open', 'ticket': 5, 'lots': 0.1, 'price': 2000}, headers=H)
d = json.loads(st.get('lag:%d' % sid)); T('the broker confirming the position notes the opened time', 'opened' in d)
time.sleep(1.1); lag.stamp(sid, 'sent'); lag.stamp(sid, 'opened')
d2 = json.loads(st.get('lag:%d' % sid)); T('a second note never overwrites the first', d2['sent'] == first_sent and d2['opened'] == d['opened'])

g = lag.gaps(d)
T('gaps are whole seconds and the total runs from the candle close', all(isinstance(v, int) for v in g.values() if v is not None) and g['total'] == d['opened'] - (BAR + 900))
T('candle_to_server is measured from the candle close', g['candle_to_server'] == d['got'] - (BAR + 900))

lag.created(sid + 100, BAR, 'someone'); T('a signal with no recorded arrival still gets a record', json.loads(st.get('lag:%d' % (sid + 100))).get('via') == 'other')
st.x("INSERT INTO signals(id,symbol,side,status,created) VALUES(?,?,?,?,?)", (sid + 100, 'XAUUSD', 'buy', 'pending', int(time.time())))
rep = c.get('/api/admin/lag', headers=ADM).get_json()
T('owner report lists the signals that have timings', rep['count'] == 2 and {x['id'] for x in rep['recent']} == {sid, sid + 100})
T('owner report names the biggest typical gap', rep['biggest'] in ('candle_to_server', 'server_scan', 'signal_to_sent', 'sent_to_open'))
T('a normal user cannot read it', c.get('/api/admin/lag', headers=USR).status_code in (401, 403))

real = st.put
def boom(*a, **k): raise RuntimeError('db down')
st.put = boom
try: lag.got('', 'ea'); lag.created(1, 1, ''); lag.stamp(1, 'sent'); ok = True
except Exception: ok = False
st.put = real
T('a failing timing note is swallowed', ok)
e = lag.report(0); T('no signals gives an empty report, no crash', e['count'] == 0 and e['biggest'] is None)

bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
if bad: sys.exit(1)
