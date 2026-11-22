"""Section 5B-2b checks: the Binance SPOT TESTNET bot is switched on (key check, Start bot, Trade on Binance, loop started, plain words). Binance is faked, no network.
Run: python tests/test_bn2b.py"""
import os, sys, time, glob, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_bn2b_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='BTCUSD', BROKER_KEY='x' * 32)
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, brokers as bk, tradeon, alerts, botstate, binance_bot as bb, binance_trade as bt
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'boss@x.com', 'bob@x.com'): c.get('/api/me', headers=H(e))
A, O, B = 'dev-amy@x.com', 'dev-boss@x.com', 'dev-bob@x.com'
st.x('UPDATE users SET plan_until=? WHERE uid IN (?,?)', (int(time.time()) + 86400 * 30, A, B))
KEY, SEC = 'K' * 40, 'S' * 40
S = {'code': 200, 'body': None, 'can': True, 'bal': '250', 'calls': []}
def http(method, path, key, qs):
    S['calls'].append((method, path))
    if (method, path) not in bt.ALLOWED: raise AssertionError('call outside ALLOWED: %s %s' % (method, path))
    if path == '/api/v3/account':
        if S['code'] != 200: return S['code'], S['body'] or {}
        return 200, {'canTrade': S['can'], 'balances': [{'asset': 'USDT', 'free': S['bal'], 'locked': '0'}]}
    return 404, {}
bt._http = http
KICKS = []
bb.kick = lambda uid, scan, paid: KICKS.append(uid)          # the real kick starts a thread; here we only record it
def save(email=None, who=A):
    return c.post('/api/brokers/Binance', json={'key': KEY, 'secret': SEC}, headers=H(email or 'amy@x.com'))
def binrow(uid): return next((b for b in bk.view(uid) if b['name'] == 'Binance'), None)
_ck = [0]
def clock(): _ck[0] += 20; return time.time() + _ck[0]          # a new time for each check, so the 8 s wait never gets in the way

# ---- the tile and the catalog speak the truth
save()
v = binrow(A)
T('tile data: Binance trades is True now, status saved, mode demo', v['trades'] is True and v['status'] == 'saved' and v['mode'] == 'demo')
cat = {x['name']: x for x in c.get('/api/brokers', headers=H('amy@x.com')).get_json()['catalog']}
T('catalog says testnet, fake money, and that real is not available', 'testnet' in cat['Binance']['tile'].lower() and 'fake money' in cat['Binance']['works'] and 'Real-money' in cat['Binance']['not'])
T('plain words exist for every new reason', all(k in bk.REASONS and len(bk.REASONS[k]) > 20 for k in ('real not ready', 'no key', 'no crypto symbols', 'cannot trade', 'other platform')))
T("'other platform' no longer names Deriv (it is shown on the Binance tile too)", 'Deriv' not in bk.REASONS['other platform'])

# ---- key check (demo = testnet)
T('no key saved: asks for it', bb.verify(B, http, clock()) == (False, 'Save your Binance testnet key and secret first.'))
ok, msg = bb.verify(A, http, clock())
v = binrow(A)
T('good testnet key: ok, verified, balance 250 shown as demo', ok and v['status'] == 'verified' and v['balance'] == 250.0 and v['acct_demo'] is True)
T('the note says testnet, fake money and the 1-minute stop check', 'Testnet' in msg and 'fake money' in msg and 'once a minute' in msg)
T('the check only read the account (no order)', [x for x in S['calls'] if x[0] == 'POST'] == [] and all(p == '/api/v3/account' for _, p in S['calls']))
T('the key and secret are in no message or note', KEY not in msg and SEC not in msg and KEY not in bk.note(A, 'Binance') and SEC not in bk.note(A, 'Binance'))
t0 = clock(); r1 = bb.verify(A, http, t0); r2 = bb.verify(A, http, t0 + 1)
T('checking twice within 8 seconds waits', r2 == (False, 'Wait a few seconds and try again.'))
S['code'], S['body'] = 401, {'code': -2015, 'msg': 'Invalid API-key'}
ok, msg = bb.verify(A, http, clock())
T('a key Binance does not accept -> rejected with a plain note', not ok and 'did not accept' in msg and binrow(A)['status'] == 'rejected')
S['code'], S['body'] = 200, None; bb.verify(A, http, clock())
T('a good key again -> verified again', binrow(A)['status'] == 'verified')
S['code'], S['body'] = 503, {}
ok, msg = bb.verify(A, http, clock())
T('Binance down is NOT the key\'s fault: still verified, message says try again', (not ok) and 'not answering' in msg and binrow(A)['status'] == 'verified')
S['code'] = 200; S['can'] = False
ok, msg = bb.verify(A, http, clock())
T('a key that cannot trade -> rejected', (not ok) and 'cannot trade' in msg and binrow(A)['status'] == 'rejected')
S['can'] = True; bb.verify(A, http, clock())
def boom(*a, **k): raise RuntimeError('network ' + KEY)
ok, msg = bb.verify(A, boom, clock())
T('a network error gives a plain message and never the key', (not ok) and KEY not in msg and 'Could not reach' in msg)
r = c.post('/api/brokers/Binance/verify', headers=H('amy@x.com')).get_json()
T('route: verify in demo uses the testnet check', r['ok'] and 'Testnet' in r['message'] or 'Wait a few seconds' in r['message'])
bb._vlast.clear(); r = c.post('/api/brokers/Binance/verify', headers=H('amy@x.com')).get_json()
T('route: verify ok returns the tile row', r['ok'] and next(b for b in r['brokers'] if b['name'] == 'Binance')['status'] == 'verified')

# ---- Start bot on the Binance card
bb._vlast.clear()
def tile_bot(email, on): return c.post('/api/brokers/Binance/bot', json={'on': on}, headers=H(email))
T('Binance card: Start before choosing Binance is refused (never on by default)', tile_bot('amy@x.com', True).status_code == 400 and 'Choose Binance' in tile_bot('amy@x.com', True).get_json()['error'] and bk.bot_flag(A, 'Binance') is not True and not KICKS)
c.post('/api/trade-on', json={'platform': 'Deriv'}, headers=H('amy@x.com'))
r = tile_bot('amy@x.com', True)
T('Binance card: Start while Deriv is chosen is refused with the chosen name', r.status_code == 400 and 'Deriv' in r.get_json()['error'] and not KICKS)
c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('amy@x.com'))
r = tile_bot('amy@x.com', True)
T('Binance chosen + checked + plan: Start works, flag on, the loop is kicked once', r.status_code == 200 and bk.bot_flag(A, 'Binance') is True and KICKS == [A])
T('Binance card Stop: flag off, note says bot off', tile_bot('amy@x.com', False).status_code == 200 and bk.bot_flag(A, 'Binance') is False and 'The bot is off' in binrow(A)['why'])
st.x("UPDATE broker_links SET status='saved' WHERE uid=? AND broker='Binance'", (A,)); KICKS.clear()
r = tile_bot('amy@x.com', True)
T('a key that is not checked yet cannot start', r.status_code == 400 and 'not checked' in r.get_json()['error'] and not KICKS)
st.x("UPDATE broker_links SET status='verified' WHERE uid=? AND broker='Binance'", (A,))
st.x('UPDATE users SET plan_until=? WHERE uid=?', (int(time.time()) - 10, A))
r = tile_bot('amy@x.com', True)
T('plan ended: Start is refused (402)', r.status_code == 402 and not KICKS)
st.x('UPDATE users SET plan_until=? WHERE uid=?', (int(time.time()) + 86400 * 30, A))
r = c.post('/api/brokers/Binance/mode', json={'mode': 'real', 'confirm': 'REAL'}, headers=H('amy@x.com'))
T('no Real switch for Binance: Real is refused in plain words', r.status_code == 400 and 'testnet' in r.get_json()['error'].lower())
bk.set_mode(A, 'Binance', 'real'); r = tile_bot('amy@x.com', True)
T('even if a Real flag was somehow set, Start is refused', r.status_code == 400 and 'not available' in r.get_json()['error'] and not KICKS)
bk.set_mode(A, 'Binance', 'demo')

# ---- the Bot tab Start / Stop
KICKS.clear(); links.set_bot(A, False)
r = c.post('/api/bot', json={'on': True}, headers=H('amy@x.com')).get_json()
T('Bot tab Start with Binance chosen starts the Binance bot only', bk.bot_flag(A, 'Binance') is True and KICKS == [A] and links.bot_on(A) is False)
T('and the Bot tab says Binance is running (broker Binance, plain words)', r.get('broker') == 'Binance' and r.get('running') is True)
r = c.post('/api/bot', json={'on': False}, headers=H('amy@x.com')).get_json()
T('Bot tab Stop stops Binance', bk.bot_flag(A, 'Binance') is False and r.get('running') is False)
bk.set_bot(A, 'Binance', True)
c.post('/api/trade-on', json={'platform': 'MT5'}, headers=H('amy@x.com'))
T('choosing MT5 switches the Binance bot off and says why', bk.bot_flag(A, 'Binance') is False and binrow(A)['why_code'] == 'other platform')
c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('amy@x.com'))
r = c.post('/api/bot', json={'on': True}, headers=H('bob@x.com'))
T('a person with no Binance key: Start with Binance chosen asks for the key, nothing starts', (c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('bob@x.com')), c.post('/api/bot', json={'on': True}, headers=H('bob@x.com')))[1].status_code == 400 and bk.bot_flag(B, 'Binance') is None)
st.x("UPDATE broker_links SET status='saved' WHERE uid=? AND broker='Binance'", (A,)); bk.set_bot(A, 'Binance', False)
r = c.post('/api/bot', json={'on': True}, headers=H('amy@x.com'))
T('Bot tab Start with an unchecked Binance key says so', r.status_code == 400 and 'not checked' in r.get_json()['error'] and bk.bot_flag(A, 'Binance') is False)
st.x("UPDATE broker_links SET status='verified' WHERE uid=? AND broker='Binance'", (A,))
KICKS.clear(); links.new_key(A); c.post('/api/trade-on', json={'platform': 'MT5'}, headers=H('amy@x.com')); links.set_bot(A, False)          # Amy has an MT5 key here, so the request really reaches the platform gates
c.post('/api/bot', json={'on': True}, headers=H('amy@x.com'))
T('with MT5 chosen the Bot tab Start starts MT5 and never touches Binance', links.bot_on(A) is True and bk.bot_flag(A, 'Binance') is not True and not KICKS)

# ---- the owner (admin) path
c.post('/api/brokers/Binance', json={'key': KEY, 'secret': SEC}, headers=H('boss@x.com')); bb._vlast.clear(); bb.verify(O, http, clock())
c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('boss@x.com')); KICKS.clear()
r = c.post('/api/bot', json={'on': True}, headers=H('boss@x.com'))
T('owner: Start with Binance chosen starts Binance and leaves the owner EA switch off', r.status_code == 200 and bk.bot_flag(O, 'Binance') is True and st.get('bot_enabled') != '1' and KICKS == [O])
c.post('/api/bot', json={'on': False}, headers=H('boss@x.com'))
T('owner: Stop stops Binance', bk.bot_flag(O, 'Binance') is False)

# ---- the Bot tab words
bk.set_bot(A, 'Binance', False); tradeon.set_(A, False, 'Binance')
e = botstate.explain(A, False, True)
T('Bot tab, Binance chosen and bot off: stopped, broker Binance', e['state'] == 'stopped' and e['broker'] == 'Binance' and e['running'] is False)
bk.set_bot(A, 'Binance', True); bk.set_why(A, 'Binance', 'ok'); e = botstate.explain(A, False, True)
T('Bot tab, Binance running fine: watching, says testnet', e['state'] == 'watching' and 'testnet' in e['why'] and e['broker'] == 'Binance')
bk.set_why(A, 'Binance', 'no crypto symbols'); e = botstate.explain(A, False, True)
T('Bot tab, a problem: waiting with the plain words', e['state'] == 'waiting' and 'crypto market' in e['why'])
bk.set_why(A, 'Binance', 'real not ready'); T('real not ready has its own words', 'not available' in botstate.explain(A, False, True)['why'])
st.x("DELETE FROM kv WHERE k LIKE 'why:%:Binance'"); e = botstate.explain(A, False, True)
T('no note yet: starting, never a made-up state', e['code'] == 'starting')
T('plan ended is still said first', botstate.explain(A, False, False)['code'] == 'plan ended')
tradeon.set_(A, False, 'Deriv'); T('Binance not chosen: the Bot tab is the old one (no broker Binance)', botstate.explain(A, False, True).get('broker') != 'Binance')

# ---- 5A gate and the loop are wired
T('trade-on view: Binance trades, note says testnet', (tradeon.set_(A, False, 'Binance'), c.get('/api/trade-on', headers=H('amy@x.com')).get_json())[1]['platforms'][2]['trades'] is True and 'testnet' in tradeon.view(A)['note'])
bb.round_all  # exists
src = open(os.path.join(ROOT, 'backend', 'app.py'), encoding='utf-8').read()
T('the app starts the Binance loop', "binance_bot.start(_scan, _paid)" in src and 'binance_bot' in src.split('authmail, binance, ')[1].split('\n')[0])
T('the old "does not trade yet" words are gone from the server', 'does not trade yet' not in src and 'does not trade yet' not in open(os.path.join(ROOT, 'backend', 'tradeon.py')).read())
idx = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page: Binance card says testnet and fake money, never the real key, 1-minute stop check', 'testnet.binance.vision' in idx and 'Never paste your real Binance key' in idx and 'about once a minute' in idx)
T('page: the Start bot button is on the Binance card and posts to its own broker', '((n==="Deriv"||bn)&&cur&&cur.status==="verified"' in idx and '"/api/brokers/"+n+"/bot"' in idx and '"/api/brokers/Deriv/bot"' not in idx)
T('page: the tile shows Testnet, not "Read-only, no trading"', 'Testnet bot on' in idx and 'Read-only, no trading' not in idx)
T('every Binance call in these checks stayed inside the allowed list', all((m, p) in bt.ALLOWED for m, p in S['calls']))
T('binance.py (Section 2, real read-only) is untouched: still no order call', 'requests.post' not in open(os.path.join(ROOT, 'backend', 'binance.py')).read())
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
