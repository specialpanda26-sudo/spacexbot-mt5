"""Checks Section 10b: backend/envcheck.py (names and sentences only, never a value), GET /api/admin/health returns env + env_count for admins only,
and the Setup check card in the Admin panel. Run: python tests/test_env10.py"""
import os, sys, json, base64, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, '_env10_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='SENTINEL-ea-key-value-123456', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import envcheck as E
from backend.app import app
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
SA = json.dumps({'private_key': 'SENTINEL-pk', 'client_email': 'a@b.iam', 'project_id': 'p'})
GOOD = dict(DATABASE_URL='postgresql://postgres.abcd:SENTINELpw@aws-0-eu.pooler.supabase.com:5432/postgres', BASE_URL='https://spacexbot.onrender.com', EA_KEY='SENTINEL-ea-key-value-123456',
    ADMIN_EMAILS='boss@gmail.com', ADMIN_PASS='SENTINELpass99', SUPABASE_URL='https://abc.supabase.co', SUPABASE_ANON_KEY='SENTINELanon', SUPABASE_SERVICE_KEY='SENTINELsvc',
    AUTH_MAIL_PROVIDER='resend', GOOGLE_WEB_CLIENT_ID='123.apps.googleusercontent.com', RESEND_API_KEY='re_SENTINELkey', MAIL_FROM='spaceXBot <alerts@mybrand.com>',
    PAYHERO_API_KEY='SENTINELpk', PAYHERO_API_SECRET='SENTINELps', PAYHERO_CHANNEL_ID='14575', PAYHERO_CALLBACK_SECRET='SENTINELcb', PAYHERO_PROVIDER='m-pesa-direct',
    PAYPAL_CLIENT_ID='SENTINELppc', PAYPAL_SECRET='SENTINELpps', PAYPAL_ENV='live', FCM_SERVICE_ACCOUNT=SA, PUBLIC_URL='https://spacexbot.onrender.com',
    BROKER_KEY='SENTINELbroker-key-long', DERIV_APP_ID='12345')
def lvl(env, key):
    for r in E.report(env):
        if r['key'] == key or r['key'].startswith(key): return r['level']
def w(**kv): d = dict(GOOD); d.update(kv); return d
def wo(*ks): d = dict(GOOD); [d.pop(k) for k in ks]; return d

s = E.summary(E.report(GOOD)); T('a fully set environment has nothing to fix or check', s['bad'] == 0 and s['warn'] == 0 and s['ok'] >= 20)
s = E.summary(E.report({})); T('an empty environment is all red or amber', s['bad'] >= 8 and s['ok'] <= 3)
T('no value, not even its first characters, appears in the report', all(v[:12] not in ' '.join(r['key'] + ' ' + r['msg'] for r in E.report(GOOD)) for v in GOOD.values() if len(v) >= 12))
T('no secret value ever appears in the report', 'SENTINEL' not in json.dumps(E.report(GOOD)) and 'SENTINEL' not in json.dumps(E.report(w(DEV_AUTH='1', PAYHERO_PROVIDER='nope'))))
for k in ('DATABASE_URL', 'BASE_URL', 'EA_KEY', 'SUPABASE_URL', 'PAYHERO_API_KEY', 'PAYHERO_API_SECRET', 'PAYHERO_CHANNEL_ID', 'PAYHERO_CALLBACK_SECRET', 'BROKER_KEY', 'DERIV_APP_ID'):
    T('missing %s is red' % k, lvl(wo(k), k) == 'bad')
for k in ('ADMIN_EMAILS', 'SUPABASE_SERVICE_KEY', 'GOOGLE_WEB_CLIENT_ID', 'RESEND_API_KEY', 'FCM_SERVICE_ACCOUNT', 'PUBLIC_URL'):
    T('missing %s is amber (a feature is off, nothing breaks)' % k, lvl(wo(k), k) == 'warn')
T('example text from .env.example is red', lvl(w(EA_KEY='change-me-long-random'), 'EA_KEY') == 'bad' and lvl(w(BASE_URL='https://your-service.onrender.com'), 'BASE_URL') == 'bad'
  and lvl(w(PAYHERO_CALLBACK_SECRET='another-long-random'), 'PAYHERO_CALLBACK_SECRET') == 'bad' and lvl(w(MAIL_FROM='spaceXBot <alerts@yourdomain.com>'), 'MAIL_FROM') == 'bad')
T('a short EA key or BROKER_KEY is flagged', lvl(w(EA_KEY='short'), 'EA_KEY') == 'warn' and lvl(w(BROKER_KEY='short'), 'BROKER_KEY') == 'bad')
T('BASE_URL must be https', lvl(w(BASE_URL='http://x.onrender.com'), 'BASE_URL') == 'bad')
T('an empty ADMIN_PASS is fine (pass off); an example or short one is not', lvl(wo('ADMIN_PASS'), 'ADMIN_PASS') == 'ok' and lvl(w(ADMIN_PASS='change-me-8-or-more-characters'), 'ADMIN_PASS') == 'bad' and lvl(w(ADMIN_PASS='abc'), 'ADMIN_PASS') == 'warn')
T('DEV_AUTH=1 is red and DEV_AUTH unset adds no row', lvl(w(DEV_AUTH='1'), 'DEV_AUTH') == 'bad' and lvl(GOOD, 'DEV_AUTH') is None)
T('AUTH_MAIL_PROVIDER=resend without the Resend pieces is red', lvl(wo('RESEND_API_KEY'), 'AUTH_MAIL_PROVIDER') == 'bad' and lvl(wo('MAIL_FROM'), 'AUTH_MAIL_PROVIDER') == 'bad')
T('a Resend key must start with re_', lvl(w(RESEND_API_KEY='abc123'), 'RESEND_API_KEY') == 'bad')
T('a provider typo, a CALLBACK_URL on another site and a non-number channel are red', lvl(w(PAYHERO_PROVIDER='nope'), 'PAYHERO_PROVIDER') == 'bad' and lvl(w(CALLBACK_URL='https://other.com/x'), 'CALLBACK_URL') == 'bad' and lvl(w(PAYHERO_CHANNEL_ID='abc'), 'PAYHERO_CHANNEL_ID') == 'bad')
T('PayPal off or in sandbox is amber', lvl(wo('PAYPAL_SECRET'), 'PAYPAL_CLIENT_ID') == 'warn' and lvl(w(PAYPAL_ENV='sandbox'), 'PAYPAL_ENV') == 'warn')
T('FCM: base64 JSON ok; garbage and incomplete JSON red', lvl(w(FCM_SERVICE_ACCOUNT=base64.b64encode(SA.encode()).decode()), 'FCM_SERVICE_ACCOUNT') == 'ok' and lvl(w(FCM_SERVICE_ACCOUNT='not json'), 'FCM_SERVICE_ACCOUNT') == 'bad' and lvl(w(FCM_SERVICE_ACCOUNT='{"project_id":"p"}'), 'FCM_SERVICE_ACCOUNT') == 'bad')
T('PUBLIC_URL on another site than BASE_URL is amber; http is red', lvl(w(PUBLIC_URL='https://other.onrender.com'), 'PUBLIC_URL') == 'warn' and lvl(w(PUBLIC_URL='http://x'), 'PUBLIC_URL') == 'bad')
T('DERIV_REAL=1 is amber', lvl(w(DERIV_REAL='1'), 'DERIV_REAL') == 'warn' and lvl(GOOD, 'DERIV_REAL') is None)
T('quotes around a value do not hide it', lvl(w(BASE_URL='"https://spacexbot.onrender.com"'), 'BASE_URL') == 'ok')
T('report() with no argument reads the real environment', any(r['key'] == 'EA_KEY' and r['level'] == 'ok' for r in E.report()))

c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
c.get('/api/me', headers=H('boss@x.com')); c.get('/api/me', headers=H('joe@x.com'))
T('a normal user cannot read the setup check', c.get('/api/admin/health', headers=H('joe@x.com')).status_code == 403)
r = c.get('/api/admin/health', headers=H('boss@x.com')); j = r.get_json() or {}
T('the admin gets env + env_count and the old keys are still there', r.status_code == 200 and isinstance(j.get('env'), list) and j['env'] and set(j.get('env_count', {})) == {'bad', 'warn', 'ok'} and 'problems' in j and 'ok' in j and 'mpesa_ready' in j)
T('the endpoint never returns a secret value', 'SENTINEL' not in r.get_data(as_text=True))

page = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read(); i = page.find('function envCard(')
T('index.html: the card is defined once, before panel(), and called once after the panel is built', page.count('function envCard(') == 1 and i < page.find('function panel(){ovEl.classList.add("wide");') and page.count(' envCard();') == 1 and page.count('<div id="aEnv"></div>') == 1)
if shutil.which('node'):
    fn = page[i:page.find('function panel(){ovEl.classList.add("wide");')]
    JS = r'''
const src = process.argv[1]; const box = { dataset: {}, innerHTML: '' }; const btns = {};
const $ = (s) => s === '#aEnv' ? box : (btns[s] = btns[s] || {}); const esc = (t) => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
let calls = 0; const SXA = { api: (u) => { calls++; return Promise.resolve({ env: [{ group: 'Core', key: 'EA_KEY', level: 'bad', msg: 'Not set <b>' }, { group: 'Emails', key: 'MAIL_FROM', level: 'warn', msg: 'Check it' }, { group: 'Core', key: 'BASE_URL', level: 'ok', msg: 'Set.' }], env_count: { bad: 1, warn: 1, ok: 1 } }); } };
new Function('$', 'esc', 'SXA', src + ';envCard();')($, esc, SXA);
setTimeout(() => { const a = box.innerHTML; btns['#aEnvA'].onclick(); const b = box.innerHTML; btns['#aEnvR'].onclick(); setTimeout(() => console.log(JSON.stringify({ a, b, calls })), 20); }, 20);'''
    r = subprocess.run(['node', '-e', JS, fn], capture_output=True, text=True)
    if r.returncode: print(r.stderr[-600:]); T('the card runs in node', False)
    else:
        o = json.loads(r.stdout.strip().splitlines()[-1])
        T('card: problems first, ok rows hidden, escaped text, counts in the chip', 'EA_KEY' in o['a'] and 'MAIL_FROM' in o['a'] and 'BASE_URL' not in o['a'] and '1 to fix' in o['a'] and '&lt;b&gt;' in o['a'] and 'class="chip stop"' in o['a'] and 'class="chip watch"' in o['a'] and '<b>Not' not in o['a'])
        T('card: Show everything reveals the ok rows; Check again asks the server again', 'BASE_URL' in o['b'] and 'Show problems only' in o['b'] and o['calls'] == 2)
else: print('SKIP node card checks')
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
