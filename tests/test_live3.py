"""Section 3 checks: live numbers (GET /api/live) + the Live card on Home, the strip on the Bot tab and the top chip. No network, no real broker.
Run: python tests/test_live3.py. The page code sits between /*S3-start*/ and /*S3-end*/ in static/index.html and runs here against a fake page (needs node; skipped without it)."""
import os, sys, re, json, glob, time, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'live3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, brokers as bk, links, livestats as ls
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
A, B, O = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'; TOK = 'abcDEF1234567890'
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
NOW = time.time(); DAY = st.day_start()
def sig(uid, status, pnl=None, closed=None, sym='XAUUSD', side='buy', fill=2345.1, strat='gold_scalp'):
    st.x("INSERT INTO signals(symbol,side,entry,status,created,pnl,closed,strategy,fill,uid) VALUES(?,?,?,?,?,?,?,?,?,?)", (sym, side, fill, status, int(NOW), pnl, closed, strat, fill, uid))
def snap(uid, admin=False, now=None): return ls.snapshot(uid, admin, now)

# ---- server numbers ----
s = snap(A)
T('nothing connected: state none, no sources, zeros (never sample numbers)', s['state'] == 'none' and s['sources'] == [] and s['balance'] == 0 and s['equity'] == 0 and s['today'] == 0 and s['open'] == 0 and s['trades'] == [])
bk.save(A, 'Deriv', {'token': TOK}); bk.set_bal(A, 'Deriv', 1000.5, 'USD', True)
s = snap(A)
T('Deriv demo: live, balance = equity, demo mode, one source', s['state'] == 'live' and s['mode'] == 'demo' and s['balance'] == 1000.5 and s['equity'] == 1000.5 and s['floating'] == 0 and [x['id'] for x in s['sources']] == ['Deriv'])
T('a Deriv balance older than 3 minutes is stale, not live', snap(A, now=NOW + 400)['state'] == 'stale' and snap(A, now=NOW + 400)['balance'] == 1000.5)
bk.set_bal(A, 'Deriv', 250.0, 'USD', False)
T('a real Deriv account makes the mode real', snap(A)['mode'] == 'real' and snap(A)['sources'][0]['mode'] == 'real')
bk.set_bal(A, 'Deriv', 1000.5, 'USD', True)
sig(A, 'closed', 5.0, int(NOW)); sig(A, 'closed', -2.0, int(NOW)); sig(A, 'closed', 100.0, DAY - 100); sig(B, 'closed', 77.0, int(NOW)); sig(A, 'open')
s = snap(A)
T("today = trades closed since the day start (yesterday's and other people's are left out)", s['today'] == 3.0 and s['today_n'] == 2)
T('today_pct is against the balance at the start of the day', abs(s['today_pct'] - round(3.0 / (1000.5 - 3.0) * 100, 2)) < 0.005)
t0 = s['trades'][0] if s['trades'] else {}
T('open trades: the count and the rows (readable strategy name, price)', s['open'] == 1 and len(s['trades']) == 1 and t0.get('symbol') == 'XAUUSD' and t0.get('side') == 'buy' and t0.get('price') == 2345.1 and t0.get('strategy_name') not in ('', None, 'gold_scalp'))
sig(A, 'open', side='sell', sym='EURUSD'); sig(A, 'open', side='buy', sym='GBPUSD')
T('open rows are newest first and capped', [x['symbol'] for x in snap(A)['trades']][:2] == ['GBPUSD', 'EURUSD'] and snap(A)['open'] == 3)
for i in range(12): sig(A, 'open', sym='US%d' % i)
T('at most 8 open rows are listed, the count is still true', len(snap(A)['trades']) == 8 and snap(A)['open'] == 15)
st.x("DELETE FROM signals WHERE uid=? AND status='open'", (A,)); sig(A, 'open')
T("another person's trades never show up", snap(B)['today'] == 77.0 and snap(B)['open'] == 0 and snap(B)['state'] == 'none')
links.new_key(B); st.set_acct({'balance': 520.25, 'equity': 525.5, 'open': 2, 'demo': True}, B)
s = snap(B)
T('MT5 account: balance, equity, floating and the EA open count', s['state'] == 'live' and s['balance'] == 520.25 and s['equity'] == 525.5 and s['floating'] == 5.25 and s['open'] == 2 and s['sources'][0]['id'] == 'MT5')
T('the open count is the larger of the EA count and our own rows', (sig(B, 'open'), sig(B, 'open'), sig(B, 'open'), snap(B)['open'])[-1] == 3)
T('MT5 not heard from for 2 minutes: stale', snap(B, now=NOW + 200)['state'] == 'stale' and snap(B, now=NOW + 200)['sources'][0]['online'] is False)
st.set_acct({'balance': 520.25, 'equity': 525.5, 'open': 2, 'demo': False}, B)
T('an MT5 account that is not a demo account makes the mode real', snap(B)['mode'] == 'real')
st.set_acct({'balance': 'abc', 'equity': 1}, B)
T('a balance that is not a number is ignored (no NaN on screen)', snap(B)['state'] == 'none')
st.set_acct({'balance': float('nan'), 'equity': 1}, B)
T('a NaN balance is ignored too', snap(B)['state'] == 'none')
st.set_acct({'balance': 100, 'equity': None, 'demo': True}, B)
T('missing equity falls back to the balance', snap(B)['equity'] == 100 and snap(B)['floating'] == 0)
bk.save(B, 'Deriv', {'token': TOK}); bk.set_bal(B, 'Deriv', 900.0, 'USD', True)
s = snap(B)
T('Deriv + MT5 together: both listed, balances added up', [x['id'] for x in s['sources']] == ['Deriv', 'MT5'] and s['balance'] == 1000.0)
st.set_acct({'balance': 5000.0, 'equity': 5010.0, 'open': 0, 'demo': True}, '')
sig('', 'closed', 8.0, int(NOW)); sig(O, 'closed', 2.0, int(NOW)); sig(A, 'closed', 999.0, int(NOW))
s = snap(O, True)
T("owner: reads the owner's EA, counts the EA's trades and the owner's own Deriv trades, never other people's", s['sources'][0]['id'] == 'MT5' and s['balance'] == 5000.0 and s['equity'] == 5010.0 and s['today'] == 10.0)
T('a non-admin never reads the owner EA scope (own trades only: 5 - 2 + 999)', snap(A)['balance'] == 1000.5 and snap(A)['today'] == 1002.0)

# ---- the route ----
T('GET /api/live needs a sign-in', c.get('/api/live').status_code == 401)
from backend import sbauth
_v = sbauth.verify; sbauth.verify = lambda t: {'uid': 'dev-ghost', 'email': 'ghost@x.com', 'name': 'g', 'verified': False}
r = c.get('/api/live', headers=H('ghost@x.com')); sbauth.verify = _v
T('GET /api/live needs a verified email (403)', r.status_code == 403)
r = c.get('/api/live', headers=H('amy@x.com')); j = r.get_json()
T("the route answers with the person's own numbers", r.status_code == 200 and j['balance'] == 1000.5 and j['state'] == 'live')
T('the route never carries a token, key or secret', 'token' not in json.dumps(j).lower() and 'secret' not in json.dumps(j).lower() and TOK not in json.dumps(j))
T("bob's route shows bob's numbers, not amy's", c.get('/api/live', headers=H('bob@x.com')).get_json()['balance'] == 1000.0)
T('the owner route uses the owner scope', c.get('/api/live', headers=H('boss@x.com')).get_json()['balance'] == 5000.0)

# ---- the page ----
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the page code is in the page exactly once, after the Account card', html.count('/*S3-start*/') == 1 and html.count('/*S3-end*/') == 1 and html.find('/*S2-end*/') < html.find('/*S3-start*/'))
T('the places it uses exist (Home, Bot tab, #eq, #stats, #openList, the Demo data chip)', all(x in html for x in ('id="view-home"', 'id="view-bot"', 'id="eq"', 'id="stats"', 'id="openList"', 'chip demo app-only')))
m = re.search(r'/\*S3-start\*/(.*?)/\*S3-end\*/', html, re.S); CODE = m.group(1) if m else ''
HARNESS = r'''
const code = process.argv[1], OUT = [], tick = () => new Promise(r => setTimeout(r, 5));
function page(user, st) {
  const timers = [], calls = []; let now = 1700000000000;
  const el = () => { const e = {innerHTML: '', hidden: false, className: '', title: '', style: {}, on: false, inserted: [], handlers: {}, classList: {contains: c => c === 'on' && e.on}, insertBefore(n) { e.inserted.push(n); }, addEventListener(t, f) { e.handlers[t] = f; }, closest() { return e; }}; return e; };
  const vh = el(), vb = el(), buddy = el(), acct = el(), eq = el(), stats = el(), openList = el(), chip = el();
  chip.className = 'chip demo app-only'; chip.innerHTML = '<span class="dot"></span>Demo data'; chip.title = 'No broker connected. Every number is sample data.';
  vh.querySelector = () => buddy;
  const document = {hidden: false, createElement: el, querySelector: s => s === '.top-actions .chip.demo' ? chip : null, addEventListener(t, f) { document.vis = f; },
    getElementById: id => ({'view-home': vh, 'view-bot': vb, acctc: acct, eq, stats, openList})[id] || null};
  const SXA = {user: () => st.user, api: (u, o) => { calls.push({u, o}); return st.next(); }};
  const MO = function (f) { this.observe = () => {}; MO.f = f; };
  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', 'Date', code)(document, {SXA}, SXA, f => timers.push(f), MO, {now: () => now});
  const H = vh.inserted[0], S = vb.inserted[0];
  const run = async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } };
  return {H, S, chip, eq, stats, openList, vh, vb, calls, run, document, mo: () => MO.f(), setNow: v => { now = v; }, live: () => calls.filter(c => c.u === '/api/live')};
}
const J = o => Object.assign({state: 'live', mode: 'demo', balance: 1000.5, equity: 1004.7, floating: 4.2, today: 4.2, today_pct: 0.42, today_n: 2, open: 1,
  trades: [{symbol: 'XAUUSD', side: 'buy', price: 2345.1, strategy_name: 'Gold scalp'}], sources: [{id: 'MT5', name: 'MT5', mode: 'demo', balance: 1000.5, equity: 1004.7, online: true}]}, o || {});
const U = {uid: 'u1', verified: true, active: true, admin: false}, ok = j => () => Promise.resolve(j);
(async () => {
  let p = page(null, {user: null, next: ok(J())}); await p.run(1);
  OUT.push(['signed out: no Live card, chip keeps its Demo data text, sample cards are shown, nothing asked', p.H.hidden === true && p.S.hidden === true && p.chip.innerHTML.includes('Demo data') && p.live().length === 0 && p.eq.style.display !== 'none']);
  p = page({uid: 'x', verified: false}, {user: {uid: 'x', verified: false}, next: ok(J())}); await p.run(6);
  OUT.push(['email not verified: nothing is asked and nothing is shown', p.live().length === 0 && p.H.hidden === true]);
  p = page(U, {user: U, next: ok(J({state: 'none', sources: [], balance: 0, equity: 0, today: 0, open: 0, trades: []}))}); await p.run(1);
  OUT.push(['no broker connected: still sample data, honest chip, no Live card', p.live().length === 1 && p.H.hidden === true && p.chip.innerHTML.includes('Demo data') && p.chip.className === 'chip demo app-only' && p.eq.style.display !== 'none']);
  const st = {user: U, next: ok(J())}; p = page(U, st); p.vh.on = true; await p.run(1);
  let h = p.H.innerHTML;
  OUT.push(['connected demo: the Live card shows equity, balance, today in dollars and the open count', p.H.hidden === false && h.includes('$1,004.70') && h.includes('$1,000.50') && h.includes('+$4.20') && h.includes('Open trades')]);
  OUT.push(['profit shows an up arrow in the good colour, with the percentage', h.includes('\u25B2 +$4.20 today (+0.4%)') && h.includes('num good')]);
  OUT.push(['the open trade row has the symbol, side, price and the readable strategy name', h.includes('XAUUSD Buy') && h.includes('at 2345.1') && h.includes('Gold scalp')]);
  OUT.push(['says where the numbers come from and how fresh they are', h.includes('MT5 demo') && h.includes('updated just now') && h.includes('Floating +$4.20')]);
  OUT.push(['the top chip says Live Demo (green), no longer Demo data', p.chip.innerHTML.includes('Live Demo') && !p.chip.innerHTML.includes('Demo data') && p.chip.className.includes('ok')]);
  OUT.push(['the sample equity, stats and open-trades cards are hidden while real numbers are shown', p.eq.style.display === 'none' && p.stats.style.display === 'none' && p.openList.style.display === 'none']);
  OUT.push(['the Bot tab strip has equity, today with the arrow, open count', p.S.hidden === false && p.S.innerHTML.includes('Equity $1,004.70') && p.S.innerHTML.includes('\u25B2 +$4.20') && p.S.innerHTML.includes('1 open')]);
  st.next = ok(J({today: -3.1, today_pct: -0.3, equity: 997.4, floating: -3.1})); await p.run(5);
  h = p.H.innerHTML;
  OUT.push(['a losing day: down arrow, bad colour, minus sign', h.includes('\u25BC -$3.10 today (-0.3%)') && h.includes('num bad') && p.S.innerHTML.includes('\u25BC -$3.10')]);
  st.next = ok(J({today: 0, today_pct: 0, equity: 1000.5, floating: 0})); await p.run(5);
  OUT.push(['a flat day: no arrow, no plus or minus', p.H.innerHTML.includes('<div class="num muted">$0.00 today') && p.S.innerHTML.includes('<span class="muted">$0.00</span>')]);
  st.next = ok(J({today: -0.004})); await p.run(5);
  OUT.push(['a tiny loss that rounds to zero shows $0.00, never -$0.00', p.H.innerHTML.includes('$0.00 today') && !p.H.innerHTML.includes('-$0.00')]);
  st.next = ok(J({mode: 'real'})); await p.run(5);
  OUT.push(['a real account: the chip says Live Real in the warning colour', p.chip.innerHTML.includes('Live Real') && p.chip.className.includes('stop') && p.H.innerHTML.includes('Live Real') && p.H.innerHTML.includes('chip stop')]);
  st.next = ok(J({state: 'stale'})); await p.run(5);
  OUT.push(['broker offline: Offline chip, last numbers kept, said in words', p.chip.innerHTML.includes('Offline') && p.chip.className.includes('watch') && p.H.innerHTML.includes('broker looks offline') && p.H.innerHTML.includes('$1,004.70')]);
  st.next = ok(J()); await p.run(5);
  OUT.push(['it comes back to Live when the broker answers again', p.chip.innerHTML.includes('Live Demo') && !p.H.innerHTML.includes('looks offline')]);
  st.next = () => Promise.reject(new Error('down')); await p.run(5);
  OUT.push(['one failed refresh keeps showing live numbers', p.chip.innerHTML.includes('Live Demo')]);
  await p.run(10);
  OUT.push(['three failed refreshes in a row: Offline and "Cannot reach the server", numbers kept', p.chip.innerHTML.includes('Offline') && p.H.innerHTML.includes('Cannot reach the server') && p.H.innerHTML.includes('$1,004.70')]);
  st.next = ok(J()); await p.run(5);
  OUT.push(['and one good answer clears it', p.chip.innerHTML.includes('Live Demo') && !p.H.innerHTML.includes('Cannot reach')]);
  st.next = ok(J({state: 'none', sources: [], balance: 0, equity: 0, today: 0, open: 0, trades: []})); await p.run(5);
  OUT.push(['broker disconnected: the Live card goes, samples and the Demo data chip come back', p.H.hidden === true && p.chip.innerHTML.includes('Demo data') && p.chip.className === 'chip demo app-only' && p.eq.style.display === '' && p.stats.style.display === '' && p.openList.style.display === '']);
  p = page(U, {user: U, next: ok(J())}); await p.run(1); p.setNow(1700000000000 + 30000); await p.run(1);
  OUT.push(['"updated 30 s ago" keeps counting between refreshes without asking the server again', p.H.innerHTML.includes('updated 30 s ago') && p.live().length === 1]);
  p = page(U, {user: U, next: ok(J())}); p.vh.on = true; await p.run(31);
  OUT.push(['Home open: asks every 5 seconds (first answer + 6 more)', p.live().length === 7]);
  p = page(U, {user: U, next: ok(J())}); await p.run(31);
  OUT.push(['another tab open: asks only every 20 seconds (first answer + 1 more)', p.live().length === 2]);
  p = page(U, {user: U, next: ok(J())}); p.vb.on = true; await p.run(1); p.document.hidden = true; const n0 = p.live().length; await p.run(15);
  OUT.push(['phone screen off or app in the background: no asking', p.live().length === n0]);
  p.document.hidden = false; p.document.vis(); await tick();
  OUT.push(['coming back to the app refreshes at once', p.live().length === n0 + 1]);
  p = page(U, {user: U, next: ok(J({trades: [{symbol: '<img src=x>', side: 'sell', price: '<b>1</b>', strategy_name: '"><script>x</script>'}], sources: [{name: '<i>MT5', mode: 'demo', online: true}]}))}); await p.run(1);
  OUT.push(['server text is escaped (no HTML injection)', !p.H.innerHTML.includes('<img') && !p.H.innerHTML.includes('<script') && !p.H.innerHTML.includes('<i>') && p.H.innerHTML.includes('&lt;img')]);
  const st2 = {user: U, next: ok(J())}; p = page(U, st2); await p.run(1); st2.user = null; await p.run(1);
  OUT.push(['signing out hides the card and brings back the Demo data chip at once', p.H.hidden === true && p.S.hidden === true && p.chip.innerHTML.includes('Demo data') && p.eq.style.display === '']);
  p = page(U, {user: U, next: ok({state: 'live'})}); await p.run(1);
  OUT.push(['a half-empty answer does not crash or print undefined/NaN', p.H.hidden === false && !/undefined|NaN/.test(p.H.innerHTML + p.S.innerHTML)]);
  const st3 = {user: U, next: ok(J())}; p = page(U, st3); p.vh.on = true; await p.run(1); const was = p.H.innerHTML;
  st3.user = {uid: 'u2', verified: true, active: true, admin: false}; st3.next = () => new Promise(() => {}); await p.run(1);
  OUT.push(['another person signs in on this phone: the first person numbers disappear at once, before the new answer', was.includes('$1,004.70') && p.H.hidden === true && p.S.hidden === true && p.chip.innerHTML.includes('Demo data')]);
  p = page(U, {user: U, next: () => new Promise(() => {})}); p.vh.on = true; await p.run(40);
  OUT.push(['a slow answer is waited for: no pile of requests', p.live().length === 1]);
  p = page({uid: 'x', verified: false}, {user: {uid: 'x', verified: false}, next: ok(J())}); p.mo(); await tick();
  OUT.push(['opening Home or Bot with an unverified email still asks nothing', p.live().length === 0]);
  p = page(U, {user: U, next: ok(J())}); await p.run(1); const n1 = p.live().length; p.mo(); await tick();
  OUT.push(['opening the Home or Bot tab refreshes the numbers at once', p.live().length === n1 + 1]);
  console.log(JSON.stringify(OUT));
})();
'''
if not shutil.which('node'): print('SKIP page checks: node not installed')
else:
    ck = subprocess.run(['node', '-e', 'new Function(require("fs").readFileSync(0,"utf8"))'], input=CODE.encode(), capture_output=True)
    T('the page code parses', ck.returncode == 0)
    p = subprocess.run(['node', '-e', HARNESS, CODE], capture_output=True, text=True)
    try: out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception: out = []; print(p.stdout[-400:], p.stderr[-600:])
    T('the page checks ran', len(out) >= 25)
    for n, ok in out: T(n, ok)
for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
