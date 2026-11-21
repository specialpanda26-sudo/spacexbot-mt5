"""Section 6 checks: Resend mailer, alert recipients, daily cap, receipts. No network. Run: python tests/test_mail.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'mail_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', RESEND_API_KEY='re_test', MAIL_FROM='spaceXBot <a@b.com>', MAIL_ALERT_CAP='3', MAIL_HARD_CAP='5', MAIL_WELCOME='0')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import store as st, mailer as M, payments as pay
R = []
def T(name, ok): R.append((name, bool(ok)))
class Resp:
    def __init__(s, code, j): s.status_code = code; s._j = j
    def json(s): return s._j
calls = []; nxt = [Resp(200, {'id': 'em_1'})]
def fake(url, json=None, headers=None, timeout=None):
    calls.append((url, json, headers)); r = nxt[0]
    if isinstance(r, Exception): raise r
    return r
M.requests.post = fake
def day_count(): return int(st.get(M._day_key()) or 0)

T('send ok: right url, bearer key, idempotency key', M.send('a@x.com', 's', '<p>h</p>', 't', idem='k1')[0] and calls[-1][0] == 'https://api.resend.com/emails' and calls[-1][2]['Authorization'] == 'Bearer re_test' and calls[-1][2]['Idempotency-Key'] == 'k1' and calls[-1][1]['to'] == ['a@x.com'])
for code, word in ((401, 'key'), (403, 'domain'), (422, 'MAIL_FROM'), (429, 'quota')):
    nxt[0] = Resp(code, {'name': 'x', 'message': 'm'}); ok, why = M.send('a@x.com', 's', 'h', 't')
    T('error %d is explained, not raised' % code, not ok and word in why)
nxt[0] = Resp(409, {'name': 'invalid_idempotent_request'}); T('409 same key means already sent', M.send('a@x.com', 's', 'h', 't', idem='k1') == (True, 'duplicate'))
nxt[0] = RuntimeError('boom'); T('network error is returned, not raised', M.send('a@x.com', 's', 'h', 't')[0] is False)
T('failed sends do not use up the daily count', day_count() == 1)
nxt[0] = Resp(200, {'id': 'em_2'})

st.x('DELETE FROM kv WHERE k=?', (M._day_key(),))
T('alert cap blocks the 4th alert', [M.send('a@x.com', 's', 'h', 't')[0] for _ in range(4)] == [True, True, True, False])
T('receipts still get through after the alert cap', M.send('a@x.com', 's', 'h', 't', kind='receipt')[0] and day_count() == 4)
T('test emails ignore the cap and the count', M.send('a@x.com', 's', 'h', 't', kind='test')[0] and day_count() == 4)

H = lambda e: {'Authorization': 'Bearer dev:' + e}; C = app.test_client()
for e in ('boss@x.com', 'joe@x.com', 'ann@x.com', 'bob@x.com'): C.get('/api/me', headers=H(e))
for e in ('joe@x.com', 'ann@x.com'): st.x('UPDATE users SET plan_until=? WHERE email=?', (int(time.time()) + 86400, e))
st.x('UPDATE users SET notif=? WHERE email=?', ('{"trade":0}', 'ann@x.com'))
T('alerts go to admin and active subscribers who kept trade alerts on', sorted(e for _, e in M._recipients()) == ['boss@x.com', 'joe@x.com'])
st.x('DELETE FROM kv WHERE k=?', (M._day_key(),)); calls.clear()
T('alert sends one email per person with a per-person key', M._alerts('BUY XAUUSD', 'Entry 1', key='sig7-new') == 2 and sorted(c[2]['Idempotency-Key'][:9] for c in calls) == ['sig7-new/', 'sig7-new/'] and calls[0][1]['to'] != calls[1][1]['to'])
os.environ['RESEND_API_KEY'] = ''; calls.clear()
T('not set up: nothing is sent and nothing breaks', M._alerts('x', 'y') == 0 and M.send('a@x.com', 's', 'h', 't')[0] is False and not calls)
os.environ['RESEND_API_KEY'] = 're_test'

plan = pay.plans()[0]
st.x("INSERT INTO payments(ref,uid,provider,plan,amount,currency,status,created,phone) VALUES(?,?,?,?,?,?,?,?,?)", ('R1', 'dev-joe@x.com', 'finoq', plan['id'], 1.0, 'KES', 'pending', int(time.time()), '254700000000'))
st.x("INSERT INTO payments(ref,uid,provider,plan,amount,currency,status,created) VALUES(?,?,?,?,?,?,?,?)", ('R2', 'dev-joe@x.com', 'finoq', plan['id'], 1.0, 'KES', 'pending', int(time.time())))
got = []; real = M.receipt; M.receipt = lambda ref: got.append(ref)
cb = {'ref': 'R1', 'success': True, 'failed': False, 'amount': 1.0, 'phone': '', 'receipt': 'QWE123', 'code': ''}
T('paid M-Pesa payment asks for a receipt once, a repeat callback does not', pay.settle_deposit(cb) == 'paid' and pay.settle_deposit(cb) == 'duplicate' and got == ['R1'])
M.receipt = real; calls.clear(); st.x('DELETE FROM kv WHERE k=?', (M._day_key(),))
T('receipt email has plan, amount and the M-Pesa code', M._receipt_now('R1') and 'QWE123' in calls[-1][1]['html'] and 'KES 1' in calls[-1][1]['text'] and calls[-1][1]['to'] == ['joe@x.com'] and calls[-1][2]['Idempotency-Key'] == 'receipt/R1')
T('no receipt for an unpaid or unknown payment', M._receipt_now('R2') is False and M._receipt_now('nope') is False)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
