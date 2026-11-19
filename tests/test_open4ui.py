"""R4 page checks: the "Positions at once" card on the Bot tab. The code between /*R4-start*/ and /*R4-end*/ in static/index.html runs against a fake page (needs node;
skipped without it). Run: python tests/test_open4ui.py"""
import os, sys, re, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the block is in the page exactly once, after the Bot status block', html.count('/*R4-start*/') == 1 and html.count('/*R4-end*/') == 1 and html.find('/*S4-end*/') < html.find('/*R4-start*/') and 'id="view-bot"' in html)
CODE = re.search(r'/\*R4-start\*/(.*?)/\*R4-end\*/', html, re.S).group(1)
HARNESS = r'''
const code = process.argv[2], OUT = [], tick = () => new Promise(r => setTimeout(r, 5));
function page(u, api) {
  const timers = [], calls = [], toasts = [], W = {sxToast: m => toasts.push(m)};
  const card = {hidden: false, innerHTML: '', className: '', style: {}, handlers: {}, addEventListener(t, f) { card.handlers[t] = f; }};
  const vb = {on: true, classList: {contains: c => c === 'on' && vb.on}, insertBefore(n) { vb.card = n; }, firstChild: null};
  const doc = {hidden: false, getElementById: id => id === 'view-bot' ? vb : null, createElement: () => card};
  const SXA = {user: () => u.v, api: (p, o) => { calls.push({p, o}); return api(p, o); }}; W.SXA = SXA;
  const MO = function (f) { this.observe = () => {}; MO.f = f; };
  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', code)(doc, W, SXA, f => timers.push(f), MO);
  const click = async n => { card.handlers.click({target: {closest: () => n === null ? null : {dataset: {mo: String(n)}}}}); await tick(); await tick(); };
  return {card, vb, calls, toasts, click, run: async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } }, open: async () => { MO.f(); await tick(); }};
}
const LIM = o => Object.assign({max_open: 0, max_open_now: 3, max_open_default: 3, max_open_ceiling: 6}, o || {});
const mk = (lim, live) => (p, o) => p === '/api/limits' ? (o && o.method === 'POST' ? Promise.resolve(Object.assign(lim, {max_open: o.body.max_open, max_open_now: o.body.max_open || lim.max_open_default})) : Promise.resolve(lim)) : Promise.resolve({open: live});
const U = {uid: 'u', verified: true};
(async () => {
  let p = page({v: null}, mk(LIM(), 1)); await p.run(1);
  OUT.push(['signed out: card hidden, nothing asked', p.card.hidden === true && p.calls.length === 0]);
  p = page({v: {uid: 'u', verified: false}}, mk(LIM(), 1)); await p.run(2);
  OUT.push(['email not verified: nothing asked', p.card.hidden === true && p.calls.length === 0]);
  p = page({v: U}, mk(LIM(), 2)); await p.run(1); let h = p.card.innerHTML;
  OUT.push(['signed in: asks the limits and the live numbers', p.calls.some(c => c.p === '/api/limits') && p.calls.some(c => c.p === '/api/live') && p.card.hidden === false]);
  OUT.push(['buttons: Default (3) and 1 to the ceiling 6, Default is the pressed one', h.includes('Default (3)') && h.includes('data-mo="6"') && !h.includes('data-mo="7"') && h.includes('data-mo="0" aria-pressed="true"') && h.includes('data-mo="5" aria-pressed="false"')]);
  OUT.push(['says how many are open now against the limit, and the ceiling in words', h.includes('Open now 2 of 3') && h.includes('up to 6')]);
  p = page({v: U}, mk(LIM({max_open: 5, max_open_now: 5}), 1)); await p.run(1); h = p.card.innerHTML;
  OUT.push(['a saved pick of 5 is the pressed button and the chip shows the number in force', h.includes('data-mo="5" aria-pressed="true"') && h.includes('data-mo="0" aria-pressed="false"') && h.includes('Open now 1 of 5')]);
  p = page({v: U}, mk(LIM({max_open_ceiling: 3}), 0)); await p.run(1);
  OUT.push(['the buttons follow the owner ceiling (3)', p.card.innerHTML.includes('data-mo="3"') && !p.card.innerHTML.includes('data-mo="4"')]);
  p = page({v: U}, mk(LIM(), 1)); await p.run(1); await p.click(4); const post = p.calls.find(c => c.o && c.o.method === 'POST');
  OUT.push(['tapping 4 posts {max_open: 4} to /api/limits', post && post.p === '/api/limits' && post.o.body.max_open === 4]);
  OUT.push(['after saving, 4 is pressed and the chip says of 4, a toast says so', p.card.innerHTML.includes('data-mo="4" aria-pressed="true"') && p.card.innerHTML.includes('of 4') && p.toasts.some(t => t.includes('4 positions'))]);
  const n = p.calls.length; await p.click(4); OUT.push(['tapping the one already chosen asks nothing', p.calls.length === n]);
  await p.click(0); OUT.push(['tapping Default posts 0 and says back to the default', p.calls[p.calls.length - 1].o.body.max_open === 0 && p.toasts.some(t => t.includes('default'))]);
  await p.click(null); OUT.push(['a tap that is not on a button does nothing', p.calls.length === n + 1]);
  const lim = LIM(); p = page({v: U}, (a, o) => a === '/api/limits' && o && o.method === 'POST' ? Promise.reject(new Error('Positions at once must be a whole number from 1 to 6')) : mk(lim, 1)(a, o)); await p.run(1); await p.click(5);
  OUT.push(['a refused save shows the server message and keeps the old pick', p.card.innerHTML.includes('whole number from 1 to 6') && p.card.innerHTML.includes('data-mo="0" aria-pressed="true"')]);
  p = page({v: U}, (a, o) => a === '/api/limits' && o && o.method === 'POST' ? Promise.reject(new Error('<img src=x>')) : mk(LIM(), 1)(a, o)); await p.run(1); await p.click(2);
  OUT.push(['a message from the server is escaped, never run as HTML', !p.card.innerHTML.includes('<img') && p.card.innerHTML.includes('&lt;img')]);
  p = page({v: U}, (a) => a === '/api/limits' ? Promise.reject(new Error('x')) : Promise.resolve({open: 1})); await p.run(1);
  OUT.push(['limits cannot be loaded: says cannot reach the server, shows no buttons', p.card.innerHTML.includes('Cannot reach the server') && !p.card.innerHTML.includes('data-mo')]);
  p = page({v: U}, (a) => a === '/api/limits' ? Promise.resolve(LIM()) : Promise.reject(new Error('x'))); await p.run(1);
  OUT.push(['the live numbers failing only drops the "open now" count', p.card.innerHTML.includes('Limit 3') && p.card.innerHTML.includes('data-mo="2"')]);
  p = page({v: U}, mk(LIM(), 1)); await p.run(1); const k = p.calls.length; p.vb.on = false; await p.run(40);
  OUT.push(['not asked again while the Bot tab is not open', p.calls.length === k]);
  p.vb.on = true; await p.open(); OUT.push(['asked again when the Bot tab opens', p.calls.length > k]);
  console.log(JSON.stringify(OUT));
})();
'''
if subprocess.call(['node', '-v'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
    hp = os.path.join(HERE, 'open4_harness.js'); open(hp, 'w').write(HARNESS)
    o = subprocess.run(['node', hp, CODE], capture_output=True, text=True); os.remove(hp)
    try:
        for n, ok in json.loads(o.stdout.strip().splitlines()[-1]): T('page: ' + n, ok)
    except Exception: T('page harness ran: ' + (o.stderr or o.stdout)[:500], False)
else: print('node missing: page checks skipped')
bad = [n for n, ok in R if not ok]; print('%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
