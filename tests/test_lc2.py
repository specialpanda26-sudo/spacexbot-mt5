"""LC2 checks: the desktop app and the MT5 EA obey the person's biggest lot (max_lot). No network.
Run: python tests/test_lc2.py   (exit 1 on any FAIL)"""
import os, sys, types, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
_f = os.path.join(HERE, 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import store as st, burst
ok = []
def chk(name, c): ok.append((name, bool(c)))
def lots(fb): return [o['lots'] if 'lots' in o else o.get('volume') for o in fb.orders]
def clear(): st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")
def make(n=3):
    clear()
    s = {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}
    return burst.create('', 'XAUUSD', s, {'kind': 'quick', 'n': n, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test')

# ---------- desktop: one normal trade ----------
burst.save('', {'max_lot': 100, 'lot': 0}); clear()          # LS1: 0 now means the safe 0.06, so 'no cap' is a big typed number
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3)
clear(); D.new_signal(risk=5.0); D.go(e, clock, 2)
base = lots(fb)
chk('no cap: a normal trade is bigger than 0.02 (so the next checks mean something)', len(base) == 1 and base[0] > 0.02)
burst.save('', {'max_lot': 0.02}); clear()
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3)
clear(); D.new_signal(risk=5.0); D.go(e, clock, 2)
chk('cap 0.02: the normal trade is cut to 0.02', len(fb.orders) == 1 and abs(lots(fb)[0] - 0.02) < 1e-9)
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); fb.info['XAUUSD']['vol_min'] = 0.1
clear(); D.new_signal(risk=5.0); D.go(e, clock, 2)
chk('cap below the broker minimum: refused, nothing traded', len(fb.orders) == 0)

# ---------- desktop: a burst group ----------
import json; st.put('burst:', json.dumps({'max_lot': 0.03, 'lot': 0.2, 'lot_mode': 'fixed'}))          # an old save with a fixed lot bigger than the cap (the panel now refuses it): the cap wins
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); ids = make(3); D.go(e, clock, 2)
chk('burst: 3 entries, each cut to 0.03 even though the fixed lot is 0.2', len(fb.orders) == 3 and all(abs(x - 0.03) < 1e-9 for x in lots(fb)))
burst.save('', {'max_lot': 100, 'lot': 0.2})
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); ids = make(3); D.go(e, clock, 2)
chk('burst, cap off: the fixed lot 0.2 is used', len(fb.orders) == 3 and all(abs(x - 0.2) < 1e-9 for x in lots(fb)))
burst.save('', {'max_lot': 0.05, 'lot': 0.02})
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); ids = make(3); D.go(e, clock, 2)
chk('burst: a fixed lot under the cap is left alone (0.02)', len(fb.orders) == 3 and all(abs(x - 0.02) < 1e-9 for x in lots(fb)))
burst.save('', {'max_lot': 0, 'lot': 0})

# ---------- EA: the source obeys it (the EA cannot run here, so check the code is in place) ----------
src = open(os.path.join(HERE, '..', 'ea', 'SpaceXBridge.mq5'), encoding='utf-8').read()
def body(name):
    m = re.search(r'\nvoid %s\(.*?\n\}\n' % name, src, re.S); return m.group(0) if m else ''
ex, bx = body('Execute'), body('ExecuteBasket')
chk('EA: Execute takes maxLot', 'double maxLot = 0' in ex.split('{')[0])
chk('EA: ExecuteBasket takes maxLot', 'double maxLot = 0' in bx.split('{')[0])
chk('EA: single trade cuts lots to maxLot after the stake sizing', ex.find('StakeLots(sym') < ex.find('lots > maxLot') < ex.find('trade.Buy(lots'))
chk('EA: basket cuts lots to maxLot before opening', bx.find('lots > maxLot') != -1 and bx.find('lots > maxLot') < bx.find('trade.Buy(lots'))
chk('EA: a cap below the broker minimum rejects', ex.count('below the broker minimum lot') == 1 and bx.count('below the broker minimum lot') == 1)
chk('EA: both calls pass the server max_lot', src.count('JStr(res, "max_lot")') == 2)
chk('EA: version raised so the recompile is visible', '#property version "1.26"' in src)
badn = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if badn else 0)
