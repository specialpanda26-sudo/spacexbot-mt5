"""Losing-streak card (static/streak_ui.js) on the Bot tab: person asks to continue, admin reviews. Needs node (skipped if missing).
Run: python tests/test_streakui.py   Runs against a fake page and a fake server; nothing is written to disk."""
import os, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
code = open(os.path.join(ROOT, 'static', 'streak_ui.js'), encoding='utf-8').read(); html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok)))
T('the page loads streak_ui.js once, right after prefs_ui.js', html.count('/static/streak_ui.js') == 1 and html.find('prefs_ui.js') < html.find('streak_ui.js') < html.find('quick_ui.js'))
T('no made-up numbers, no stored copies, no hard-coded colours', 'Math.random' not in code and 'localStorage' not in code and '#' not in ''.join(l for l in code.splitlines() if 'style=' in l))
HARNESS = r'''
const code = require('fs').readFileSync(0, 'utf8'), OUT = [], ok = (n, c) => OUT.push([n, !!c]), tick = () => new Promise(r => setTimeout(r, 5));
function el(id) { const e = {id, _h: '', hidden: false, className: '', style: {}, on: false, handlers: {}, inserted: [], classList: {contains: c => c === 'on' && e.on},
  insertBefore(n, ref) { e.inserted.push([n, ref]); }, addEventListener(t, f) { e.handlers[t] = f; }};
  Object.defineProperty(e, 'innerHTML', {get: () => e._h, set: v => { e._h = v; }}); return e; }
const NOW = Math.floor(Date.now() / 1000);
const PS = o => Object.assign({owner: false, paused: true, k: 3, until: NOW + 7200, since: NOW - 600, losses: [-5, -5, -5.5], request: null}, o || {});
function page(st) {
  const timers = [], calls = [], toasts = [];
  const vb = el('view-bot'), bs = el('botstatec');
  const document = {hidden: false, createElement: () => el(''), getElementById: id => id === 'view-bot' ? vb : id === 'botstatec' ? bs : null};
  const SXA = {user: () => st.user, api: (u, o) => { calls.push({u, o}); return st.next(u, o); }};
  const MO = function (f) { MO.f = f; this.observe = () => {}; };
  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', code)(document, {SXA, sxToast: t => toasts.push(t)}, SXA, f => timers.push(f), MO);
  const C = vb.inserted[0][0];
  return {C, vb, bs, at: vb.inserted[0][1], calls, toasts, html: () => C.innerHTML, run: async () => { timers.forEach(f => f()); await tick(); await tick(); },
    click: async (k, v) => { C.handlers.click({target: {closest: s => s === '[data-' + k + ']' ? {getAttribute: () => v} : null}}); await tick(); await tick(); },
    type: t => C.handlers.input({target: {getAttribute: () => '', value: t}})};
}
const P = {uid: 'u1', verified: true, admin: false}, AD = {uid: 'o', verified: true, admin: true}, okp = j => () => Promise.resolve(j);
(async () => {
  let p = page({user: null, next: okp(PS())}); await p.run();
  ok('signed out: hidden, empty, nothing asked', p.C.hidden === true && p.html() === '' && p.calls.length === 0);
  p = page({user: P, next: okp(PS())});
  ok('the card sits right after the Bot status card', p.at === p.bs.nextSibling && p.C.id === 'streakc');
  await p.run(); let h = p.html();
  ok('paused: asks GET /api/streak (not the admin route) and shows the card', p.calls.length === 1 && p.calls[0].u === '/api/streak' && p.C.hidden === false);
  ok('says how many losses, the dollar amounts and when it ends by itself', h.includes('3 losses in a row') && h.includes('-$5.00, -$5.00, -$5.50') && h.includes('starts again by itself at'));
  ok('has the ask button and says nothing changes until the admin says yes', h.includes('data-ask="1"') && h.includes('Ask the admin to let me continue') && h.includes('Nothing changes until they say yes'));
  await p.click('ask', '');
  const post = p.calls.find(c => c.o && c.o.method === 'POST');
  ok('tapping it posts to /api/streak/request', post && post.u === '/api/streak/request');
  p = page({user: P, next: (u, o) => Promise.resolve(o ? PS({request: {status: 'pending', since: NOW - 600, t: NOW}}) : PS())}); await p.run(); await p.click('ask', ''); h = p.html();
  ok('after sending: waiting message, toast, and no ask button', h.includes('Your request is with the admin') && !h.includes('data-ask') && p.toasts.includes('Sent to the admin'));
  p = page({user: P, next: okp(PS({request: {status: 'declined', since: NOW - 600, note: 'Wait for tomorrow <b>'}}))}); await p.run(); h = p.html();
  ok('declined for this pause: the admin note is shown (escaped), no ask button', h.includes('said not now') && h.includes('Wait for tomorrow &lt;b&gt;') && !h.includes('data-ask'));
  p = page({user: P, next: okp(PS({request: {status: 'declined', since: NOW - 99999, note: ''}}))}); await p.run();
  ok('declined for an OLDER pause: may ask again', p.html().includes('data-ask'));
  p = page({user: P, next: okp(PS({paused: false, k: 0, until: 0, since: 0, losses: [], request: {status: 'approved', decided: NOW - 60, note: 'be careful'}}))}); await p.run(); h = p.html();
  ok('approved a minute ago: "Trading allowed again" with the note and the other limits still apply', h.includes('Trading allowed again') && h.includes('be careful') && h.includes('daily and weekly loss limits still apply') && !h.includes('data-ask'));
  p = page({user: P, next: okp(PS({paused: false, k: 0, until: 0, since: 0, losses: [], request: {status: 'approved', decided: NOW - 90000, note: ''}}))}); await p.run();
  ok('approved more than a day ago: card hidden', p.C.hidden === true && p.html() === '');
  p = page({user: P, next: okp(PS({paused: false, k: 0, losses: [], request: null}))}); await p.run();
  ok('not paused and nothing to say: card hidden', p.C.hidden === true && p.html() === '');
  p = page({user: P, next: okp(PS({owner: true, paused: false}))}); await p.run();
  ok('owner or not paused: hidden', p.C.hidden === true);
  p = page({user: P, next: (u, o) => o ? Promise.reject(new Error('Your request is already with the admin.')) : Promise.resolve(PS())}); await p.run(); await p.click('ask', ''); h = p.html();
  ok('a refused ask: the server words are shown and the button is still there', h.includes('already with the admin') && h.includes('data-ask') && p.toasts.length === 0);
  p = page({user: P, next: () => Promise.reject(new Error('x'))}); await p.run();
  ok('server down: nothing shown, no crash', p.C.hidden === true && p.html() === '');

  // ---------- admin ----------
  const W = o => ({waiting: [Object.assign({uid: 'u9', email: 'amy@x.com', k: 3, losses: [-5, -5, -5], t: NOW - 120, status: 'pending'}, o || {})], recent: []});
  p = page({user: AD, next: okp({waiting: [], recent: []})}); await p.run();
  ok('admin with nothing waiting: hidden, and only the admin route was asked', p.C.hidden === true && p.calls.length === 1 && p.calls[0].u === '/api/admin/streak');
  const stx = {user: AD, next: (u, o) => Promise.resolve(o ? {waiting: [], recent: [{uid: 'u9', status: o.body.approve ? 'approved' : 'declined'}]} : W())};
  p = page(stx); await p.run(); h = p.html();
  ok('admin sees who is waiting, the losses and Approve / Decline', p.C.hidden === false && h.includes('Pause requests') && h.includes('amy@x.com') && h.includes('3 losses in a row: -$5.00, -$5.00, -$5.00') && h.includes('data-a="u9"') && h.includes('data-d="u9"'));
  await p.click('a', 'u9'); h = p.html();
  ok('Approve only asks "are you sure": a note box, Confirm and Cancel, no POST yet', h.includes('Let this person trade again now?') && h.includes('data-note') && h.includes('data-go') && !p.calls.some(c => c.o));
  await p.click('no', ''); h = p.html();
  ok('Cancel goes back to the two buttons, nothing sent', h.includes('data-a="u9"') && !h.includes('data-go') && !p.calls.some(c => c.o));
  await p.click('a', 'u9'); p.type('be careful'); await p.click('go', '');
  const ap = p.calls.find(c => c.o && c.o.method === 'POST');
  ok('Confirm posts exactly {uid, approve: true, note} to /api/admin/streak', ap && ap.u === '/api/admin/streak' && JSON.stringify(ap.o.body) === '{"uid":"u9","approve":true,"note":"be careful"}');
  ok('after approving: the row is gone, card hidden, toast', p.C.hidden === true && p.toasts.includes('Approved. Trading can continue.'));
  p = page(stx); await p.run(); await p.click('d', 'u9'); h = p.html();
  ok('Decline asks "keep it paused?" first', h.includes('Keep the pause on for this person?') && h.includes('Yes, keep it paused'));
  await p.click('go', ''); const dp = p.calls.find(c => c.o && c.o.method === 'POST');
  ok('Decline posts {approve: false} with an empty note', dp && JSON.stringify(dp.o.body) === '{"uid":"u9","approve":false,"note":""}' && p.toasts.includes('Declined. The pause stays.'));
  p = page({user: AD, next: (u, o) => o ? Promise.reject(new Error('That pause already ended by itself.')) : Promise.resolve(W())}); await p.run(); await p.click('a', 'u9'); await p.click('go', ''); h = p.html();
  ok('a refused decision: the reason is shown and the confirm stays', h.includes('already ended by itself') && h.includes('data-go') && p.toasts.length === 0);
  p = page({user: AD, next: okp(W({email: '<img src=x>'}))}); await p.run();
  ok('email is escaped', !p.html().includes('<img') && p.html().includes('&lt;img'));
  console.log(JSON.stringify(OUT));
})();
'''
r = subprocess.run(['node', '-e', HARNESS], input=code, capture_output=True, text=True, timeout=30)
try: out = json.loads(r.stdout.strip().splitlines()[-1])
except Exception: out = []; print(r.stdout[-500:], r.stderr[-900:])
for n, ok in out: T(n, ok)
T('the page test ran all its checks', len(out) == 25)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
