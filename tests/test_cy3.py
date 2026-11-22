"""CY3 tests: the Auto-cycle card on the Bot tab + the extra facts (today, last) in GET /api/cycle. Needs node for the card part (skipped if missing).
Run: python tests/test_cy3.py   The card code goes to node through a pipe and runs against a fake page and a fake server (no temp files)."""
import os, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_cy3_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, cycle, groupcap, deriv_group as dg
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
me = H('amy@x.com'); c.get('/api/me', headers=me); U = 'dev-amy@x.com'

# ---- server facts
j = c.get('/api/cycle', headers=me).get_json()
T('GET shows today = 0 and no last reason at the start', j.get('today') == 0 and j.get('last') == '' and j['settings']['on'] is False)
st.put('cyc_why:' + U, 'daily limit of 2 new groups reached'); st.put(dg._day_key(U, __import__('time').time()), 2)
j = c.get('/api/cycle', headers=me).get_json()
T('after the engine ran: today and the plain-words reason are shown', j['today'] == 2 and j['last'] == 'daily limit of 2 new groups reached')
st.put('cyc_why:' + U, 'cycle off'); T("the reason 'cycle off' is not shown as a problem", c.get('/api/cycle', headers=me).get_json()['last'] == '')
j = c.post('/api/cycle', json={'on': True}, headers=me).get_json(); T('POST also returns today and last', 'today' in j and 'last' in j and j['settings']['on'] is True)
T("another person's facts are separate", c.get('/api/cycle', headers=H('bob@x.com')).get_json()['today'] == 0)
T('cycle.view works for the owner (uid empty) too', 'today' in cycle.view('') and 'last' in cycle.view(''))

# ---- the page
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the CY3 block is in the page exactly once', html.count('/*CY3-start*/') == 1 and html.count('/*CY3-end*/') == 1)
T('the card sits under the group card and above Run check', html.index('id="gcSave"') < html.index('/*CY3-start*/') < html.index('card(["Run check",""]'))
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
i = html.index('/*CY3-start*/'); BLOCK = html[i:html.index('/*CY3-end*/', i)]
JS = r"""
const BLOCK = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
// the block reads window.SXA and the global SXA, so give both
function runWith(st) {
  const E = {}, get = id => E[id] || (E[id] = { id, value: '', textContent: '', attrs: {}, disabled: false, setAttribute(k, v) { this.attrs[k] = v; } });
  const $ = s => get(s.slice(1)); const cards = []; const vb = { appendChild: x => cards.push(x) }; const card = (h, body) => ({ h, body }); const toasts = [];
  const SXA = { api: (p, o) => { st.calls.push([p, o && o.body]); return st.fail ? Promise.reject(new Error(st.fail)) : Promise.resolve(st.data); } };
  const win = st.noSXA ? {} : { SXA };
  new Function('vb', '$', 'card', 'toast', 'window', 'SXA', BLOCK)(vb, $, card, m => toasts.push(m), win, st.noSXA ? undefined : SXA);
  return { E, get, cards, toasts };
}
const tick = () => new Promise(r => setImmediate(r));
(async () => {
  let st = { calls: [], data: { settings: { on: true, max_per_day: 7 }, note: '', today: 3, last: '' } }; let p = runWith(st); await tick();
  ok('the card is added with the title Auto-cycle', p.cards.length === 1 && p.cards[0].h[0] === 'Auto-cycle');
  ok('the card loads GET /api/cycle on start', st.calls[0] && st.calls[0][0] === '/api/cycle' && st.calls[0][1] === undefined);
  ok('the switch, the number and the chip show the saved choices', p.get('cyOn').attrs['aria-checked'] === true && p.get('cyN').value === 7 && p.get('cyChip').textContent === 'On');
  ok('the note says how many groups opened today', p.get('cyNote').textContent === 'New groups opened today: 3 of 7.');

  st = { calls: [], data: { settings: { on: true, max_per_day: 10 }, note: 'Switch on the group profit target first.', today: 0, last: '' } }; p = runWith(st); await tick();
  ok('switched on but the group target is missing: the chip says Needs setup and the plain-words note is shown', p.get('cyChip').textContent === 'Needs setup' && p.get('cyNote').textContent.indexOf('Switch on the group profit target first.') === 0);

  st = { calls: [], data: { settings: { on: true, max_per_day: 2 }, note: '', today: 2, last: 'daily limit of 2 new groups reached' } }; p = runWith(st); await tick();
  ok('the last reason is shown in words', p.get('cyNote').textContent.indexOf('Last time it did not open one: daily limit of 2 new groups reached.') > 0);

  st = { calls: [], data: { settings: { on: false, max_per_day: 10 }, note: '', today: 0, last: 'x' } }; p = runWith(st); await tick();
  ok('switched off: chip Off and no note', p.get('cyChip').textContent === 'Off' && p.get('cyNote').textContent === '');

  p.get('cyOn').onclick.call(p.get('cyOn')); ok('tapping the switch flips it and the chip at once', p.get('cyOn').attrs['aria-checked'] === true && p.get('cyChip').textContent === 'On');
  st.data = { settings: { on: true, max_per_day: 25 }, note: '', today: 0, last: '' }; p.get('cyN').value = '25'; st.calls.length = 0;
  p.get('cySave').onclick.call(p.get('cySave')); await tick(); await tick();
  ok('Save posts the switch and the number to /api/cycle', st.calls.length === 1 && st.calls[0][0] === '/api/cycle' && st.calls[0][1].on === true && st.calls[0][1].max_per_day === 25);
  ok('after Save the page says so and shows the server answer', p.get('cyMsg').textContent === 'Saved on the server.' && p.get('cyN').value === 25 && p.toasts.indexOf('Auto-cycle saved') >= 0 && p.get('cySave').disabled === false);

  p.get('cyN').value = ''; st.calls.length = 0; p.get('cySave').onclick.call(p.get('cySave')); await tick(); await tick();
  ok('a blank number is not sent, so the saved number stays', st.calls[0][1].max_per_day === undefined && st.calls[0][1].on === true);

  st.fail = 'New groups per day must be a whole number from 1 to 100'; p.get('cySave').onclick.call(p.get('cySave')); await tick(); await tick();
  ok('a refused save shows the server message and the button comes back', p.get('cyMsg').textContent === st.fail && p.get('cySave').disabled === false);

  st = { calls: [], noSXA: true }; p = runWith(st); await tick();
  ok('signed out: nothing is requested and Save asks to sign in', st.calls.length === 0 && (p.get('cySave').onclick.call(p.get('cySave')), p.toasts.indexOf('Sign in first') >= 0));
  console.log(JSON.stringify(OUT));
})();
"""
r = subprocess.run(['node', '-e', JS], input=json.dumps(BLOCK), capture_output=True, text=True, timeout=60)
try: out = json.loads(r.stdout.strip().splitlines()[-1])
except Exception: print(r.stdout[-400:], r.stderr[-900:]); out = []
T('the card code ran in node', bool(out))
for n, ok in out: T(n, ok)
bad_ = [n for n, ok in R if not ok]
print('\n%d passed, %d failed' % (len(R) - len(bad_), len(bad_)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_ else 0)
