"""Section 4 tests: the Offline banner. The phone may say "offline" while the server is reachable; the banner must only appear when a request to the server fails.
Runs the page's own offline code in node with a fake page and a fake network. Run: python tests/test_net4.py (needs node)"""
import os, re, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
html = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
m = re.search(r'/\* ---- offline screen ---- \*/(.*?)/\* ---- cancelled payment ---- \*/', html, re.S)
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
T('the offline code is in the page once', html.count('/* ---- offline screen ---- */') == 1 and m is not None)
JS = r'''
const SEG = %s;
const sleep = ms => new Promise(r => setTimeout(r, ms));
function mkEl(){ const s = new Set(); return { classList: { toggle: (c, on) => { on ? s.add(c) : s.delete(c); }, add: c => s.add(c), remove: c => s.delete(c), contains: c => s.has(c) }, style: {}, setAttribute(){}, appendChild(){}, innerHTML: '', textContent: '', offsetWidth: 0, offsetHeight: 0 }; }
async function run(nav, net, U) {
  const L = {}, sel = {}, toasts = []; let calls = 0;
  const navigator = { onLine: nav }, win = { addEventListener: (t, f) => { L[t] = f; }, AbortController, SXA: null };
  const fetch = () => { calls++; return net.ok ? Promise.resolve({}) : Promise.reject(new Error('down')); };
  const doc = { createElement: () => mkEl(), body: mkEl() };
  const $ = s => sel[s] || (sel[s] = mkEl());
  const f = new Function('document', 'window', 'navigator', 'fetch', 'setInterval', 'IL2', '$', 'dots', 'tst', 'U', SEG + '\nreturn {off: off, offb: offb};');
  const o = f(doc, win, navigator, fetch, () => 0, { off: '' }, $, () => {}, t => toasts.push(t), U);
  await sleep(30);
  return { o, L, sel, toasts, navigator, net, calls: () => calls, state: () => [o.off.classList.contains('on'), o.offb.classList.contains('on')] };
}
(async () => {
  const out = [];
  let r = await run(false, { ok: true }, {});
  out.push(['phone says offline but the server answers: no banner, no full screen', JSON.stringify(r.state()) === '[false,false]' && r.calls() === 1]);
  r = await run(false, { ok: false }, {});
  out.push(['server really unreachable, signed in: the banner shows (not the full screen)', JSON.stringify(r.state()) === '[false,true]']);
  r = await run(false, { ok: false }, null);
  out.push(['server really unreachable, not signed in: the full screen shows', JSON.stringify(r.state()) === '[true,false]']);
  r = await run(true, { ok: false }, {});
  out.push(['phone says online: nothing shown and no request made', JSON.stringify(r.state()) === '[false,false]' && r.calls() === 0]);
  r = await run(false, { ok: false }, {});
  r.navigator.onLine = true; r.net.ok = true; r.L.online(); await sleep(30);
  out.push(['coming back online hides the banner and says Back online', JSON.stringify(r.state()) === '[false,false]' && r.toasts.includes('Back online')]);
  r = await run(false, { ok: false }, null);
  const b = r.sel['#offGo']; b.onclick.call(b); await sleep(1100);
  out.push(['Try again while still down: no Back online, screen stays', !r.toasts.includes('Back online') && JSON.stringify(r.state()) === '[true,false]']);
  r.net.ok = true; b.onclick.call(b); await sleep(1100);
  out.push(['Try again once the server answers: Back online and the screen goes', r.toasts.includes('Back online') && JSON.stringify(r.state()) === '[false,false]']);
  console.log(JSON.stringify(out));
})();
''' % json.dumps(m.group(1) if m else '')
res = subprocess.run(['node', '-e', JS], capture_output=True, text=True, timeout=60)
try:
    for name, ok in json.loads(res.stdout.strip().splitlines()[-1]): T(name, ok)
except Exception as e: T('the node run finished (%s) %s' % (repr(e)[:60], res.stderr[:200]), False)
p = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (p, len(R))); sys.exit(0 if p == len(R) else 1)
