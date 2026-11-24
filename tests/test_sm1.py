"""SM1 tests: Deriv small stakes are refused with the real cause. Fake Deriv session, no network. Run: python tests/test_sm1.py"""
import os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_sm1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, deriv, burst
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
class Fake:
    def __init__(s): s.log = []
    def ask(s, m):
        s.log.append(m)
        if m.get('proposal'):
            if float(m['amount']) < 1: return {'error': {'message': 'Minimum stake of 1.00 is required.'}}
            return {'proposal': {'id': 'q1', 'ask_price': m['amount']}}
        if m.get('buy'): return {'buy': {'contract_id': 777}}
        return {'error': {'message': 'x'}}
    def amounts(s): return [m['amount'] for m in s.log if m.get('proposal')]
def sig(risk=0.33, grp=None): return {'id': 1, 'symbol': 'EURUSD', 'side': 'buy', 'entry': 1.1, 'sl': 1.09, 'tp': 1.12, 'risk_pct': risk, 'grp': grp}
deriv._mult_ok.clear()
f = Fake(); k, r = deriv._place(f, sig(0.001), 1000.0, 'USD')          # risk 0.01 USD: even the smallest multiplier (5) gives a stake of about 0.22
T('a normal entry under 1 USD is rejected with the real cause, no proposal sent', k == 'rejected' and 'at least 1 USD' in r and 'no multiplier fits' not in r and f.amounts() == [] and len(r) < 120)
f = Fake(); k, r = deriv._place(f, sig(1.0), 1000.0, 'USD')
T('a normal entry of 1 USD or more still opens', k == 'open' and r['stake'] >= 1)
deriv._mult_ok.clear(); st.put('bg:50', '{"k":"quick","n":5,"each":0.5,"gb":40,"t":1,"stake":0.5}')
f = Fake(); k, r = deriv._place(f, dict(sig(), grp=50), 1000.0, 'USD')
T('a burst stake of 0.5 is still sent to Deriv (Deriv decides)', f.amounts() and all(a == 0.5 for a in f.amounts()))
T('...and when Deriv refuses it, the note names the setting to change', k == 'rejected' and 'Stake per entry' in r and '0.5' in r and len(r) < 120)
deriv._mult_ok.clear(); st.put('bg:51', '{"k":"quick","n":5,"each":1.0,"gb":40,"t":1,"stake":1.0}')
f = Fake(); k, r = deriv._place(f, dict(sig(), grp=51), 1000.0, 'USD')
T('a burst stake of 1 opens', k == 'open' and r['stake'] == 1.0)
class Down(Fake):
    def ask(s, m):
        if m.get('proposal'): return {'error': {'message': 'Market is closed.'}}
        return super().ask(m)
deriv._mult_ok.clear(); f = Down(); k, r = deriv._place(f, dict(sig(), grp=50), 1000.0, 'USD')
T("another refusal (market closed) keeps Deriv's own words", k == 'rejected' and r == 'Market is closed.')
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the Burst card label says Deriv needs 1 or more', 'Stake per entry ($) - Deriv only, needs 1 or more' in html)
print('%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
