"""Section N1 checks: the Android app registers its phone for push alerts (static/live.js, code between /*N1-start*/ and /*N1-end*/).
Runs the real live.js in node against a fake phone (Capacitor push plugin), fake server and fake Supabase. Needs node; skipped if missing.
Run: python tests/test_push1.py"""
import os, sys, shutil, subprocess, json
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'live.js')
HARNESS = r'''
const fs = require('fs'); const SRC = fs.readFileSync(process.argv[1], 'utf8'); const TOKEN = 'tok_' + 'x'.repeat(40);
const sleep = (ms) => new Promise(r => setTimeout(r, ms)); const out = {};
async function boot(o) {
  o = o || {}; const store = Object.assign({}, o.store || {}), order = [], posts = [], toasts = [], sb = [];
  global.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
  global.sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} };
  global.location = { origin: 'http://t', hash: o.hash || '' };
  const st = { uid: 'u1', failTok: o.failTok || 0, offline: !!o.offline }; let cb = null;
  const auth = { onAuthStateChange(f) { cb = f; }, getSession: () => Promise.resolve({ data: { session: { access_token: 'tk', user: { id: st.uid } } }, error: null }),
                 signOut: () => { order.push('signOut'); return Promise.resolve({ data: {}, error: null }); } };
  global.fetch = (path, init) => {
    init = init || {}; const body = init.body ? JSON.parse(init.body) : null;
    if (path === '/api/me') {
      if (st.offline) return Promise.reject(new TypeError('Failed to fetch'));
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ uid: st.uid, email: st.uid + '@x.com', verified: true, active: true }) });
    }
    if (path === '/api/push/token') {
      order.push('token'); posts.push({ path, body, auth: (init.headers || {}).Authorization });
      if (st.failTok > 0) { st.failTok--; return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: 'boom' }) }); }
    }
    if (path === '/api/push/unregister') { order.push('unregister'); posts.push({ path, body }); }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ ok: true }) });
  };
  const plug = { calls: [], L: {} };
  const P = {
    checkPermissions: () => { plug.calls.push('check'); return Promise.resolve({ receive: o.perm || 'prompt' }); },
    requestPermissions: () => { plug.calls.push('request'); return Promise.resolve({ receive: o.asked || 'granted' }); },
    register: () => { plug.calls.push('register'); if (o.token !== false) setTimeout(() => plug.L.registration && plug.L.registration({ value: o.token || TOKEN }), 0); return Promise.resolve(); },
    addListener: (n, f) => { plug.L[n] = f; return Promise.resolve({ remove() {} }); },
  };
  const win = { SXB: { sb: { url: 'https://x.supabase.co', key: 'k' } }, supabase: { createClient: () => ({ auth }) }, sxToast: m => toasts.push(m) };
  if (o.native !== false) win.Capacitor = { isNativePlatform: () => true, registerPlugin: () => P, Plugins: { PushNotifications: P } };
  global.window = win; eval(SRC);
  const X = win.SXA;
  return { X, plug, posts, toasts, order, store, st,
    async signIn(uid) { st.uid = uid || st.uid; await cb('SIGNED_IN', { user: { id: st.uid } }); await sleep(40); } };
}
const tokPosts = (b) => b.posts.filter(p => p.path === '/api/push/token');
(async () => {
  let b;
  b = await boot({ native: false }); await b.signIn(); out.browser = { calls: b.plug.calls, posts: b.posts.length };
  b = await boot({ perm: 'prompt' }); await b.signIn(); out.ask = { calls: b.plug.calls, posts: b.posts.slice(), saved: b.store.sxb_pt };
  b = await boot({ perm: 'granted' }); await b.signIn(); out.granted = { calls: b.plug.calls, n: tokPosts(b).length };
  b = await boot({ perm: 'prompt', asked: 'denied' }); await b.signIn(); await b.X.refresh(); await sleep(30); await b.X.refresh(); await sleep(30);
  out.denied = { calls: b.plug.calls, posts: b.posts.length, toasts: b.toasts.length, toast: b.toasts[0] };
  b = await boot({ perm: 'granted', token: false, store: { sxb_pt: TOKEN } }); await b.signIn();
  out.saved = { posts: tokPosts(b).map(p => p.body), calls: b.plug.calls };
  b = await boot({ perm: 'granted' }); await b.signIn(); await b.X.refresh(); await sleep(30); await b.X.refresh(); await sleep(30);
  out.dedupe = { n: tokPosts(b).length };
  b = await boot({ perm: 'granted' }); await b.signIn('u1'); await b.signIn('u2'); out.twoUsers = { n: tokPosts(b).length, regs: b.plug.calls.filter(c => c === 'register').length };
  b = await boot({ perm: 'granted' }); await b.signIn(); b.order.length = 0; await b.X.signOut(); await sleep(20);
  out.signout = { order: b.order, post: b.posts.find(p => p.path === '/api/push/unregister'), saved: b.store.sxb_pt === undefined };
  b = await boot({ native: false }); await b.signIn(); b.order.length = 0; await b.X.signOut(); await sleep(20); out.signoutBrowser = { order: b.order };
  b = await boot({ perm: 'granted' }); await b.signIn(); const h = [];
  for (const r of ['#signals', '#plans', '#stats', '#home', '#trades', '#javascript:alert(1)', '#constructor', '#../x', '#admin', '']) {
    global.location.hash = '#start'; b.plug.L.pushNotificationActionPerformed({ notification: { data: { route: r } } }); h.push(global.location.hash);
  }
  global.location.hash = '#start'; b.plug.L.pushNotificationActionPerformed({ notification: {} }); b.plug.L.pushNotificationActionPerformed(null); h.push(global.location.hash);
  out.routes = h;
  b = await boot({ perm: 'granted', token: false }); await b.signIn(); b.plug.L.registrationError({ error: 'x' }); await sleep(20); out.regError = { posts: b.posts.length };
  b = await boot({ perm: 'granted', offline: true, store: { sxb_me: JSON.stringify({ uid: 'u1', email: 'u1@x.com', verified: true }) } }); await b.signIn();
  b.X.push.sync(); await sleep(30);
  out.offline = { calls: b.plug.calls, posts: b.posts.length, me: !!(b.X.user() && b.X.user().offline) };
  b = await boot({ perm: 'granted' }); await b.signIn(); const before = tokPosts(b).length; b.st.offline = true; await b.X.refresh(); await sleep(30);
  b.plug.L.registration({ value: 'tok_late_' + 'y'.repeat(40) }); await sleep(30); out.lateOffline = { me: !!(b.X.user() && b.X.user().offline), extra: tokPosts(b).length - before };
  b = await boot({ native: false, store: { sxb_pt: TOKEN } }); await b.signIn(); b.order.length = 0; await b.X.signOut(); await sleep(20); out.signoutBrowserSaved = { order: b.order };
  b = await boot({ perm: 'granted', failTok: 1 }); await b.signIn(); const a1 = b.posts.length, s1 = b.store.sxb_pt; await b.X.refresh(); await sleep(40);
  out.retry = { first: a1, firstSaved: s1 === undefined, total: tokPosts(b).length, saved: b.store.sxb_pt === TOKEN };
  b = await boot({ perm: 'granted' }); await b.signIn('u1'); await b.X.signOut(); await sleep(20); await b.signIn('u1');
  out.resign = { n: tokPosts(b).length, regs: b.plug.calls.filter(c => c === 'register').length };
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
'''
r = subprocess.run(['node', '-e', HARNESS, JS], capture_output=True, text=True, timeout=60)
if r.returncode: print(r.stderr); sys.exit(1)
o = json.loads(r.stdout.strip().splitlines()[-1]); TOKEN = 'tok_' + 'x' * 40
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
src = open(JS, encoding='utf-8').read()
T('live.js carries the N1 block', '/*N1-start*/' in src and '/*N1-end*/' in src)
T('in a normal browser nothing is asked and nothing is sent', o['browser'] == {'calls': [], 'posts': 0})
a = o['ask']
T('in the app it asks permission first, then registers (check, request, register)', a['calls'] == ['check', 'request', 'register'])
t = [p for p in a['posts'] if p['path'] == '/api/push/token']
T('the phone token goes to /api/push/token with platform android', len(t) == 1 and t[0]['body'] == {'token': TOKEN, 'platform': 'android'})
T('the token is sent signed in (Bearer header)', t and t[0]['auth'] == 'Bearer tk')
T('the token is remembered on the phone after the server accepted it', a['saved'] == TOKEN)
T('permission already granted: it does not ask again, it registers', o['granted']['calls'] == ['check', 'register'] and o['granted']['n'] == 1)
d = o['denied']
T('permission refused: no register, nothing sent', d['calls'] == ['check', 'request'] and d['posts'] == 0)
T('permission refused: the person is told once how to allow it (not on every refresh)', d['toasts'] == 1 and 'Allow notifications' in d['toast'])
T('a token remembered from last time is sent right away, no wait for the phone', o['saved']['posts'] == [{'token': TOKEN, 'platform': 'android'}])
T('the same token is not sent twice in one session', o['dedupe']['n'] == 1)
T('another person signing in on the same phone registers it again for them', o['twoUsers']['n'] == 2 and o['twoUsers']['regs'] == 2)
s = o['signout']
T('sign-out tells the server this phone is leaving, BEFORE the session ends', s['order'] == ['unregister', 'signOut'])
T('sign-out sends the phone token and forgets it locally', s['post'] and s['post']['body'] == {'token': TOKEN} and s['saved'])
T('sign-out in a browser works as before (no unregister call)', o['signoutBrowser']['order'] == ['signOut'])
r_ = o['routes']
T('tap on an alert opens the matching screen (signals and stats -> trades, plans -> profile)', r_[0] == '#trades' and r_[1] == '#profile' and r_[2] == '#trades')
T('tap on home / trades alerts goes there', r_[3] == '#home' and r_[4] == '#trades')
T('a strange or unknown route is ignored (script text, constructor, path tricks, admin, empty, missing data)', all(x == '#start' for x in r_[5:]))
T('a registration error is harmless: nothing is sent', o['regError']['posts'] == 0)
T('an offline (saved) account does not try to register', o['offline']['me'] and o['offline']['calls'] == [] and o['offline']['posts'] == 0)
rt = o['retry']
T('a failed send is retried on the next refresh and only then remembered', rt['first'] == 1 and rt['firstSaved'] and rt['total'] == 2 and rt['saved'])
T('sign out then sign in again as the same person registers and sends the token again', o['resign']['n'] == 2 and o['resign']['regs'] == 2)
T('a late phone token while the account is offline is not sent', o['lateOffline']['me'] and o['lateOffline']['extra'] == 0)
T('sign-out in a browser never calls unregister, even with an old token saved', o['signoutBrowserSaved']['order'] == ['signOut'])
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
