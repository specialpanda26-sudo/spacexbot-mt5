"""Section A4 checks: signals and alerts show the readable strategy name and the target. Run: python tests/test_sigtext.py
Covers strategy_info.alert_body, the _scan alert, pushcopy kinds 1 and 7, the phone-mode feed and push, GET /api/signals,
the EA 'opened' push, and the signal card in static/index.html (code between /*A4-start*/ and /*A4-end*/, run in node)."""
import os, sys, re, json, time, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'sigtext_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend import app as appmod
from backend.app import app
from backend import store as st, strategy_info as si, pushcopy, assist, push, sbauth
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
C.get('/api/me', headers=A)

# ---- the alert text (strategy_info.alert_body)
b = si.alert_body('gold_scalp', 2650.5, 2645.0, 2661.5)
T('alert text: the readable name, not the raw id', 'Liquidity sweep scalp' in b and 'gold_scalp' not in b)
T('alert text: entry, stop-loss and the target', '2650.5' in b and '2645.0' in b and '2661.5' in b and 'Target' in b)
b2 = si.alert_body('ma_cross+gold_scalp', 1, 2, 3)
T('alert text: a combined signal lists every readable name', '20/50 EMA cross' in b2 and 'Liquidity sweep scalp' in b2 and 'ma_cross' not in b2 and 'gold_scalp' not in b2)
b3 = si.alert_body('nightly_range', 1, 2, 3)
T('alert text: a taught strategy (no INFO line) gets a readable made-up name', 'Nightly range' in b3 and 'nightly_range' not in b3)
for empty in ('', None):
    b4 = si.alert_body(empty, 1, 2, 3)
    T('alert text: no strategy -> no empty name, no "None" (%r)' % (empty,), b4.startswith('Entry') and 'None' not in b4 and 'Target 3' in b4)

# ---- the scan's alert and the stored signal
M = [{'t': 1700000000 + i * 900, 'o': 100.0, 'h': 100.5, 'l': 99.5, 'c': 100.0, 'v': 1} for i in range(200)]
sent = []
sbauth.notify = lambda title, body, key=None, only=None: sent.append((title, body, key))
appmod.bars.get = lambda sym, tf, uid='': M
appmod.risk.global_gate = lambda *a, **k: (True, '')
appmod.risk.symbol_gate = lambda *a, **k: (True, '')
appmod.assist.announce = lambda sid: None
appmod.brain.evaluate = lambda *a, **k: {'side': 'buy', 'entry': 100.0, 'sl': 98.5, 'tp': 103.0, 'strategy': 'ma_cross+gold_scalp', 'score': 2, 'adx': 25.0}
appmod._last_scan.clear(); st.put('lastbar:XAUUSD', '')
appmod._scan('XAUUSD')
T('scan sends one alert for the new signal', len(sent) == 1 and sent[0][0] == 'BUY XAUUSD')
body = sent[0][1] if sent else ''
T('scan alert: readable names, no raw ids', '20/50 EMA cross' in body and 'Liquidity sweep scalp' in body and 'ma_cross' not in body and 'gold_scalp' not in body)
T('scan alert: entry, stop-loss and target', '100.0' in body and '98.5' in body and '103.0' in body and 'Target' in body)
row = st.q('SELECT strategy FROM signals ORDER BY id DESC', one=True)
T('the stored signal keeps the raw id (stats and learning need it)', row and row['strategy'] == 'ma_cross+gold_scalp')

# ---- pushcopy kinds 1 and 7
def comp(kind, **kw): return pushcopy.compose(kind, **kw)[1]
base = dict(sym='XAUUSD', side='buy', entry=2650.0, sl=2645.0, tp=2660.0)
K = {1: dict(base, risk=1), 7: dict(base, lots=0.05, mins=15)}
OLD = {1: 'Entry 2650.0, stop-loss 2645.0, take-profit 2660.0. Risking 1% of the account.',
       7: 'BUY at about 2650.0, stop-loss 2645.0, take-profit 2660.0. About 0.05 lots at your risk setting. Take or skip it in the app within 15 min.'}
for k, facts in K.items():
    w = comp(k, strategy='gold_scalp', **facts)
    T('push kind %d: readable name, no raw id' % k, 'Strategy: Liquidity sweep scalp.' in w and 'gold_scalp' not in w)
    T('push kind %d: entry, stop-loss and take-profit are still there' % k, '2650.0' in w and '2645.0' in w and '2660.0' in w and 'take-profit' in w)
    T('push kind %d: the strategy line comes after the take-profit' % k, w.find('take-profit') < w.find('Strategy:'))
    T('push kind %d: without a strategy the text is exactly as before' % k, comp(k, **facts) == OLD[k] and comp(k, strategy='', **facts) == OLD[k] and comp(k, strategy=None, **facts) == OLD[k])
    T('push kind %d: a combined signal lists every name' % k, all(x in comp(k, strategy='ma_cross+gold_scalp', **facts) for x in ('20/50 EMA cross', 'Liquidity sweep scalp')))
old_label = si.label
si.label = lambda s: 1 / 0
try: w = comp(1, strategy='gold_scalp', **K[1])
finally: si.label = old_label
T('push: if the name lookup fails the trade text is still sent', w == OLD[1])
t, bb, im = pushcopy.compose(7, strategy='gold_scalp')
T('push: a missing fact never crashes and still gets the name', isinstance(bb, str) and 'Liquidity sweep scalp' in bb)

# ---- phone mode: the feed and the 'signal found' push
now = int(time.time())
sid = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)', ('XAUUSD', 'buy', 2650.0, 2645.0, 2660.0, 1.0, 'gold_scalp', 2, 'pending', now, None))
feed = {r['id']: r for r in assist.feed('u1')}
T('feed: each signal has strategy_name (readable) and keeps the raw strategy', feed.get(sid, {}).get('strategy_name') == 'Liquidity sweep scalp' and feed.get(sid, {}).get('strategy') == 'gold_scalp')
cmb = [r for r in feed.values() if r.get('strategy') == 'ma_cross+gold_scalp']
T('feed: a combined signal gets every readable name', bool(cmb) and all(x in (cmb[0].get('strategy_name') or '') for x in ('20/50 EMA cross', 'Liquidity sweep scalp')))
got = []
push.configured = lambda: True
assist.audience = lambda now=None: [{'uid': 'u1', 'balance': 1000.0, 'risk': 1.0}]
push.send = lambda uid, kind, body, title, key, img=None: (got.append((kind, body, title)) or (1, ''))
try: n_sent = assist.announce_now(sid)
except Exception as e: n_sent = 'crash: %s' % e
T('phone push: sent to the phone-mode person', n_sent == 1 and len(got) == 1 and got[0][0] == 7)
T('phone push: readable name, no raw id, target kept', bool(got) and 'Strategy: Liquidity sweep scalp.' in got[0][1] and 'gold_scalp' not in got[0][1] and 'take-profit 2660.0' in got[0][1])

# ---- GET /api/signals
r = C.get('/api/signals', headers=A)
rows = {x['id']: x for x in r.json} if r.status_code == 200 else {}
T('/api/signals: strategy_name next to the raw strategy', rows.get(sid, {}).get('strategy_name') == 'Liquidity sweep scalp' and rows.get(sid, {}).get('strategy') == 'gold_scalp')
T('/api/signals: every row has a strategy_name', bool(rows) and all(x.get('strategy_name') for x in rows.values()))

# ---- EA reports a trade opened: push kind 1 carries the strategy
calls = []
appmod.push.notify = lambda kind, key=None, **facts: calls.append((kind, key, facts))
r = C.post('/api/ea/report', json={'status': 'open', 'id': sid, 'ticket': '1', 'lots': 0.1, 'price': 2650.2}, headers={'X-EA-Key': 'k'})
c1 = [c for c in calls if c[0] == 1]
T('EA opened: push kind 1 is sent with the raw strategy fact', r.status_code == 200 and len(c1) == 1 and c1[0][2].get('strategy') == 'gold_scalp')
T('EA opened: the text shows the readable name', c1 and 'Strategy: Liquidity sweep scalp.' in pushcopy.compose(1, **c1[0][2])[1])

# ---- the signal card in static/index.html (run in node)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('card code is in the page exactly once', html.count('/*A4-start*/') == 1 and html.count('/*A4-end*/') == 1)
m = re.search(r'/\*A4-start\*/(.*?)/\*A4-end\*/', html, re.S); CODE = m.group(1) if m else ''
HARNESS = r'''
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const usd = v => '$' + Number(v).toFixed(2), ago = t => 'just now';
const sigHtml = new Function('esc', 'usd', 'ago', 'BUSY', 'RES', code + '; return sigHtml;')(esc, usd, ago, false, null);
const now = Date.now() / 1000, OUT = [];
const base = {id: 7, symbol: 'XAUUSD', side: 'buy', entry: 2650.5, sl: 2645, tp: 2661.5, created: now, valid_until: now + 600, state: 'new', size: {}};
const mk = x => sigHtml(Object.assign({}, base, x));
let h = mk({strategy: 'gold_scalp', strategy_name: 'Liquidity sweep scalp'});
OUT.push(['card shows the readable name, not the raw id', h.includes('Liquidity sweep scalp') && !h.includes('gold_scalp')]);
OUT.push(['card still shows entry, stop-loss and take-profit', h.includes('Entry about 2650.5') && h.includes('Stop-loss 2645') && h.includes('Take-profit 2661.5')]);
OUT.push(['the name sits between the title and the prices', h.indexOf('BUY XAUUSD') < h.indexOf('Liquidity sweep scalp') && h.indexOf('Liquidity sweep scalp') < h.indexOf('Entry about')]);
OUT.push(['the take and skip buttons still work', h.includes('data-act="take"') && h.includes('data-act="skip"')]);
h = mk({strategy: 'nightly_range'});
OUT.push(['no name from the server: the id is made readable', h.includes('Nightly range') && !h.includes('nightly_range')]);
h = mk({strategy: 'a_b+c_d'});
OUT.push(['no name from the server: a combined id is made readable', h.includes('A b + c d')]);
h = mk({strategy: '', strategy_name: ''});
OUT.push(['no strategy at all: no Strategy line', !h.includes('Strategy') && h.includes('Entry about')]);
h = mk({strategy: null});
OUT.push(['strategy null: no Strategy line and no "null"', !h.includes('Strategy') && !h.includes('null')]);
h = mk({strategy_name: '<img src=x onerror=alert(1)>'});
OUT.push(['the name is escaped (no HTML injection)', !h.includes('<img') && h.includes('&lt;img')]);
h = mk({side: 'sell', strategy_name: 'Alpha'});
OUT.push(['a sell card shows it too', h.includes('SELL XAUUSD') && h.includes('Alpha')]);
for (const s of ['late', 'taken', 'skipped', 'done']) OUT.push(['name shown in state ' + s, mk({state: s, strategy_name: 'Alpha', mine: {lots: 0.1, outcome: 'win', pnl: 5}}).includes('Alpha')]);
console.log(JSON.stringify(OUT));
'''
if shutil.which('node'):
    p = subprocess.run(['node', '-'], input='const code = ' + json.dumps(CODE) + ';\n' + HARNESS, capture_output=True, text=True)
    try:
        for n, ok in json.loads(p.stdout.strip().splitlines()[-1]): T(n, ok)
    except Exception: T('card code runs in node: ' + (p.stderr or p.stdout)[-200:], False)
else: print('SKIP card checks: node not installed')

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
