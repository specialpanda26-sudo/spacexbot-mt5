"""PL5: the tiny-account check is per account. Plan accounts: off by default, the buyer may set their own percent. Everyone else: the owner's global setting.
Run: python tests/test_plan_risk.py   (last line: N checks, M failed)"""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
_f = os.path.join(HERE, 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import store as st, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def clear(): st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")
def lots(fb): return [o['lots'] for o in fb.orders]
def bad(d):
    try: burst.save('', d); return False
    except ValueError: return True
def poll(bal, kind=None):
    clear(); clock, fb, web, e, sf = D.rig(); c = D.Client('http://t', 'ownerkey', web)
    acct = {'balance': float(bal), 'equity': float(bal), 'login': 7, 'demo': True, 'trade_allowed': True}
    c.sync(acct); clear()
    if kind:
        s = {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}
        burst.create('', 'XAUUSD', s, {'kind': kind, 'n': 3, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test')
    else: D.new_signal(risk=1.0)
    r = c.sync(acct); return (r.get('basket') or r.get('signal') or {})
def group(bal):
    clear(); clock, fb, web, e, sf = D.rig(); fb.acct['balance'] = float(bal); D.go(e, clock, 3); clear()
    burst.create('', 'XAUUSD', {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}, {'kind': 'quick', 'n': 3, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test'); D.go(e, clock, 2); return fb

burst.save('', {'plan_usd': 0, 'max_lot': 0, 'tiny_pct': 0}); st.put('tiny_risk_pct', '10')
T('no plan: the owner setting (10) is used, single and burst', burst.tiny_pct('') == 10 and poll(100).get('tiny_pct') == 10 and poll(100, 'quick').get('tiny_pct') == 10)
burst.save('', {'plan_usd': 20})
T('plan: check is OFF by default (0) even though the owner setting is 10', burst.tiny_pct('') == 0 and poll(100).get('tiny_pct') == 0 and poll(100, 'quick').get('tiny_pct') == 0)
burst.save('', {'tiny_pct': 15})
T('plan: the buyer\'s own number is sent', burst.tiny_pct('') == 15 and poll(100).get('tiny_pct') == 15 and poll(100, 'quick').get('tiny_pct') == 15)
T('bad numbers refused', bad({'tiny_pct': -1}) and bad({'tiny_pct': 101}) and bad({'tiny_pct': 'x'}) and bad({'tiny_pct': True}) and burst.get('')['tiny_pct'] == 15)
burst.save('', {'plan_usd': 0})
T('plan removed: the owner setting applies again', burst.tiny_pct('') == 10)
st.put('tiny_risk_pct', '25'); T('owner setting change is followed (no plan)', poll(100).get('tiny_pct') == 25); st.put('tiny_risk_pct', '10')

# end to end on the fake MT5: a $40 account, 0.01 lot loses $5 at this stop = 12.5% > 10%
burst.save('', {'plan_usd': 0, 'lot_mode': 'fixed', 'lot': 0.01, 'tiny_pct': 0})
T('control, no plan, $40 account: refused by the 10% check', lots(group(40)) == [])
burst.save('', {'plan_usd': 10, 'tiny_pct': 0})
T('$10 plan, $40 account: check off by default, trades 3 x 0.01', lots(group(40)) == [0.01] * 3)
burst.save('', {'tiny_pct': 10})
T('$10 plan with the buyer\'s own 10% check: refused as a whole', lots(group(40)) == [])
T('same $10 plan with 10% check on a $400 account: trades', lots(group(400)) == [0.01] * 3)
burst.save('', {'plan_usd': 0, 'tiny_pct': 0})
n = len(R); f = sum(1 for _, ok in R if not ok); print('%d checks, %d failed' % (n, f)); sys.exit(1 if f else 0)
