"""LS1 checks: safe default biggest lot (0.06), lot modes (smallest / fixed / auto), and that both bridges get and obey them. No network.
Run: python tests/test_ls1.py   (last line: N checks, M failed)"""
import os, sys, types, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
_f = os.path.join(HERE, 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import store as st, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def lots(fb): return [o['lots'] for o in fb.orders]
def clear(): st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")
def bad(d):
    try: burst.save('', d); return False
    except ValueError: return True
def make(n=3):
    clear(); s = {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}
    return burst.create('', 'XAUUSD', s, {'kind': 'quick', 'n': n, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test')
def single(**kw):
    clear(); clock, fb, web, e, sf = D.rig(**kw); D.go(e, clock, 3); clear(); D.new_signal(risk=5.0); D.go(e, clock, 2); return fb
def group(n=3, vol_min=None):
    clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3)
    if vol_min: fb.info['XAUUSD']['vol_min'] = vol_min
    make(n); D.go(e, clock, 2); return fb

# ---- server: defaults and validation ----
st.put('burst:', '{}')
g = burst.get('')
T('nothing saved: mode auto, no typed cap, but the cap in use is 0.06 and it is soft', g['lot_mode'] == 'auto' and g['max_lot'] == 0 and burst.eff_max_lot('') == 0.06 and burst.max_lot_soft('') == 1 and burst.eff_lot('') == 0)
T('a typed cap is used as typed and is not soft', burst.save('', {'max_lot': 0.1})['max_lot'] == 0.1 and burst.eff_max_lot('') == 0.1 and burst.max_lot_soft('') == 0)
T('clearing the cap goes back to 0.06', burst.save('', {'max_lot': 0})['max_lot'] == 0 and burst.eff_max_lot('') == 0.06)
T('smallest mode asks for 0.01', burst.save('', {'lot_mode': 'smallest'})['lot_mode'] == 'smallest' and burst.eff_lot('') == 0.01)
T('fixed mode without a lot is refused', bad({'lot_mode': 'fixed'}))
T('fixed 0.02 is saved and used', burst.save('', {'lot_mode': 'fixed', 'lot': 0.02})['lot'] == 0.02 and burst.eff_lot('') == 0.02)
T('fixed lot above the biggest lot is refused (default 0.06)', bad({'lot': 0.2}) and burst.get('')['lot'] == 0.02)
T('raising the biggest lot first lets the bigger fixed lot through', burst.save('', {'max_lot': 0.5, 'lot': 0.2})['lot'] == 0.2)
T('lowering the biggest lot under the fixed lot is refused', bad({'max_lot': 0.1}))
T('bad modes refused', all(bad({'lot_mode': b}) for b in ('big', '', None, 1, True)))
burst.save('', {'max_lot': 0, 'lot_mode': 'auto'})
T('auto mode sends lot 0 even when a fixed lot is remembered', burst.eff_lot('') == 0)
T('an old caller sending lot 0 means automatic', burst.save('', {'lot_mode': 'fixed', 'lot': 0.02}) and burst.save('', {'lot': 0})['lot_mode'] == 'auto')
T('an old caller sending only a lot means fixed', burst.save('', {'lot': 0.03})['lot_mode'] == 'fixed')
burst.save('', {'lot_mode': 'auto', 'lot': 0, 'max_lot': 0})

# ---- desktop app: the default cap works, nothing bigger than 0.06 goes out ----
burst.save('', {'lot_mode': 'auto', 'lot': 0, 'max_lot': 0})
fb = single()
T('auto: 5% risk would be a big lot, but the order is cut to 0.06', len(fb.orders) == 1 and lots(fb) == [0.06])
T('auto burst: every entry cut to 0.06', lots(group(3)) == [0.06] * 3)
burst.save('', {'lot_mode': 'smallest'})
T('smallest: a normal trade is 0.01', lots(single()) == [0.01])
T('smallest: every burst entry is 0.01', lots(group(3)) == [0.01] * 3)
T('smallest on a broker whose minimum is 0.1: lifted to 0.1, not refused', lots(group(2, vol_min=0.1)) == [0.1, 0.1])
burst.save('', {'lot_mode': 'fixed', 'lot': 0.03})
T('fixed 0.03: a normal trade is 0.03 (single trades obey it now)', lots(single()) == [0.03])
T('fixed 0.03: burst entries are 0.03', lots(group(2)) == [0.03] * 2)
burst.save('', {'lot_mode': 'auto', 'lot': 0, 'max_lot': 0})
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); fb.info['XAUUSD']['vol_min'] = 0.1; clear(); D.new_signal(risk=5.0); D.go(e, clock, 2)
T('auto, broker minimum 0.1 above the default cap: still trades at 0.1', lots(fb) == [0.1])
burst.save('', {'max_lot': 0.02})
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); fb.info['XAUUSD']['vol_min'] = 0.1; clear(); D.new_signal(risk=5.0); D.go(e, clock, 2)
T('a TYPED cap under the broker minimum still refuses', fb.orders == [])
burst.save('', {'max_lot': 0, 'lot_mode': 'auto', 'lot': 0})

# ---- what the bridge receives ----
src = open(os.path.join(HERE, '..', 'ea', 'SpaceXBridge.mq5'), encoding='utf-8').read()
ex = src[src.index('void Execute('):src.index('//--- BURST BASKET')]
T('EA: Execute takes a fixed lot and the soft flag', 'double fixedLot = 0' in ex.split('{')[0] and 'double maxLotSoft = 0' in ex.split('{')[0])
T('EA: Execute uses the fixed lot and skips the big stake when one is set', 'if(fixedLot > 0) lots = MathMax(fixedLot, mn)' in ex and 'fixedLot <= 0' in ex)
T('EA: the poll passes lot and max_lot_soft to both', src.count('JStr(res, "max_lot_soft")') == 2)
T('EA: version raised so the recompile is visible', '#property version "1.24"' in src)
print('%d checks, %d failed' % (len(R), sum(1 for _, ok in R if not ok)))
sys.exit(1 if any(not ok for _, ok in R) else 0)
