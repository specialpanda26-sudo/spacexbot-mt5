"""Section N1b checks: the phone-alert DELIVERY path.
 - push.py: trade alerts carry the trade id in their tag; owner trades go to admins only; admin test route.
 - a fake FCM records every message that would be sent, and the payload is checked.
 - static/live.js: push plugin fallback (nativePromise + addListener) and the saved reason (node).
 - static/index.html: admin "Send test alert" button (node).
 - android-wrapper/native/LiveMessagingService.java: compiled against recording stubs (javac) and run: the alert is drawn while the app is open.
Run: python tests/test_push2.py   (node and javac are optional: those parts print SKIP)"""
import os, sys, re, json, time, shutil, subprocess, threading, types
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'push2_test.db'); WORK = os.path.join(HERE, '_push2_work')   # helper files go inside tests/, never the system temp folder
os.makedirs(WORK, exist_ok=True)
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com,boss2@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, links
R = []
def T(name, ok): R.append((name, bool(ok)))

# ---------- a fake FCM: nothing leaves the machine ----------
SENT = []
class Resp:
    status_code = 200; text = '{}'
    def json(self): return {}
class FakeReq:
    def post(self, url, json=None, headers=None, data=None, timeout=None):
        if 'messages:send' in url: SENT.append(json['message'])
        return Resp()
push.requests = FakeReq()
push._access_token = lambda: 'fake-access-token'
ACC = {'project_id': 'p', 'client_email': 'e@p.iam', 'private_key': 'k'}
push._account = lambda: ACC
class SyncThread:                       # broadcast() normally runs in a background thread; run it now so the test can look
    def __init__(self, target=None, daemon=None): self.t = target
    def start(self): self.t()
push.threading = types.SimpleNamespace(Thread=SyncThread, Lock=threading.Lock)
push.quiet_now = lambda *a, **k: False

C = app.test_client()
H = lambda e: {'Authorization': 'Bearer dev:' + e}
uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in ('boss@x.com', 'boss2@x.com', 'joe@x.com', 'ann@x.com', 'free@x.com')}
for e in ('joe@x.com', 'ann@x.com'): C.post('/api/admin/grant', json={'email': e, 'days': 30}, headers=H('boss@x.com'))
TOKS = {e: 'tok_%s_' % e.split('@')[0] + 'x' * 30 for e in ('boss@x.com', 'joe@x.com', 'ann@x.com', 'free@x.com')}
for e, t in TOKS.items(): push.save_token(uid[e], t)
who = {t: e for e, t in TOKS.items()}
def sent_to(): return sorted(who[m['token']] for m in SENT)
def newsig(owner_uid=''):
    st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES('XAUUSD','buy',2000,1990,2020,1,'gold_scalp',2,'sent',?,?)", (int(time.time()), owner_uid))
    return st.q('SELECT MAX(id) AS i FROM signals', (), True)['i']
def report(sid, key, **d):
    SENT.clear(); r = C.post('/api/ea/report', json=dict(id=sid, **d), headers={'X-EA-Key': key}); return r.status_code

# ---------- item 3: tags carry the trade id ----------
T('tag: kinds 1-4 and 8 include the trade id', all(push.tag_for(k, 'sig12-x') == 'k%s-sig12-x' % k for k in (1, 2, 3, 4, 8)))
T('tag: two trades give two different tags', push.tag_for(1, 'sig12-open') != push.tag_for(1, 'sig13-open'))
T('tag: the person id broadcast() adds after the slash is not in the tag', push.tag_for(1, 'sig12-open/uid-123') == 'k1-sig12-open')
T('tag: never longer than 60', len(push.tag_for(1, 's' * 200)) <= 60)
T('tag: a kind without a trade shares one tag per kind', push.tag_for(5) == 'k5' and push.tag_for(11, 'x') == 'k11' and push.tag_for(1) == 'k1')

# ---------- items 3+4 through the real route: owner's EA ----------
s1 = newsig(); s2 = newsig()
T('owner EA: open returns 200', report(s1, 'k', status='open', ticket='1', lots=0.1, price=2000) == 200)
T('owner trade open goes to admins only (not to subscribers with a plan, not to a free user)', sent_to() == ['boss@x.com'])
m = SENT[0] if SENT else {}; n = m.get('android', {}).get('notification', {})
T('payload: title, channel, icon and tag', m.get('notification', {}).get('title') == 'BUY XAUUSD is live' and n.get('channel_id') == 'sxb_high' and n.get('icon') == 'ic_stat_sxb' and n.get('tag') == 'k1-sig%d-open' % s1)
T('payload: data has kind, category, route, tag as text, and a high priority', m.get('data', {}).get('kind') == '1' and m['data'].get('cat') == 'trade' and m['data'].get('route') == '#signals' and m['data'].get('tag') == n.get('tag') and m['android'].get('priority') == 'HIGH')
report(s2, 'k', status='open', ticket='2', lots=0.1, price=2001)
T('second trade has a different tag, so the first banner is not replaced', SENT and SENT[0]['android']['notification']['tag'] == 'k1-sig%d-open' % s2 and SENT[0]['android']['notification']['tag'] != n.get('tag'))
report(s1, 'k', status='closed', pnl=50, reason='tp')
mm = SENT[0] if SENT else {}
T('owner TP: kind 2, to admins only, tag has the trade id', sent_to() == ['boss@x.com'] and mm['data']['kind'] == '2' and mm['android']['notification']['tag'] == 'k2-sig%d-closed' % s1 and 'Hooray' in mm['notification']['title'])
report(s2, 'k', status='closed', pnl=-20, reason='sl')
T('owner SL: kind 3, admins only', sent_to() == ['boss@x.com'] and SENT[0]['data']['kind'] == '3' and SENT[0]['android']['notification']['tag'] == 'k3-sig%d-closed' % s2)
s3 = newsig(); report(s3, 'k', status='closed', pnl=5, reason='manual')
T('owner manual close: kind 4, admins only', sent_to() == ['boss@x.com'] and SENT[0]['data']['kind'] == '4')
s4 = newsig(); report(s4, 'k', status='rejected', reason='spread')
T('owner skipped: kind 8, admins only, tag has the trade id', sent_to() == ['boss@x.com'] and SENT[0]['data']['kind'] == '8' and SENT[0]['android']['notification']['tag'] == 'k8-sig%d-skipped' % s4)
# both admins with a phone: both get it
push.save_token(uid['boss2@x.com'], 'tok_boss2_' + 'x' * 30); who['tok_boss2_' + 'x' * 30] = 'boss2@x.com'
s5 = newsig(); report(s5, 'k', status='open', ticket='5', lots=0.1, price=2000)
T('every admin phone gets the owner trade', sent_to() == ['boss2@x.com', 'boss@x.com'])

# ---------- a subscriber's own EA key: only that person ----------
key = links.new_key(uid['joe@x.com']); s6 = newsig(uid['joe@x.com'])
T('subscriber EA: own trade open goes to that subscriber only', report(s6, key, status='open', ticket='9', lots=0.1, price=2000) == 200 and sent_to() == ['joe@x.com'])
report(s6, key, status='closed', pnl=12, reason='tp')
T('subscriber EA: own result goes to that subscriber only (not the admin, not another subscriber)', sent_to() == ['joe@x.com'] and SENT[0]['data']['kind'] == '2')

# ---------- recipients() ----------
T('recipients(): default = subscribers with a plan and admins, not a free user', set(push.recipients()) == {uid['boss@x.com'], uid['boss2@x.com'], uid['joe@x.com'], uid['ann@x.com']})
T('recipients(admins_only): only the admins', set(push.recipients(True)) == {uid['boss@x.com'], uid['boss2@x.com']})
T('notify() without admins/only still reaches every subscriber (other kinds keep working)', (SENT.clear(), push.notify(32, 'daily-test', sym='XAUUSD', pnl=1, n=1), sent_to())[2] == ['ann@x.com', 'boss2@x.com', 'boss@x.com', 'joe@x.com'])

# ---------- item 5: admin test route ----------
T('test route: a normal user is refused', C.post('/api/admin/push/test', headers=H('joe@x.com')).status_code == 403)
push._account = lambda: {}
r = C.post('/api/admin/push/test', headers=H('boss@x.com'))
T('test route: no FCM_SERVICE_ACCOUNT -> 400 with a plain message that names it', r.status_code == 400 and 'FCM_SERVICE_ACCOUNT' in r.json['error'])
push._account = lambda: ACC
st.x('DELETE FROM push_tokens WHERE uid=?', (uid['boss2@x.com'],))
SENT.clear(); r = C.post('/api/admin/push/test', headers=H('boss2@x.com'))
T('test route: admin with no phone -> 400 and tells them what to do', r.status_code == 400 and 'No phone is registered' in r.json['error'] and r.json['devices'] == 0 and not SENT)
push.quiet_now = lambda *a, **k: True
SENT.clear(); r = C.post('/api/admin/push/test', headers=H('boss@x.com'))
T('test route: sends to the admin phone, even in quiet hours', r.status_code == 200 and r.json['sent'] == 1 and sent_to() == ['boss@x.com'])
T('test route payload: title spaceXBot test, high channel', SENT and SENT[0]['notification']['title'] == 'spaceXBot test' and SENT[0]['android']['notification']['channel_id'] == 'sxb_high')
push.quiet_now = lambda *a, **k: False

# ---------- live.js (node) ----------
NODE = shutil.which('node')
LIVE = r'''
const fs = require('fs'); const SRC = fs.readFileSync(process.argv[2], 'utf8'); const sleep = ms => new Promise(r => setTimeout(r, ms));
async function boot(cap, native, pre) {
  const store = Object.assign({}, pre || {}), posts = [];
  global.localStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
  global.sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} }; global.location = { origin: 'http://t', hash: '' };
  let cb = null; const auth = { onAuthStateChange(f) { cb = f; }, getSession: () => Promise.resolve({ data: { session: { access_token: 'tk', user: { id: 'u1' } } }, error: null }), signOut: () => Promise.resolve({}) };
  global.fetch = (path, init) => { init = init || {}; if (path === '/api/push/token') posts.push(JSON.parse(init.body));
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(path === '/api/me' ? { uid: 'u1', email: 'u1@x.com', verified: true, active: true } : { ok: true }) }); };
  global.window = { SXB: { sb: { url: 'https://x.supabase.co', key: 'k' } }, supabase: { createClient: () => ({ auth }) }, sxToast() {} };
  if (cap) global.window.Capacitor = cap;
  eval(SRC); await cb('SIGNED_IN', { user: { id: 'u1' } }); await sleep(60);
  return { store, posts, X: global.window.SXA };
}
(async () => {
  const out = {}; const calls = [], listeners = {};
  const TOK = 'tok_' + 'z'.repeat(40);
  const cap = { isNativePlatform: () => true,
    nativePromise: (plugin, method, opts) => { calls.push(plugin + '.' + method); if (method === 'checkPermissions') return Promise.resolve({ receive: 'granted' });
      if (method === 'register') { setTimeout(() => listeners.registration && listeners.registration({ value: TOK }), 0); } return Promise.resolve({}); },
    addListener: (plugin, ev, fn) => { calls.push('listen:' + plugin + '.' + ev); listeners[ev] = fn; return { remove() {} }; } };
  let b = await boot(cap, true);
  out.fallback = { calls, tokenPosts: b.posts.length, token: b.posts[0] && b.posts[0].token === TOK, saved: b.store.sxb_pt === TOK, why: b.store.sxb_pt_why || null };
  b = await boot({ isNativePlatform: () => true, foo: 1 }, true);
  out.noPlugin = { why: b.store.sxb_pt_why || '', posts: b.posts.length, helper: b.X.push.why() };
  b = await boot({ isNativePlatform: () => false }, false); out.browser = { why: b.store.sxb_pt_why || null };
  b = await boot(null, false); out.noCap = { why: b.store.sxb_pt_why || null };
  b = await boot(cap, true, { sxb_pt_why: 'old problem @ yesterday' }); out.cleared = { why: b.store.sxb_pt_why || null, saved: !!b.store.sxb_pt };
  console.log(JSON.stringify(out));
})();
'''
if NODE:
    p = os.path.join(WORK, 'live.js'); open(p, 'w').write(LIVE)
    rr = subprocess.run([NODE, p, os.path.join(ROOT, 'static', 'live.js')], capture_output=True, text=True, timeout=60)
    try: J = json.loads(rr.stdout.strip().splitlines()[-1])
    except Exception: J = {}; print(rr.stdout[-400:], rr.stderr[-400:])
    f = J.get('fallback', {})
    T('live.js fallback: no registerPlugin, uses nativePromise for PushNotifications methods', 'PushNotifications.checkPermissions' in f.get('calls', []) and 'PushNotifications.register' in f.get('calls', []))
    T('live.js fallback: listens through Capacitor.addListener and the token reaches the server', 'listen:PushNotifications.registration' in f.get('calls', []) and f.get('token') and f.get('saved'))
    T('live.js fallback: a working start leaves no failure reason', f.get('why') is None)
    n = J.get('noPlugin', {})
    T('live.js: native app with no plugin saves a short reason (sxb_pt_why) and posts nothing', 'no push plugin' in n.get('why', '') and n.get('posts') == 0 and len(n.get('why', '')) < 260 and n.get('helper') == n.get('why'))
    T('live.js: an old failure reason is cleared once the token reaches the server', J.get('cleared', {}).get('saved') and J['cleared'].get('why') is None)
    T('live.js: a browser (not the app) saves no reason', J.get('browser', {}).get('why') is None and J.get('noCap', {}).get('why') is None)
else: print('SKIP live.js tests: node not installed')

# ---------- admin button (node) ----------
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('admin panel: Send test alert button sits before the Strategies card', 0 < html.find('id="pnTest"') < html.find('id="aStr"') and html.count('/*N1b-start*/') == 1 and html.count('/*N1b-end*/') == 1)
mb = re.search(r'/\*N1b-start\*/(.*?)/\*N1b-end\*/', html, re.S); BTN = mb.group(1) if mb else ''
BTNJS = r'''
const code = process.argv[2]; const out = {};
async function run(api, why) {
  const btn = { disabled: false }, msg = { textContent: '' }, toasts = [], calls = [];
  const $ = s => (s === '#pnTest' ? btn : s === '#pnMsg' ? msg : { });
  const tst = t => toasts.push(t); const SXA = { api: (p, o) => { calls.push([p, o && o.method]); return api(); }, push: { why: () => why } };
  eval(code); const during = btn.disabled; const p = btn.onclick.call(btn); const mid = { disabled: btn.disabled, text: msg.textContent };
  await new Promise(r => setTimeout(r, 20)); return { calls, mid, end: { disabled: btn.disabled, text: msg.textContent }, toasts };
}
(async () => {
  out.ok = await run(() => Promise.resolve({ sent: 2, devices: 2 }), '');
  out.one = await run(() => Promise.resolve({ sent: 1, devices: 1 }), '');
  out.fail = await run(() => Promise.reject(new Error('No phone is registered for your account.')), 'no push plugin (Capacitor found) @ t');
  console.log(JSON.stringify(out));
})();
'''
if NODE and BTN:
    p = os.path.join(WORK, 'btn.js'); open(p, 'w').write(BTNJS)
    rr = subprocess.run([NODE, p, BTN], capture_output=True, text=True, timeout=60)
    try: J = json.loads(rr.stdout.strip().splitlines()[-1])
    except Exception: J = {}; print(rr.stdout[-400:], rr.stderr[-400:])
    ok, one, fl = J.get('ok', {}), J.get('one', {}), J.get('fail', {})
    T('button: POSTs /api/admin/push/test and disables itself while sending', ok.get('calls') == [['/api/admin/push/test', 'POST']] and ok.get('mid', {}).get('disabled') is True and ok.get('mid', {}).get('text') == 'Sending...')
    T('button: shows how many phones got it, then is usable again', 'Sent to 2 phones' in ok.get('end', {}).get('text', '') and 'Sent to 1 phone.' in one.get('end', {}).get('text', '') and ok['end']['disabled'] is False)
    T('button: a failure shows the server text and the phone reason, and is usable again', 'No phone is registered' in fl.get('end', {}).get('text', '') and 'no push plugin' in fl['end']['text'] and fl['end']['disabled'] is False)
else: print('SKIP button tests: node not installed')

# ---------- Android service (javac against recording stubs) ----------
JAVA = os.path.join(ROOT, 'android-wrapper', 'native', 'LiveMessagingService.java'); SRCJ = open(JAVA, encoding='utf-8').read()
T('java: the foreground branch is wired into onMessageReceived before super', SRCJ.find('showForeground(message)') != -1 and SRCJ.find('showForeground(message)') < SRCJ.find('super.onMessageReceived(message)'))
STUBS = {
 'android/content/Context.java': 'package android.content; public abstract class Context { public static final String NOTIFICATION_SERVICE="notification"; public java.util.Map<String,Object> services=new java.util.HashMap<>(); public Object getSystemService(String n){return services.get(n);} public android.content.pm.PackageManager getPackageManager(){return new android.content.pm.PackageManager();} public String getPackageName(){return "com.spacexbot.app";} public android.content.res.Resources getResources(){return new android.content.res.Resources();} }',
 'android/content/ContextWrapper.java': 'package android.content; public class ContextWrapper extends Context {}',
 'android/content/Intent.java': 'package android.content; public class Intent { public static final int FLAG_ACTIVITY_NEW_TASK=1, FLAG_ACTIVITY_CLEAR_TOP=2, FLAG_ACTIVITY_SINGLE_TOP=4; public int flags; public java.util.Map<String,String> extras=new java.util.HashMap<>(); public Intent setFlags(int f){flags=f;return this;} public Intent putExtra(String k,String v){extras.put(k,v);return this;} }',
 'android/content/pm/PackageManager.java': 'package android.content.pm; public class PackageManager { public android.content.Intent getLaunchIntentForPackage(String p){return new android.content.Intent();} }',
 'android/content/res/Resources.java': 'package android.content.res; public class Resources { public int getIdentifier(String n,String t,String p){return 77;} }',
 'android/app/Notification.java': 'package android.app; public class Notification { public String channel,title,text,big; public int icon,priority; public boolean autoCancel,ongoing; public PendingIntent pi; }',
 'android/app/PendingIntent.java': 'package android.app; public class PendingIntent { public static final int FLAG_UPDATE_CURRENT=1, FLAG_IMMUTABLE=2; public android.content.Intent intent; public int req; public static PendingIntent getActivity(android.content.Context c,int r,android.content.Intent i,int f){PendingIntent p=new PendingIntent();p.intent=i;p.req=r;return p;} }',
 'android/app/NotificationChannel.java': 'package android.app; public class NotificationChannel { public String id; public int imp; public NotificationChannel(String id,CharSequence n,int imp){this.id=id;this.imp=imp;} public void setDescription(String d){} public void setShowBadge(boolean b){} }',
 'android/app/NotificationManager.java': 'package android.app; import java.util.*; public class NotificationManager { public static final int IMPORTANCE_LOW=2, IMPORTANCE_HIGH=4; public List<NotificationChannel> channels=new ArrayList<>(); public List<Object[]> shown=new ArrayList<>(); public List<Integer> cancelled=new ArrayList<>(); public void createNotificationChannel(NotificationChannel c){channels.add(c);} public NotificationChannel getNotificationChannel(String id){for(NotificationChannel c:channels) if(c.id.equals(id)) return c; return null;} public void cancel(int id){cancelled.add(id);} public void notify(int id,Notification n){shown.add(new Object[]{null,id,n});} public void notify(String tag,int id,Notification n){shown.add(new Object[]{tag,id,n});} }',
 'android/os/Build.java': 'package android.os; public class Build { public static class VERSION { public static int SDK_INT=34; } public static class VERSION_CODES { public static final int O=26; } }',
 'android/R.java': 'package android; public class R { public static class drawable { public static final int ic_dialog_info=1; } }',
 'androidx/core/app/NotificationCompat.java': 'package androidx.core.app; import android.app.*; public class NotificationCompat { public static final int PRIORITY_LOW=-1, PRIORITY_HIGH=1; public static final String CATEGORY_STATUS="status"; public static final int VISIBILITY_PRIVATE=0;'
   ' public static class Style {} public static class BigTextStyle extends Style { public String t; public BigTextStyle bigText(CharSequence s){t=String.valueOf(s);return this;} }'
   ' public static class Builder { Notification n=new Notification(); public Builder(android.content.Context c,String ch){n.channel=ch;} public Builder setSmallIcon(int i){n.icon=i;return this;} public Builder setContentTitle(CharSequence s){n.title=String.valueOf(s);return this;} public Builder setContentText(CharSequence s){n.text=String.valueOf(s);return this;}'
   ' public Builder setStyle(Style s){if(s instanceof BigTextStyle) n.big=((BigTextStyle)s).t;return this;} public Builder setOngoing(boolean b){n.ongoing=b;return this;} public Builder setOnlyAlertOnce(boolean b){return this;} public Builder setShowWhen(boolean b){return this;} public Builder setWhen(long w){return this;} public Builder setCategory(String c){return this;}'
   ' public Builder setPriority(int p){n.priority=p;return this;} public Builder setVisibility(int v){return this;} public Builder setPublicVersion(Notification x){return this;} public Builder setTimeoutAfter(long t){return this;} public Builder setAutoCancel(boolean b){n.autoCancel=b;return this;} public Builder setContentIntent(PendingIntent p){n.pi=p;return this;} public Notification build(){return n;} } }',
 'com/google/firebase/messaging/RemoteMessage.java': 'package com.google.firebase.messaging; import java.util.*; public class RemoteMessage { public Map<String,String> data=new HashMap<>(); public Notification notif; public String id; public Map<String,String> getData(){return data;} public Notification getNotification(){return notif;} public String getMessageId(){return id;}'
   ' public static class Notification { public String title,body,channel,tag; public String getTitle(){return title;} public String getBody(){return body;} public String getChannelId(){return channel;} public String getTag(){return tag;} } }',
 'com/capacitorjs/plugins/pushnotifications/MessagingService.java': 'package com.capacitorjs.plugins.pushnotifications; public class MessagingService extends android.content.ContextWrapper { public static int superCalls=0; public void onMessageReceived(com.google.firebase.messaging.RemoteMessage m){superCalls++;} }',
}
HARNESSJ = r'''
package com.spacexbot.app;
import android.app.*; import android.content.Context; import com.google.firebase.messaging.RemoteMessage; import java.util.*;
public class Harness {
  static NotificationManager nm;
  static LiveMessagingService svc() { nm = new NotificationManager(); LiveMessagingService s = new LiveMessagingService(); s.services.put(Context.NOTIFICATION_SERVICE, nm); return s; }
  static RemoteMessage msg(String title, String body, String ch, String tag, String id, String... kv) {
    RemoteMessage m = new RemoteMessage(); m.id = id;
    if (title != null) { m.notif = new RemoteMessage.Notification(); m.notif.title = title; m.notif.body = body; m.notif.channel = ch; m.notif.tag = tag; }
    for (int i = 0; i + 1 < kv.length; i += 2) m.data.put(kv[i], kv[i + 1]);
    return m;
  }
  static void show(String name) {
    for (Object[] r : nm.shown) { Notification n = (Notification) r[2]; Map<String,String> x = n.pi == null ? new HashMap<String,String>() : n.pi.intent.extras;
      System.out.println(name + "|tag=" + r[0] + "|id=" + r[1] + "|ch=" + n.channel + "|title=" + n.title + "|text=" + n.text + "|icon=" + n.icon + "|auto=" + n.autoCancel + "|prio=" + n.priority
        + "|route=" + x.get("route") + "|kind=" + x.get("kind") + "|mid=" + x.get("google.message_id") + "|datatag=" + x.get("tag") + "|req=" + (n.pi == null ? -1 : n.pi.req)); }
    System.out.println(name + "|count=" + nm.shown.size() + "|channels=" + nm.channels.size() + "|super=" + com.capacitorjs.plugins.pushnotifications.MessagingService.superCalls);
  }
  public static void main(String[] a) {
    com.capacitorjs.plugins.pushnotifications.MessagingService.superCalls = 0;
    LiveMessagingService s = svc();
    s.onMessageReceived(msg("Trade opened", "BUY XAUUSD", "sxb_high", "k1-sig5-open", "m1", "kind", "1", "route", "#signals", "tag", "k1-sig5-open")); show("fg");
    s.onMessageReceived(msg("Trade opened", "BUY XAUUSD", "sxb_high", "k1-sig6-open", "m2", "kind", "1", "route", "#signals", "tag", "k1-sig6-open")); show("two");
    s = svc(); s.onMessageReceived(msg(null, null, null, null, "m3", "kind", "7")); show("dataonly");
    s = svc(); s.onMessageReceived(msg("Daily summary", "ok", "sxb_low", null, "m4", "kind", "32", "route", "#stats", "tag", "k32")); show("low");
    s = svc(); s.onMessageReceived(msg("Hi", "b", "", null, null, "kind", "5")); show("nochannel");
    s = svc(); s.onMessageReceived(msg(null, null, null, null, "m5", "type", "live", "title", "Bot running", "text", "x")); show("live");
  }
}
'''
JAVAC = shutil.which('javac'); JBIN = shutil.which('java')
if JAVAC and JBIN:
    tmp = os.path.join(WORK, 'java'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp); files = []
    for rel, body in STUBS.items():
        pth = os.path.join(tmp, 'src', rel); os.makedirs(os.path.dirname(pth), exist_ok=True); open(pth, 'w').write(body); files.append(pth)
    d = os.path.join(tmp, 'src', 'com', 'spacexbot', 'app'); os.makedirs(d, exist_ok=True)
    shutil.copy(JAVA, os.path.join(d, 'LiveMessagingService.java')); open(os.path.join(d, 'Harness.java'), 'w').write(HARNESSJ)
    files += [os.path.join(d, 'LiveMessagingService.java'), os.path.join(d, 'Harness.java')]
    cp = subprocess.run([JAVAC, '-d', os.path.join(tmp, 'out')] + files, capture_output=True, text=True)
    T('java: LiveMessagingService.java compiles', cp.returncode == 0)
    if cp.returncode: print(cp.stderr[-1500:])
    else:
        rj = subprocess.run([JBIN, '-cp', os.path.join(tmp, 'out'), 'com.spacexbot.app.Harness'], capture_output=True, text=True)
        L = {}
        for line in rj.stdout.splitlines():
            parts = line.split('|'); L.setdefault(parts[0], []).append(dict(x.split('=', 1) for x in parts[1:]))
        fg = L.get('fg', [{}])[0]; two = L.get('two', [{}, {}])
        T('java foreground: an alert is shown with the server title, text and channel', fg.get('title') == 'Trade opened' and fg.get('text') == 'BUY XAUUSD' and fg.get('ch') == 'sxb_high')
        T('java foreground: small icon ic_stat_sxb (resource found), tap opens the app, auto-cancel, high priority', fg.get('icon') == '77' and fg.get('req') != '-1' and fg.get('auto') == 'true' and fg.get('prio') == '1')
        T('java foreground: tap carries the data extras (route, kind, tag) and google.message_id so the page sees the tap', fg.get('route') == '#signals' and fg.get('kind') == '1' and fg.get('datatag') == 'k1-sig5-open' and fg.get('mid') == 'm1')
        T('java foreground: same tag replaces, a different trade tag is a second alert', fg.get('tag') == 'k1-sig5-open' and len(two) >= 3 and {two[0].get('tag'), two[1].get('tag')} == {'k1-sig5-open', 'k1-sig6-open'} and two[-1].get('count') == '2')
        T('java foreground: the page still hears about it (super called each time)', two[-1].get('super') == '2')
        T('java foreground: a data-only message draws nothing', L.get('dataonly', [{}])[-1].get('count') == '0')
        lo = L.get('low', [{}])[0]
        T('java foreground: the low channel is used and created if missing, low priority', lo.get('ch') == 'sxb_low' and lo.get('prio') == '-1' and L['low'][-1].get('channels') == '1')
        nc = L.get('nochannel', [{}])[0]
        T('java foreground: no channel in the message falls back to sxb_high', nc.get('ch') == 'sxb_high' and nc.get('tag') == 'null' and nc.get('mid') not in (None, 'null'))
        lv = L.get('live', [{}])[0]
        T('java: the pinned "Bot running" message still works and is not drawn as an alert', lv.get('id') == '7001' and lv.get('title') == 'Bot running' and lv.get('ch') == 'sxb_live' and L['live'][-1].get('super') == L['nochannel'][-1].get('super'))
    shutil.rmtree(tmp, ignore_errors=True)
else: print('SKIP java tests: javac not installed')

# ---------- item 6: docs ----------
env = open(os.path.join(ROOT, '.env.example'), encoding='utf-8').read(); rd = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read()
for name in ('FCM_SERVICE_ACCOUNT', 'PUBLIC_URL', 'PUSH_DAILY_CAP', 'GOOGLE_SERVICES_JSON_BASE64'):
    T('.env.example and README both explain ' + name, name in env and name in rd)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
shutil.rmtree(WORK, ignore_errors=True)
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
