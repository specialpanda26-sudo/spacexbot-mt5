"""Section N3 checks: billing alerts 38-44 through a FAKE FCM (nothing leaves the machine).
 38 payment received, 39 M-Pesa prompt sent, 40 payment not completed, 41 PayPal confirmed, 42/43/44 plan ends in 3 days / tomorrow / ended.
Each check reads the payload: title, body, channel_id, tag, data.kind / route. Run: python tests/test_bill3.py"""
import os, sys, time, types, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'bill3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t',
                  PAYHERO_API_KEY='k', PAYHERO_API_SECRET='s', PAYHERO_CHANNEL_ID='1', PAYHERO_CALLBACK_SECRET='cs')
os.environ.pop('FCM_SERVICE_ACCOUNT', None)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, push, payments as pay, billalerts, alerts
R = []
def T(name, ok): R.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name)

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
push._account = lambda: {'project_id': 'p', 'client_email': 'e@p.iam', 'private_key': 'k'}
class SyncThread:
    def __init__(self, target=None, daemon=None): self.t = target
    def start(self): self.t()
push.threading = types.SimpleNamespace(Thread=SyncThread, Lock=threading.Lock)
QUIET = [False]
push.quiet_now = lambda *a, **k: QUIET[0]

C = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
EM = ('boss@x.com', 'free@x.com', 'ann@x.com', 'bob@x.com', 'cat@x.com', 'dan@x.com', 'eve@x.com', 'nophone@x.com')
uid = {e: C.get('/api/me', headers=H(e)).json['uid'] for e in EM}
for e in EM:
    if e != 'nophone@x.com': push.save_token(uid[e], 'tok_%s_' % e.split('@')[0] + 'x' * 30)
who = {'tok_%s_' % e.split('@')[0] + 'x' * 30: e for e in EM}
def got(): return sorted(who[m['token']] for m in SENT)
def msg(): return SENT[0] if SENT else {'notification': {}, 'data': {}, 'android': {'notification': {}}}
def clear(): SENT.clear()
def until(e): return billalerts.until_text(st.q('SELECT plan_until FROM users WHERE uid=?', (uid[e],), True)['plan_until'])
def webhook(ref, status, amount=500, code=None):
    return pay.settle_deposit(pay.parse_webhook({'status': status, 'external_reference': ref, 'amount': amount, 'provider_reference': 'RCP' + ref[-4:], **({'result_code': code} if code else {})}))

# ---------- 39: prompt sent, to a person with NO plan ----------
class GwResp:
    status_code = 200; content = b'{}'
    def json(self): return {'reference': 'CK-1'}
pay._post = lambda url, body: (GwResp(), {'reference': 'CK-1'})
clear(); ref1 = pay.stk_push(uid['free@x.com'], 'p1', '0712345678')
T('39: the prompt-sent alert reaches a person with no plan', got() == ['free@x.com'])
m = msg(); n = m['android']['notification']
T('39: title, channel, tag, kind and route', m['notification']['title'] == 'M-Pesa prompt sent' and n['channel_id'] == 'sxb_high' and n['tag'] == 'k39' and m['data']['kind'] == '39' and m['data']['route'] == '#plans')
T('39: the words are facts only (PIN, no promise)', 'PIN' in m['notification']['body'])
pay._post = lambda url, body: (_ for _ in ()).throw(RuntimeError('down'))
clear()
try: pay.stk_push(uid['free@x.com'], 'p1', '0712345678')
except RuntimeError: pass
T('39: no alert when the gateway never got the prompt (the person sees the error on screen)', SENT == [])

# ---------- 38: payment received ----------
clear(); r = webhook(ref1, 'SUCCESS')
T('38: success callback activates and sends the alert to that person only', r == 'paid' and got() == ['free@x.com'])
m = msg(); n = m['android']['notification']
T('38: title, channel, tag, kind, route', m['notification']['title'] == 'Payment received' and n['channel_id'] == 'sxb_high' and n['tag'] == 'k38' and m['data']['kind'] == '38' and m['data']['route'] == '#plans')
T('38: the body names the real new end date', until('free@x.com') in m['notification']['body'] and billalerts.until_text(time.time() + 7 * 86400) in m['notification']['body'])
clear(); r = webhook(ref1, 'SUCCESS')
T('38: a repeated callback sends nothing', r == 'duplicate' and SENT == [])

# ---------- 40: payment not completed ----------
pay._post = lambda url, body: (GwResp(), {})
ref2 = pay.stk_push(uid['ann@x.com'], 'p1', '0712345678'); clear()
r = webhook(ref2, 'FAILED', 0, 1032)
T('40: a failed callback sends the not-completed alert to a person with no plan', r == 'failed' and got() == ['ann@x.com'] and msg()['notification']['title'] == 'Payment did not go through' and msg()['data']['kind'] == '40')
T('40: tag, channel and route', msg()['android']['notification']['tag'] == 'k40' and msg()['android']['notification']['channel_id'] == 'sxb_high' and msg()['data']['route'] == '#plans')
clear(); r = webhook(ref2, 'FAILED', 0, 1032)
T('40: a repeated failed callback sends nothing', r == 'duplicate' and SENT == [])
ref3 = pay.stk_push(uid['bob@x.com'], 'p1', '0712345678'); clear()
r = webhook(ref3, 'SUCCESS', 100)
T('40/38: an underpaid payment sends neither (nothing was credited)', r == 'underpaid' and SENT == [])
ref4 = pay.stk_push(uid['bob@x.com'], 'p1', '0712345678'); clear()
st.x("UPDATE payments SET created=? WHERE ref=?", (int(time.time()) - 3600, ref4)); pay.reconcile()
T('40: a prompt nobody answered expires and sends alert 40 once', got() == ['bob@x.com'] and msg()['data']['kind'] == '40')
clear(); pay.reconcile()
T('40: the next reconcile does not send it again', SENT == [])
clear(); r = webhook(ref4, 'SUCCESS')
T('38: a late success after expiry still credits and says Payment received', r == 'paid' and got() == ['bob@x.com'] and msg()['data']['kind'] == '38')

# ---------- 41: PayPal ----------
pp = pay._new(uid['cat@x.com'], 'paypal', 'p1', 4, 'USD'); row = pay._row(pp); clear()
pay._pp_apply(row, 'paid', {'purchase_units': [{'payments': {'captures': [{'id': 'CAP1'}]}}]})
T('41: PayPal paid sends kind 41 to that person only, with the end date', got() == ['cat@x.com'] and msg()['data']['kind'] == '41' and msg()['notification']['title'] == 'PayPal payment confirmed' and until('cat@x.com') in msg()['notification']['body'])
clear(); pay._pp_apply(pay._row(pp), 'paid', {})
T('41: a repeat sends nothing', SENT == [])
pp2 = pay._new(uid['dan@x.com'], 'paypal', 'p1', 4, 'USD'); clear()
pay._pp_apply(pay._row(pp2), 'failed', {})
T('40: a failed PayPal payment sends the not-completed alert', got() == ['dan@x.com'] and msg()['data']['kind'] == '40')
pp3 = pay._new(uid['eve@x.com'], 'paypal', 'p1', 4, 'USD'); clear()
pay._pp_apply(pay._row(pp3), 'pending', {})
T('PayPal still pending sends nothing', SENT == [])

ppx = pay._new(uid['dan@x.com'], 'paypal', 'p1', 4, 'USD'); st.x("UPDATE payments SET created=? WHERE ref=?", (int(time.time()) - 5 * 3600, ppx)); clear(); pay.reconcile()
T('40: a PayPal order nobody completed expires after 4 hours and sends alert 40 once', got() == ['dan@x.com'] and msg()['data']['kind'] == '40')
clear(); pay.reconcile()
T('40: ...and not again', SENT == [])
refb = pay.stk_push(uid['free@x.com'], 'p1', '0712345678'); clear(); webhook(refb, 'SUCCESS')
T('38: a second payment by the same person gets its own alert (the key is per payment)', got() == ['free@x.com'] and msg()['data']['kind'] == '38')
clear(); push.notify_user(uid['free@x.com'], 39, 'dup-key-1'); push.notify_user(uid['free@x.com'], 39, 'dup-key-1')
T('notify_user: the same key is sent only once per person', got() == ['free@x.com'])
clear(); push.notify_user(uid['free@x.com'], 999, 'dup-key-2'); push.notify_user(uid['free@x.com'], 39)
T('notify_user: an unknown kind or a missing key never raises', len(SENT) <= 1)

# ---------- quiet hours and the person's own switch ----------
clear(); QUIET[0] = True; ref5 = pay.stk_push(uid['eve@x.com'], 'p1', '0712345678')
T('billing alerts get through quiet hours', got() == ['eve@x.com'])
QUIET[0] = False
_prefs = push.prefs; push.prefs = lambda u: {'billing': False}
clear(); ref6 = pay.stk_push(uid['eve@x.com'], 'p1', '0712345678')
T('the person\'s own Billing switch still turns them off', SENT == [])
push.prefs = _prefs
st.x("UPDATE payments SET status='failed' WHERE uid=?", (uid['eve@x.com'],))

# ---------- 42 / 43 / 44 ----------
T('which(): the five windows', [billalerts.which(x) for x in (4 * 86400, 3 * 86400, 86400 + 1, 86400, 1, 0, -2 * 86400, -2 * 86400 - 1)] == [None, 42, 42, 43, 43, 44, 44, None])
now = int(time.time())
def setpu(e, pu): st.x('UPDATE users SET plan_until=? WHERE uid=?', (int(pu), uid[e]))
for e in EM: setpu(e, 0)
setpu('ann@x.com', now + 2 * 86400); setpu('bob@x.com', now + 12 * 3600); setpu('cat@x.com', now - 3600)
setpu('dan@x.com', now + 10 * 86400); setpu('eve@x.com', now - 5 * 86400); setpu('boss@x.com', now + 2 * 86400); setpu('nophone@x.com', now + 2 * 86400)
clear(); k = billalerts.run()
by = {who[m['token']]: m for m in SENT}
T('run: 42 to the person with 2 days left, 43 at 12 hours, 44 an hour after the end', by['ann@x.com']['data']['kind'] == '42' and by['bob@x.com']['data']['kind'] == '43' and by['cat@x.com']['data']['kind'] == '44')
T('run: nothing for 10 days left, ended 5 days ago, an admin, or a person with no phone', sorted(by) == ['ann@x.com', 'bob@x.com', 'cat@x.com'] and k == 3)
T('run: titles and tags', by['ann@x.com']['notification']['title'] == 'Your plan ends in 3 days' and by['bob@x.com']['notification']['title'] == 'Your plan ends tomorrow' and by['cat@x.com']['notification']['title'] == 'Your plan has ended'
  and by['ann@x.com']['android']['notification']['tag'] == 'k42' and by['cat@x.com']['android']['notification']['channel_id'] in ('sxb_high', 'sxb_default', 'sxb_low') and by['cat@x.com']['data']['route'] == '#plans')
clear(); k = billalerts.run()
T('run again: nothing is sent twice', SENT == [] and k == 0)
setpu('ann@x.com', now + 20 * 3600)
clear(); billalerts.run()
T('run: a person whose plan moved into the next window gets the next alert once', got() == ['ann@x.com'] and msg()['data']['kind'] == '43')
setpu('ann@x.com', now + 2 * 86400 + 5)
clear(); billalerts.run()
T('run: a new end date starts a new cycle (extended plan)', got() == ['ann@x.com'] and msg()['data']['kind'] == '42')
T('run never raises, even when the sender breaks', billalerts.run(send=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('x'))) == 0)

# ---------- the timed job ----------
calls = []
billalerts_run = billalerts.run; billalerts.run = lambda *a, **k: calls.append(1)
alerts._billing_job(); billalerts.run = billalerts_run
T('alerts: the billing job calls billalerts.run', calls == [1])
alerts.start(); t0 = time.time()
while 'billing_plan' not in alerts._jobs and time.time() - t0 < 3: time.sleep(0.1)
alerts.stop()
T('alerts: the loop registers billing_plan every 10 minutes', alerts._jobs.get('billing_plan', {}).get('interval') == 600)

p = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (p, len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(0 if p == len(R) else 1)
