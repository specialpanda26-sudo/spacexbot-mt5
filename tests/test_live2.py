"""LIVE2 tests: the live 'Bot running' notification follows Deriv too, and explains itself. No network. Run: python tests/test_live2.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_live2_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
os.environ.pop('LIVE_NOTIF', None)
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, live, push, brokers as bk
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
OWN, SUB = 'dev-boss@x.com', 'dev-amy@x.com'
c.get('/api/me', headers=H('boss@x.com')); c.get('/api/me', headers=H('amy@x.com'))
st.x('UPDATE users SET plan_until=? WHERE uid=?', (int(time.time()) + 86400 * 5, SUB))
def link(uid, broker='Deriv'): st.x("INSERT OR REPLACE INTO broker_links(uid,broker,kind,label,mode,status,created,updated) VALUES(?,?,'oauth','x','demo','verified',1,1)", (uid, broker))
def reset():
    st.x("DELETE FROM kv WHERE k LIKE 'bal:%' OR k LIKE 'bot:%' OR k='acct' OR k LIKE 'acct:%'"); st.put('bot_enabled', '0'); st.x('DELETE FROM signals'); st.x('DELETE FROM push_tokens'); live._last.clear()
def snap(uid): return live.snapshot(time.time(), uid)
link(OWN); link(SUB)

# ---- the bug: the owner runs on Deriv only
reset(); bk.set_bal(OWN, 'Deriv', 1000, 'USD', True); bk.set_bot(OWN, 'Deriv', True)
s = snap(OWN); T('owner on Deriv only: bot running (this was OFF before)', s['on'] is True and s['a']['balance'] == 1000.0)
bk.set_bal(OWN, 'Deriv', 1000, 'USD', True, now=time.time() - 1000); T('Deriv balance not read for 1000 s: not running', snap(OWN)['on'] is False)
bk.set_bal(OWN, 'Deriv', 1000, 'USD', True); bk.set_bot(OWN, 'Deriv', False); T('Deriv switch off: not running', snap(OWN)['on'] is False)

# ---- MT5 still works as before
reset(); st.set_acct({'balance': 500, 'equity': 505, 'open': 1, 'demo': True}); st.put('bot_enabled', '1')
s = snap(OWN); T('owner MT5 EA online + switch on: running, balance and equity shown', s['on'] is True and s['a']['balance'] == 500.0 and s['a']['equity'] == 505.0)
st.put('bot_enabled', '0'); T('MT5 switch off: not running', snap(OWN)['on'] is False)
st.put('bot_enabled', '1'); st.put('acct', json.dumps({'balance': 500, 'equity': 505, 'open': 1, 'seen': int(time.time()) - 600})); T('EA silent for 10 minutes: not running', snap(OWN)['on'] is False)

# ---- people stay apart
reset(); bk.set_bal(OWN, 'Deriv', 1000, 'USD', True); bk.set_bot(OWN, 'Deriv', True)
T("a subscriber does not get the owner's Deriv bot", snap(SUB)['on'] is False)
bk.set_bal(SUB, 'Deriv', 20, 'USD', True); bk.set_bot(SUB, 'Deriv', True); s = snap(SUB); T("a subscriber with their own Deriv bot running: running, own balance", s['on'] is True and s['a']['balance'] == 20.0)

# ---- today and open trades (closed profit today, open trades listed)
reset(); bk.set_bal(OWN, 'Deriv', 1000, 'USD', True); bk.set_bot(OWN, 'Deriv', True); now = int(time.time())
st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,pnl,closed) VALUES('XAUUSD','buy',2000,1990,2020,0.3,'macd_cross',1,'closed',?,?,2.5,?)", (now, OWN, now))
st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,fill) VALUES('XAUUSD','sell',2000,2010,1980,0.3,'macd_cross',1,'open',?,?,2001.5)", (now, OWN))
s = snap(OWN); d = live.build(True, s)
T("the owner's own Deriv profit today counts (+2.50)", s['today'] == 2.5 and '+$2.50' in d['text'])
T('open Deriv trade is listed in the expanded text', 'SELL XAUUSD' in d['big'] and d['title'].startswith('Bot running'))

# ---- tick sends / hides
sent = []; orig = push.send_data; push.send_data = lambda u, dd: sent.append((u, dd)) or 1
reset(); bk.set_bal(OWN, 'Deriv', 1000, 'USD', True); bk.set_bot(OWN, 'Deriv', True); st.x("INSERT OR REPLACE INTO push_tokens(token,uid,platform,created,seen) VALUES('t1',?, 'android',1,1)", (OWN,))
live.tick(time.time()); T('tick: the owner phone gets the Bot running notification (Deriv only)', len(sent) == 1 and sent[0][0] == OWN and sent[0][1].get('title', '').startswith('Bot running'))
sent.clear(); bk.set_bot(OWN, 'Deriv', False); live.tick(time.time() + 1); T('tick: bot stopped -> the phone is told to hide it', len(sent) == 1 and sent[0][1].get('off') == '1')
push.send_data = orig

# ---- explain: plain words
reset(); orig_cfg = push.configured
os.environ['LIVE_NOTIF'] = '0'; ok, why = live.explain(OWN); T('LIVE_NOTIF=0 is named', not ok and 'LIVE_NOTIF' in why); os.environ.pop('LIVE_NOTIF')
push.configured = lambda: False; ok, why = live.explain(OWN); T('missing FCM_SERVICE_ACCOUNT is named', not ok and 'FCM_SERVICE_ACCOUNT' in why)
push.configured = lambda: True; ok, why = live.explain(OWN); T('no registered phone is named', not ok and 'registered' in why)
st.x("INSERT OR REPLACE INTO push_tokens(token,uid,platform,created,seen) VALUES('t1',?, 'android',1,1)", (OWN,))
ok, why = live.explain(OWN); T('bot not running is named', not ok and 'not running' in why)
bk.set_bal(OWN, 'Deriv', 1000, 'USD', True); bk.set_bot(OWN, 'Deriv', True); ok, why = live.explain(OWN); T('everything in place: ok', ok and 'appears within a minute' in why)
c.post('/api/me/profile', json={'n': {'live': 0}}, headers=H('boss@x.com')); ok, why = live.explain(OWN); T('switch off is named', not ok and 'switch is off' in why)
c.post('/api/me/profile', json={'n': {'live': 1}}, headers=H('boss@x.com'))
st.x('UPDATE users SET plan_until=0 WHERE uid=?', (SUB,)); st.x("INSERT OR REPLACE INTO push_tokens(token,uid,platform,created,seen) VALUES('t2',?, 'android',1,1)", (SUB,)); ok, why = live.explain(SUB); T('subscriber with an ended plan is told so', not ok and 'plan' in why)
push.configured = orig_cfg

# ---- endpoint and page
T('the why endpoint needs a signed-in person', c.get('/api/live/why').status_code in (401, 403))
push.configured = lambda: True; r = c.get('/api/live/why', headers=H('boss@x.com')); j = r.get_json()
T('GET /api/live/why answers ok + why', r.status_code == 200 and j.get('ok') is True and isinstance(j.get('why'), str)); push.configured = orig_cfg
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read(); js = open(os.path.join(ROOT, 'static', 'live.js'), encoding='utf-8').read()
T('Profile > Notifications has the Check button', 'id="liveWhy"' in html or 'id=\\"liveWhy\\"' in html)
T('live.js calls /api/live/why', '/api/live/why' in js and '#liveWhy' in js)

bad_ = [n for n, ok in R if not ok]
print('\n%d passed, %d failed' % (len(R) - len(bad_), len(bad_)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_ else 0)
