"""Checks Section 2 of the update pop-up: finds the version through the native bridge, checks again on return (once a minute), says why it stayed silent, Update now falls back.
Needs node; skipped if node is missing. Run: python tests/test_update2.py"""
import os, sys, json, shutil, subprocess
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'update.js')
HARNESS = r'''
const code = require('fs').readFileSync(process.argv[1], 'utf8'); const out = {};
function el(tag) { const e = { tag, style: {}, kids: [], textContent: '', id: '', onclick: null, parent: null };
  e.appendChild = (c) => { c.parent = e; e.kids.push(c); return c; }; e.remove = () => { if (e.parent) e.parent.kids = e.parent.kids.filter(k => k !== e); }; return e; }
function find(n, f) { if (f(n)) return n; for (const k of n.kids) { const r = find(k, f); if (r) return r; } return null; }
function phone(o) {
  const body = el('body'), timers = [], store = {}, ls = {}, ev = {}; let fetches = 0, clock = 1e6;
  const document = { body, hidden: false, readyState: 'complete', createElement: el, getElementById: (id) => find(body, n => n.id === id), addEventListener: (t, f) => { ev[t] = f; } };
  const cap = { isNativePlatform: () => true, Plugins: {} };
  if (o.viaPlugin) cap.Plugins.App = { getInfo: () => Promise.resolve({ build: '1000' }) };
  if (o.viaNative) cap.nativePromise = (p, m) => (p === 'App' && m === 'getInfo') ? Promise.resolve({ build: '1000' }) : Promise.reject(new Error('x'));
  const loc = { href: '' };
  const window = { Capacitor: cap, location: loc, open: () => (o.openFails ? null : {}), addEventListener() {} };
  const sessionStorage = { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = v; } };
  const localStorage = { setItem: (k, v) => { ls[k] = v; } };
  const fetch = () => { fetches++; if (o.status) return Promise.resolve({ ok: false, status: o.status }); return Promise.resolve({ ok: true, json: () => Promise.resolve({ tag_name: o.ref.tag }) }); };
  new Function('window', 'document', 'sessionStorage', 'localStorage', 'fetch', 'setTimeout', 'Date', code)(window, document, sessionStorage, localStorage, fetch, (f) => timers.push(f), { now: () => clock });
  return { body, timers, ls, loc, ev, tick: (s) => { clock += s * 1000; }, get fetches() { return fetches; }, U: window.SXBUpdate, button: (t) => find(body, n => n.textContent === t) };
}
const wait = () => new Promise(r => setTimeout(r, 20));
(async () => {
  let p = phone({ viaNative: true, ref: { tag: 'app-1001' } }); p.timers[0](); await wait(); out.native = p.body.kids.length;
  p = phone({ viaPlugin: true, status: 404, ref: {} }); p.timers[0](); await wait(); out.notfound = [p.body.kids.length, /private/.test(p.U.why()), /private/.test(p.ls.sxb_upd_why)];
  p = phone({ ref: {} }); p.timers[0](); await wait(); out.noplug = [p.body.kids.length, /App plugin/.test(p.U.why()), p.fetches];
  const ref = { tag: 'app-1000' }; p = phone({ viaPlugin: true, ref }); p.timers[0](); await wait(); out.first = [p.body.kids.length, /up to date/.test(p.U.why())];
  ref.tag = 'app-1001'; p.ev.visibilitychange(); await wait(); out.soon = [p.fetches, p.body.kids.length];
  p.tick(61); p.ev.visibilitychange(); await wait(); out.later = [p.fetches, p.body.kids.length, p.U.why()];
  p = phone({ viaPlugin: true, ref: { tag: 'app-1001' } }); p.timers[0](); await wait(); p.button('Later').onclick(); p.tick(61); p.ev.visibilitychange(); await wait(); out.afterLater = [p.body.kids.length, p.fetches];
  p = phone({ viaPlugin: true, openFails: true, ref: { tag: 'app-1001' } }); p.timers[0](); await wait(); p.button('Update now').onclick(); out.fallback = [p.loc.href === p.U.APK, p.body.kids.length];
  console.log(JSON.stringify(out));
})();
'''
r = subprocess.run(['node', '-e', HARNESS, JS], capture_output=True, text=True, timeout=60)
if r.returncode != 0: print('node failed:', (r.stderr or r.stdout)[-600:]); sys.exit(1)
o = json.loads(r.stdout.strip().splitlines()[-1]); R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
T('version is found through the native bridge when Plugins.App is missing', o['native'] == 1)
T('release not found (private or wrong repo): no pop-up, the reason is saved', o['notfound'] == [0, True, True])
T('no App plugin: no pop-up, no web call, the reason says so', o['noplug'] == [0, True, 0])
T('same version: the reason says up to date', o['first'] == [0, True])
T('coming back within a minute does not ask GitHub again', o['soon'] == [1, 0])
T('coming back after a minute finds the new release and shows the pop-up', o['later'][:2] == [2, 1] and o['later'][2] == '')
T('after Later, coming back does not show it again', o['afterLater'] == [0, 1])
T('Update now falls back to the same window when a new one is blocked', o['fallback'] == [True, 0])
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
