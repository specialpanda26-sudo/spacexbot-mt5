"""Checks the update popup (static/update.js) with a fake phone: newer release shows it, same or older does not, Later hides it, errors stay silent.
Needs node; skipped if node is missing. Run: python tests/test_update.py"""
import os, sys, json, shutil, subprocess
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
JS = os.path.join(ROOT, 'static', 'update.js')
HARNESS = r'''
const fs = require('fs'); const code = fs.readFileSync(process.argv[1], 'utf8'); const out = {};
function el(tag) { const e = { tag, style: {}, kids: [], textContent: '', id: '', onclick: null, parent: null };
  e.appendChild = (c) => { c.parent = e; e.kids.push(c); return c; };
  e.remove = () => { if (e.parent) e.parent.kids = e.parent.kids.filter(k => k !== e); };
  return e; }
function find(n, f) { if (f(n)) return n; for (const k of n.kids) { const r = find(k, f); if (r) return r; } return null; }
function phone(o) {
  const body = el('body'), timers = [], opened = [], store = {}; let fetches = 0;
  const document = { body, readyState: 'complete', createElement: el, getElementById: (id) => find(body, n => n.id === id) };
  const App = o.noApp ? undefined : { getInfo: () => Promise.resolve({ build: o.have || '1000', version: '1.0.' + (o.have || '1000') }) };
  const window = { Capacitor: o.web ? undefined : { isNativePlatform: () => true, Plugins: { App } }, open: (u) => opened.push(u), addEventListener() {} };
  const sessionStorage = { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = v; } };
  const fetch = (u) => { fetches++; if (o.fail) return Promise.reject(new Error('offline')); if (o.http) return Promise.resolve({ ok: false });
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ tag_name: o.tag || 'app-1001' }) }); };
  new Function('window', 'document', 'sessionStorage', 'fetch', 'setTimeout', code)(window, document, sessionStorage, fetch, (f) => timers.push(f));
  return { body, timers, opened, store, window, get fetches() { return fetches; }, button: (t) => find(body, n => n.textContent === t) };
}
const wait = () => new Promise(r => setTimeout(r, 20));
(async () => {
  const U = phone({}).window.SXBUpdate;
  out.build = [U.build('app-12345'), U.build('1.0.777'), U.build(''), U.build('desktop-latest'), U.build(null)];
  out.newer = [U.newer('app-1001', '1000'), U.newer('app-1000', '1000'), U.newer('app-999', '1000'), U.newer('latest', '1000'), U.newer('app-1001', '')];
  let p = phone({}); out.timer = [p.timers.length, phone({ web: true }).timers.length];
  p.timers[0](); await wait();
  out.shown = [p.body.kids.length, !!p.button('Update now'), !!p.button('Later')];
  p.window.SXBUpdate.check(); await wait(); out.once = p.body.kids.length;
  p.button('Update now').onclick(); out.update = [p.opened.length, p.opened[0] === U.APK, p.body.kids.length];
  p = phone({}); p.timers[0](); await wait(); p.button('Later').onclick();
  const f0 = p.fetches; p.window.SXBUpdate.check(); await wait(); out.later = [p.body.kids.length, p.store.sxb_update_later, p.fetches === f0];
  p = phone({ tag: 'app-1000' }); p.timers[0](); await wait(); out.same = p.body.kids.length;
  p = phone({ fail: true }); p.timers[0](); await wait(); out.offline = p.body.kids.length;
  p = phone({ http: true }); p.timers[0](); await wait(); out.http = p.body.kids.length;
  p = phone({ noApp: true }); p.timers[0](); await wait(); out.noapp = [p.body.kids.length, p.fetches];
  console.log(JSON.stringify(out));
})();
'''
r = subprocess.run(['node', '-e', HARNESS, JS], capture_output=True, text=True, timeout=60)
if r.returncode != 0: print('node failed:', (r.stderr or r.stdout)[-600:]); sys.exit(1)
o = json.loads(r.stdout.strip().splitlines()[-1]); R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
T('build number is read from tags and versions', o['build'] == [12345, 777, 0, 0, 0])
T('only a higher release counts as newer', o['newer'] == [True, False, False, False, False])
T('check is scheduled in the app, not in a normal browser', o['timer'] == [1, 0])
T('newer release shows the popup with Update now and Later', o['shown'] == [1, True, True])
T('popup is never shown twice', o['once'] == 1)
T('Update now opens the apk link and closes the popup', o['update'] == [1, True, 0])
T('Later closes it and it stays away until the app is opened again', o['later'] == [0, '1', True])
T('same version: no popup', o['same'] == 0)
T('offline or GitHub error: no popup, no crash', o['offline'] == 0 and o['http'] == 0)
T('app version unknown: no popup, no web call', o['noapp'] == [0, 0])
T('index.html loads update.js once', open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read().count('/static/update.js') == 1)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
