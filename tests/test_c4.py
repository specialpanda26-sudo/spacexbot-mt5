"""C4 checks: the cartoon how-to guide (backend/guide.py, GET /api/guide, static/guide.js). No network. Run: python tests/test_c4.py"""
import os, sys, glob, re, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_c4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD', BROKER_KEY='unit-test-lock-key-0123456789')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import guide, alerts
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
c.get('/api/me', headers=H('amy@x.com'))
rd = lambda *p: open(os.path.join(ROOT, *p), encoding='utf-8').read()
ix, js = rd('static', 'index.html'), rd('static', 'guide.js'); txt = str(guide.STEPS)
j = c.get('/api/guide', headers=H('amy@x.com')).get_json()
T('signed in: 9 steps, total matches', len(j['steps']) == 9 and j['total'] == 9)
T('signed out is refused', c.get('/api/guide').status_code in (401, 403))
T('step ids are unique and every step has 2 to 5 plain points', len({s['id'] for s in guide.STEPS}) == 9 and all(2 <= len(s['points']) <= 5 and s['title'] and s['intro'] for s in guide.STEPS))
T('covers the 9 topics asked for', [s['id'] for s in guide.STEPS] == ['signup', 'subscribe', 'connect', 'mode', 'start', 'signal', 'safety', 'alerts', 'help'])
T('every cartoon is one the site already has (window.IL2)', all(re.search(r'IL2\.%s=|[,{]%s:il2\(' % (s['art'], s['art']), ix) for s in guide.STEPS))
T('wording says demo or real, and the word REAL is explained', 'Demo' in txt and 'Real' in txt and 'REAL' in txt)
T('no profit promise', not re.search(r'guarantee|risk.free|sure profit|always win|make money', txt + js, re.I))
T('names all three brokers and says Binance does not trade yet', all(b in txt for b in ('Deriv', 'MT5', 'Binance')) and 'testnet only for now' in txt)
T('brand line is Ogolla Tech (two L, the owner is Ogolla)', j['brand'] == 'Powered by Ogolla Tech')
T('the one-L spelling is nowhere in the app files', not [f for f in glob.glob(os.path.join(ROOT, 'backend', '*.py')) + glob.glob(os.path.join(ROOT, 'static', '*.js')) + glob.glob(os.path.join(ROOT, 'emails', '*.html')) + [os.path.join(ROOT, 'static', 'index.html')] if 'Ogola' in open(f, encoding='utf-8').read()])
import backend.course as course
cm = {l['id']: l['art'] for l in course.LESSONS}; gm = {s['id']: s['art'] for s in guide.STEPS}
T('cartoons follow what the site already shows for the same topic', gm['signup'] == 'rocket' and gm['subscribe'] == 'coin' and gm['connect'] == 'plug' and gm['alerts'] == 'push' and gm['mode'] == cm['accounts'] and gm['signal'] == cm['signal'] and gm['safety'] == cm['rules'] and gm['start'] == cm['meet'])
T('page loads guide.js', '<script src="/static/guide.js"></script>' in ix)
T('the page escapes text and calls the server route', 'function esc' in js and '/api/guide' in js and 'innerHTML' in js)
T('no colours written, only site variables and classes', not re.search(r'#[0-9a-fA-F]{3,6}\b', js) and all(k in js for k in ('card-head', 'chip', 'btn', 'panel', 'note', 'muted')))
if shutil.which('node'):
    r = subprocess.run(['node', '--check', os.path.join(ROOT, 'static', 'guide.js')], capture_output=True, text=True); T('guide.js is valid JavaScript', r.returncode == 0)
for f in glob.glob(DB + '*'): os.remove(f)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
