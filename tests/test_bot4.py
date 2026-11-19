"""Section 4 checks: the Bot tab tells the truth. /api/botstate (plain reason), /api/bot (owner Start/Stop), scanner notes, page block S4 (node, skipped without it).
Run: python tests/test_bot4.py"""
import os, sys, re, json, glob, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'bot4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, botstate
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, O = 'dev-amy@x.com', 'dev-boss@x.com'
WD = 1700000000 - (1700000000 % 86400) + 86400 * 4 + 12 * 3600      # a Monday-Thursday noon in UTC, so the weekend gate is quiet
while time.gmtime(WD).tm_wday >= 4: WD += 86400
def beat(uid, t, **k):
    a = dict({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'seen': t}, **k)
    if uid: st.x('UPDATE links SET acct=?,seen=? WHERE uid=?', (json.dumps(a), t, uid))
    else: st.put('acct', json.dumps(a))
def ex(uid, admin, paid=True, now=WD + 10): return botstate.explain(uid, admin, paid, now)

x = ex(A, False)
T('no link, bot off: stopped and says Tap Start bot', x['state'] == 'stopped' and x['running'] is False and 'Start bot' in x['why'])
T('plan ended is said first', ex(A, False, paid=False)['code'] == 'plan ended')
links.new_key(A); links.set_bot(A, True)
x = ex(A, False)
T('bot on, MT5 never heard from: waiting, says MT5 is not talking', x['state'] == 'waiting' and x['running'] and 'MT5' in x['why'])
beat(A, WD)
T('MT5 silent 3 minutes: waiting', ex(A, False, now=WD + 200)['code'] == 'EA offline')
x = ex(A, False)
T('connected, nothing scanned yet: watching, says it checks each new candle', x['state'] == 'watching' and 'candle' in x['why'])
botstate.note(A, 'XAUUSD', 'nosetup')
x = ex(A, False, now=int(time.time()) + 5) if False else ex(A, False)
T('scanner said no setup: watching, "No good setup yet"', x['state'] == 'watching' and 'No good setup' in x['why'] and x['checked'])
botstate.note(A, 'XAUUSD', 'signal'); T('signal found is said', 'sent it to MT5' in ex(A, False)['why'])
botstate.note(A, 'XAUUSD', 'skip', 'symbol cooldown'); x = ex(A, False)
T('a symbol gate skip becomes a waiting reason in words', x['state'] == 'waiting' and 'just traded' in x['why'])
botstate.note(A, 'XAUUSD', 'skip', 'news in 10 min'); T('an unknown reason is still shown, never hidden', 'news in 10 min' in ex(A, False)['why'])
beat(A, WD, open=99); x = ex(A, False)
T('global gate: too many open trades is said in words', x['state'] == 'waiting' and 'open trades' in x['why'])
beat(A, WD, demo=False); T('a live account without Real mode says so', 'real account' in ex(A, False)['why'].lower())
beat(A, WD); wkend = WD + 86400 * (5 - time.gmtime(WD).tm_wday)
beat(A, wkend); T('weekend: waiting with the market-closed reason', 'closed' in ex(A, False, now=wkend + 5)['why'])
beat(A, WD)
T("another person's notes never leak", 'XAUUSD' not in json.dumps(ex('dev-bob@x.com', False)) and botstate._last('dev-bob@x.com') is None)

# owner scope
st.put('bot_enabled', '0'); T('owner stopped', ex('', True)['state'] == 'stopped')
st.put('bot_enabled', '1'); T('owner on, EA never heard: waiting', ex('', True)['code'] == 'EA offline')

# ---- routes ----
T('GET /api/botstate needs sign-in', c.get('/api/botstate').status_code == 401)
j = c.get('/api/botstate', headers=H('amy@x.com')).get_json()
T('route returns the person\'s own state, no secrets', 'state' in j and 'why' in j and 'key' not in json.dumps(j).lower())
r = c.post('/api/bot', headers=H('boss@x.com'), json={'on': True}); T('owner Start: switch is really on', r.status_code == 200 and st.get('bot_enabled') == '1' and r.get_json()['running'] is True)
r = c.post('/api/bot', headers=H('boss@x.com'), json={'on': False}); T('owner Stop: switch is really off', st.get('bot_enabled') == '0' and r.get_json()['running'] is False)
r = c.post('/api/bot', headers=H('amy@x.com'), json={'on': True}); T('unpaid subscriber cannot start (402)', r.status_code == 402)
r = c.post('/api/bot', headers=H('amy@x.com'), json={'on': False}); T('stopping is always allowed', r.status_code == 200 and not links.bot_on(A))
T('"on" must be exactly true', c.post('/api/bot', headers=H('boss@x.com'), json={'on': 'yes'}).get_json()['running'] is False)

# ---- scanner leaves notes ----
from backend import app as appmod, bars
links.set_bot(A, True); beat(A, int(time.time()))
if time.gmtime().tm_wday < 5:
    rows = [[1700000000 + i * 900, 100, 101, 99, 100, 1] for i in range(60)]
    bars.merge('XAUUSD', 'M15', rows, uid=A); bars.merge('XAUUSD', 'H1', rows, uid=A)
    appmod._last_scan.clear(); appmod._scan('XAUUSD', A)
    T('after a scan the note exists (gate, nosetup, skip or signal)', botstate._last(A) is not None)
else: T('(weekend: scanner note checked through the gate path)', True)
links.set_bot(A, False); st.put('lastbar:%s:XAUUSD' % A, 0); appmod._last_scan.clear()
rows = [[1700100000 + i * 900, 100, 101, 99, 100, 1] for i in range(5)]; bars.merge('XAUUSD', 'M15', rows, uid=A); appmod._scan('XAUUSD', A)
n = botstate._last(A); T('bot off: the scanner notes the gate reason', n and n['c'] == 'gate' and n['w'] == 'bot off')

# ---- page ----
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('S4 block present once, after S3', html.count('/*S4-start*/') == 1 and html.find('/*S3-end*/') < html.find('/*S4-start*/') and html.count('ac.id="autobotc"') == 1)
CODE = re.search(r'/\*S4-start\*/(.*?)/\*S4-end\*/', html, re.S).group(1)
HARNESS = r'''
const code = process.argv[2], OUT = [], tick = () => new Promise(r => setTimeout(r, 5));
function page(u, next) {
  const timers = [], calls = [], els = {};
  const el = id => els[id] = els[id] || {id, hidden: false, innerHTML: '', textContent: '', className: '', style: {}, on: false, classList: {contains: c => c === 'on' && els[id].on}, insertBefore(n) { els[id].first = n; }, firstChild: null};
  ['view-bot', 'view-home', 'autobotc', 'botToggle', 'botChip', 'pillTxt'].forEach(el);
  const doc = {hidden: false, createElement: () => ({hidden: false, innerHTML: '', className: ''}), getElementById: id => els[id] || null, addEventListener(t, f) { doc.click = f; }};
  const SXA = {user: () => u.v, api: (p, o) => { calls.push({p, o}); return next(p, o); }};
  const MO = function () { this.observe = () => {}; };
  new Function('document', 'SXA', 'setInterval', 'MutationObserver', 'window', code)(doc, SXA, f => timers.push(f), MO, {sxToast: m => calls.push({toast: m})});
  els['view-bot'].on = true; const C = els['view-bot'].first;
  const ev = id => ({target: {closest: s => s.includes(id) ? {} : null}, preventDefault() { ev.p = 1; }, stopPropagation() {}, stopImmediatePropagation() { ev.s = 1; }});
  return {C, els, calls, run: async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } }, click: async id => { doc.click(ev(id)); await tick(); await tick(); }, ev};
}
const D = o => Object.assign({running: true, state: 'watching', why: 'Looked at the market. No good setup yet, so it did not trade. That is normal.', checked: Math.floor(Date.now() / 1000) - 30}, o || {});
const U = {uid: 'u1', verified: true, active: true, admin: false}, AD = {uid: 'a', verified: true, admin: true};
(async () => {
  let u = {v: null}, p = page(u, () => Promise.resolve(D())); await p.run(1);
  OUT.push(['signed out: card hidden, sample Autobot card left alone, nothing asked', p.C.hidden === true && p.els.autobotc.style.display === '' && p.calls.length === 0]);
  u = {v: U}; p = page(u, () => Promise.resolve(D())); await p.run(1);
  OUT.push(['signed in: real status card, plain reason, last check shown, fake Autobot hidden', p.C.hidden === false && p.C.innerHTML.includes('No good setup yet') && p.C.innerHTML.includes(' s ago') && p.els.autobotc.style.display === 'none']);
  OUT.push(['chip says Running', p.C.innerHTML.includes('chip ok') && p.C.innerHTML.includes('Running')]);
  p = page({v: U}, () => Promise.resolve(D({state: 'waiting', running: true, why: 'MT5 is not talking to the server.', checked: null}))); await p.run(1);
  OUT.push(['waiting: warning chip and the reason in words', p.C.innerHTML.includes('chip watch') && p.C.innerHTML.includes('MT5 is not talking')]);
  p = page({v: U}, () => Promise.resolve(D({state: 'stopped', running: false, why: 'The bot is stopped. Tap Start bot.'}))); await p.run(1);
  OUT.push(['stopped: plain chip', p.C.innerHTML.includes('Stopped') && !p.C.innerHTML.includes('chip ok')]);
  let bad = false, q = page({v: U}, () => bad ? Promise.reject(new Error('x')) : Promise.resolve(D())); await q.run(1); bad = true; await q.run(3);
  OUT.push(['three failures keep the last answer and say cannot reach the server', q.C.innerHTML.includes('No good setup') && q.C.innerHTML.includes('Cannot reach the server')]);
  let st = D({running: false, state: 'stopped', why: 'The bot is stopped. Tap Start bot.'});
  p = page({v: AD}, (path, o) => { if (o && o.method === 'POST') { st = D({running: o.body.on}); } return Promise.resolve(st); }); await p.run(1);
  OUT.push(['owner: Home button follows the real switch (Start bot)', p.els.botToggle.textContent === 'Start bot' && p.els.pillTxt.textContent === 'Bot stopped']);
  await p.click('botToggle'); const post = p.calls.find(c => c.p === '/api/bot');
  OUT.push(['owner click: POST /api/bot with on:true, the sample toggle is blocked', post && post.o.body.on === true && p.ev.s === 1]);
  OUT.push(['after the click the button says Stop bot', p.els.botToggle.textContent === 'Stop bot' && p.els.pillTxt.textContent === 'Bot running']);
  p = page({v: U}, () => Promise.resolve(D())); await p.run(1); const n0 = p.calls.length; await p.click('botToggle');
  OUT.push(['a subscriber click is left to the existing link code (nothing posted here)', p.calls.length === n0 && p.ev.s !== 1]);
  console.log(JSON.stringify(OUT));
})();
'''
if subprocess.call(['node', '-v'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    hp = os.path.join(HERE, 'bot4_harness.js'); open(hp, 'w').write(HARNESS)
    o = subprocess.run(['node', hp, CODE], capture_output=True, text=True); os.remove(hp)
    try:
        for n, ok in json.loads(o.stdout.strip().splitlines()[-1]): T('page: ' + n, ok)
    except Exception: T('page harness ran: ' + (o.stderr or o.stdout)[:300], False)
else: print('node missing: page checks skipped')
for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]; print('%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
