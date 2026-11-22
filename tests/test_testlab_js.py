"""Test Lab 1 page checks. Part A: static/test_lab.js against a fake page (needs node). Part B: the real index.html in Chromium (needs playwright; skipped if missing).
Run: python tests/test_testlab_js.py"""
import os, sys, shutil, subprocess, json, mimetypes
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
IDX = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('index.html: lab script tag, #tlab slot, hooks present', IDX.count('/static/test_lab.js') == 1 and IDX.count('<div id="tlab"></div>') == 1 and IDX.count('window.sxLabHooks=') == 1)
HARNESS = r'''
const fs = require('fs'); const out = {}; const els = {};
const mk = (id) => (els[id] = { id, style: {}, parentNode: { removeChild: (e) => { delete els[e.id]; } }, innerHTML: '', textContent: '', attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; }, set onclick(f) { this._c = f; }, get onclick() { return this._c; } });
let body = []; const log = [];
global.document = { getElementById: (i) => els[i] || null, createElement: () => { const e = mk('tmp'); delete els.tmp; return e; }, body: { appendChild: (e) => { els[e.id] = e; body.push(e.id); if (e.innerHTML.includes('tlStop')) els.tlStop = mk('tlStop'); }, }, };
global.MutationObserver = function () { this.observe = () => {}; };
let reply; global.window = { SXA: { api: (p, o) => { log.push(p); return reply(p, o); } }, sxLabHooks: { pay: (w) => log.push('pay:' + w), stop: () => log.push('stop') }, sxDerivLogin: { say: (m) => log.push('say:' + m) } };
eval(fs.readFileSync(process.argv[1], 'utf8'));
const L = window.sxTestLab, tick = () => new Promise(r => setImmediate(r));
(async () => {
  // off
  let el = mk('tlab'); reply = () => Promise.resolve({ on: false, cases: [] }); L.mount(el); await tick();
  out.off = el.innerHTML; out.offNoBtn = !el.innerHTML.includes('data-tl-case');
  // on
  el = mk('tlab2'); reply = () => Promise.resolve({ on: true, cases: [{ id: 'pay_ok', group: 'Payment', label: 'Success' }, { id: 'deriv_ok', group: 'Deriv login', label: 'Success' }] });
  L.mount(el); await tick(); out.on = el.innerHTML;
  mk('tlErr');
  const click = async (id, r) => { reply = (p) => r instanceof Error ? Promise.reject(r) : Promise.resolve(r); await el.onclick({ target: { closest: () => ({ getAttribute: () => id }) } }); await tick(); };
  delete els.tlBan; log.length = 0;
  await click('pay_ok', { fake: true, kind: 'pay', what: 'ok', msg: '' }); out.payBanner = !!els.tlBan && els.tlBan.innerHTML.includes('Test mode'); out.payLog = log.slice();
  log.length = 0; delete els.tlBan; await click('deriv_ok', { fake: true, kind: 'deriv', what: 'ok', msg: 'Deriv connected. Demo account found.' }); out.derivLog = log.slice(); out.derivBanner = !!els.tlBan;
  log.length = 0; delete els.tlBan; await click('x', { kind: 'pay', what: 'ok' }); out.notFake = { banner: !!els.tlBan, log: log.slice(), err: els.tlErr.textContent };
  log.length = 0; await click('x', Object.assign(new Error('Test Lab is off.'), { status: 403 })); out.denied = els.tlErr.textContent;
  // Stop button
  delete els.tlBan; L.banner(true); log.length = 0; els.tlStop.onclick(); out.stop = { log: log.slice(), gone: !els.tlBan };
  console.log(JSON.stringify(out));
})();
'''
if shutil.which('node'):
    r = subprocess.run(['node', '-e', HARNESS, os.path.join(ROOT, 'static', 'test_lab.js')], capture_output=True, text=True, timeout=30)
    if r.returncode: print(r.stderr); sys.exit(1)
    o = json.loads(r.stdout.strip().splitlines()[-1])
    T('switch off: no buttons, a plain note says how to turn it on', o['offNoBtn'] and 'TEST_LAB=1' in o['off'])
    T('switch on: a button per case, grouped', o['on'].count('data-tl-case') == 2 and 'Deriv login' in o['on'] and 'Payment' in o['on'])
    T('payment case: Test mode bar shown, payment screen hook called with ok', o['payBanner'] and 'pay:ok' in o['payLog'])
    T('Deriv case: Test mode bar shown, the real words are shown', o['derivBanner'] and 'say:Deriv connected. Demo account found.' in o['derivLog'])
    T('a reply that is not marked fake is refused: no bar, no screen', o['notFake']['banner'] is False and not any(x.startswith(('pay:', 'say:')) for x in o['notFake']['log']) and 'could not be shown' in o['notFake']['err'])
    T('a server refusal is shown in plain words', o['denied'] == 'Test Lab is off.')
    T('Stop removes the bar and closes the screen', 'stop' in o['stop']['log'] and o['stop']['gone'])
else: print('SKIP part A: node missing')
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 390, 'height': 800})
        def h(route):
            u = route.request.url
            if not u.startswith('http://app.test/'): return route.abort()
            path = u[len('http://app.test/'):].split('?')[0].split('#')[0]
            f = os.path.join(ROOT, path)
            if path.startswith('static/') and os.path.isfile(f): return route.fulfill(body=open(f, 'rb').read(), content_type=mimetypes.guess_type(f)[0] or 'text/plain')
            if path.startswith('api/'): return route.fulfill(status=401, body='{}', content_type='application/json')
            route.fulfill(status=404, body='')
        pg.route('**/*', h); pg.goto('http://app.test/static/index.html'); pg.wait_for_timeout(1500)
        pg.evaluate("window.SXA=window.SXA||{refresh:()=>Promise.resolve(),api:()=>Promise.resolve({})}")
        txt = lambda: pg.evaluate("(document.querySelector('.panel')||{}).innerText||''")
        for w, want in (('ok', 'Payment received'), ('fail', 'did not go through'), ('slow', 'Still waiting'), ('cancel', 'Payment cancelled')):
            pg.evaluate("w=>window.sxLabHooks.pay(w)", w); pg.wait_for_timeout(500)
            T('Chromium, real screen for %s says "%s"' % (w, want), want in txt())
        pg.evaluate("localStorage.setItem('sxb_pend', JSON.stringify({ref:'REAL',u:'x',t:Date.now(),m:'mpesa'}))")
        for w in ('ok', 'fail', 'slow', 'cancel'): pg.evaluate("w=>window.sxLabHooks.pay(w)", w)
        pg.wait_for_timeout(400)
        T('Chromium: a real pending payment is still saved after every fake case', 'REAL' in (pg.evaluate("localStorage.getItem('sxb_pend')") or ''))
        pg.evaluate("window.sxTestLab.banner(true)"); T('Chromium: Test mode bar is on screen', pg.evaluate("!!document.getElementById('tlBan')"))
        pg.click('#tlStop'); T('Chromium: Stop removes the bar', pg.evaluate("!document.getElementById('tlBan')"))
        b.close()
except Exception as e: print("SKIP part B (browser not available here):", str(e)[:80])
print('%d/%d' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
