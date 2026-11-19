"""Pay fix 5 checks: the M-Pesa prompt never carries account_id. Run: python tests/test_pay5.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'pay5_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PAYHERO_API_KEY='a', PAYHERO_API_SECRET='b',
                  PAYHERO_CHANNEL_ID='7', PAYHERO_CALLBACK_SECRET='sec', PAYHERO_ACCOUNT_ID='11352')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import payments as pay
SENT = []
class Resp:
    status_code = 200; content = b'x'
    def json(self): return {'success': True, 'reference': 'PH-1'}
def fake_post(url, **kw): SENT.append((url, kw.get('json'))); return Resp()
pay.requests.post = fake_post
C = app.test_client(); U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name)
C.get('/api/me', headers=U)
PH = ('0712345678', '0733000111', '0112345678'); bodies = []
for ph in PH:
    SENT.clear(); C.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': ph}, headers=U)
    if SENT: bodies.append(SENT[0][1])
T('three numbers, three prompts sent', len(bodies) == 3)
T('no prompt carries account_id', len(bodies) == 3 and all('account_id' not in b for b in bodies))
T('channel, provider and network are still sent', len(bodies) == 3 and all(b['channel_id'] == 7 and b['provider'] == 'sasapay' and b['network_code'] == '63902' for b in bodies))
T('each number goes out in local form', [b['phone_number'] for b in bodies] == list(PH))
if os.path.exists(DB): os.remove(DB)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
