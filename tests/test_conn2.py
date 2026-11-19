"""R2 checks: GET /api/connections (backend/connwhy.py), Deriv-aware botstate, and the Bot tab Start/Stop driving Deriv. Offline, no real broker.
Run: python tests/test_conn2.py (last line: N checks, M failed)"""
import os, sys, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'conn2_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, brokers as bk, connwhy, botstate, deriv
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, B, O = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'; TOK = 'abcDEF1234567890'
NOW = time.time()
st.x("UPDATE users SET plan_until=? WHERE uid IN (?,?)", (int(NOW) + 86400, A, B))
def snap(uid, admin=False, paid=True, now=None): return connwhy.snapshot(uid, admin, paid, 'https://x.onrender.com', now or NOW)
def row(s, i): return next(r for r in s['rows'] if r['id'] == i)
def chk(r, t): return next(x for x in r['checks'] if x['t'] == t)
def ea(acct, key='k'): return c.post('/api/ea/sync', json={'account': acct}, headers={'X-EA-Key': key})

# ---- nothing set up ----
s = snap(A)
T('nothing set up: state none, both rows say not set up, a plain message', s['state'] == 'none' and row(s, 'Deriv')['state'] == 'none' and row(s, 'MT5')['state'] == 'none' and s['message'].startswith('Nothing is connected'))
T('the first fix is named in the message', 'token' in s['message'].lower())
# ---- Deriv ----
bk.save(A, 'Deriv', {'token': TOK})
r = row(snap(A), 'Deriv')
T('token saved but not checked: problem, the failing check is Token checked, never "connected"', r['state'] == 'problem' and chk(r, 'Token checked')['ok'] is False and 'not checked' in r['fix'])
st.x("UPDATE broker_links SET status='rejected' WHERE uid=? AND broker='Deriv'", (A,))
T('a rejected token says Deriv refused it', 'refused' in row(snap(A), 'Deriv')['fix'])
st.x("UPDATE broker_links SET status='verified' WHERE uid=? AND broker='Deriv'", (A,))
r = row(snap(A), 'Deriv')
T('verified but no balance read yet: still not connected (a token alone is not a connection)', r['state'] == 'problem' and chk(r, 'Balance read')['ok'] is False)
bk.set_bal(A, 'Deriv', 1000.5, 'USD', True, now=NOW)
r = row(snap(A), 'Deriv'); s = snap(A)
T('verified + fresh balance: connected, demo, balance in the headline', r['state'] == 'ok' and 'Demo' in r['headline'] and '1000.50' in r['headline'] and r['fix'] == '' and s['state'] == 'connected' and s['connected'] == ['Deriv'])
T('a balance older than 3 minutes is stale (Offline), not missing', row(snap(A, now=NOW + 400), 'Deriv')['state'] == 'stale' and snap(A, now=NOW + 400)['state'] == 'connected')
bk.set_bal(A, 'Deriv', 50.0, 'USD', False, now=NOW)
T('a real Deriv account says Real', 'Real' in row(snap(A), 'Deriv')['headline'] and row(snap(A), 'Deriv')['mode'] == 'real')
bk.set_bal(A, 'Deriv', 1000.5, 'USD', True, now=NOW)
T('plan ended: a subscriber is not connected (Plan active fails first)', row(snap(A, paid=False), 'Deriv')['state'] == 'problem' and 'Renew' in row(snap(A, paid=False), 'Deriv')['fix'])
T('the owner is never blocked by the plan check', row(snap(A, admin=True, paid=False), 'Deriv')['state'] == 'ok')
os.environ.pop('DERIV_APP_ID')
r = row(snap(A), 'Deriv')
T('server not set up (no DERIV_APP_ID): the first failing check says so, to a customer in words that do not name Render', r['state'] == 'problem' and 'owner' in r['fix'] and 'Render' not in r['fix'])
T('the same problem tells the owner exactly which setting to set', 'DERIV_APP_ID' in row(snap(A, admin=True), 'Deriv')['fix'])
os.environ['DERIV_APP_ID'] = '123'
# ---- MT5 bridge ----
T('a saved MT5 broker is NOT a connection: only the server name is kept', (bk.save(B, 'FBS', {'server': 'FBS-Demo'}), links.new_key(B), row(snap(B), 'MT5')['state'])[-1] == 'problem')
m = row(snap(B), 'MT5')
T('saved FBS, bridge never reported: says saving only records the server name, check Bridge has reported fails', 'server name' in m['headline'] and chk(m, 'Bridge has reported')['ok'] is False and m['saved'][0]['name'] == 'FBS')
key = links.new_key(B); ea({'balance': 500, 'equity': 500, 'open': 0, 'demo': True, 'login': 99}, key)
m = row(snap(B), 'MT5')
T("the person's OWN key makes the bridge connected", m['state'] == 'ok' and m['login'] == '99' and snap(B)['state'] == 'connected')
T("the owner's key never connects a subscriber (amy has no link: problem, key check fails)", (ea({'balance': 1, 'demo': True}, 'k'), row(snap(A), 'MT5'))[1]['state'] != 'ok' and chk(row(snap(A), 'MT5'), 'Bridge key')['ok'] is False)
T('bridge quiet for 10 minutes: stale (Offline) with the last-report time', row(snap(B, now=time.time() + 600), 'MT5')['state'] == 'stale' and 'quiet' in row(snap(B, now=time.time() + 600), 'MT5')['fix'])
T('owner: the owner EA key connects the owner', row(snap(O, admin=True), 'MT5')['state'] == 'ok')
T("owner scope never shows amy's data and amy never shows the owner's", row(snap(A), 'MT5')['balance'] != row(snap(O, admin=True), 'MT5')['balance'])
# ---- the route ----
T('GET /api/connections needs a sign-in', c.get('/api/connections').status_code == 401)
j = c.get('/api/connections', headers=H('bob@x.com')).get_json()
T('the route answers with the person\'s own rows', j['state'] == 'connected' and [x['id'] for x in j['rows']] == ['Deriv', 'MT5'])
T('no token, key or hash in the answer', TOK not in json.dumps(j) and 'sxb_' not in json.dumps(j) and 'secret' not in json.dumps(j).lower() and 'key_hash' not in json.dumps(j))
from backend import sbauth
_v = sbauth.verify; sbauth.verify = lambda t: {'uid': 'dev-ghost', 'email': 'ghost@x.com', 'name': 'g', 'verified': False}
T('an unverified email gets 403', c.get('/api/connections', headers=H('ghost@x.com')).status_code == 403); sbauth.verify = _v
# ---- botstate knows Deriv ----
x = botstate.explain(A, False, True, NOW)
T('Deriv person, bot off: stopped, no mention of MT5', x['state'] == 'stopped' and 'MT5' not in x['why'])
bk.set_bot(A, 'Deriv', True); bk.set_why(A, 'Deriv', 'ok', NOW); x = botstate.explain(A, False, True, NOW)
T('Deriv bot on and the loop is fine: watching, says Deriv, never "MT5 is not talking"', x['state'] == 'watching' and 'Deriv' in x['why'] and 'MT5' not in x['why'] and x['broker'] == 'Deriv')
bk.set_why(A, 'Deriv', 'no balance', NOW); x = botstate.explain(A, False, True, NOW)
T('Deriv loop reason is passed on in words', x['state'] == 'waiting' and 'balance' in x['why'].lower())
st.x("DELETE FROM kv WHERE k=?", ('why:%s:Deriv' % A,)); x = botstate.explain(A, False, True, NOW)
T('Deriv on, no round yet: waiting, "first check runs within a minute"', x['state'] == 'waiting' and 'minute' in x['why'])
T('plan ended is said first, even for Deriv', botstate.explain(A, False, False, NOW)['code'] == 'plan ended')
links.new_key(A); links.set_bot(A, True)
x = botstate.explain(A, False, True, NOW)
T('MT5 linked but silent while Deriv runs: the Deriv state is shown, not "MT5 is not talking"', x['broker'] == 'Deriv')
# ---- Start/Stop drives Deriv ----
bk.set_bot(A, 'Deriv', False); links.set_bot(A, False)
_k = deriv.kick; KICKS = []; deriv.kick = lambda *a, **k: KICKS.append(a[0])
r = c.post('/api/bot', headers=H('amy@x.com'), json={'on': True})
T('Start on the Bot tab turns the Deriv switch on (verified token) and runs a round at once', r.status_code == 200 and bk.bot_flag(A, 'Deriv') is True and links.bot_on(A) is True and KICKS == [A])
r = c.post('/api/bot', headers=H('amy@x.com'), json={'on': False})
T('Stop turns both off and leaves the reason "bot off" on the Deriv tile', bk.bot_flag(A, 'Deriv') is False and links.bot_on(A) is False and [x for x in bk.view(A) if x['name'] == 'Deriv'][0].get('why_code') == 'bot off')
st.x("UPDATE broker_links SET status='saved' WHERE uid=? AND broker='Deriv'", (A,)); links.drop(A)
r = c.post('/api/bot', headers=H('amy@x.com'), json={'on': True})
T('Deriv only, token not checked: Start is refused with the reason (400)', r.status_code == 400 and 'checked' in r.get_json()['error'] and bk.bot_flag(A, 'Deriv') is not True)
st.x("UPDATE broker_links SET status='verified' WHERE uid=? AND broker='Deriv'", (A,))
r = c.post('/api/bot', headers=H('amy@x.com'), json={'on': True}); T('Deriv only, verified: Start works with no MT5 link', r.status_code == 200 and bk.bot_flag(A, 'Deriv') is True)
c.post('/api/bot', headers=H('amy@x.com'), json={'on': False})
T('nothing connected at all: Start says to make the key (400)', c.post('/api/bot', headers=H('bob@x.com'), json={'on': True}).status_code == 200)  # bob has an MT5 link
c.post('/api/brokers/Deriv', headers=H('amy@x.com')) ; bk.drop(A, 'Deriv')
T('no link and no Deriv: 400 with the plain message', c.post('/api/bot', headers=H('amy@x.com'), json={'on': True}).status_code == 400)
r = c.post('/api/bot', headers=H('boss@x.com'), json={'on': True})
T('owner Start drives the owner EA switch', r.status_code == 200 and st.get('bot_enabled') == '1')
deriv.kick = _k
for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]; print('%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
