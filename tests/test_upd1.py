"""UPD1 checks: a newer app release sends a phone notification (kind 51) and an Alerts entry, once per person per build; tapping it opens the update prompt.
A fake FCM and a fake GitHub: nothing leaves the machine. Run: python tests/test_upd1.py   (node is optional: those parts print SKIP)"""
import os, sys, re, json, time, shutil, subprocess, threading, types
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'upd1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, update_alerts as ua
R = []
def T(name, ok): R.append((name, bool(ok)))

SENT = []
class Resp:
    status_code = 200; text = '{}'
    def json(self): return {}
class FakeReq:
    def post(self, url, json=None, headers=None, data=None, timeout=None):
        if 'messages:send' in url: SENT.append(json['message'])
        return Resp()
push.requests = FakeReq(); push._access_token = lambda: 'fake'
push._account = lambda: {'project_id': 'p', 'client_email': 'e@p.iam', 'private_key': 'k'}
push.quiet_now = lambda *a, **k: False
C = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in ('boss@x.com', 'free@x.com', 'ann@x.com')}
for e in uid: push.save_token(uid[e], 'tok_%s_' % e.split('@')[0] + 'x' * 30)
now = time.time()
rel = lambda b, age_days=0: (lambda: {'build': b, 'at': int(now - age_days * 86400)})

T('the build number is read from the tag the same way as the app', ua.build('app-123') == 123 and ua.build('app-') == 0 and ua.build('v2') == 2 and ua.build(None) == 0)
T('kind 51 exists, in the system category, high channel', push.KINDS.get(51, {}).get('cat') == 'system' and push.KINDS[51]['ch'] == 'hi')
n = ua.update_job(now, rel(55))
T('everyone with a phone is reached, free users too (3 people)', n == 3 and len(SENT) == 3)
d = SENT[0]['data'] if SENT else {}
T('the payload opens the update prompt (route #update, kind 51)', d.get('route') == '#update' and str(d.get('kind')) == '51')
T('the banner says which build', 'Build 55' in json.dumps(SENT[0]) if SENT else False)
SENT.clear(); T('the same build is never sent twice to the same person', ua.update_job(now, rel(55)) == 0 and not SENT)
T('a newer build is announced again', ua.update_job(now, rel(56)) == 3)
SENT.clear(); T('an old release (older than 3 days) is not announced', ua.update_job(now, rel(57, age_days=4)) == 0 and not SENT)
T('no answer from GitHub: nothing happens, no crash', ua.update_job(now, lambda: None) == 0)
def has51(u):
    try: return any(int(e.get('kind') or 0) == 51 for e in json.loads(st.get('inbox:' + u) or '[]'))
    except Exception: return False
T('an Alerts entry is kept for each person, once per build', all(has51(u) for u in uid.values()) and all(sum(1 for e in json.loads(st.get('inbox:' + u) or '[]') if int(e.get('kind') or 0) == 51 and 'Build 55' in e.get('body', '')) == 1 for u in uid.values()))
push.quiet_now = lambda *a, **k: True
SENT.clear(); T('quiet hours hold it back (and it is tried again next run)', ua.update_job(now, rel(58)) == 0 and not SENT)
push.quiet_now = lambda *a, **k: False
T('...and it goes out when quiet hours end', ua.update_job(now, rel(58)) == 3)
T('the job is on the alerts loop', "update_alerts" in open(os.path.join(ROOT, 'backend', 'app.py'), encoding='utf-8').read() and 'register_job(\'update_alerts\'' in open(os.path.join(ROOT, 'backend', 'update_alerts.py'), encoding='utf-8').read())
from backend import alerts
ua.register(); j = alerts._jobs.get('update_alerts') or {}
T('registered on the alerts loop every 30 minutes', j.get('interval') == 1800)
T('first run is about 60 seconds after start, not at once', 50 <= (time.time() - j.get('last_run', 0)) * -1 + 1800 <= 61)
T('it runs in its own thread so a slow GitHub never holds up other jobs', 'threading.Thread(target=update_job' in open(os.path.join(ROOT, 'backend', 'update_alerts.py'), encoding='utf-8').read())

# ---------- the app: a tap on the notification opens the prompt (node) ----------
live = open(os.path.join(ROOT, 'static', 'live.js'), encoding='utf-8').read(); upd = open(os.path.join(ROOT, 'static', 'update.js'), encoding='utf-8').read()
T('live.js: route "update" calls SXBUpdate.open() before the normal screen map', re.search(r'if \(r === "update"\) \{ try \{ window\.SXBUpdate && window\.SXBUpdate\.open\(\); \} catch \(x\) \{\} return; \}.*?r = GOMAP\[r\] \|\| r;', live, re.S))
T('update.js: open() clears "Maybe later", looks right now and says when already current', 'function open()' in upd and 'sessionStorage.removeItem(LATER)' in upd.split('function open()')[1][:300] and 'You are on the latest version.' in upd and 'open: open' in upd)
if shutil.which('node'):
    for f in ('live.js', 'update.js'):
        T('%s still parses' % f, subprocess.run(['node', '--check', os.path.join(ROOT, 'static', f)], capture_output=True).returncode == 0)
    js = r"""
var calls = [], store = {}, LATER = 'sxb_update_later';
global.window = global; global.sessionStorage = {getItem:k=>store[k]||null, setItem:(k,v)=>{store[k]=v}, removeItem:k=>{delete store[k]}};
global.localStorage = {getItem:()=>null, setItem(){}, removeItem(){}};
global.addEventListener = function(){}; global.document = {addEventListener(){}, getElementById(){return null}, readyState:'loading'}; global.fetch = undefined;
global.Capacitor = {isNativePlatform: () => true};
global.sxToast = m => calls.push('toast:' + m);
""" + upd + r"""
store[LATER] = '1';
SXBUpdate.open();
console.log(JSON.stringify({later: store[LATER] || null, fn: typeof SXBUpdate.open}));
"""
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    out = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else {}
    T('node: open() works and clears the "Maybe later" mark', out.get('fn') == 'function' and out.get('later') is None)
else: print('SKIP node parts')
bad = [n for n, ok in R if not ok]
print('\n'.join(('ok   ' if ok else 'FAIL ') + n for n, ok in R)); print('%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
