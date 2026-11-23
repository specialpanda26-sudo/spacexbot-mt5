"""Presets S5 page checks: the "Small account settings" card on the Bot tab (static/prefs_ui.js, block A2). Needs node (skipped if missing).
Run: python tests/test_presetsui.py   The file runs against a fake page and a fake server; nothing is written to disk."""
import os, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
code = open(os.path.join(ROOT, 'static', 'prefs_ui.js'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok)))
T('the card block is in the file exactly once, before the Open trades card', code.count('A2. Small account settings') == 1 and code.find('A2. Small account settings') < code.find('B. Open trades'))
T('no made-up numbers and no stored copies (no random, sample, localStorage)', 'Math.random' not in code and 'localStorage' not in code)
T('only site colours (CSS variables) in the new block', '#' not in ''.join(l for l in code.split('A2. Small')[1].split('B. Open trades')[0].splitlines() if 'style=' in l and '#' in l.replace('&#', '')) )
HARNESS = r'''
const code = require('fs').readFileSync(0, 'utf8'), OUT = [], ok = (n, c) => OUT.push([n, !!c]), tick = () => new Promise(r => setTimeout(r, 5));
function el(id) { const e = {id, _h: '', hidden: false, className: '', style: {}, on: false, handlers: {}, inserted: [], classList: {contains: c => c === 'on' && e.on},
  insertBefore(n, ref) { e.inserted.push([n, ref]); }, querySelector: () => null, addEventListener(t, f) { e.handlers[t] = f; }};
  Object.defineProperty(e, 'innerHTML', {get: () => e._h, set: v => { e._h = v; }}); return e; }
const tier = (k, loss) => ({strategies: ['a', 'b', 'c'], alone: true, min_conf: 1, entries: 1, max_open: 1, streak: 2, risk_pct: 1, loss_pct: loss, burst_on: false, minute: false});
const ML = (bal, extra) => Object.assign({known: true, balance: bal, risk_pct: 1, risk_usd: Math.round(bal) / 100, rows: [], warn: false, blocked: false, message: ''}, extra || {});
const STATUS = o => Object.assign({tiers: {10: tier(10, 2), 20: tier(20, 2.5), 30: tier(30, 3)}, active: null, can_undo: false, not_included: ['Drawdown stop', 'Daily profit target'], owner: false, demo: true,
  minlot: {10: ML(20), 20: ML(20), 30: ML(20)}}, o || {});
function page(st) {
  const timers = [], calls = [], toasts = [], reloads = [], pcalls = [];
  const vb = el('view-bot'), pc = el('prefc'), toastF = t => toasts.push(t);
  const document = {hidden: false, createElement: () => el(''), getElementById: id => id === 'view-bot' ? vb : id === 'prefc' ? pc : null};
  const SXA = {user: () => st.user, api: (u, o) => { if (u.indexOf('/api/prefs') === 0) { pcalls.push(u); return Promise.resolve({prefs: {}, strategies: [], ceiling: 1}); } calls.push({u, o}); return st.next(u, o); }};
  const MO = function (f) { MO.f = f; this.observe = () => {}; };
  const win = {SXA, sxToast: toastF, };
  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', code)(document, win, SXA, f => timers.push(f), MO);
  const ins = vb.inserted.map(x => x[0]), C = ins.find(n => n.id === 'presetc');
  return {C, vb, pc, before: vb.inserted.find(x => x[0] === C)[1], calls, toasts, get reloads() { return pcalls.slice(1); }, html: () => C.innerHTML, tick1: async () => { timers.forEach(f => f()); await tick(); await tick(); },
    click: async sel => { const m = {}; ['p', 'ok', 'no', 'undo'].forEach(k => m[k] = null);
      C.handlers.click({target: {closest: s => { const k = s.replace('[data-', '').replace(']', ''); return k === sel.k ? {getAttribute: () => sel.v} : null; }}}); await tick(); await tick(); }};
}
const U = {uid: 'u1', verified: true}, okp = j => () => Promise.resolve(j);
(async () => {
  let p = page({user: null, next: okp(STATUS())}); await p.tick1();
  ok('signed out: card hidden, empty, nothing asked', p.C.hidden === true && p.html() === '' && p.calls.length === 0);
  p = page({user: {uid: 'x', verified: false}, next: okp(STATUS())}); await p.tick1();
  ok('email not verified: hidden, nothing asked', p.C.hidden === true && p.calls.length === 0);
  p = page({user: U, next: okp(STATUS())});
  ok('the card is placed right before the Strategies card', p.before === p.pc);
  await p.tick1(); let h = p.html();
  ok('asks GET /api/presets once and shows the card', p.calls.length === 1 && p.calls[0].u === '/api/presets' && p.C.hidden === false);
  ok('title and exactly three buttons $10 $20 $30, none pressed', h.includes('<h2>Small account settings</h2>') && (h.match(/data-p="/g) || []).length === 3 && h.includes('data-p="10" aria-pressed="false"') && h.includes('>$30<'));
  ok('says it does not make money or keep an account safe', h.includes('does not make money or keep an account safe'));
  ok('nothing to confirm and no undo before a tap', !h.includes('data-ok') && !h.includes('data-undo'));
  await p.click({k: 'p', v: '20'}); h = p.html();
  ok('tapping $20 only picks: no POST yet, $20 pressed, confirm box shown', p.calls.length === 1 && h.includes('data-p="20" aria-pressed="true"') && h.includes('data-ok') && h.includes('Confirm $20 settings'));
  ok('the dollar loss is shown BEFORE Confirm (1% of $20.00 = $0.20), in the same box', h.includes('Most one trade may lose: about $0.20 (1% of your $20.00 balance)') && h.indexOf('about $0.20') < h.indexOf('data-ok'));
  ok('group loss limit in dollars: 2.5% of $20.00 = $0.50, and says it is for 2 or more entries', h.includes('stops at a loss of $0.50 (2.5%)') && h.includes('2 or more entries'));
  ok('lists the values and what is not set', h.includes('3 strategies') && h.includes('stop after 2 losses in a row') && h.includes('Not set by this: drawdown stop; daily profit target'));
  await p.click({k: 'p', v: '30'}); h = p.html();
  ok('picking another size changes the box (3% of $20.00 = $0.60) and still saves nothing', h.includes('Confirm $30 settings') && h.includes('$0.60') && p.calls.length === 1);
  await p.click({k: 'no', v: ''}); h = p.html();
  ok('Cancel closes the box and saves nothing', !h.includes('data-ok') && p.calls.length === 1);
  const st1 = STATUS({active: 10, can_undo: true});
  const stx = {user: U, next: (u, o) => Promise.resolve(st1)}; p = page(stx); await p.tick1(); await p.click({k: 'p', v: '10'}); await p.click({k: 'ok', v: ''});
  const post = p.calls.find(c => c.o && c.o.method === 'POST');
  ok('Confirm posts exactly {tier: 10} to /api/presets', post && post.u === '/api/presets' && JSON.stringify(post.o.body) === '{"tier":10}');
  h = p.html();
  ok('after saving: $10 on chip, $10 pressed, box closed, toast, Strategies card reloaded', h.includes('$10 on') && h.includes('data-p="10" aria-pressed="true"') && !h.includes('data-ok') && p.toasts.includes('Smaller-risk settings are on') && p.reloads.length === 1);
  ok('undo button now shown', h.includes('data-undo') && h.includes('Back to my old settings'));
  st1.active = null; st1.can_undo = false; p.calls.length = 0; await p.click({k: 'undo', v: ''});
  const up = p.calls.find(c => c.o && c.o.method === 'POST');
  ok('undo posts exactly {undo: true}, toasts, and reloads the Strategies card', up && JSON.stringify(up.o.body) === '{"undo":true}' && p.toasts.includes('Your old settings are back') && p.reloads.length === 2);
  ok('after undo: no chip, no undo button', !p.html().includes('chip info') && !p.html().includes('data-undo'));
  // no balance: no dollar claim
  p = page({user: U, next: okp(STATUS({minlot: {10: ML(0, {known: false}), 20: ML(0, {known: false}), 30: ML(0, {known: false})}}))}); await p.tick1(); await p.click({k: 'p', v: '20'}); h = p.html();
  ok('balance unknown: says so and shows no dollar amount at all', h.includes('balance is not known yet') && !h.includes('Most one trade may lose') && !/\$0\.\d\d/.test(h.replace('$20 settings', '')));
  // minimum lot warning / blocked
  p = page({user: U, next: okp(STATUS({minlot: {10: ML(20, {warn: true, message: 'Your balance is too small for this market on this account type. Try a cent account or a demo.'}), 20: ML(20, {warn: true, blocked: true, message: 'Your balance is too small for this market on this account type. Try a cent account or a demo.'}), 30: ML(20)}}))}); await p.tick1();
  await p.click({k: 'p', v: '10'}); h = p.html();
  ok('small balance warning is shown and Confirm still works', h.includes('too small for this market') && !/data-ok="1" disabled/.test(h));
  await p.click({k: 'p', v: '20'}); h = p.html();
  ok('blocked (no market can trade): the reason is shown and Confirm is off', h.includes('too small for this market') && /data-ok="1" disabled/.test(h));
  await p.click({k: 'ok', v: ''}); ok('a disabled Confirm sends nothing', !p.calls.some(c => c.o && c.o.method === 'POST') || false);
  // real mode and owner
  p = page({user: U, next: okp(STATUS({demo: false}))}); await p.tick1(); h = p.html();
  ok('Real mode: all three buttons disabled, says use Demo first', (h.match(/data-p="\d+" aria-pressed="false" disabled/g) || []).length === 3 && h.includes('Demo account first'));
  await p.click({k: 'p', v: '10'}); ok('Real mode: a tap does nothing', !p.html().includes('data-ok'));
  p = page({user: U, next: okp(STATUS({owner: true}))}); await p.tick1();
  ok('owner: the card is hidden and empty (no tap for the owner bot)', p.C.hidden === true && p.html() === '');
  // errors
  p = page({user: U, next: (u, o) => o ? Promise.reject(new Error('Try the smaller-risk settings on a demo account first.')) : Promise.resolve(STATUS())}); await p.tick1(); await p.click({k: 'p', v: '20'}); await p.click({k: 'ok', v: ''}); h = p.html();
  ok('a refused save: the server words are shown, the box stays, nothing claimed as saved', h.includes('on a demo account first') && h.includes('data-ok') && !h.includes('$20 on') && p.toasts.length === 0 && p.reloads.length === 0);
  p = page({user: U, next: () => Promise.reject(new Error('x'))}); await p.tick1();
  ok('server down: shows Cannot reach the server and no buttons', p.html().includes('Cannot reach the server.') && !p.html().includes('data-p'));
  p = page({user: U, next: okp(STATUS({tiers: {10: Object.assign(tier(10, 2), {strategies: ['<img src=x>']}), 20: tier(20, 2.5), 30: tier(30, 3)}, not_included: ['<b>x</b>']}))}); await p.tick1(); await p.click({k: 'p', v: '10'});
  ok('server text is escaped', !p.html().includes('<b>x</b>') && p.html().includes('&lt;b&gt;x&lt;/b&gt;'));
  console.log(JSON.stringify(OUT));
})();
'''
r = subprocess.run(['node', '-e', HARNESS], input=code, capture_output=True, text=True, timeout=30)
try: out = json.loads(r.stdout.strip().splitlines()[-1])
except Exception: out = []; print(r.stdout[-500:], r.stderr[-900:])
for n, ok in out: T(n, ok)
T('the page test ran all its checks', len(out) == 28)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
