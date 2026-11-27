"""PL3: the plan lot reaches MT5 on every market, and a plan never trades a bigger lot than it allows (fake MT5, Windows app path).
Run: python tests/test_plan_market.py   (last line: N checks, M failed)"""
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
EUR = dict(point=0.00001, digits=5, ask=1.09642, bid=1.09641, tick_size=0.00001, tick_value=1.0, stops_level=10)
SPEC = {'XAUUSD': ('XAUUSD', 2300.0, 2295.0, 2310.0, {}), 'EURUSD': ('EURUSD', 1.0964, 1.0950, 1.0990, EUR)}
def group(sym, plan, vmin=0.01, n=3):
    st.put('tiny_risk_pct', '0'); burst.save('', {'plan_usd': plan}); clear()
    clock, fb, web, e, sf = D.rig(); fb.acct['balance'] = 10000.0; fb.info[sym].update(SPEC[sym][4]); fb.info[sym]['vol_min'] = vmin
    D.go(e, clock, 3); clear()
    s = {'side': 'buy', 'entry': SPEC[sym][1], 'sl': SPEC[sym][2], 'tp': SPEC[sym][3], 'strategy': 't', 'score': 2}
    ids = burst.create('', sym, s, {'kind': 'quick', 'n': n, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test'); D.go(e, clock, 2)
    return fb, ids
def single(sym, plan, vmin=0.01):
    st.put('tiny_risk_pct', '0'); burst.save('', {'plan_usd': plan}); clear()
    clock, fb, web, e, sf = D.rig(); fb.acct['balance'] = 10000.0; fb.info[sym].update(SPEC[sym][4]); fb.info[sym]['vol_min'] = vmin
    D.go(e, clock, 3); clear()
    i = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
             (sym, 'buy', SPEC[sym][1], SPEC[sym][2], SPEC[sym][3], 5.0, 't', 3, 'pending', int(__import__('time').time()), None))
    D.go(e, clock, 2); return fb, i
def note(i): return (st.q('SELECT note FROM signals WHERE id=?', (i,), True) or {}).get('note') or ''

burst.save('', {'plan_usd': 0, 'max_lot': 0})          # the shared desktop test setup types a biggest lot of 100, which hides the soft flag; real accounts that never typed one must be covered
for sym in ('XAUUSD', 'EURUSD'):
    for plan, want in ((10, 0.01), (20, 0.02), (30, 0.03), (60, 0.06)):
        fb, ids = group(sym, plan)
        T('%s burst group, $%d plan: 3 entries of %g lot' % (sym, plan, want), lots(fb) == [want] * 3)
    for plan, want in ((10, 0.01), (30, 0.03)):
        T('%s single trade, $%d plan: %g lot even for a perfect setup' % (sym, plan, want), lots(single(sym, plan)[0]) == [want])
T('plan is strict: soft flag is 0 for a plan', burst.max_lot_soft('') == 0)
for sym in ('XAUUSD', 'EURUSD'):
    fb, ids = group(sym, 20, vmin=0.1)
    T('%s: broker minimum 0.1 is above the $20 plan (0.02): group refused, nothing traded' % sym, lots(fb) == [] and 'broker minimum' in ' '.join(note(i) for i in ids))
    fb, i = single(sym, 20, vmin=0.1)
    T('%s: same for a single trade' % sym, lots(fb) == [] and 'broker minimum' in note(i))
fb, ids = group('XAUUSD', 60, vmin=0.05)
T('broker minimum 0.05 is under the $60 plan (0.06): trades the plan lot 0.06', lots(fb) == [0.06] * 3)
fb, ids = group('XAUUSD', 10, vmin=0.02)
T('broker minimum 0.02 is above the $10 plan (0.01): refused', lots(fb) == [])
burst.save('', {'plan_usd': 0, 'lot_mode': 'fixed', 'lot': 0.01, 'max_lot': 0})
T('no plan: old behaviour kept (soft flag 1, broker minimum may be used)', burst.max_lot_soft('') == 1)
st.put('tiny_risk_pct', '10')
n = len(R); f = sum(1 for _, ok in R if not ok); print('%d checks, %d failed' % (n, f)); sys.exit(1 if f else 0)
