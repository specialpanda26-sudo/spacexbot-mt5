"""PL2: a managed plan forces burst ON and wins over Auto mode (for that account only). Run: python tests/test_plan_burst.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_pl2_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, burst, burst_look
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def bad(d):
    try: burst.save('', d); return False
    except ValueError: return True
st.put('burst_enabled', '1'); st.put('auto_mode', '0')
burst.save('', {'plan_usd': 0, 'on': False})
T('no plan: burst stays off when saved off', burst.get('')['on'] is False and burst.plan_active('') is False)
burst.save('', {'plan_usd': 20})
T('plan $20: burst is forced on even though never switched on', burst.get('')['on'] is True and burst.plan_active(''))
T('plan: cannot switch burst off', bad({'on': False}))
T('plan: still on after the refused save', burst.get('')['on'] is True)
T('plan: switching burst on is fine', burst.save('', {'on': True})['on'] is True)
g = burst.save('', {'plan_usd': 0, 'on': False})
T('plan 0 + burst off in one save is allowed', g['plan_usd'] == 0 and g['on'] is False)
st.put('auto_mode', '1')
burst.save('', {'on': True})
ok, why = burst.due('')
T('Auto mode ON, burst on, no plan: paused as before', ok is False and why == burst.AUTO_WHY)
burst.save('', {'plan_usd': 30})
T('Auto mode ON + plan: NOT paused by Auto mode', burst.due('')[1] != burst.AUTO_WHY)
T('card does not say paused-by-auto for a plan', burst.explain('').get('blocked') != 'auto')
A._burst_scan('XAUUSD', '')
T('scanner skips the Auto mode pause for a plan', 'Auto mode is ON' not in str(burst_look.last('', None)))
burst.save('', {'plan_usd': 0, 'on': True})
A._burst_scan('XAUUSD', '')
T('scanner still pauses without a plan', 'Auto mode is ON' in str(burst_look.last('', None)))
T('lot rule still intact', burst.save('', {'plan_usd': 40}) and burst.eff_lot('') == 0.04)
st.put('auto_mode', '0')
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
n = len(R); f = sum(1 for _, ok in R if not ok); print('%d checks, %d failed' % (n, f)); sys.exit(1 if f else 0)
