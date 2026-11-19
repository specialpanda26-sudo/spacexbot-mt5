"""Section 2 checks: the Account card on the Bot tab + the Deriv Demo/Real switch (fake Deriv, no network, no temp files). Run: python tests/test_acct.py
The card's code sits between /*S2-start*/ and /*S2-end*/ in static/index.html and is run here against a fake page (needs node; that part is skipped without it)."""
import os, sys, re, json, glob, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'acct_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, brokers as bk, deriv, links
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
TOK = 'abcDEF1234567890'; A, Bo = 'dev-amy@x.com', 'dev-bob@x.com'
ACC = {'data': [{'account_id': 'VRTC1', 'account_type': 'demo', 'currency': 'USD'}, {'account_id': 'CR9', 'account_type': 'real', 'currency': 'USD'}]}
def http(m, p, t): return (200, ACC) if m == 'GET' else (200, {'data': {'url': 'wss://fake/' + p.split('/')[-2]}})
class FakeWS:
    def __init__(s, url): s.url, s.q = url, []
    def send(s, t):
        m = json.loads(t); s.q.append(json.dumps({'balance': {'balance': 1000.5 if s.url.endswith('VRTC1') else 250.0, 'currency': 'USD'}, 'req_id': m['req_id']}))
    def recv(s): return s.q.pop(0)
    def close(s): pass
made = []
def conn(url): w = FakeWS(url); made.append(w); return w
deriv._http, deriv._connect = http, conn
c.get('/api/me', headers=H('amy@x.com')); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, A)); c.get('/api/me', headers=H('bob@x.com'))
def post(who, name, body): return c.post('/api/brokers/%s/mode' % name, json=body, headers=H(who))
def dv(uid): return [b for b in bk.view(uid) if b['name'] == 'Deriv'][0]

# ---- server: the Deriv Demo/Real route ----
T('no token saved yet -> plain-words 400', (lambda r: r.status_code == 400 and 'token' in r.get_json()['error'])(post('amy@x.com', 'Deriv', {'mode': 'demo'})))
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com')); deriv.verify(A, http, 100, conn)
T('a verified token starts in demo with the demo balance', dv(A)['mode'] == 'demo' and dv(A)['balance'] == 1000.5 and dv(A)['acct_demo'] is True)
T('a bad mode word is refused', post('amy@x.com', 'Deriv', {'mode': 'live'}).status_code == 400)
T('an MT5 broker is refused here (it trades through the MT5 app)', (lambda r: r.status_code == 400 and 'MT5' in r.get_json()['error'])(post('amy@x.com', 'FBS', {'mode': 'real', 'confirm': 'REAL'})))
r = post('amy@x.com', 'Deriv', {'mode': 'real'})
T('Real without typing REAL is refused and nothing changes', r.status_code == 400 and dv(A)['mode'] == 'demo')
r = post('amy@x.com', 'Deriv', {'mode': 'real', 'confirm': 'real'})
T('lowercase "real" is not enough', r.status_code == 400 and dv(A)['mode'] == 'demo')
bk.save(Bo, 'Deriv', {'token': TOK})
T('Real needs an active plan (402)', post('bob@x.com', 'Deriv', {'mode': 'real', 'confirm': 'REAL'}).status_code == 402 and dv(Bo)['mode'] == 'demo')
T('Demo needs no plan', post('bob@x.com', 'Deriv', {'mode': 'demo'}).status_code == 200)
bk.set_bot(A, 'Deriv', True); made.clear()
r = post('amy@x.com', 'Deriv', {'mode': 'real', 'confirm': 'REAL'})
T('Real with REAL works', r.status_code == 200 and dv(A)['mode'] == 'real')
T('the switch stops the bot and says why', dv(A)['bot'] is False and dv(A)['why_code'] == 'bot off')
T('the balance shown is now the real account (the demo one was forgotten)', dv(A)['balance'] == 250.0 and dv(A)['acct_demo'] is False and made and made[-1].url.endswith('CR9'))
bk.set_bot(A, 'Deriv', True)
r = post('amy@x.com', 'Deriv', {'mode': 'demo'})
T('back to Demo: bot stopped again, demo balance back', r.status_code == 200 and dv(A)['mode'] == 'demo' and dv(A)['bot'] is False and dv(A)['balance'] == 1000.5 and dv(A)['acct_demo'] is True)
T('the answer carries the broker list (the app updates from it)', any(b['name'] == 'Deriv' and b['mode'] == 'demo' for b in r.get_json()['brokers']))
def down(*a): raise ConnectionError('Deriv is down')
deriv._http = down; bk.set_bot(A, 'Deriv', True)
post('amy@x.com', 'Deriv', {'mode': 'real', 'confirm': 'REAL'})
T('Deriv unreachable at the switch: no stale demo balance is left under the Real badge', dv(A)['mode'] == 'real' and dv(A).get('balance') is None and dv(A)['bot'] is False)
deriv._http = http; post('amy@x.com', 'Deriv', {'mode': 'demo'}); deriv.refresh(A)

# ---- the bot follows the card's switch ----
yes = lambda u: True; scans = []; scan = lambda s, u: scans.append(s)
links.new_key(A); links.set_mode(A, 'demo')
bk.set_mode(A, 'Deriv', 'real'); bk.set_bot(A, 'Deriv', True); made.clear()
T('card says Real (MT5 link says demo) -> the bot uses the real account', deriv.run_once(A, scan, yes, conn, http, 1700000000) == 'ok' and made[0].url.endswith('CR9') and st.acct(A)['allow_live'] is True)
links.set_mode(A, 'real'); bk.set_mode(A, 'Deriv', 'demo'); bk.set_bot(A, 'Deriv', True); made.clear()
T('card says Demo (MT5 link says real) -> the card wins, demo account', deriv.run_once(A, scan, yes, conn, http, 1700000000) == 'ok' and made[0].url.endswith('VRTC1') and st.acct(A)['allow_live'] is False)
st.x('DELETE FROM kv WHERE k=?', ('mode:%s:Deriv' % A,))
T('switch never used -> the old MT5 link mode still counts (nothing that worked breaks)', bk.mode(A, 'Deriv') == 'real' and dv(A)['mode'] == 'real')
bk.set_mode(A, 'Deriv', 'real'); bk.save(A, 'Deriv', {'token': TOK + 'x'})
T('saving a new token forgets the switch', bk.mode_flag(A, 'Deriv') is None)
bk.set_mode(A, 'Deriv', 'real'); bk.drop(A, 'Deriv')
T('removing the connection forgets the switch', bk.mode_flag(A, 'Deriv') is None)
bk.save(A, 'FBS', {'server': 'FBS-Demo'})
T('an MT5 broker tile still shows demo', [b['mode'] for b in bk.view(A) if b['name'] == 'FBS'] == ['demo'])

# ---- the page: the card code ----
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the card code is in the page exactly once, before the Phone mode card', html.count('/*S2-start*/') == 1 and html.count('/*S2-end*/') == 1 and html.find('/*S2-start*/') < html.find('/* ---- Phone mode card'))
T('the Bot tab has the place it is put in (#view-bot)', 'id="view-bot"' in html)
m = re.search(r'/\*S2-start\*/(.*?)/\*S2-end\*/', html, re.S); CODE = m.group(1) if m else ''
HARNESS = r'''
const code = process.argv[1], OUT = [], tick = () => new Promise(r => setTimeout(r, 5));
function page(user, state) {
  const timers = [], toasts = [], calls = [], rc = {value: ''};
  const el = () => { const e = {innerHTML: '', hidden: false, handlers: {}, classList: {contains: c => c === 'on'}, addEventListener(t, f) { e.handlers[t] = f; }, contains: () => false, insertBefore(n) { e.child = n; }}; return e; };
  const vb = el(), nav = {clicked: 0, click() { nav.clicked++; }};
  const document = {activeElement: null, hidden: false, getElementById: id => id === 'view-bot' ? vb : id === 'acRc' ? rc : null, createElement: el, querySelector: () => nav};
  const SXA = {user: () => user, api: (u, o) => { calls.push({u, o}); return state.api(u, o); }};
  const win = {SXA, sxToast: t => toasts.push(t)};
  new Function('document', 'window', 'SXA', 'setInterval', 'setTimeout', 'MutationObserver', code)(document, win, SXA, f => timers.push(f), () => 0, function () { this.observe = () => {}; });
  const C = vb.child;
  const fire = ds => C.handlers.click({target: {closest: () => ({dataset: ds})}});
  return {C, calls, toasts, nav, rc, fire, tickOnce: () => timers[0](), mode: () => calls.filter(c => /\/mode$/.test(c.u))};
}
const dvo = o => Object.assign({name: 'Deriv', kind: 'token', label: '...abcd', mode: 'demo', status: 'verified', bot: false, balance: 1000.5, currency: 'USD', acct_demo: true}, o || {});
const fbs = {name: 'FBS', kind: 'mt5', label: 'FBS-Demo', mode: 'demo', status: 'saved', bot: false};
function srv(st) { st.api = (u, o) => {
  if (st.fail && o && o.method === 'POST') return Promise.reject(st.fail);
  if (u === '/api/brokers') return Promise.resolve({brokers: st.brokers});
  if (u === '/api/link') return Promise.resolve(st.link || {linked: false});
  if (u === '/api/brokers/Deriv/mode') { const d = st.brokers.filter(b => b.name === 'Deriv')[0]; d.mode = o.body.mode; d.balance = o.body.mode === 'real' ? 250 : 1000.5; return Promise.resolve({brokers: st.brokers}); }
  if (u === '/api/link/mode') { st.link.mode = o.body.mode; return Promise.resolve(st.link); }
  return Promise.resolve({});
}; return st; }
const U = {uid: 'u1', verified: true, active: true, admin: false};
(async () => {
  let p = page(null, srv({brokers: []}));
  OUT.push(['signed out: the card stays hidden', p.C.hidden === true && p.C.innerHTML === '']);
  p = page(U, srv({brokers: []})); p.tickOnce(); await tick();
  OUT.push(['nothing connected: says so and offers to connect (no fake numbers)', p.C.hidden === false && p.C.innerHTML.includes('Not connected') && p.C.innerHTML.includes('samples') && p.C.innerHTML.includes('data-act="cn"')]);
  p.fire({act: 'cn'}); OUT.push(['the Connect a broker button opens the Connect tab', p.nav.clicked === 1]);
  const st = srv({brokers: [dvo()]}); p = page(U, st); p.tickOnce(); await tick();
  let h = p.C.innerHTML;
  OUT.push(['Deriv on demo: Demo badge, balance with currency', h.includes('chip ok') && h.includes('>Demo<') && h.includes('1,000.50 USD')]);
  OUT.push(['Demo button is the pressed one', /data-m="demo" data-r="Deriv" aria-pressed="true"/.test(h) && /data-m="real" data-r="Deriv" aria-pressed="false"/.test(h)]);
  OUT.push(['says that switching stops the bot', h.includes('Switching mode stops the bot')]);
  p.fire({m: 'real', r: 'Deriv'});
  OUT.push(['tapping Real only asks for REAL (nothing sent yet)', p.mode().length === 0 && p.C.innerHTML.includes('Type REAL to confirm') && p.C.innerHTML.includes('you can lose it all')]);
  p.rc.value = 'real'; p.fire({act: 'go'}); await tick();
  OUT.push(['wrong word: error shown, nothing sent', p.mode().length === 0 && p.C.innerHTML.includes('Type REAL in capital letters')]);
  p.rc.value = ' REAL '; p.fire({act: 'go'}); await tick(); await tick();
  const c1 = p.mode()[0];
  OUT.push(['REAL typed: posts mode real with the confirm word to the Deriv route', c1 && c1.u === '/api/brokers/Deriv/mode' && c1.o.method === 'POST' && c1.o.body.mode === 'real' && c1.o.body.confirm === 'REAL']);
  h = p.C.innerHTML;
  OUT.push(['then shows the Real badge, the real balance, a toast that the bot stopped', h.includes('chip stop') && h.includes('>Real<') && h.includes('250.00 USD') && !h.includes('Type REAL to confirm') && p.toasts.includes('Real mode on. Bot stopped.')]);
  p.fire({m: 'demo', r: 'Deriv'}); await tick(); await tick();
  const c2 = p.mode()[1];
  OUT.push(['back to Demo: posts mode demo with no confirm word', c2 && c2.o.body.mode === 'demo' && !('confirm' in c2.o.body) && p.C.innerHTML.includes('chip ok') && p.toasts.includes('Demo mode on. Bot stopped.')]);
  p.fire({m: 'demo', r: 'Deriv'}); await tick();
  OUT.push(['tapping the mode already on does nothing', p.mode().length === 2]);
  p.fire({m: 'real', r: 'Deriv'}); p.fire({act: 'no'});
  OUT.push(['Cancel closes the REAL box without sending', !p.C.innerHTML.includes('Type REAL to confirm') && p.mode().length === 2]);
  st.fail = {status: 402, message: 'subscription required'}; p.fire({m: 'real', r: 'Deriv'}); p.rc.value = 'REAL'; p.fire({act: 'go'}); await tick(); await tick();
  OUT.push(['no plan (402): plain words, mode unchanged on screen', p.C.innerHTML.includes('A plan is needed for Real mode.') && p.C.innerHTML.includes('>Demo<')]);
  p = page(U, srv({brokers: [dvo({status: 'saved', balance: undefined})]})); p.tickOnce(); await tick();
  OUT.push(['token not checked: no switch, tells you to check it', !p.C.innerHTML.includes('data-m=') && p.C.innerHTML.includes('Save your Deriv token again')]);
  p = page(U, srv({brokers: [dvo({balance: null})]})); p.tickOnce(); await tick();
  OUT.push(['balance not read yet is said in words, not shown as 0', p.C.innerHTML.includes('Balance not read yet') && !p.C.innerHTML.includes('0.00')]);
  p = page(U, srv({brokers: [fbs]})); p.tickOnce(); await tick();
  OUT.push(['MT5 broker without a key: marked "Needs MT5 app", no switch, no balance', p.C.innerHTML.includes('Needs MT5 app') && !p.C.innerHTML.includes('data-m=') && !p.C.innerHTML.includes('Balance')]);
  const s3 = srv({brokers: [fbs, dvo()], link: {linked: true, mode: 'demo', bot: false, online: true, balance: 520.25, equity: 520.25}}); p = page(U, s3); p.tickOnce(); await tick();
  h = p.C.innerHTML;
  OUT.push(['MT5 with a key: one MT5 row named after the broker, with its balance; Deriv row too', h.includes('MT5 (FBS)') && h.includes('520.25') && h.includes('1,000.50 USD') && (h.match(/class="seg"/g) || []).length === 2]);
  p.fire({m: 'real', r: 'MT5'}); OUT.push(['MT5 Real box warns about AllowLive', p.C.innerHTML.includes('AllowLive')]);
  p.rc.value = 'REAL'; p.fire({act: 'go'}); await tick(); await tick();
  const c3 = p.calls.filter(c => c.u === '/api/link/mode')[0];
  OUT.push(['MT5 switch uses the existing MT5 route', c3 && c3.o.body.mode === 'real' && c3.o.body.confirm === 'REAL' && p.C.innerHTML.includes('chip stop')]);
  p = page({uid: 'a', verified: true, active: true, admin: true}, srv({brokers: [dvo()]})); p.tickOnce(); await tick();
  OUT.push(['owner (admin): no MT5 link asked for, Deriv still shown', !p.calls.some(c => c.u === '/api/link') && p.C.innerHTML.includes('1,000.50 USD')]);
  p = page(U, srv({brokers: [dvo({currency: '<img src=x>'}), Object.assign({}, fbs, {name: '<i>FBS'})]})); p.tickOnce(); await tick();
  OUT.push(['server text is escaped (no HTML injection)', !p.C.innerHTML.includes('<img') && p.C.innerHTML.includes('&lt;img') && !p.C.innerHTML.includes('<i>') && p.C.innerHTML.includes('&lt;i&gt;FBS')]);
  p = page({uid: 'u', verified: false}, srv({brokers: [dvo()]})); p.tickOnce(); await tick();
  OUT.push(['unverified email: card hidden', p.C.hidden === true]);
  console.log(JSON.stringify(OUT));
})();
'''
if not shutil.which('node'): print('SKIP page checks: node not installed')
else:
    ck = subprocess.run(['node', '-e', 'new Function(require("fs").readFileSync(0,"utf8"))'], input=CODE.encode(), capture_output=True)
    T('the card code parses', ck.returncode == 0)
    p = subprocess.run(['node', '-e', HARNESS, CODE], capture_output=True, text=True)
    try: out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception: out = []; print(p.stdout[-400:], p.stderr[-600:])
    T('the page checks ran', len(out) >= 20)
    for n, ok in out: T(n, ok)
for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
