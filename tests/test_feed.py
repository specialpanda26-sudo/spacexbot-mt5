"""Tests for backend/feed.py (server price feed) and its admin routes. No network: Yahoo is faked. Run: python tests/test_feed.py"""
import os, sys, time, math, random, json, subprocess, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'feed_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
os.environ.pop('FEED_MAP', None); os.environ.pop('FEED_ON', None)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend import app as appmod, feed, store as st, bars
from backend.feed import FeedError
C = appmod.app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
NOW = 1_700_000_000 - 1_700_000_000 % 900 + 900 * 10      # a quarter-hour boundary

def yahoo(tf, n, now=NOW, holes=(), last_forming=False, base=2300.0):
    step = feed.STEP[tf]; end = now - now % step - step; ts = [end - step * (n - 1 - i) for i in range(n)]      # the last CLOSED candle is the one before the current quarter-hour
    if last_forming: ts[-1] = now - now % step                # a candle that started and has not finished
    random.seed(1); p = base; O = []; H = []; L = []; Cc = []; V = []
    for i in range(n):
        o = p; p += random.gauss(0, 1.2); O.append(o); H.append(max(o, p) + .4); L.append(min(o, p) - .4); Cc.append(p); V.append(10)
    for i in holes: O[i] = H[i] = L[i] = Cc[i] = None
    return {'chart': {'result': [{'timestamp': ts, 'indicators': {'quote': [{'open': O, 'high': H, 'low': L, 'close': Cc, 'volume': V}]}}], 'error': None}}
class Resp:
    def __init__(s, js=None, code=200): s.js, s.status_code = js, code
    def json(s):
        if s.js is None: raise ValueError('no json')
        return s.js
CALLS = []; MODE = {'v': 'ok'}
def fake_get(url, params=None, headers=None, timeout=None):
    CALLS.append((url, dict(params or {})))
    if MODE['v'] == 'ok': return Resp(yahoo('M15' if params['interval'] == '15m' else 'H1', 700 if params['interval'] == '15m' else 400, now=NOW))
    if MODE['v'] == '429': return Resp({}, 429)
    if MODE['v'] == 'html': return Resp(None)
    if MODE['v'] == 'net': raise feed.requests.ConnectionError('x')
feed.requests.get = fake_get

# ---- parsing ----
rows = feed.parse_yahoo(yahoo('M15', 50), 'M15', now=NOW + 60)
T('good reply gives all candles, oldest first', len(rows) == 50 and rows == sorted(rows) and len(rows[0]) == 6)
T('a candle that is still forming is dropped', len(feed.parse_yahoo(yahoo('M15', 50, last_forming=True), 'M15', now=NOW + 60)) == 49)
T('holes (None) are skipped', len(feed.parse_yahoo(yahoo('M15', 50, holes=(3, 4)), 'M15', now=NOW + 60)) == 48)
r = feed.parse_yahoo(yahoo('M15', 50), 'M15', now=NOW + 60)
T('every candle has high >= open/close and low <= open/close', all(x[2] >= max(x[1], x[4]) and x[3] <= min(x[1], x[4]) for x in r))
js = yahoo('M15', 5); js['chart']['result'][0]['indicators']['quote'][0]['high'][2] = 1.0       # a bad high from the source
r = feed.parse_yahoo(js, 'M15', now=NOW + 60); T('a high below the close is repaired, not trusted', r[2][2] >= max(r[2][1], r[2][4]))
js = yahoo('M15', 5); js['chart']['result'][0]['indicators']['quote'][0]['close'][1] = 0
T('a zero price is dropped', len(feed.parse_yahoo(js, 'M15', now=NOW + 60)) == 4)
def bad(js, tf='M15'):
    try: feed.parse_yahoo(js, tf, now=NOW + 60); return False
    except FeedError: return True
T('Yahoo error object gives a plain error', bad({'chart': {'result': None, 'error': {'description': 'Not Found'}}}))
T('missing candles give a plain error', bad({'chart': {'result': [{}], 'error': None}}) and bad({}) and bad(None) and bad({'chart': {'result': [], 'error': None}}))
T('all candles forming/holes gives a plain error', bad(yahoo('M15', 2, holes=(0, 1))))
T('FEED_MAP default is gold only', feed.parse_map() == {'XAUUSD': 'GC=F'})
T('FEED_MAP parses several and ignores junk', feed.parse_map('XAUUSD:GC=F, eurusd:EURUSD=X ,junk,:x,y:') == {'XAUUSD': 'GC=F', 'EURUSD': 'EURUSD=X'})

# ---- fetch ----
MODE['v'] = 'ok'; CALLS.clear(); r = feed.fetch('XAUUSD', 'M15', now=NOW + 60)
T('fetch asks Yahoo for GC=F 15m', 'GC=F' in CALLS[0][0] and CALLS[0][1]['interval'] == '15m' and len(r) > 600)
T('fetch asks for 1h candles as 60m', (feed.fetch('XAUUSD', 'H1', now=NOW + 60), CALLS[-1][1]['interval'])[1] == '60m')
def raises(f):
    try: f(); return None
    except FeedError as e: return str(e)
MODE['v'] = '429'; T('HTTP 429 says so', '429' in (raises(lambda: feed.fetch('XAUUSD', 'M15')) or ''))
MODE['v'] = 'html'; T('a non-JSON reply says so', 'JSON' in (raises(lambda: feed.fetch('XAUUSD', 'M15')) or ''))
MODE['v'] = 'net'; T('a network failure says so', 'network' in (raises(lambda: feed.fetch('XAUUSD', 'M15')) or ''))
MODE['v'] = 'ok'; T('a symbol with no feed name is refused', raises(lambda: feed.fetch('USDJPY', 'M15')) is not None)

# ---- tick ----
scanned = []; scan = lambda s, u='': scanned.append((s, u))
def fresh():
    CALLS.clear(); scanned.clear(); feed._h1.clear(); MODE['v'] = 'ok'
    st.put('feed_on', '0'); st.put('acct', '{}'); st.put('symbols', 'XAUUSD,EURUSD')
    for k in [k for k in list(bars._d) if k[0] == '']: bars._d.pop(k)
fresh(); feed.tick(scan, now=NOW + 60)
T('feed off: nothing is downloaded or scanned', not CALLS and not scanned and not bars.get('XAUUSD', 'M15'))
fresh(); st.put('feed_on', '1'); s = feed.tick(scan, now=NOW + 60)
T('feed on: candles stored for the owner, both charts', len(bars.get('XAUUSD', 'M15')) > 300 and len(bars.get('XAUUSD', 'H1')) > 300)
T('feed on: only symbols in the symbols setting AND the feed map are fetched', {c[0] for c in CALLS} == {feed.URL % 'GC=F'})
T('feed on: the scan runs for the owner slot', scanned == [('XAUUSD', '')])
a = st.acct('')
T('feed on: owner account is marked demo + server feed and fresh', a.get('demo') is True and a.get('feed') == 'server' and time.time() - a['seen'] < 5)
T('status shows the last candle and no error', s['on'] and s['sym']['XAUUSD']['last'] and not s['err'] and s['ok'] == NOW + 60)
n = len(CALLS); feed.tick(scan, now=NOW + 120)
T('the hour chart is not downloaded again within 10 minutes', sum(1 for c in CALLS[n:] if c[1]['interval'] == '60m') == 0 and any(c[1]['interval'] == '15m' for c in CALLS[n:]))
feed.tick(scan, now=NOW + 60 + feed.H1_EVERY + 1)
T('the hour chart is downloaded again after 10 minutes', sum(1 for c in CALLS[n:] if c[1]['interval'] == '60m') == 1)
fresh(); st.put('feed_on', '1'); st.set_acct({'demo': True, 'balance': 1000, 'login': 5}, '')
s = feed.tick(scan, now=time.time())
T('your own EA online: the feed stays out and touches nothing', not CALLS and not scanned and not bars.get('XAUUSD', 'M15') and 'EA' in s['note'] and st.acct('').get('login') == 5)
fresh(); st.put('feed_on', '1'); st.put('acct', json.dumps({'demo': True, 'balance': 1000, 'seen': int(time.time()) - 500}))
feed.tick(scan, now=time.time()); T('an EA that went quiet more than 2 minutes ago: the feed takes over', bool(scanned))
fresh(); st.put('feed_on', '1'); feed.tick(scan, now=NOW + 60); CALLS.clear(); scanned.clear()
feed.tick(scan, now=NOW + 200); T('the feed keeps itself going (its own marker is not mistaken for an EA)', bool(scanned) and bool(CALLS))
fresh(); st.put('feed_on', '1'); MODE['v'] = '429'; s = feed.tick(scan, now=NOW + 60)
T('a failed download: no scan, no account change, error shown', not scanned and not st.acct('').get('feed') and '429' in s['err'])
MODE['v'] = 'ok'; s = feed.tick(scan, now=NOW + 120); T('next round recovers and clears the error', bool(scanned) and not s['err'])
fresh(); st.put('feed_on', '1')
def boom(sym, u=''): raise RuntimeError('x')
try: feed.tick(boom, now=NOW + 60); T('a failing scan does not crash the round', True)
except Exception: T('a failing scan does not crash the round', False)
fresh(); st.put('feed_on', '1'); os.environ['FEED_MAP'] = 'XAUUSD:GC=F,EURUSD:EURUSD=X'; _g = feed.requests.get
feed.requests.get = lambda url, params=None, **k: Resp({}, 429) if 'EURUSD' in url else _g(url, params=params, **k)
feed.tick(scan, now=NOW + 60); feed.requests.get = _g; os.environ.pop('FEED_MAP')
T('one symbol failing does not block the other', scanned == [('XAUUSD', '')] and 'EURUSD' in feed.status()['err'] and feed.status()['sym']['XAUUSD']['err'] == '')
st.put('symbols', 'EURUSD'); fresh(); st.put('feed_on', '1'); st.put('symbols', 'EURUSD'); feed.tick(scan, now=NOW + 60)
T('gold not in the symbols setting: nothing fetched', not CALLS and not scanned)

# ---- check() ----
fresh(); MODE['v'] = 'ok'; c = feed.check(now=NOW + 60)
T('check works and stores nothing', c['ok'] and 'closed candles' in c['msg'] and not bars.get('XAUUSD', 'M15') and not scanned)
MODE['v'] = '429'; c = feed.check(); T('check reports the reason when it fails', not c['ok'] and '429' in c['msg'])
MODE['v'] = 'ok'

# ---- routes ----
C.get('/api/me', headers=A); C.get('/api/me', headers=U)
T('a normal user cannot read the feed status', C.get('/api/admin/feed', headers=U).status_code == 403 and C.get('/api/admin/feed').status_code == 401)
T('a normal user cannot switch it on', C.post('/api/admin/feed', json={'on': True}, headers=U).status_code == 403 and st.get('feed_on') != '1')
fresh(); r = C.get('/api/admin/feed', headers=A)
T('admin reads the status', r.status_code == 200 and r.json['on'] is False and r.json['map'] == {'XAUUSD': 'GC=F'})
r = C.post('/api/admin/feed', json={'check': True}, headers=A)
T('admin check returns ok and does not switch it on', r.status_code == 200 and r.json['ok'] and st.get('feed_on') == '0')
MODE['v'] = '429'
CALLS.clear(); r = C.post('/api/admin/feed', json={'on': True}, headers=A); time.sleep(0.5)
T('admin turns it on', r.status_code == 200 and r.json['on'] is True and st.get('feed_on') == '1')
T('turning on starts a round right away', len(CALLS) > 0)
r = C.post('/api/admin/feed', json={'on': False}, headers=A); T('admin turns it off', r.json['on'] is False and st.get('feed_on') == '0')
T('on must be true or false', C.post('/api/admin/feed', json={'on': 'yes'}, headers=A).status_code == 400 and st.get('feed_on') == '0')
T('an empty request just reports', C.post('/api/admin/feed', json={}, headers=A).status_code == 200)
MODE['v'] = 'ok'

# ---- feed -> real scan -> signal -> phone-mode announce ----
fresh(); st.put('feed_on', '1'); st.put('bot_enabled', '1')
sigs = []; real_eval = appmod.brain.evaluate; real_ann = appmod.assist.announce; real_g, real_sg = appmod.risk.global_gate, appmod.risk.symbol_gate
appmod.brain.evaluate = lambda m, h, *a, **k: {'side': 'buy', 'entry': m[-1]['c'], 'sl': m[-1]['c'] - 5, 'tp': m[-1]['c'] + 10, 'strategy': 'ma_cross', 'score': 3, 'adx': 25, 'n': len(m), 'nh': len(h)}
appmod.assist.announce = lambda sid: sigs.append(sid); appmod.risk.symbol_gate = lambda *a, **k: (True, 'ok')
appmod._last_scan.clear(); feed.tick(appmod._scan, now=NOW + 60)
row = st.q("SELECT * FROM signals WHERE symbol='XAUUSD' ORDER BY id DESC LIMIT 1", one=True)
wk = time.gmtime().tm_wday >= 5 or (time.gmtime().tm_wday == 4 and time.gmtime().tm_hour >= 20)
T('the real scan saw the newest candle from the feed', st.get('lastbar:XAUUSD') == str(bars.get('XAUUSD', 'M15')[-1]['t']))
T('weekday: a signal is stored for the owner and announced to phone-mode people', wk or (row and row['uid'] is None and row['side'] == 'buy' and sigs == [row['id']]))
T('the strategies got enough history (15m and 1h)', len(bars.get('XAUUSD', 'M15')) >= 220 and len(bars.get('XAUUSD', 'H1')) >= 60)
appmod.brain.evaluate = real_eval; appmod.assist.announce = real_ann; appmod.risk.symbol_gate = real_sg

# ---- the admin card in the page ----
h = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the admin page has the Price feed card and its four buttons', all(x in h for x in ('Price feed', 'id="pfChk"', 'id="pfOn"', 'id="pfOff"', 'id="pfRef"', 'id="pfMsg"')))
T('the card talks to /api/admin/feed', h.count('/api/admin/feed') >= 3)
try:
    js = '\n;\n'.join(re.findall(r'<script>(.*?)</script>', h, re.S)); p = os.path.join(HERE, 'feed_page.js'); open(p, 'w', encoding='utf-8').write(js)
    r = subprocess.run(['node', '--check', p], capture_output=True, text=True); os.remove(p)
    T('the page script still parses (node --check)', r.returncode == 0)
except FileNotFoundError: print('(node not found: page script check skipped)')
T('app.py imports alerts (alerts.start() used to crash with a NameError, so live.start() never ran)', hasattr(appmod, 'alerts') and appmod.alerts._running is True)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
