"""Checks Section 5 of the update pop-up: it is built from the site's own pieces (.ov/.panel, .btn primary big block, CSS variables), shows the animated "update" cartoon,
the new build number and the release note line, never writes a colour or a font by hand, animates only when motion is allowed. Needs node; skipped if node is missing.
Run: python tests/test_update5.py"""
import os, re, sys, json, shutil, subprocess
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
HERE = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(HERE, '..', 'static', 'update.js')
HTML = os.path.join(HERE, '..', 'static', 'index.html')
src = open(JS, encoding='utf-8').read()
page = open(HTML, encoding='utf-8').read()
m = re.search(r"var CH2='([^']*)'", page)
CH2 = m.group(1) if m else ''
HARNESS = r'''
const code = require('fs').readFileSync(process.argv[1], 'utf8'); const CH2 = process.argv[2]; const out = {};
function el(tag) { const e = { tag, style: {}, kids: [], textContent: '', id: '', className: '', attrs: {}, innerHTML: '', onclick: null, parent: null };
  e.appendChild = (c) => { c.parent = e; e.kids.push(c); return c; }; e.remove = () => { if (e.parent) e.parent.kids = e.parent.kids.filter(k => k !== e); };
  e.setAttribute = (k, v) => { e.attrs[k] = v; }; e.focus = () => { e.focused = true; }; return e; }
function all(n, a) { a = a || []; a.push(n); n.kids.forEach(k => all(k, a)); return a; }
function phone(o) {
  const body = el('body'), timers = [], store = {}, opened = []; let seen = null;
  const append = body.appendChild; body.appendChild = (c) => { seen = c.className; return append(c); };
  const document = { body, hidden: false, readyState: 'complete', createElement: el, getElementById: (id) => all(body).find(n => n.id === id) || null, addEventListener() {} };
  const cap = { isNativePlatform: () => true, Plugins: { App: { getInfo: () => Promise.resolve({ build: '1000' }) } } };
  const window = { Capacitor: cap, location: { href: '' }, open: (u) => { opened.push(u); return {}; }, addEventListener() {} };
  const sessionStorage = { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = v; } };
  const fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({ tag_name: 'app-1001', body: o.body }) });
  new Function('window', 'document', 'sessionStorage', 'localStorage', 'fetch', 'setTimeout', 'Date', code)(window, document, sessionStorage, { setItem() {} }, fetch, (f) => timers.push(f), { now: () => 1e6 });
  const find = (f) => all(body).find(f);
  return { body, timers, store, opened, U: window.SXBUpdate, find, byText: (t) => find(n => n.textContent === t), get seen() { return seen; } };
}
const wait = () => new Promise(r => setTimeout(r, 20));
async function run(body) { const p = phone({ body }); p.timers[0](); await wait(); return p; }
(async () => {
  let p = await run('## What changed\n- Faster start, fixed chart');
  const ov = p.body.kids[0], panel = ov.kids.find(k => k.className === 'panel'), bd = ov.kids.find(k => k.className === 'bd'), css = ov.kids.find(k => k.tag === 'style');
  out.shell = [p.body.kids.length, ov.id, p.seen, ov.className, !!panel, !!bd, panel && panel.attrs.role, panel && panel.attrs['aria-modal']];
  const cart = all(ov).find(n => n.className === 'ucart');
  out.art = { svg: cart.innerHTML.indexOf('class="ill2 upd"') > -1, arrow: /class="ua"/.test(cart.innerHTML), flame: /class="uf"/.test(cart.innerHTML), sparks: (cart.innerHTML.match(/class="us us\d"/g) || []).length, char: cart.innerHTML.indexOf(CH2) > -1 && CH2.length > 200, arm: cart.innerHTML.indexOf('M114 146c-14 4-26 2-38-4') > -1 };
  out.title = (all(ov).find(n => n.tag === 'h2') || {}).textContent;
  out.fix = all(ov).filter(n => n.className !== 'unote' && /fix/i.test(n.textContent)).length;
  out.said = all(ov).some(n => n.textContent === 'A new update is available for spaceXBot. Update now to get the latest features.');
  const lines = all(ov).filter(n => n.tag === 'p').map(n => n.textContent);
  out.build = lines.some(t => /New build 1001/.test(t) && /you have 1000/.test(t));
  out.note = lines.some(t => t === "What's new: Faster start, fixed chart") || lines;
  const go = p.byText('Update now'), no = p.byText('Maybe later');
  out.btn = [go.className, no.className, true];
  out.css = css.textContent;
  p.U.show(); out.twice = p.body.kids.length;
  go.onclick(); out.go = [p.opened[0] === p.U.APK, p.body.kids.length];
  p = await run('Install spacexbot.apk on your Android phone.'); out.boiler = all(p.body).filter(n => n.className === 'unote').length;
  p = await run('**Faster** `start`'); out.md = (all(p.body).find(n => n.className === 'unote') || {}).textContent;
  p = await run('x'.repeat(40) + ' ' + 'y'.repeat(200)); const ln = (all(p.body).find(n => n.className === 'unote') || {}).textContent || ''; out.long = [ln.length <= 160, /…$/.test(ln)];
  p = await run('<img src=x onerror=alert(1)>'); const nt = all(p.body).find(n => n.className === 'unote'); out.xss = [nt && nt.textContent.indexOf('<img') > -1, all(p.body).every(n => n.innerHTML.indexOf('<img') < 0)];
  p = await run(''); out.nonote = all(p.body).filter(n => n.className === 'unote').length;
  p = await run('a'); p.byText('Maybe later').onclick(); out.later = [p.store.sxb_update_later, p.body.kids.length];
  p = await run('a'); p.body.kids[0].kids.find(k => k.className === 'bd').onclick(); out.backdrop = [p.store.sxb_update_later, p.body.kids.length];
  console.log(JSON.stringify(out));
})();
'''
r = subprocess.run(['node', '-e', HARNESS, JS, CH2], capture_output=True, text=True, timeout=60)
if r.returncode != 0: print('node failed:', (r.stderr or r.stdout)[-600:]); sys.exit(1)
o = json.loads(r.stdout.strip().splitlines()[-1]); css = o['css']; R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
# the part of the style that is inside the reduced-motion media block, and the rest
i = css.find('@media (prefers-reduced-motion:no-preference){'); depth = 0; j = i
for j in range(css.find('{', i), len(css)):
    depth += (css[j] == '{') - (css[j] == '}')
    if depth == 0: break
inside, outside = css[i:j + 1], css[:i] + css[j + 1:]
code_nofill = src.replace(CH2, '').replace('fill="#26262a"', '')
vars_used = set(re.findall(r'var\((--[a-z0-9-]+)', css))
vars_site = set(re.findall(r'(--[a-z0-9-]+)\s*:', page.split('*{box-sizing')[0]))
names = re.findall(r'animation:\s*(sxu\w+)', css)
T('pop-up is the site overlay: .ov with .bd and .panel (dialog), opened after the first paint', o['shell'] == [1, 'sxbUpd', 'ov', 'ov open', True, True, 'dialog', 'true'])
T('the "update" cartoon is there: phone, download arrow, flame, 4 sparkles, arm', o['art']['svg'] and o['art']['arrow'] and o['art']['flame'] and o['art']['sparks'] == 4 and o['art']['arm'])
T('the dark-haired site character is in the cartoon and is exactly CH2 from index.html', o['art']['char'] and ("var CH = '" + CH2 + "';") in src)
T('title is Update available', o['title'] == 'Update available')
T('the card text says a new update is available and never mentions fixes (the release note line is separate)', o['said'] is True and o['fix'] == 0)
T('new build and installed build are shown', o['build'] is True)
T('release note line is shown with a What\'s new label, markdown heading dropped', o['note'] is True)
T('Update now is .btn primary big block, Maybe later is a quiet .btn without primary', o['btn'] == ['btn primary big block', 'btn block q', True])
T('release note never becomes HTML (textContent only)', o['xss'] == [True, True])
T('install boilerplate (spacexbot.apk) is not shown as a note; empty text shows none', o['boiler'] == 0 and o['nonote'] == 0)
T('markdown marks are cleaned and a long note is cut with an ellipsis', o['md'] == "What's new: Faster start" and o['long'] == [True, True])
T('showing twice makes one pop-up', o['twice'] == 1)
T('Update now opens the apk and closes; Maybe later and a tap outside close it for this session', o['go'] == [True, 0] and o['later'] == ['1', 0] and o['backdrop'] == ['1', 0])
T('no hand-written colour, rgb() or font anywhere in update.js (only the site character art and the IL2 fill marker)', not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsl|Arial|Helvetica|font-family', code_nofill))
T('every CSS variable it uses is one the site defines', vars_used and vars_used <= vars_site)
T('all motion lives inside @media (prefers-reduced-motion:no-preference); outside it nothing animates', 'animation' not in outside and '@keyframes' not in outside and 'animation' in inside)
T('every animation has its keyframes', names and all(('@keyframes ' + n + '{') in inside for n in names))
T('iteration-count infinite!important so the calm block cannot stop it', 'animation-iteration-count:infinite!important' in inside)
T('the still pose is complete: nothing is hidden outside the motion block', 'opacity:0' not in outside and 'display:none' not in outside)
T('the REPO line is untouched in form (Section 1 can still rewrite it)', re.search(r'var REPO = "[^"/]+/[^"/]+";', src) is not None)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
