"""Checks Section 8c: the "Something went wrong" and "<broker> is connected" cartoon screens.
The decision code and the whole H8c block run in node against a fake page, fake clock and fake localStorage. No temp files. Run: python tests/test_pop8c.py"""
import os, re, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def cut(a, b):
    i = S.find(a); j = S.find(b, i + 1) if i > -1 else -1
    return S[i:j + len(b)] if i > -1 and j > -1 else ''
blk = cut('/*H8c-start*/', '/*H8c-end*/'); pure = cut('/*H8c-pure-start*/', '/*H8c-pure-end*/')
T('the H8c block is in the page once, in its own script tag after H8b', S.count('/*H8c-start*/') == 1 and S.count('/*H8c-end*/') == 1 and S.find('/*H8b-end*/') < S.find('/*H8c-start*/') and S.count('/*H8c-pure-start*/') == 1)
T('the Connect-tab check publishes its last answer once (window.SXCONN)', S.count('window.SXCONN = {') == 1 and S.find('/*R2-start*/') < S.find('window.SXCONN = {') < S.find('/*R2-end*/'))
T('the pictures exist in IL2 and the block uses them (cx, plug)', 'cx=il2(' in S.replace(' ', '') or 'IL2.cx=il2(' in S)
T('the block uses I.cx and I.plug', 'I.cx' in blk and 'I.plug' in blk)
T('it is the site pop-up: .ov, .bd, .panel, .btn primary big block, dialog role', all(x in blk for x in ('"ov"', '"bd"', '"panel"', 'btn primary big block', 'role", "dialog"')))
T('no hard-coded colour, no Arial in the block', not re.search(r'#[0-9a-fA-F]{3,8}\b|Arial|rgb\(', blk))
T('text goes in with textContent; the only HTML inserted is the IL2 picture', 'innerHTML' not in blk and blk.count('insertAdjacentHTML') == 1)
T('wording is facts only: no fixes, guarantee, profit promise', not re.search(r'(?i)\bfix|guarantee|you will (earn|win|profit)|make money|hurry|last chance|don.t miss', blk))
T('the sign-in file (static/live.js) was not touched by this section', 'H8c' not in open(os.path.join(ROOT, 'static', 'live.js'), encoding='utf-8').read())
js = r"""
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
const pk = new Function(P.pure + ';return {err:h8err,errok:h8errok,map:h8map,conn:h8conn,w:h8words};')();
ok('err: the plain message is caught', pk.err('Something went wrong. Try again.') && pk.err('something went wrong'));
ok('err: other messages are not (no connection, cannot reach the server, empty)', !pk.err('No connection. Check your internet.') && !pk.err('Cannot reach the server. Try again shortly.') && !pk.err('') && !pk.err(null) && !pk.err(undefined));
ok('errok: first time = yes; busy = no; under 30 s = no; 30 s later = yes', pk.errok({open: false, last: 0, now: 1e6}) && !pk.errok({open: true, last: 0, now: 1e6}) && !pk.errok({open: false, last: 1e6, now: 1e6 + 29999}) && pk.errok({open: false, last: 1e6, now: 1e6 + 30000}));
const rows = (a, b) => [{id: 'Deriv', state: a}, {id: 'MT5', state: b}];
const C = (r, prev, seen) => pk.conn({rows: r, prev: prev === undefined ? null : prev, seen: seen || []});
ok('conn: first look (no previous answer) = nothing, even when connected', C(rows('ok', 'ok'), null).length === 0);
ok('conn: none -> ok = that broker', C(rows('ok', 'none'), pk.map(rows('none', 'none'))).join() === 'Deriv');
ok('conn: problem -> ok = that broker', C(rows('none', 'ok'), pk.map(rows('none', 'problem'))).join() === 'MT5');
ok('conn: offline (stale) -> ok is NOT a new connection', C(rows('ok', 'ok'), pk.map(rows('stale', 'stale'))).length === 0);
ok('conn: ok -> ok = nothing', C(rows('ok', 'ok'), pk.map(rows('ok', 'ok'))).length === 0);
ok('conn: ok -> problem = nothing', C(rows('problem', 'none'), pk.map(rows('ok', 'ok'))).length === 0);
ok('conn: a broker that was not in the previous answer is not celebrated', C(rows('ok', 'ok'), {Deriv: 'ok'}).length === 0);
ok('conn: already celebrated on this phone = nothing', C(rows('ok', 'none'), pk.map(rows('none', 'none')), ['Deriv']).length === 0);
ok('conn: both at once = both ids', C(rows('ok', 'ok'), pk.map(rows('none', 'problem'))).join() === 'Deriv,MT5');
ok('conn: junk rows do not crash', C([null, {}, {id: 'X'}], {}).length === 0 && C(undefined, {}).length === 0);
const a = pk.w('error'), b = pk.w('connected', 'Deriv');
ok('words error: title, reload and close, account kept', a.title === 'Something went wrong' && a.go === 'Reload the app' && a.no === 'Close' && /account and saved settings are still here/.test(a.text));
ok('words connected: names the broker, says the bot needs starting', b.title === 'Deriv is connected' && b.go === 'Go to Bot tab' && b.no === 'Not now' && /does not trade until you start it on the Bot tab/.test(b.text) && pk.w('connected', 'MT5').title === 'MT5 is connected');

function world(o) {
  o = o || {};
  const reg = [], timers = [], calls = {reload: 0, bot: 0, toast: []}, store = {};
  const mk = (tag) => { const e = {tag, className: '', children: [], attrs: {}, hidden: false, textContent: '', html: '', id: '', offsetWidth: 1,
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, appendChild(c) { this.children.push(c); c.parent = this; if (this.attached) att(c); return c; },
    insertAdjacentHTML(w, h) { this.html += h; }, focus() {}, click() { if (this.onclick) this.onclick(); }, remove() { unatt(this); } }; return e; };
  const att = (e) => { e.attached = true; reg.push(e); e.children.forEach(att); };
  const unatt = (e) => { e.attached = false; const i = reg.indexOf(e); if (i > -1) reg.splice(i, 1); e.children.forEach(unatt); };
  const body = mk('body'); body.attached = true;
  const botBtn = mk('button'); botBtn.onclick = () => calls.bot++;
  const doc = {createElement: mk, body, getElementById: (id) => reg.find((e) => e.id === id) || null,
    querySelector: (q) => q === '.ov.open' ? (reg.find((e) => /\bov\b/.test(e.className) && /\bopen\b/.test(e.className)) || null) : q === '[data-go="bot"]' ? (o.noBotBtn ? null : botBtn) : null};
  let me = o.me === undefined ? null : o.me, nowMs = 1700000000000;
  const SXA = {user: () => me};
  const win = {IL2: {cx: '<svg class="ill2" id="PCX"></svg>', plug: '<svg class="ill2" id="PPLUG"></svg>'}, location: {reload: () => calls.reload++}};
  win.sxToast = (m) => calls.toast.push(m);
  const FD = class extends Date { static now() { return nowMs; } };
  const ls = {getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { if (o.lsBroken) throw new Error('full'); store[k] = String(v); }};
  const setT = (f, ms) => { timers.push({f, ms, kind: 't'}); return timers.length; }, setI = (f, ms) => { timers.push({f, ms, kind: 'i'}); return timers.length; };
  new Function('window', 'document', 'SXA', 'setTimeout', 'setInterval', 'Date', 'localStorage', P.blk)(win, doc, SXA, setT, setI, FD, ls);
  const ov = () => doc.getElementById('h8cov');
  const find = (e, f) => { if (f(e)) return e; for (const c of e.children) { const r = find(c, f); if (r) return r; } return null; };
  const btn = (txt) => find(ov(), (e) => e.tag === 'button' && e.textContent === txt);
  const pub = (r, u, age) => { win.SXCONN = {u: u || 'a', j: {rows: r}, t: nowMs - (age || 0)}; };
  return {win, calls, doc, ov, btn, find, store, timers, H: win.sxH8c, setMe: (v) => { me = v; }, adv: (s) => { nowMs += s * 1000; }, add: (c) => doc.body.appendChild(c), mk, pub};
}
const title = (w) => { const h = w.ov() && w.find(w.ov(), (e) => e.tag === 'h2'); return h && h.textContent; };
const R = (a, b) => [{id: 'Deriv', state: a}, {id: 'MT5', state: b}];

let w = world({me: {uid: 'a'}});
ok('start: one timer, every 1.5 s, nothing shown', w.timers.length === 1 && w.timers[0].ms === 1500 && w.timers[0].kind === 'i' && !w.ov());
w.win.sxToast('Something went wrong. Try again.');
ok('error: the toast became a card with the cross picture inside the panel', title(w) === 'Something went wrong' && w.ov().attrs['data-kind'] === 'error' && w.ov().children[1].html.indexOf('PCX') > -1 && w.calls.toast.length === 0);
ok('error: it is the site pop-up (ov open, bd + panel, big primary block, quiet Close, centred title)', w.ov().className === 'ov open' && w.ov().children[0].className === 'bd' && w.ov().children[1].className === 'panel' && w.btn('Reload the app').className === 'btn primary big block' && w.btn('Close').className === 'btn block' && w.find(w.ov(), (e) => e.tag === 'h2').attrs.style === 'text-align:center');
w.btn('Reload the app').onclick();
ok('error: Reload the app closes the card and reloads once', !w.ov() && w.calls.reload === 1);
w.win.sxToast('Something went wrong. Try again.');
ok('error: a second one within 30 s shows the plain toast again (nothing is lost)', !w.ov() && w.calls.toast.length === 1);
w.adv(31); w.win.sxToast('Something went wrong.');
ok('error: 30 s later a new card opens', title(w) === 'Something went wrong');
w.btn('Close').onclick();
ok('error: Close just closes it, no reload', !w.ov() && w.calls.reload === 1);
w.adv(31); w.win.sxToast('Something went wrong.'); w.ov().children[0].onclick();
ok('error: tapping the dim background closes it too', !w.ov() && w.calls.reload === 1);
const before = w.calls.toast.length; w.win.sxToast('Saved.'); w.win.sxToast('Cannot reach the server. Try again shortly.');
ok('error: other toasts pass straight through', w.calls.toast.slice(before).join('|') === 'Saved.|Cannot reach the server. Try again shortly.' && !w.ov());

w = world({me: {uid: 'a'}}); const other = w.mk('div'); other.className = 'ov open'; w.add(other); w.win.sxToast('Something went wrong.');
ok('error busy: never on top of another open pop-up, the toast shows instead', !w.ov() && w.calls.toast.length === 1);
w = world({me: {uid: 'a'}, lsBroken: true}); w.win.sxToast('Something went wrong.');
ok('error: storage blocked changes nothing for the error card', title(w) === 'Something went wrong');

w = world({me: {uid: 'a'}}); w.pub(R('none', 'none')); w.H.check();
ok('conn: the first answer opens nothing', !w.ov());
w.adv(5); w.pub(R('ok', 'none')); w.H.check();
ok('conn: Deriv none -> ok opens the card with the plug picture', title(w) === 'Deriv is connected' && w.ov().attrs['data-kind'] === 'connected' && w.ov().children[1].html.indexOf('PPLUG') > -1);
ok('conn: it is the site pop-up with Go to Bot tab (big primary) and quiet Not now', w.ov().className === 'ov open' && w.btn('Go to Bot tab').className === 'btn primary big block' && w.btn('Not now').className === 'btn block');
ok('conn: it remembers on this phone who was celebrated', JSON.parse(w.store.sxb_bc).u === 'a' && JSON.parse(w.store.sxb_bc).ids.join() === 'Deriv');
w.btn('Go to Bot tab').onclick();
ok('conn: Go to Bot tab closes the card and taps the Bot tab once', !w.ov() && w.calls.bot === 1);
w.adv(5); w.pub(R('problem', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'none')); w.H.check();
ok('conn: connecting Deriv again later does not repeat the card (once per person and broker)', !w.ov());
w.adv(5); w.pub(R('ok', 'ok')); w.H.check();
ok('conn: but the other broker still gets its own card', title(w) === 'MT5 is connected');

w = world({me: {uid: 'a'}}); w.pub(R('none', 'none')); w.H.check(); const o2 = w.mk('div'); o2.className = 'ov open'; w.add(o2);
w.adv(5); w.pub(R('ok', 'none')); w.H.check();
ok('conn busy: not on top of another open pop-up', !w.ov() && !w.store.sxb_bc);
o2.className = 'ov'; w.H.check();
ok('conn busy: it opens at the next look once the other pop-up is closed (nothing was marked or lost)', title(w) === 'Deriv is connected' && !!w.store.sxb_bc);
w.H.check();
ok('conn busy: another look while it is open does not open a second card', w.doc.body.children.filter((c) => c.id === 'h8cov').length === 1);

w = world({me: {uid: 'a'}}); w.pub(R('none', 'none')); w.H.check(); w.adv(5); w.pub(R('stale', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'none')); w.H.check();
ok('conn: offline (stale) then ok is not a new connection, no card', !w.ov());
w = world({me: {uid: 'a'}}); w.pub(R('none', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'ok')); w.H.check();
ok('conn: both at once = one card (the first), both remembered', title(w) === 'Deriv is connected' && JSON.parse(w.store.sxb_bc).ids.join() === 'Deriv,MT5');

w = world({me: {uid: 'a'}}); w.pub(R('none', 'none'), 'b'); w.H.check(); w.adv(5); w.pub(R('ok', 'none'), 'b'); w.H.check();
ok('conn: an answer that belongs to another person is ignored', !w.ov());
w = world({me: {uid: 'a'}}); w.pub(R('none', 'none')); w.H.check(); w.adv(500); w.pub(R('ok', 'none'), 'a', 130000); w.H.check();
ok('conn: an answer older than 2 minutes is ignored', !w.ov());
w = world({me: {uid: 'a', offline: true}}); w.pub(R('none', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'none')); w.H.check();
ok('conn: the saved copy while the server sleeps shows nothing', !w.ov());
w = world({me: null}); w.pub(R('none', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'none')); w.H.check();
ok('conn: signed out shows nothing', !w.ov());
w = world({me: {uid: 'a'}}); w.H.check();
ok('conn: no answer published yet = nothing, no crash', !w.ov());
w = world({me: {uid: 'a'}}); w.pub(R('none', 'none')); w.H.check(); w.setMe({uid: 'b'}); w.adv(5); w.pub(R('ok', 'none'), 'b'); w.H.check();
ok('conn: a different person signing in starts fresh (their first answer opens nothing)', !w.ov());
w.adv(5); w.pub(R('none', 'none'), 'b'); w.H.check(); w.adv(5); w.pub(R('ok', 'none'), 'b'); w.H.check();
ok('conn: and then their own change opens their own card', title(w) === 'Deriv is connected' && JSON.parse(w.store.sxb_bc).u === 'b');
w = world({me: {uid: 'a'}, lsBroken: true}); w.pub(R('none', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'none')); w.H.check();
ok('conn: storage blocked, the card still opens and nothing crashes', title(w) === 'Deriv is connected');
w = world({me: {uid: 'a'}, noBotBtn: true}); w.pub(R('none', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'none')); w.H.check(); let threw = false; try { w.btn('Go to Bot tab').onclick(); } catch (e) { threw = true; }
ok('conn: if the page has no Bot tab button, Go to Bot tab just closes the card', !threw && !w.ov());
w = world({me: {uid: 'a'}}); w.pub(R('none', 'none')); w.H.check(); w.adv(5); w.pub(R('ok', 'none')); w.H.check(); w.btn('Not now').onclick();
ok('conn: Not now closes it without moving to the Bot tab', !w.ov() && w.calls.bot === 0);
w.win.sxToast('Something went wrong.');
ok('error after connected closed: still works (separate rule)', title(w) === 'Something went wrong');
w.btn('Close').onclick(); w.pub(R('ok', 'ok')); w.adv(5); w.H.check();
ok('conn: an error card open blocks a connected card until it is closed', !w.ov());
console.log(JSON.stringify(OUT));
"""
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
r = subprocess.run(['node', '-e', js], input=json.dumps({'pure': pure, 'blk': blk.replace('/*H8c-start*/', '', 1)}), capture_output=True, text=True)
if r.returncode:
    T('node harness ran', False); print(r.stderr[-800:])
else:
    for n, ok in json.loads(r.stdout.strip().splitlines()[-1]): T(n, ok)
print('%d/%d passed' % (sum(R), len(R)))
sys.exit(0 if all(R) else 1)
