"""C-AUTH 2 checks: Log in with Deriv button + return message (static/deriv_login.js, hooks in static/index.html). Needs node. Run: python tests/test_cauth2.py"""
import os, sys, shutil, subprocess, json
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
JS = os.path.join(ROOT, 'static', 'deriv_login.js'); IDX = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
HARNESS = r'''
const fs = require('fs'); const out = {};
function boot(search, hash, api) {
  const el = {}; const mk = (id) => (el[id] = el[id] || { id, textContent: '', hidden: true });
  const hist = []; mk('toast'); mk('pLn');
  global.window = { SXA: api === null ? undefined : { api }, location: { search, hash, pathname: '/', href: 'http://t/' }, history: { replaceState: (a, b, u) => hist.push(u) } };
  global.document = { getElementById: (id) => el[id] || null };
  global.setTimeout = (f) => 0; global.clearTimeout = () => 0;
  eval(fs.readFileSync(process.argv[1], 'utf8'));
  return { el, hist, W: global.window };
}
const ok = (v) => Promise.resolve(v); const bad = (o) => Promise.reject(o);
(async () => {
  let t = boot('', '#connect', (p) => ok({}));
  out.html = t.W.sxDerivLogin.html(); out.noParam = t.hist.length === 0 && t.el.toast.textContent === '';
  // click -> opens only auth.deriv.com
  let calls = [];
  t = boot('', '', (p) => { calls.push(p); return p === '/api/deriv/login' ? ok({ url: 'https://auth.deriv.com/oauth2/auth?x=1' }) : ok({ seconds_left: null }); });
  let btn = { disabled: false }, err = { textContent: '' }; t.W.sxDerivLogin.wire(btn, err); btn.onclick(); await new Promise(r => setImmediate(r));
  out.go = { href: t.W.location.href, calls, disabled: btn.disabled };
  t = boot('', '', (p) => p === '/api/deriv/login' ? ok({ url: 'https://evil.example/steal' }) : ok({}));
  btn = { disabled: false }; err = { textContent: '' }; t.W.sxDerivLogin.wire(btn, err); btn.onclick(); await new Promise(r => setImmediate(r));
  out.evil = { href: t.W.location.href, disabled: btn.disabled, err: err.textContent };
  t = boot('', '', (p) => p === '/api/deriv/login' ? bad({ status: 503, message: 'Deriv login is not switched on yet.' }) : ok({}));
  btn = { disabled: false }; err = { textContent: '' }; t.W.sxDerivLogin.wire(btn, err); btn.onclick(); await new Promise(r => setImmediate(r));
  out.err503 = { href: t.W.location.href, disabled: btn.disabled, err: err.textContent };
  t = boot('', '', (p) => p === '/api/deriv/login' ? bad({ status: 402, message: 'x' }) : ok({}));
  btn = { disabled: false }; err = { textContent: '' }; t.W.sxDerivLogin.wire(btn, err); btn.onclick(); await new Promise(r => setImmediate(r));
  out.err402 = err.textContent;
  // days left note
  t = boot('', '', (p) => ok({ seconds_left: 5 * 86400, days_left: 5 })); btn = { disabled: false }; t.W.sxDerivLogin.wire(btn, { textContent: '' }); await new Promise(r => setImmediate(r));
  out.note = t.el.pLn.textContent;
  // coming back
  t = boot('?deriv=ok', '#connect', (p) => ok({ last: { ok: true, msg: 'Deriv connected. Balance read.' } })); await new Promise(r => setImmediate(r));
  out.backOk = { toast: t.el.toast.textContent, hist: t.hist };
  t = boot('?deriv=fail', '#connect', (p) => ok({ last: { ok: false, msg: 'Deriv login was cancelled. Nothing was connected.' } })); await new Promise(r => setImmediate(r));
  out.backFail = { toast: t.el.toast.textContent, hist: t.hist };
  t = boot('?deriv=fail', '#connect', (p) => ok({ last: null })); await new Promise(r => setImmediate(r));
  out.backNoMsg = t.el.toast.textContent;
  console.log(JSON.stringify(out));
})();
'''
r = subprocess.run(['node', '-e', HARNESS, JS], capture_output=True, text=True, timeout=30)
if r.returncode: print(r.stderr); sys.exit(1)
o = json.loads(r.stdout.strip().splitlines()[-1]); R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
T('button html has id pL and the words Log in with Deriv', 'id="pL"' in o['html'] and 'Log in with Deriv' in o['html'])
T('button html shows a Deriv logo or badge', 'sxLogo' in open(JS, encoding='utf-8').read() and ('<span aria-hidden' in o['html'] or '<img' in o['html'] or '<svg' in o['html']))
T('button html says no token copy and no withdraw', 'never copy a token' in o['html'] and 'never to withdraw' in o['html'])
T('no ?deriv= in the address: nothing happens', o['noParam'])
T('tap asks the server for the login address', '/api/deriv/login' in o['go']['calls'])
T('tap opens the auth.deriv.com address', o['go']['href'].startswith('https://auth.deriv.com/'))
T('an address on another site is refused', o['evil']['href'] == 'http://t/' and 'Could not open' in o['evil']['err'] and o['evil']['disabled'] is False)
T('server error text is shown and the button works again', o['err503']['err'] == 'Deriv login is not switched on yet.' and o['err503']['disabled'] is False and o['err503']['href'] == 'http://t/')
T('no plan (402) says a plan is needed', 'plan is needed' in o['err402'])
T('days left note', 'about 5 more day' in o['note'])
T('back ok: toast is the server message, address cleaned, #connect kept', o['backOk']['toast'] == 'Deriv connected. Balance read.' and o['backOk']['hist'] == ['/#connect'])
T('back fail: toast is the server message', 'cancelled' in o['backFail']['toast'])
T('back fail with no saved message: generic words', o['backNoMsg'] == 'Deriv login did not work. Try again.')
T('index.html: script tag', IDX.count('<script src="/static/deriv_login.js"></script>') == 1)
T('index.html: button shown only for Deriv', 'n==="Deriv"&&window.sxDerivLogin?window.sxDerivLogin.html()' in IDX)
T('index.html: button wired to the error line', 'window.sxDerivLogin.wire($("#pL"),$("#pE"))' in IDX)
T('index.html: token paste field still there', 'id="pF"' in IDX and 'id="pG"' in IDX)
print('%d/%d' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
