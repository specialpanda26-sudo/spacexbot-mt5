"""Checks Section 10a: the Settings row "App updates" (update.js row()/status() + one hook in index.html). Needs node; skipped if missing. Run: python tests/test_why10.py"""
import os, re, sys, json, shutil, subprocess
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
HERE = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(HERE, '..', 'static', 'update.js'); HTML = os.path.join(HERE, '..', 'static', 'index.html')
HARNESS = r'''
const code = require('fs').readFileSync(process.argv[1], 'utf8'); const out = {};
function el(t) { const e = { tag: t, kids: [], textContent: '', id: '', className: '', attrs: {}, innerHTML: '', onclick: null };
  e.appendChild = c => { e.kids.push(c); return c; }; e.remove = () => {}; e.setAttribute = (k, v) => { e.attrs[k] = v; }; return e; }
function phone(o) {
  const store = {}, ls = Object.assign({}, o.ls || {}), body = el('body'), nodes = {}, L = {}; let fetches = 0;
  const document = { body, hidden: false, readyState: 'complete', createElement: el, getElementById: id => nodes[id] || null, addEventListener: (k, f) => { L[k] = f; } };
  const cap = { isNativePlatform: () => o.native !== false, Plugins: { App: { getInfo: () => Promise.resolve({ build: '1000' }) } } };
  const window = { Capacitor: cap, location: { href: '' }, open: () => ({}), addEventListener() {} };
  const sessionStorage = { getItem: k => store[k] || null, setItem: (k, v) => { store[k] = v; }, removeItem: k => { delete store[k]; } };
  const localStorage = { getItem: k => (k in ls ? ls[k] : null), setItem: (k, v) => { ls[k] = v; } };
  const timers = [];
  const fetch = () => { fetches++; return Promise.resolve({ ok: o.status ? false : true, status: o.status || 200, json: () => Promise.resolve({ tag_name: o.tag || 'app-1000', body: '' }) }); };
  new Function('window', 'document', 'sessionStorage', 'localStorage', 'fetch', 'setTimeout', 'Date', code)(window, document, sessionStorage, localStorage, fetch, f => timers.push(f), Date);
  return { U: window.SXBUpdate, timers, store, ls, L, nodes, doc: document, get fetches() { return fetches; } };
}
const wait = () => new Promise(r => setTimeout(r, 20));
(async () => {
  let p = phone({ native: false }); out.web = [p.U.row(), p.U.status()];
  p = phone({}); out.fresh = p.U.row();
  p = phone({ ls: { sxb_upd_why: 'GitHub answered with an error' } }); out.saved = p.U.status();
  p = phone({ ls: { sxb_upd_why: '<b>x</b>' } }); out.esc = p.U.row();
  p = phone({}); p.timers[0](); await wait(); out.up = p.U.status();
  p = phone({ status: 404 }); p.timers[0](); await wait(); out.nf = p.U.status();
  p = phone({ tag: 'app-1001' }); p.timers[0](); await wait(); out.found = p.U.status();
  p = phone({ tag: 'app-1001' }); p.timers[0](); await wait(); p.store.sxb_update_later = '1';
  const node = { textContent: '' }; p.nodes.sxbUpdWhy = node; const before = p.fetches;
  const btn = { getAttribute: k => (k === 'data-upd' ? 'check' : null) };
  p.L.click({ target: { closest: () => btn } }); await wait(); await wait();
  out.click = { cleared: !p.store.sxb_update_later, fetched: p.fetches - before, text: node.textContent };
  const other = p.fetches; p.L.click({ target: { closest: () => null } }); await wait(); out.other = p.fetches - other;
  console.log(JSON.stringify(out));
})();
'''
r = subprocess.run(['node', '-e', HARNESS, JS], capture_output=True, text=True)
if r.returncode: print(r.stderr[-800:]); sys.exit(1)
o = json.loads(r.stdout.strip().splitlines()[-1]); src = open(JS, encoding='utf-8').read(); page = open(HTML, encoding='utf-8').read()
ok = 0; n = 0
def T(name, c):
    global ok, n; n += 1; ok += bool(c); print(('PASS ' if c else 'FAIL ') + name)
T('in a normal browser the row is empty and says it is for the Android app', o['web'][0] == '' and 'Android' in o['web'][1])
T('in the app the row has the title, a note line and a Check now button', 'App updates' in o['fresh'] and 'id="sxbUpdWhy"' in o['fresh'] and 'data-upd="check"' in o['fresh'] and 'Check for updates now' in o['fresh'] and 'Not checked yet' in o['fresh'])
T('the reason saved from an earlier run shows before any check', 'GitHub answered with an error' in o['saved'])
T('a saved reason is never written as HTML', '<b>' not in o['esc'] and '&lt;b&gt;' in o['esc'])
T('up to date is said in plain words with how long ago', 'up to date' in o['up'] and 'Checked just now' in o['up'])
T('a missing release names the private repo / wrong name cause', 'private' in o['nf'])
T('a newer build says so and points to the button', 'newer app is out' in o['found'])
T('the button clears Maybe later, checks again and refreshes the line', o['click']['cleared'] and o['click']['fetched'] == 1 and 'newer app' in o['click']['text'])
T('a tap on anything else does nothing', o['other'] == 0)
T('index.html has the Settings hook exactly once, right before "Data on this device"', page.count('SXBUpdate.row()') == 1 and page.count('SXBUpdate.row():"")+\'<h3>Data on this device</h3>') == 1)
T('no hand-written colour or font was added', not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|Arial|font-family', src.split('/*W10*/')[1].split('function again')[0]))
print('\n%d/%d passed' % (ok, n)); sys.exit(0 if ok == n else 1)
