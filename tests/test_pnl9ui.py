"""Section 9A page checks: the Profit and loss card on Home (the P9A block in static/index.html). Needs node (skipped if missing).
Run: python tests/test_pnl9ui.py   No temp files: the block goes to node through a pipe and runs against a fake page and a fake server."""
import os, sys, re, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok)))
m = re.search(r'/\*P9A-start\*/(.*?)/\*P9A-end\*/', html, re.S); CODE = m.group(1) if m else ''
T('the P9A block is in the page exactly once, after the Live card (S3)', html.count('/*P9A-start*/') == 1 and html.count('/*P9A-end*/') == 1 and html.find('/*S3-end*/') < html.find('/*P9A-start*/'))
T('the places it uses exist (Home, the Live card slot)', 'id="view-home"' in html and 'liveempty' in html)
T('no made-up numbers in the block (no random, no sample data, no stored copy of old numbers)', not re.search(r'Math\.random|sample|HIST|localStorage|sessionStorage', CODE))
T('only the site colours (CSS variables), no hard-coded colours', not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsl', CODE) and 'var(--good)' in CODE and 'var(--bad)' in CODE)
scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
HARNESS = r'''
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), code = P.code, OUT = [], ok = (n, c) => OUT.push([n, !!c]), tick = () => new Promise(r => setTimeout(r, 5));
function bad() { const b = []; P.scripts.forEach((x, i) => { try { new Function(x); } catch (e) { b.push(i); } }); return b; }
function page(st) {
  const timers = [], calls = [];
  const el = () => { const e = {_h: '', _n: 0, hidden: false, className: '', style: {}, on: false, handlers: {}, inserted: [], classList: {contains: c => c === 'on' && e.on},
    insertBefore(n, ref) { e.inserted.push([n, ref]); }, addEventListener(t, f) { e.handlers[t] = f; }};
    Object.defineProperty(e, 'innerHTML', {get: () => e._h, set: v => { e._h = v; e._n++; }}); return e; };
  const vh = el(), le = el(); le.nextSibling = {after: 'liveempty'};
  const document = {hidden: false, createElement: el, addEventListener(t, f) { document.vis = f; }, getElementById: id => id === 'view-home' ? vh : id === 'liveempty' ? le : null};
  const SXA = {user: () => st.user, api: (u, o) => { calls.push(u); return st.next(u); }};
  const MO = function (f) { MO.f = f; this.observe = () => {}; };
  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', code)(document, {SXA}, SXA, f => timers.push(f), MO);
  const C = vh.inserted[0][0];
  return {C, vh, le, document, calls, at: vh.inserted[0][1], html: () => C.innerHTML, run: async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } }, mo: async () => { MO.f(); await tick(); },
    pick: async b => { C.handlers.click({target: {closest: () => b === null ? null : {getAttribute: () => b}}}); await tick(); }, pnl: () => calls.filter(u => u.startsWith('/api/pnl'))};
}
const J = o => Object.assign({today: {pnl: 6, n: 2}, week: {pnl: 10, n: 4}, total: {pnl: 30, n: 5}, stats: {trades: 5, wins: 3, losses: 2, win_rate: 60, max_drawdown: 4, best: 20, worst: -4},
  curve: [{t: 1, v: 20}, {t: 2, v: 18}, {t: 3, v: 24}, {t: 4, v: 20}, {t: 5, v: 30}], curve_n: 5, brokers: ['Deriv', 'MT5'], broker: '', ts: 1}, o || {});
const U = {uid: 'u1', verified: true, active: true}, V = {uid: 'u2', verified: true, active: true}, okp = j => () => Promise.resolve(j);
(async () => {
  ok('every script in the page still parses', bad().length === 0);
  let p = page({user: null, next: okp(J())}); await p.run(3);
  ok('signed out: the card is hidden, empty, and nothing is asked', p.C.hidden === true && p.C.style.display === 'none' && p.html() === '' && p.pnl().length === 0);
  p = page({user: {uid: 'x', verified: false}, next: okp(J())}); await p.run(20);
  ok('email not verified: hidden, nothing asked', p.C.hidden === true && p.pnl().length === 0);
  p = page({user: U, next: okp(J())});
  ok('the card sits on Home right after the Live card slot', p.at === p.le.nextSibling && p.C.id === 'pnlc' && p.C.className === 'card');
  let st = {user: U, next: okp(J())}; p = page(st); p.vh.on = true; await p.run(1);
  let h = p.html();
  ok('signed in and verified: the card is shown and asks /api/pnl once, with no broker in the question', p.C.hidden === false && p.C.style.display === '' && p.pnl().length === 1 && p.pnl()[0] === '/api/pnl');
  ok('title and the four numbers: Today, Last 7 days, All time, Win rate', h.includes('<h2>Profit and loss</h2>') && h.includes('<span>Today</span>') && h.includes('<span>Last 7 days</span>') && h.includes('<span>All time</span>') && h.includes('<span>Win rate</span>'));
  ok('amounts are in dollars with a plus sign and the good colour', h.includes('<b class="num good">+$6.00</b>') && h.includes('<b class="num good">+$10.00</b>') && h.includes('<b class="num good">+$30.00</b>'));
  ok('win rate is a plain percentage', h.includes('<b class="num">60%</b>'));
  ok('the note counts trades today, in 7 days, in all, won, lost and the biggest drop', h.includes('2 closed today | 4 in 7 days | 5 in all, 3 won, 2 lost | biggest drop $4.00'));
  const path = (h.match(/<path d="([^"]+)"/) || [])[1] || '';
  ok('the curve is a line that starts at zero and has one point per trade (M + 5 L)', h.includes('<svg viewBox="0 0 300 110" role="img" aria-label="Profit curve">') && path.startsWith('M8.0 102.0') && (path.match(/L/g) || []).length === 5);
  ok('the curve ends on the all-time number at the top (best point = top edge)', path.endsWith('L292.0 8.0'));
  ok('a profitable curve is drawn in the good colour', h.includes('stroke-linejoin="round" style="stroke:var(--good)"'));
  ok('says the curve is profit only, not the account balance', h.includes('Profit since your first trade (5 trades): +$30.00. This is profit only, not your account balance.'));
  ok('two brokers: the picker shows All brokers + each broker, "All" pressed', h.includes('id="pnlBroker"') && h.includes('data-pb="" aria-pressed="true">All brokers') && h.includes('data-pb="Deriv" aria-pressed="false">Deriv') && h.includes('data-pb="MT5"'));
  // ---- losses, rounding, dashes ----
  st.next = okp(J({today: {pnl: -3.1, n: 1}, week: {pnl: -0.004, n: 2}, total: {pnl: -8, n: 5}, curve: [{t: 1, v: -3}, {t: 2, v: 4}, {t: 3, v: -8}]})); await p.mo(); h = p.html();
  ok('a losing amount: minus sign, bad colour', h.includes('<b class="num bad">-$3.10</b>') && h.includes('<b class="num bad">-$8.00</b>'));
  ok('a tiny loss that rounds to zero shows $0.00 in the muted colour, never -$0.00', h.includes('<b class="num muted">$0.00</b>') && !h.includes('-$0.00'));
  ok('a losing curve is drawn in the bad colour', h.includes('style="stroke:var(--bad)"'));
  ok('a curve that crosses zero gets a dashed zero line', h.includes('stroke-dasharray="3 3" style="stroke:var(--line)"'));
  st.next = okp(J({today: {pnl: 1234.5, n: 1}})); await p.mo(); ok('big amounts get thousands commas', p.html().includes('+$1,234.50'));
  st.next = okp(J({stats: {trades: 5, wins: 2, losses: 3, win_rate: 66.7, max_drawdown: 0}})); await p.mo(); h = p.html();
  ok('win rate keeps one decimal (66.7%); no biggest-drop text when there was no drop', h.includes('66.7%') && !h.includes('biggest drop'));
  // ---- few / no trades ----
  st.next = okp(J({total: {pnl: 4, n: 1}, curve: [{t: 1, v: 4}], curve_n: 1, brokers: ['MT5']})); await p.mo(); h = p.html();
  ok('one trade: the numbers show, no curve, and it says a curve needs at least 2 trades', h.includes('+$4.00') && !h.includes('<svg') && h.includes('The profit curve needs at least 2 closed trades.'));
  ok('one broker only: no picker', !h.includes('pnlBroker'));
  st.next = okp(J({curve_n: 1})); await p.mo(); ok('the count of trades from the server decides: it says 1 trade, so no curve even if points came along', !p.html().includes('<svg') && p.html().includes('at least 2 closed trades'));
  st.next = okp(J({curve: [], curve_n: 5})); await p.mo(); ok('a missing curve with 5 trades does not break the card: numbers show, no curve', p.html().includes('+$30.00') && !p.html().includes('<svg') && p.html().includes('at least 2 closed trades'));
  st.next = okp(J({today: {pnl: 0, n: 0}, week: {pnl: 0, n: 0}, total: {pnl: 0, n: 0}, stats: {}, curve: [], curve_n: 0, brokers: []})); await p.mo(); h = p.html();
  ok('no trades: "No closed trades yet", no numbers, no curve, nothing invented', h.includes('No closed trades yet') && !h.includes('class="stats"') && !h.includes('<svg') && h.includes('Nothing on this card is invented.'));
  st.next = okp({}); await p.mo(); ok('an empty answer from the server does not break the card', p.html().includes('No closed trades yet'));
  // ---- escaping ----
  st.next = okp(J({brokers: ['<img src=x onerror=1>', 'MT5'], broker: ''})); await p.mo(); h = p.html();
  ok('broker names from the server are escaped (no HTML injection)', !h.includes('<img') && h.includes('&lt;img src=x onerror=1&gt;') && h.includes('data-pb="&lt;img'));
  // ---- the picker ----
  st = {user: U, next: okp(J())}; p = page(st); p.vh.on = true; await p.run(1);
  st.next = okp(J({broker: 'Deriv', total: {pnl: 18, n: 2}})); await p.pick('Deriv');
  ok('picking Deriv asks /api/pnl?broker=Deriv and shows that broker pressed', p.pnl()[1] === '/api/pnl?broker=Deriv' && /data-pb="Deriv" aria-pressed="true"/.test(p.html()) && /data-pb="" aria-pressed="false"/.test(p.html()));
  st.next = okp(J()); await p.pick(''); ok('picking All brokers asks with no broker again', p.pnl()[2] === '/api/pnl' && /data-pb="" aria-pressed="true"/.test(p.html()));
  const n0 = p.pnl().length; await p.pick(null); ok('a click that is not on a picker button does nothing', p.pnl().length === n0);
  let res; st = {user: U, next: () => new Promise(r => { res = r; })}; p = page(st); p.vh.on = true; await p.run(1);
  ok('while the first answer is loading the card says Loading, shows no numbers', p.html().includes('Loading your profit and loss...') && !p.html().includes('class="stats"'));
  await p.pick('Deriv'); ok('picking while loading does not fire a second request yet', p.pnl().length === 1);
  st.next = okp(J({broker: 'Deriv', total: {pnl: 18, n: 2}})); res(J({broker: ''})); await tick(); await tick();
  ok('the old answer for "All" is thrown away, and the Deriv question is asked next', p.pnl().length === 2 && p.pnl()[1] === '/api/pnl?broker=Deriv' && /aria-pressed="true">Deriv/.test(p.html()));
  // ---- polling ----
  st = {user: U, next: okp(J())}; p = page(st); p.vh.on = true; await p.run(1); await p.run(13);
  ok('Home open: no new question before 15 seconds', p.pnl().length === 1);
  await p.run(1); ok('Home open: asks again at 15 seconds', p.pnl().length === 2);
  await p.run(15); ok('...and every 15 seconds', p.pnl().length === 3);
  p.vh.on = false; await p.run(30); ok('Home closed: stops asking', p.pnl().length === 3);
  p.vh.on = true; p.document.hidden = true; await p.run(30); ok('page hidden: stops asking', p.pnl().length === 3);
  await p.mo(); ok('page hidden: even an on-screen change asks nothing', p.pnl().length === 3);
  p.document.hidden = false; p.document.vis(); await tick(); ok('coming back to the page asks right away', p.pnl().length === 4);
  p.vh.on = false; await p.mo(); ok('Home not on screen: a class change asks nothing', p.pnl().length === 4);
  p.vh.on = true; await p.mo(); ok('opening Home asks right away', p.pnl().length === 5);
  // ---- no repaint when nothing changed ----
  const w0 = p.C._n; await p.mo(); await p.mo(); ok('the same numbers again do not rewrite the card (no flicker, taps are kept)', p.C._n === w0);
  // ---- errors ----
  st = {user: U, next: () => Promise.reject(new Error('x'))}; p = page(st); p.vh.on = true; await p.run(1);
  ok('cannot load and nothing to show yet: says so in plain words', p.html().includes('Cannot load your profit and loss') && !p.html().includes('class="stats"'));
  st.next = okp(J()); await p.mo(); ok('then it recovers by itself', p.html().includes('+$30.00') && !p.html().includes('Cannot load'));
  st.next = () => Promise.reject(new Error('x')); await p.mo(); await p.mo(); ok('one or two failures: the last numbers stay, no warning yet', p.html().includes('+$30.00') && !p.html().includes('last numbers we saw'));
  await p.mo(); ok('three failures in a row: the last numbers stay with a plain warning', p.html().includes('+$30.00') && p.html().includes('Cannot reach the server. These are the last numbers we saw.'));
  // ---- people ----
  st = {user: U, next: okp(J())}; p = page(st); p.vh.on = true; await p.run(1); st.next = okp(J({broker: 'Deriv'})); await p.pick('Deriv');
  st.user = V; st.next = okp(J({total: {pnl: 7, n: 3}})); await p.run(1);
  ok('another person signs in: their own question, no broker carried over, no numbers of the first person', p.pnl()[p.pnl().length - 1] === '/api/pnl' && p.html().includes('+$7.00') && !p.html().includes('+$30.00'));
  st.user = null; await p.run(1); ok('signing out clears the card and hides it', p.C.hidden === true && p.html() === '');
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
