"""R2 page checks: the Connection check card on the Connect tab and the Your broker chip. The code between /*R2-start*/ and /*R2-end*/ in static/index.html runs here
against a fake page (needs node; skipped without it). Run: python tests/test_conn2ui.py"""
import os, sys, re, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the block is in the page exactly once', html.count('/*R2-start*/') == 1 and html.count('/*R2-end*/') == 1 and 'id="view-connect"' in html and 'class="grid2"' in html)
CODE = re.search(r'/\*R2-start\*/(.*?)/\*R2-end\*/', html, re.S).group(1)
HARNESS = r'''
const code = process.argv[2], OUT = [], tick = () => new Promise(r => setTimeout(r, 5));
function page(u, next) {
  const timers = [], calls = [], chip = {className: 'chip stop', innerHTML: 'Not connected'}, W = {};
  const vc = {on: true, classList: {contains: c => c === 'on' && vc.on}, querySelector: () => chip, insertBefore(n) { vc.card = n; }, firstChild: null};
  const doc = {hidden: false, getElementById: id => id === 'view-connect' ? vc : null, createElement: () => ({hidden: false, innerHTML: '', className: '', style: {}})};
  const SXA = {user: () => u.v, api: (p, o) => { calls.push(p); return next(); }}; W.SXA = SXA;
  const MO = function (f) { this.observe = () => {}; MO.f = f; };
  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', code)(doc, W, SXA, f => timers.push(f), MO);
  return {vc, chip, W, calls, run: async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } }, open: async () => { MO.f(); await tick(); }};
}
const row = (id, state, o) => Object.assign({id, name: id === 'MT5' ? 'MT5 bridge' : id, state, headline: id + ' headline', checks: [], fix: ''}, o || {});
const J = (a, b, msg) => ({state: [a, b].some(r => r.state === 'ok' || r.state === 'stale') ? 'connected' : 'none', message: msg || 'msg', rows: [a, b]});
const U = {uid: 'u', verified: true};
(async () => {
  let p = page({v: null}, () => Promise.resolve(J(row('Deriv', 'none'), row('MT5', 'none'))));
  await p.run(1); OUT.push(['signed out: card hidden, nothing asked', p.vc.card.hidden === true && p.calls.length === 0]);
  p = page({v: {uid: 'u', verified: false}}, () => Promise.resolve(J(row('Deriv', 'none'), row('MT5', 'none'))));
  await p.run(2); OUT.push(['email not verified: nothing asked', p.vc.card.hidden === true && p.calls.length === 0]);
  const bad = row('Deriv', 'problem', {headline: 'Deriv is saved but not connected: token checked.', checks: [{t: 'Token saved', ok: true, d: ''}, {t: 'Token checked', ok: false, d: 'The token is saved but not checked yet. Save it again to check it.'}]});
  p = page({v: U}, () => Promise.resolve(J(bad, row('MT5', 'none'), 'Nothing is connected yet. Deriv is saved but not connected.'))); await p.run(1);
  let h = p.vc.card.innerHTML;
  OUT.push(['signed in: asks GET /api/connections once', p.calls.filter(x => x === '/api/connections').length === 1 && p.vc.card.hidden === false]);
  OUT.push(['not connected: red chip, the message, the failing check with its fix, the OK check marked OK', h.includes('Not connected') && h.includes('Nothing is connected yet') && h.includes('Token checked - needs attention') && h.includes('Save it again to check it.') && h.includes('Token saved - OK')]);
  OUT.push(['the Your broker chip stays Not connected when nothing is up', p.chip.className === 'chip stop']);
  p = page({v: U}, () => Promise.resolve(J(row('Deriv', 'ok', {bot_why: 'Running. Last check went fine.'}), row('MT5', 'none')))); await p.run(1); h = p.vc.card.innerHTML;
  OUT.push(['Deriv connected: green chip, no checklist, the bot note shown', h.includes('chip ok') && !h.includes('needs attention') && h.includes('Running. Last check went fine.')]);
  OUT.push(['the Your broker chip now says Connected - Deriv (it used to look only at MT5)', p.chip.className === 'chip ok' && p.chip.innerHTML.includes('Connected - Deriv')]);
  p = page({v: U}, () => Promise.resolve(J(row('Deriv', 'ok'), row('MT5', 'ok')))); await p.run(1);
  OUT.push(['both connected: chip lists both', p.chip.innerHTML.includes('Deriv + MT5')]);
  p = page({v: U}, () => Promise.resolve(J(row('Deriv', 'stale'), row('MT5', 'none')))); await p.run(1);
  OUT.push(['old numbers: Offline in the warning colour, never Connected', p.chip.className === 'chip watch' && p.chip.innerHTML.includes('Offline - Deriv') && p.vc.card.innerHTML.includes('Offline')]);
  p = page({v: U}, () => Promise.resolve(J(row('Deriv', 'none'), row('MT5', 'ok')))); p.chip.className = 'chip ok'; p.chip.innerHTML = 'Connected MT5'; await p.run(1);
  OUT.push(['a green MT5 chip that was already there is kept as it is', p.chip.innerHTML === 'Connected MT5']);
  p = page({v: U}, () => Promise.resolve(J(row('Deriv', 'problem', {headline: '<img src=x onerror=1>'}), row('MT5', 'none'), '<b>x</b>'))); await p.run(1); h = p.vc.card.innerHTML;
  OUT.push(['text from the server is escaped, never run as HTML', !h.includes('<img') && !h.includes('<b>x') && h.includes('&lt;img')]);
  let down = false, q = page({v: U}, () => down ? Promise.reject(new Error('x')) : Promise.resolve(J(row('Deriv', 'ok'), row('MT5', 'none')))); await q.run(1); down = true; await q.run(8);
  OUT.push(['one failed refresh keeps the last answer', q.vc.card.innerHTML.includes('Connected')]);
  let none = page({v: U}, () => Promise.reject(new Error('x'))); await none.run(1);
  OUT.push(['the very first ask failing says cannot reach the server, never "connected"', none.vc.card.innerHTML.includes('Cannot reach the server') && !none.vc.card.innerHTML.includes('Connected')]);
  p = page({v: U}, () => Promise.resolve(J(row('Deriv', 'ok'), row('MT5', 'none')))); await p.run(1); const n = p.calls.length; p.vc.on = false; await p.run(12);
  OUT.push(['not asked again while the Connect tab is not open', p.calls.length === n]);
  p.vc.on = true; await p.open(); OUT.push(['asked again when the tab opens', p.calls.length === n + 1]);
  console.log(JSON.stringify(OUT));
})();
'''
if subprocess.call(['node', '-v'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    hp = os.path.join(HERE, 'conn2_harness.js'); open(hp, 'w').write(HARNESS)
    o = subprocess.run(['node', hp, CODE], capture_output=True, text=True); os.remove(hp)
    try:
        for n, ok in json.loads(o.stdout.strip().splitlines()[-1]): T('page: ' + n, ok)
    except Exception: T('page harness ran: ' + (o.stderr or o.stdout)[:400], False)
else: print('node missing: page checks skipped')
bad = [n for n, ok in R if not ok]; print('%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
