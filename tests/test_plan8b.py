"""Checks Section 8b: the "Your plan ends soon" and "Your plan has ended" cartoon screens.
The decision code and the whole H8b block run in node against a fake page, fake clock and fake localStorage. No temp files. Run: python tests/test_plan8b.py"""
import os, re, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def cut(a, b):
    i = S.find(a); j = S.find(b, i + 1) if i > -1 else -1
    return S[i:j + len(b)] if i > -1 and j > -1 else ''
blk = cut('/*H8b-start*/', '/*H8b-end*/'); pure = cut('/*H8b-pure-start*/', '/*H8b-pure-end*/')
T('the H8b block is in the page once, in its own script tag after H8', S.count('/*H8b-start*/') == 1 and S.count('/*H8b-end*/') == 1 and S.find('/*H8-end*/') < S.find('/*H8b-start*/') and S.count('/*H8b-pure-start*/') == 1)
T('the page offers sxPlans once, with the same rules as the Start-bot gate (log in / verify / plans)', S.count('window.sxPlans=function(){if(!U)auth("login");else if(!U.verified)verify();else plans()}') == 1)
T('the pictures exist in IL2 and the block uses them (wait, coin)', 'wait:il2(' in S and 'coin:il2(' in S and 'I.coin' in blk and 'I.wait' in blk)
T('it is the site pop-up: .ov, .bd, .panel, .btn primary big block, dialog role', all(x in blk for x in ('"ov"', '"bd"', '"panel"', 'btn primary big block', 'role", "dialog"')))
T('no hard-coded colour, no Arial in the block', not re.search(r'#[0-9a-fA-F]{3,8}\b|Arial|rgb\(', blk))
T('text goes in with textContent; the only HTML inserted is the IL2 picture', 'innerHTML' not in blk and blk.count('insertAdjacentHTML') == 1)
T('wording is facts only: no fixes, guarantee, profit promise, no "updates are frequent"', not re.search(r'(?i)\bfix|guarantee|you will (earn|win|profit)|make money|claude|hurry|last chance|don.t miss', blk))
T('the sign-in file (static/live.js) was not touched by this section', 'H8b' not in open(os.path.join(ROOT, 'static', 'live.js'), encoding='utf-8').read())
js = r"""
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
const pk = new Function(P.pure + ';return {k:h8plan,w:h8words};')();
const DAY = 86400, NOW = 1700000000, U = (d, x) => Object.assign({uid: 'a', plan_until: NOW + d * DAY}, x || {});
const K = (u, seen) => pk.k({u, now: NOW, seen: seen || null});
ok('kind: more than 3 days left = nothing', K(U(3.5)) === '' && K(U(30)) === '');
ok('kind: exactly 3 days left = soon', K(U(3)) === 'soon');
ok('kind: 1 hour left = soon', K(U(1 / 24)) === 'soon');
ok('kind: plan ran out = ended (also the very second it ends)', K(U(-1)) === 'ended' && K(U(0)) === 'ended');
ok('kind: never had a plan (plan_until 0) = nothing, that is the locked state not an ended plan', K(U(0, {plan_until: 0})) === '' && K({uid: 'a'}) === '');
ok('kind: an admin is never told their plan ends', K(U(1, {admin: true})) === '' && K(U(-5, {admin: true})) === '');
ok('kind: the saved copy while the server sleeps says nothing', K(U(1, {offline: true})) === '' && K(U(-1, {offline: true})) === '');
ok('kind: signed out = nothing', K(null) === '');
ok('kind: the same card for the same end date is not shown twice', K(U(1), {u: 'a', k: 'soon', t: NOW + DAY}) === '' && K(U(-1), {u: 'a', k: 'ended', t: NOW - DAY}) === '');
ok('kind: soon was seen, the plan then ended = ended shows once', K(U(-1), {u: 'a', k: 'soon', t: NOW - DAY}) === 'ended');
ok('kind: the plan was extended (new end date) = the cycle starts again', K(U(2), {u: 'a', k: 'soon', t: NOW - DAY}) === 'soon');
ok('kind: another person on the same phone has their own cards', K(U(1), {u: 'b', k: 'soon', t: NOW + DAY}) === 'soon');
const a = pk.w('soon', 2 * DAY - 5, '23 Nov 2026'), b = pk.w('soon', 5 * 3600, '22 Nov 2026'), c = pk.w('ended', -DAY, '20 Nov 2026');
ok('words soon: 2 days', a.title === 'Your plan ends soon' && /ends in 2 days, on 23 Nov 2026\./.test(a.text) && a.go === 'Extend plan' && a.no === 'Not now');
ok('words soon: under a day says so', /ends in less than a day, on 22 Nov 2026\./.test(b.text));
ok('words soon: says the days left are kept (true: payments.activate adds to the end date)', /days you have left are kept/i.test(a.text));
ok('words ended: says it ended, the bot is locked, the account is kept', c.title === 'Your plan has ended' && /ended on 20 Nov 2026/.test(c.text) && /bot is locked/.test(c.text) && /account and saved settings are still here/.test(c.text) && c.go === 'Choose a plan');

function world(o) {
  o = o || {};
  const reg = [], timers = [], calls = {plans: 0}, store = {};
  const mk = (tag) => { const e = {tag, className: '', children: [], attrs: {}, hidden: false, textContent: '', html: '', id: '', offsetWidth: 1,
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, appendChild(c) { this.children.push(c); c.parent = this; if (this.attached) att(c); return c; },
    insertAdjacentHTML(w, h) { this.html += h; }, focus() {}, remove() { unatt(this); } }; return e; };
  const att = (e) => { e.attached = true; reg.push(e); e.children.forEach(att); };
  const unatt = (e) => { e.attached = false; const i = reg.indexOf(e); if (i > -1) reg.splice(i, 1); e.children.forEach(unatt); };
  const body = mk('body'); body.attached = true;
  const doc = {createElement: mk, body, getElementById: (id) => reg.find((e) => e.id === id) || null,
    querySelector: (q) => q === '.ov.open' ? (reg.find((e) => /\bov\b/.test(e.className) && /\bopen\b/.test(e.className)) || null) : null};
  let me = o.me === undefined ? null : o.me, nowMs = NOW * 1000;
  const SXA = {user: () => me};
  const win = {IL2: {wait: '<svg class="ill2" id="PWAIT"></svg>', coin: '<svg class="ill2" id="PCOIN"></svg>'}, sxPlans: () => calls.plans++};
  const FD = class extends Date { static now() { return nowMs; } };
  const ls = {getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { if (o.lsBroken) throw new Error('full'); store[k] = String(v); }};
  const setT = (f, ms) => { timers.push({f, ms, kind: 't'}); return timers.length; }, setI = (f, ms) => { timers.push({f, ms, kind: 'i'}); return timers.length; };
  new Function('window', 'document', 'SXA', 'setTimeout', 'setInterval', 'Date', 'localStorage', P.blk)(win, doc, SXA, setT, setI, FD, ls);
  const ov = () => doc.getElementById('h8bov');
  const find = (e, f) => { if (f(e)) return e; for (const c of e.children) { const r = find(c, f); if (r) return r; } return null; };
  const btn = (txt) => find(ov(), (e) => e.tag === 'button' && e.textContent === txt);
  return {win, calls, doc, ov, btn, find, store, timers, H: win.sxH8b, setMe: (v) => { me = v; }, adv: (s) => { nowMs += s * 1000; }, add: (c) => doc.body.appendChild(c), mk};
}
const title = (w) => { const h = w.ov() && w.find(w.ov(), (e) => e.tag === 'h2'); return h && h.textContent; };

let w = world({me: U(2)});
ok('start: it checks once after 3 s and then every 5 s', w.timers.length === 2 && w.timers[0].ms === 3000 && w.timers[0].kind === 't' && w.timers[1].ms === 5000 && w.timers[1].kind === 'i');
ok('start: nothing is shown before the first check', !w.ov());
w.timers[0].f();
ok('soon: the card opens with the clock picture inside the panel', title(w) === 'Your plan ends soon' && w.ov().attrs['data-kind'] === 'soon' && w.ov().children[1].html.indexOf('PWAIT') > -1);
ok('soon: it is the site pop-up (ov open, bd + panel, big primary block button, quiet Not now)', w.ov().className === 'ov open' && w.ov().children[0].className === 'bd' && w.ov().children[1].className === 'panel' && w.btn('Extend plan').className === 'btn primary big block' && w.btn('Not now').className === 'btn block');
ok('soon: the title is centred like the text under it', w.find(w.ov(), (e) => e.tag === 'h2').attrs.style === 'text-align:center');
ok('soon: it remembers on this phone which end date it showed', JSON.parse(w.store.sxb_pe).k === 'soon' && JSON.parse(w.store.sxb_pe).u === 'a' && JSON.parse(w.store.sxb_pe).t === NOW + 2 * DAY);
w.btn('Extend plan').onclick();
ok('soon: Extend plan closes the card and opens the plan chooser once', !w.ov() && w.calls.plans === 1);
w.timers[1].f();
ok('soon: it does not come back after it was shown', !w.ov());

w = world({me: U(2)}); w.H.check(); w.btn('Not now').onclick();
ok('soon: Not now just closes it, no plan chooser', !w.ov() && w.calls.plans === 0);
w = world({me: U(2)}); w.H.check(); w.ov().children[0].onclick();
ok('soon: tapping the dim background closes it too', !w.ov() && w.calls.plans === 0);

w = world({me: U(2)}); w.H.check(); w.btn('Not now').onclick(); w.adv(3 * DAY); w.H.check();
ok('ended: three days later the plan has ended = a new card, once', title(w) === 'Your plan has ended' && w.ov().attrs['data-kind'] === 'ended' && w.ov().children[1].html.indexOf('PCOIN') > -1 && !!w.btn('Choose a plan'));
w.btn('Choose a plan').onclick();
ok('ended: Choose a plan opens the plan chooser', !w.ov() && w.calls.plans === 1);
w.H.check();
ok('ended: it is not shown again for the same end date', !w.ov());
w.setMe(U(30)); w.H.check();
ok('extended: a plan with a new far-away end date shows nothing', !w.ov());
w.adv(25 * DAY); w.H.check();
ok('extended: and when that one gets close, soon comes again', title(w) === 'Your plan ends soon');

w = world({me: U(2)}); const other = w.mk('div'); other.className = 'ov open'; w.add(other); w.H.check();
ok('busy: it never opens on top of another open pop-up', !w.ov());
other.className = 'ov'; w.H.check();
ok('busy: it opens once the other pop-up is closed (it was not marked as shown)', title(w) === 'Your plan ends soon');
w.H.check();
ok('busy: a second check while the card is open does not open a second card', w.doc.body.children.filter((c) => c.id === 'h8bov').length === 1);

w = world({me: null}); w.H.check();
ok('signed out: no card', !w.ov());
w = world({me: U(2, {admin: true})}); w.H.check();
ok('admin: no card', !w.ov());
w = world({me: U(2, {offline: true})}); w.H.check();
ok('server asleep (saved copy): no card', !w.ov());
w = world({me: U(40)}); w.H.check();
ok('plenty of time left: no card', !w.ov());
w = world({me: {uid: 'a', plan_until: 0}}); w.H.check();
ok('never had a plan: no card', !w.ov());
w = world({me: U(2), lsBroken: true}); w.H.check();
ok('storage full or blocked: the card still opens and nothing crashes', title(w) === 'Your plan ends soon');
w = world({me: U(0.2)}); w.H.check();
ok('under a day: the words say "in less than a day"', /in less than a day/.test(w.ov().children[1].children[1].textContent));
w = world({me: U(-2)}); w.H.check();
ok('ended 2 days ago and never shown: one "ended" card (no soon card first)', title(w) === 'Your plan has ended' && w.ov().attrs['data-kind'] === 'ended');
w = world({me: U(2)}); w.win.sxPlans = undefined; w.H.check(); let threw = false; try { w.btn('Extend plan').onclick(); } catch (e) { threw = true; }
ok('if the page has no plan chooser the button still just closes the card', !threw && !w.ov());
console.log(JSON.stringify(OUT));
"""
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
r = subprocess.run(['node', '-e', js], input=json.dumps({'pure': pure, 'blk': blk.replace('/*H8b-start*/', '', 1)}), capture_output=True, text=True)
if r.returncode:
    T('node harness ran', False); print(r.stderr[-800:])
else:
    for n, ok in json.loads(r.stdout.strip().splitlines()[-1]): T(n, ok)
print('%d/%d passed' % (sum(R), len(R)))
sys.exit(0 if all(R) else 1)
