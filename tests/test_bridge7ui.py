"""Section 7 page checks: the Connect tab block (S7) in static/index.html. Needs node (skipped if missing).
Run: python tests/test_bridge7ui.py   No temp files: the block goes to node through a pipe and runs against a fake page and a fake server."""
import os, sys, re, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok)))
def node(js, data):
    r = subprocess.run(['node', '-e', js], input=json.dumps(data), capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: print(r.stdout[-300:], r.stderr[-800:]); return []

T('the S7 block is in the page exactly once', html.count('/*S7-start*/') == 1 and html.count('/*S7-end*/') == 1)
T('the made-up "No signal ... next build step" message is gone', 'No signal from' not in html and 'next build step' not in html and 'every figure is sample data' not in html)
T('Check connection calls the real check', 'window.sxBridgeCheck){window.sxBridgeCheck();return}' in html)
scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
bad = node("const s=JSON.parse(require('fs').readFileSync(0,'utf8'));const b=[];s.forEach((x,i)=>{try{new Function(x)}catch(e){b.push(i)}});console.log(JSON.stringify(b))", scripts)
T('every script in the page still parses', bad == [])
i = html.index('/*S7-start*/'); BLOCK = html[i:html.index('/*S7-end*/', i)]
JS = r"""
const BLOCK = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
function el(tag) { const e = { tag, hidden: false, className: '', innerHTML: '', textContent: '', attrs: {}, classes: new Set(), parentNode: null, children: [],
  setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k] === undefined ? null : this.attrs[k]; },
  insertBefore(n, ref) { n.parentNode = this; this.children.push(n); }, querySelector() { return this._chip; } };
  e.classList = { contains: c => e.classes.has(c) }; return e; }
function run(withPage, st) {
  const win = { sxToast: m => st.toasts.push(m) }, vc = el('div'), msg = el('p'), chip = el('span'); msg.textContent = 'Pick your broker'; chip.className = 'chip stop'; chip.innerHTML = '<span class="dot"></span>Not connected'; vc._chip = chip; msg.parentNode = el('div');
  const doc = { hidden: false, getElementById: id => withPage ? (id === 'view-connect' ? vc : id === 'connMsg' ? msg : null) : null, createElement: t => el(t) };
  let tick = null; const SXA = { user: () => st.user, api: (p) => { st.calls.push(p); return st.fail ? Promise.reject(new Error('x')) : Promise.resolve(st.data); } };
  new Function('window', 'document', 'SXA', 'setInterval', 'MutationObserver', BLOCK)(win, doc, SXA, f => { tick = f; }, function () { this.observe = () => {}; });
  return { win, vc, msg, chip, tick: async n => { for (let i = 0; i < n; i++) { tick(); await new Promise(r => setImmediate(r)); } } };
}
(async () => {
  const st0 = { toasts: [], calls: [], user: null, data: null, fail: false };
  const A = run(false, st0).win.__sx7;
  ok('pure helpers are exported even without the page', A && typeof A.html === 'function');
  ok('esc blocks tags and quotes', A.esc('<b onclick="x">') === '&lt;b onclick=&quot;x&quot;&gt;');
  ok('ago words', A.ago(3) === 'just now' && A.ago(40) === '40 s ago' && A.ago(600) === '10 min ago' && A.ago(7200) === '2 h ago');
  ok('chip: online demo / online real / offline / never / expired', A.chip({ state: 'online', mode: 'demo' })[1] === 'Bridge online - Demo' && A.chip({ state: 'online', mode: 'real' })[0] === 'ok' && A.chip({ state: 'offline' })[0] === 'watch' && A.chip({ state: 'never' })[0] === 'stop' && A.chip({ state: 'expired' })[1] === 'Plan ended' && A.chip(null)[1] === 'Not connected');
  const evil = A.html({ state: 'online', message: '<img src=x onerror=1>', login: '<script>', mode: 'demo', balance: 12.5, age: 3, bot: false, can_trade: false, why: 'bot off', warn: '<b>w</b>', help: [{ t: '<i>t</i>', d: '"d"' }] });
  ok('html escapes everything that comes from the server', !/<img|<script|<i>|<b>w/.test(evil) && evil.includes('&lt;img'));
  ok('html shows account, mode, balance, last report and the bot line', evil.includes('Demo') && evil.includes('$12.50') && evil.includes('just now') && evil.includes('Not trading: bot off.'));
  const nv = A.html({ state: 'never', message: 'The bridge has not reported yet.', help: [{ t: 'a', d: 'b' }] });
  ok('never reported: no stats row, no made-up numbers, steps shown', !nv.includes('class="stats"') && nv.includes('<ol class="steps">'));
  // wiring
  const st = { toasts: [], calls: [], user: null, data: { state: 'online', message: 'Bridge online. Demo account 55.', login: '55', mode: 'demo', balance: 100, age: 4, bot: true, can_trade: true, warn: '', help: [] }, fail: false };
  const P = run(true, st);
  await P.tick(2);
  ok('signed out: asks to sign in, never calls the server, chip unchanged', P.msg.textContent.includes('Sign in') && st.calls.length === 0 && P.chip.className === 'chip stop');
  st.user = { uid: 'u', verified: false }; await P.tick(2);
  ok('signed in but not verified: asks to verify', P.msg.textContent.includes('Verify your email') && st.calls.length === 0);
  st.user = { uid: 'u', verified: true }; await P.tick(2);
  ok('verified: the real answer replaces the text, chip turns green', P.msg.hidden === true && P.vc.children[0] === undefined && P.msg.parentNode.children[0].hidden === false && P.msg.parentNode.children[0].innerHTML.includes('Demo account 55') && P.chip.className === 'chip ok' && st.calls[0] === '/api/bridge');
  const n0 = st.calls.length; await P.tick(10);
  ok('connect tab closed: no polling in the background', st.calls.length === n0);
  P.vc.classes.add('on'); await P.tick(5);
  ok('connect tab open: polls every 5 s', st.calls.length > n0);
  st.data = { state: 'offline', message: 'The bridge went quiet. Its last report was 10 min ago.', login: '55', mode: 'demo', balance: 100, age: 600, help: [] }; P.vc.classes.add('on'); await P.tick(5);
  ok('went quiet: chip turns amber and the text says so', P.chip.className === 'chip watch' && P.msg.parentNode.children[0].innerHTML.includes('went quiet'));
  st.fail = true; st.calls.length = 0; P.win.sxBridgeCheck(); await new Promise(r => setImmediate(r)); await new Promise(r => setImmediate(r));
  ok('Check connection with the server down: friendly message, no crash', st.calls.length === 1 && P.msg.hidden === false && P.msg.textContent.includes('Cannot reach'));
  st.fail = false; st.data.state = 'online'; st.data.message = 'Bridge online.'; P.win.sxBridgeCheck(); await new Promise(r => setImmediate(r)); await new Promise(r => setImmediate(r));
  ok('Check connection works again and toasts the truth', st.toasts.includes('Bridge is online'));
  st.user = null; await P.tick(2);
  ok('sign out: back to the sign-in text and the original chip', P.msg.hidden === false && P.msg.textContent.includes('Sign in') && P.chip.className === 'chip stop' && P.chip.innerHTML.includes('Not connected'));
  console.log(JSON.stringify(OUT));
})();
"""
out = node(JS, BLOCK)
for n, ok in out: T(n, ok)
T('the node checks ran', len(out) >= 14)
bad = [n for n, ok in R if not ok]
for n in bad: print('FAIL', n)
print('%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
