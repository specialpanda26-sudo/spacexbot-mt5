"""Checks Section 8a: the "Your session ended" and "Waking the server up" cartoon screens.
The decision code and the whole H8 block run in node against a fake page, fake timers and a fake SXA. No temp files. Run: python tests/test_session8.py"""
import os, re, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def cut(a, b):
    i = S.find(a); j = S.find(b, i + 1) if i > -1 else -1
    return S[i:j + len(b)] if i > -1 and j > -1 else ''
blk = cut('/*H8-start*/', '/*H8-end*/'); pure = cut('/*H8-pure-start*/', '/*H8-pure-end*/')
T('the H8 block is in the page once, in its own script tag after H7', S.count('/*H8-start*/') == 1 and S.count('/*H8-end*/') == 1 and S.find('/*H7-end*/') < S.find('/*H8-start*/') and S.count('/*H8-pure-start*/') == 1)
T('the page tells the block about every sign-in change, and offers sxLogin (once each)', S.count('window.sxH8&&window.sxH8.user(u,first,p8)') == 1 and S.count('window.sxLogin=function(){auth("login")}') == 1)
T('the previous user is read BEFORE it is replaced', 'var p8=U;U=u;slot();try{window.sxH8' in S)
T('the pictures exist in IL2 and the block uses them (lock, sleep)', 'lock:il2(' in S and 'IL2.sleep=il2(' in S and 'art("lock")' in blk and 'art("sleep")' in blk)
T('it is the site pop-up: .ov, .bd, .panel, .btn primary big block, dialog role', all(x in blk for x in ('"ov"', '"bd"', '"panel"', 'btn primary big block', 'role", "dialog"')))
T('no hard-coded colour, no Arial in the block', not re.search(r'#[0-9a-fA-F]{3,8}\b|Arial|rgb\(', blk))
T('text goes in with textContent; the only HTML inserted is the IL2 picture', 'innerHTML' not in blk and blk.count('insertAdjacentHTML') == 1)
T('wording is facts only: no fixes, guarantee, profit promise', not re.search(r'(?i)\bfix|guarantee|you will (earn|win|profit)|make money|claude', blk))
T('the sign-in file (static/live.js) was not touched by this section', 'H8' not in open(os.path.join(ROOT, 'static', 'live.js'), encoding='utf-8').read())
js = r"""
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
const pk = new Function(P.pure + ';return {k:h8kind,t:h8toast};')();
const base = {now: null, first: false, prev: true, ago: 99999};
ok('kind: login lost while signed in = expired', pk.k(base) === 'expired');
ok('kind: the person pressed Log out a moment ago = nothing', pk.k({...base, ago: 2000}) === '');
ok('kind: first answer after opening the app = nothing', pk.k({...base, first: true}) === '');
ok('kind: nobody was signed in = nothing', pk.k({...base, prev: false}) === '');
ok('kind: a signed-in person on the saved copy (server asleep) = wake', pk.k({...base, now: {offline: true}}) === 'wake');
ok('kind: a signed-in person, server answering = back', pk.k({...base, now: {uid: 'a'}}) === 'back');
ok('toast: only the "Cannot reach the server" message counts', pk.t('Cannot reach the server. Try again shortly.') && !pk.t('Saved') && !pk.t(null) && !pk.t('Allow notifications in your phone settings'));

function world(o) {
  o = o || {};
  const reg = [], toasts = [], timers = [], calls = {refresh: 0, login: 0, orig: []};
  const mk = (tag) => { const e = {tag, className: '', children: [], attrs: {}, hidden: false, textContent: '', html: '', id: '', offsetWidth: 1,
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, appendChild(c) { this.children.push(c); c.parent = this; if (this.attached) att(c); return c; },
    insertAdjacentHTML(w, h) { this.html += h; }, focus() {}, remove() { unatt(this); } }; return e; };
  const att = (e) => { e.attached = true; reg.push(e); e.children.forEach(att); };
  const unatt = (e) => { e.attached = false; const i = reg.indexOf(e); if (i > -1) reg.splice(i, 1); e.children.forEach(unatt); };
  const body = mk('body'); body.attached = true;
  const doc = {createElement: mk, body, getElementById: (id) => reg.find((e) => e.id === id) || null};
  let me = o.me === undefined ? null : o.me;
  const SXA = {user: () => me, signOut() { calls.out = (calls.out || 0) + 1; return Promise.resolve(); },
    refresh() { calls.refresh++; return o.refresh ? o.refresh(() => me, (v) => { me = v; }) : Promise.resolve(me); }};
  const win = {IL2: {lock: '<svg class="ill2" id="PLOCK"></svg>', sleep: '<svg class="ill2" id="PSLEEP"></svg>'}, SXA,
    sxToast: (m) => calls.orig.push(m), sxLogin: () => calls.login++};
  let now = 1e6; const D = {now: () => now};
  const run = new Function('window', 'document', 'SXA', 'fetch', 'setTimeout', 'clearTimeout', 'Date', P.blk);
  const fetchF = o.fetch || (() => Promise.resolve({status: 200}));
  const setT = (f, ms) => { timers.push({f, ms, on: true}); return timers.length; }, clrT = (i) => { if (timers[i - 1]) timers[i - 1].on = false; };
  run(win, doc, SXA, fetchF, setT, clrT, D);
  const flush = async () => { for (let i = 0; i < 12; i++) await new Promise((r) => setImmediate(r)); };
  const ov = () => doc.getElementById('h8ov');
  const find = (e, f) => { if (f(e)) return e; for (const c of e.children) { const r = find(c, f); if (r) return r; } return null; };
  const btn = (txt) => find(ov(), (e) => e.tag === 'button' && e.textContent === txt);
  const fire = async () => { const t = timers.filter((x) => x.on).pop(); if (!t) return false; t.on = false; t.f(); await flush(); return true; };
  return {win, SXA, calls, doc, ov, btn, find, flush, fire, timers, setMe: (v) => { me = v; }, adv: (ms) => { now += ms; }, H: win.sxH8};
}
const title = (w) => { const h = w.ov() && w.find(w.ov(), (e) => e.tag === 'h2'); return h && h.textContent; };

(async () => {
  let w = world();
  ok('the block publishes sxH8 and wraps sxToast and SXA.signOut', w.H && w.win.sxToast !== undefined && w.H.user && typeof w.H.expired === 'function');
  w.adv(60000); w.H.user(null, false, {uid: 'a'});
  ok('expired: the "Your session ended" card opens', title(w) === 'Your session ended' && w.ov().attrs['data-kind'] === 'expired');
  ok('expired: it carries the lock picture inside the panel', w.ov().children[1].html.indexOf('PLOCK') > -1);
  ok('expired: it is the site pop-up (ov open, bd + panel, big primary block button)', w.ov().className === 'ov open' && w.ov().children[0].className === 'bd' && w.ov().children[1].className === 'panel' && w.btn('Log in').className === 'btn primary big block');
  ok('expired: the title is centred like the text under it', w.find(w.ov(), (e) => e.tag === 'h2').attrs.style === 'text-align:center');
  ok('expired: the words say what happened, nothing else', /no longer valid/.test(w.ov().children[1].children[1].textContent) && !/fix|guarantee/i.test(w.ov().children[1].children[1].textContent));
  w.btn('Log in').onclick();
  ok('expired: Log in closes the card and opens the log-in screen', !w.ov() && w.calls.login === 1);
  w.H.user(null, false, {uid: 'a'}); w.btn('Not now').onclick();
  ok('expired: Not now just closes it', !w.ov() && w.calls.login === 1);
  w.H.user(null, false, {uid: 'a'}); w.ov().children[0].onclick();
  ok('expired: tapping the dim background closes it too', !w.ov());

  w = world(); w.adv(60000); await w.SXA.signOut(); w.H.user(null, false, {uid: 'a'});
  ok('a Log out the person pressed does NOT show "session ended"', !w.ov() && w.calls.out === 1);
  w = world(); w.H.user(null, false, null);
  ok('signed out all along: no card', !w.ov());
  w = world(); w.H.user(null, true, {uid: 'a'});
  ok('first answer after the app opens: no card', !w.ov());
  w = world(); w.adv(60000); w.H.user(null, false, {uid: 'a'}); w.H.user({uid: 'a'}, false, null);
  ok('expired card closes by itself when the person is signed in again (no toast)', !w.ov() && w.calls.orig.length === 0);

  w = world({me: {uid: 'a', offline: true}}); w.H.user({uid: 'a', offline: true}, false, {uid: 'a'});
  ok('wake: server asleep on the saved account opens "Waking the server up" with the moon picture', title(w) === 'Waking the server up' && w.ov().children[1].html.indexOf('PSLEEP') > -1 && w.ov().attrs['data-kind'] === 'wake');
  ok('wake: it says why and that it keeps trying; Try again is the big button, Close is quiet', /sleeps/.test(w.ov().children[1].children[1].textContent) && /keep trying/.test(w.ov().children[1].children[1].textContent) && w.btn('Try again').className === 'btn primary big block' && w.btn('Close').className === 'btn block');
  w.H.user({uid: 'a', offline: true}, false, {uid: 'a'});
  ok('wake: a second offline answer does not open a second card', w.doc.body.children.filter((c) => c.id === 'h8ov').length === 1);
  await w.fire();
  ok('wake: it looks again by itself and shows the try number', w.calls.refresh === 1 && w.find(w.ov(), (e) => e.id === 'h8s').textContent === 'Try 1 of 8' && !w.find(w.ov(), (e) => e.id === 'h8s').hidden);
  for (let i = 0; i < 12; i++) await w.fire();
  ok('wake: it gives up after 8 tries and says what to check', w.calls.refresh === 8 && /Still no answer/.test(w.find(w.ov(), (e) => e.id === 'h8s').textContent));
  w.btn('Try again').onclick(); await w.flush();
  ok('wake: Try again starts again from try 1', w.calls.refresh === 9 && w.find(w.ov(), (e) => e.id === 'h8s').textContent === 'Try 1 of 8');
  w.setMe({uid: 'a'}); w.H.user({uid: 'a'}, false, {uid: 'a'});
  ok('wake: when the server answers the card closes and one "Back online" toast shows', !w.ov() && w.calls.orig.join() === 'Back online');
  w.H.user({uid: 'a', offline: true}, false, {uid: 'a'});
  ok('wake: asleep again later = the card comes back', title(w) === 'Waking the server up');
  w.btn('Close').onclick(); w.H.user({uid: 'a', offline: true}, false, {uid: 'a'});
  ok('wake: after Close it stays closed until the server has answered once', !w.ov());

  w = world({me: {uid: 'a', offline: true}, refresh: (g, s) => Promise.reject({status: 401})});
  w.H.user({uid: 'a', offline: true}, false, {uid: 'a'}); await w.fire();
  ok('wake: if the server answers "not signed in" the card turns into "Your session ended"', title(w) === 'Your session ended');

  w = world({fetch: () => Promise.reject(new Error('net'))});
  w.win.sxToast('Cannot reach the server. Try again shortly.'); await w.flush();
  ok('toast path: no answer from the server = "Waking the server up"; the plain toast is not shown too', title(w) === 'Waking the server up' && w.calls.orig.length === 0);
  w = world({fetch: () => Promise.resolve({status: 503})});
  w.win.sxToast('Cannot reach the server. Try again shortly.'); await w.flush();
  ok('toast path: a 503 from a sleeping server also counts as waking', title(w) === 'Waking the server up');
  w = world({fetch: () => Promise.resolve({status: 200}), refresh: () => Promise.reject({status: 401})});
  w.win.sxToast('Cannot reach the server. Try again shortly.'); await w.flush();
  ok('toast path: server answers but refuses the login = "Your session ended"', title(w) === 'Your session ended');
  w = world({fetch: () => Promise.resolve({status: 200}), refresh: () => Promise.resolve({uid: 'a'})});
  w.win.sxToast('Cannot reach the server. Try again shortly.'); await w.flush();
  ok('toast path: server answers and the login works = no card at all', !w.ov());
  w = world(); w.win.sxToast('Saved'); w.win.sxToast('Allow notifications in your phone settings to get trade alerts.');
  ok('other toasts pass through untouched', w.calls.orig.length === 2 && !w.ov());
  console.log(JSON.stringify(OUT));
})();
"""
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
r = subprocess.run(['node', '-e', js], input=json.dumps({'pure': pure, 'blk': blk.replace('/*H8-start*/', '', 1)}), capture_output=True, text=True)
if r.returncode:
    T('node harness ran', False); print(r.stderr[-600:])
else:
    for n, ok in json.loads(r.stdout.strip().splitlines()[-1]): T(n, ok)
print('%d/%d passed' % (sum(R), len(R)))
sys.exit(0 if all(R) else 1)
