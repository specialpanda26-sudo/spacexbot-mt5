"""PL1: managed account plan -> lot per entry. $10 -> 0.01 ... $60 -> 0.06, driven by the PLAN not the balance. Run: python tests/test_plan_lot.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_pl1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def bad(d):
    try: burst.save('', d); return False
    except ValueError: return True
for plan, want in ((10, 0.01), (20, 0.02), (30, 0.03), (40, 0.04), (50, 0.05), (60, 0.06), (19, 0.01), (25, 0.02), (99, 0.09), (100, 0.10), (200, 0.20), (1000, 1.0)):
    T('plan_lot(%g) == %g' % (plan, want), burst.plan_lot(plan) == want)
T('no plan / junk -> 0', all(burst.plan_lot(x) == 0.0 for x in (0, 5, 9.99, -10, None, 'x', float('nan'))))
burst.save('', {'plan_usd': 0, 'lot_mode': 'auto', 'lot': 0, 'max_lot': 0})
for plan, want in ((10, 0.01), (20, 0.02), (30, 0.03), (60, 0.06)):
    g = burst.save('', {'plan_usd': plan})
    T('save $%d -> mode plan' % plan, g['lot_mode'] == 'plan' and g['plan_usd'] == plan)
    T('$%d -> eff_lot %g and eff_max_lot %g' % (plan, want, want), burst.eff_lot('') == want and burst.eff_max_lot('') == want)
    T('$%d: perfect setup is NOT raised above the plan lot' % plan, burst.strength_cap('', True) == want)
T('plan beats real balance (tier ignored)', burst.eff_max_lot('') == 0.06 and burst.save('', {'plan_usd': 10})['plan_usd'] == 10 and burst.eff_max_lot('') == 0.01)
T('plan beats a typed lot_mode afterwards', burst.save('', {'lot_mode': 'fixed', 'lot': 0.05})['lot_mode'] == 'plan' and burst.eff_lot('') == 0.01)
T('message names the plan', 'Managed $10 plan' in burst.lot_now('')['message'])
T('bad plans refused', bad({'plan_usd': 5}) and bad({'plan_usd': 'abc'}) and bad({'plan_usd': 5000}) and bad({'plan_usd': True}) and bad({'plan_usd': 12.5}))
T('refused plan saves nothing', burst.get('')['plan_usd'] == 10)
g = burst.save('', {'plan_usd': 0})
T('plan 0 leaves plan mode (back to auto)', g['plan_usd'] == 0 and g['lot_mode'] == 'auto')
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
n = len(R); f = sum(1 for _, ok in R if not ok); print('%d checks, %d failed' % (n, f)); sys.exit(1 if f else 0)
