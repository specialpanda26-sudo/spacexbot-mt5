"""Reset today button (page): the P9A block in static/index.html. Needs node (skipped if missing).
Run: python tests/test_reset6ui.py   No temp files: the block goes to node through a pipe and runs against a fake page and a fake server."""
import os, sys, re, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok)))
m = re.search(r'/\*P9A-start\*/(.*?)/\*P9A-end\*/', html, re.S); CODE = m.group(1) if m else ''
s3 = re.search(r'/\*S3-start\*/(.*?)/\*S3-end\*/', html, re.S); S3 = s3.group(1) if s3 else ''
T('the Reset today code is inside the P9A block, once', CODE.count('function resetRow()') == 1 and CODE.count('function doReset(') == 1 and html.count('function resetRow()') == 1)
T('the Live card says "since reset" when the day was reset', 'D.today_reset ? " since reset" : " today"' in S3)
T('the button only talks to /api/pnl/reset (no other write)', CODE.count('/api/pnl/reset') == 1 and not re.search(r'localStorage|sessionStorage|Math\.random', CODE))
T('only the site colours and components (btn, note), no hard-coded colours', not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsl', CODE) and 'class="btn"' in CODE)
scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
HARNESS = r'''
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), code = P.code, OUT = [], ok = (n, c) => OUT.push([n, !!c]), tick = () => new Promise(r => setTimeout(r, 5));
function bad() { const b = []; P.scripts.forEach((x, i) => { try { new Function(x); } catch (e) { b.push(i); } }); return b; }
function page(st) {
  const timers = [], calls = [], toasts = [];
  const el = () => { const e = {_h: '', hidden: false, className: '', style: {}, on: false, handlers: {}, inserted: [], classList: {contains: c => c === 'on' && e.on},
    insertBefore(n, ref) { e.inserted.push([n, ref]); }, addEventListener(t, f) { e.handlers[t] = f; }};
    Object.defineProperty(e, 'innerHTML', {get: () => e._h, set: v => { e._h = v; }}); return e; };
  const vh = el(), le = el(); le.nextSibling = {after: 'liveempty'};
  const document = {hidden: false, createElement: el, addEventListener() {}, getElementById: id => id === 'view-home' ? vh : id === 'liveempty' ? le : null};
  const SXA = {user: () => st.user, api: (u, o) => { calls.push([u, o || null]); return st.next(u, o); }};
  const MO = function () { this.observe = () => {}; };
  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', code)(document, {SXA, sxToast: m => toasts.push(m)}, SXA, f => timers.push(f), MO);
  const C = vh.inserted[0][0];
  const tap = async (sel, val) => { C.handlers.click({target: {closest: s => s === sel ? {getAttribute: () => val} : null}}); await tick(); };
  return {C, calls, toasts, html: () => C.innerHTML, run: async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } },
    rs: v => tap('[data-rs]', v), pb: v => tap('[data-pb]', v), posts: () => calls.filter(c => c[0] === '/api/pnl/reset').map(c => c[1])};
}
const J = o => Object.assign({today: {pnl: 6, n: 2}, today_reset: null, week: {pnl: 10, n: 4}, total: {pnl: 30, n: 5}, stats: {trades: 5, wins: 3, losses: 2, win_rate: 60, max_drawdown: 4, best: 20, worst: -4},
  curve: [{t: 1, v: 20}, {t: 2, v: 18}, {t: 3, v: 24}, {t: 4, v: 20}, {t: 5, v: 30}], curve_n: 5, brokers: ['Deriv', 'MT5'], broker: '', ts: 1}, o || {});
const AFTER = J({today: {pnl: 0, n: 0}, today_reset: 1700048400});
const U = {uid: 'u1', verified: true, active: true};
const server = (extra) => (u, o) => Promise.resolve(u === '/api/pnl/reset' ? ((o && o.body && o.body.undo) ? J() : AFTER) : J(extra));
(async () => {
  ok('every script in the page still parses', bad().length === 0);
  let p = page({user: U, next: server()}); await p.run(1);
  let h = p.html();
  ok('a normal day: the Reset today button is there and nothing was sent', h.includes('data-rs="ask"') && h.includes('>Reset today</button>') && p.posts().length === 0);
  ok('it says what the button does: starts again from zero, nothing deleted', h.includes("Starts today's count again from zero. Nothing is deleted."));
  ok('the numbers say Today (not Since reset) before a reset', h.includes('<span>Today</span>') && h.includes('2 closed today |') && !h.includes('Since reset'));
  await p.rs('ask'); h = p.html();
  ok('first tap only asks: the button turns into "Tap again to reset today" and still nothing is sent', h.includes('data-rs="go"') && h.includes('Tap again to reset today') && p.posts().length === 0);
  await p.run(3); ok('still waiting for the second tap after 3 seconds', p.html().includes('Tap again to reset today'));
  await p.run(6); h = p.html();
  ok('a forgotten confirm goes back to "Reset today" by itself and sends nothing', h.includes('data-rs="ask"') && !h.includes('Tap again') && p.posts().length === 0);
  await p.rs('ask'); await p.rs('go'); h = p.html();
  ok('second tap sends exactly one POST /api/pnl/reset with the broker picker value (empty = all)', p.posts().length === 1 && JSON.stringify(p.posts()[0]) === JSON.stringify({method: 'POST', body: {broker: ''}}));
  ok('after the reset the card shows the server answer: Since reset $0.00, 0 closed since reset', h.includes('<span>Since reset</span>') && h.includes('<b class="num muted">$0.00</b>') && h.includes('0 closed since reset |'));
  ok('it explains the reset and offers Undo (trades, Journal, 7 days, all time and risk limits are not changed)', h.includes('Today counts from') && h.includes('because you reset it') && h.includes('risk limits are not changed') && h.includes('data-rs="undo"') && h.includes('>Undo reset</button>'));
  ok('the reset button is gone while a reset is active (one button at a time)', !h.includes('>Reset today</button>') && !h.includes('Tap again'));
  ok('the 7-day and all-time numbers are untouched on the card', h.includes('+$10.00') && h.includes('+$30.00') && h.includes('5 in all'));
  ok('a toast says what happened', p.toasts.includes('Today starts again from zero'));
  await p.rs('undo'); h = p.html();
  ok('Undo sends POST {undo: true} and the card is back to Today with the Reset today button', p.posts().length === 2 && p.posts()[1].body.undo === true && h.includes('<span>Today</span>') && h.includes('data-rs="ask"') && p.toasts.includes('Reset undone'));
  // ---- guards ----
  let slow, st = {user: U, next: (u, o) => u === '/api/pnl/reset' ? new Promise(r => { slow = () => r(AFTER); }) : Promise.resolve(J())}; p = page(st); await p.run(1);
  await p.rs('ask'); await p.rs('go'); await p.rs('go'); await p.rs('go');
  ok('while a reset is on its way, more taps send nothing more (one POST)', p.posts().length === 1 && p.html().includes(' disabled'));
  slow(); await tick(); ok('and the button works again after the answer', !p.html().includes(' disabled') && p.html().includes('Undo reset'));
  p = page({user: U, next: (u, o) => u === '/api/pnl/reset' ? Promise.reject(new Error('Could not reach the server')) : Promise.resolve(J())}); await p.run(1);
  await p.rs('ask'); await p.rs('go'); h = p.html();
  ok('a failed reset: the old numbers stay, a toast says why, the button is usable again', h.includes('<span>Today</span>') && h.includes('data-rs="ask"') && !h.includes(' disabled') && p.toasts.includes('Could not reach the server'));
  p = page({user: U, next: server()}); await p.run(1); await p.rs('bogus'); ok('an unknown button value does nothing', p.posts().length === 0);
  p = page({user: U, next: server()}); await p.run(1); await p.pb('Deriv'); await p.rs('ask'); await p.rs('go');
  ok('with the broker picker on Deriv the POST carries broker Deriv', p.posts().length === 1 && p.posts()[0].body.broker === 'Deriv');
  p = page({user: U, next: (u, o) => Promise.resolve(J({total: {pnl: 0, n: 0}}))}); await p.run(1); h = p.html();
  ok('no closed trades at all: no Reset button, just the honest empty message', h.includes('No closed trades yet') && !h.includes('data-rs'));
  p = page({user: U, next: server()}); await p.run(1); await p.run(1);
  p.rs('ask'); ok('the card still renders the picker and the curve with the button (nothing else was lost)', p.html().includes('id="pnlBroker"') && p.html().includes('aria-label="Profit curve"'));
  console.log(JSON.stringify(OUT));
})();
'''
def run():
    r = subprocess.run(['node', '-e', HARNESS], input=json.dumps({'code': CODE, 'scripts': scripts}), capture_output=True, text=True, timeout=120)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: print(r.stdout[-400:], r.stderr[-1200:]); return [['the page harness ran', False]]
for n, ok in run(): T(n, ok)
for n, ok in R: print('PASS' if ok else 'FAIL', n)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
