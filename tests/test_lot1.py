import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import store as st, burst
ok = []
def chk(name, c): ok.append((name, bool(c)))
def bad(d):
    try: burst.save('', d); return False
    except ValueError: return True
def make(n=3):
    st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")
    s = {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}
    return burst.create('', 'XAUUSD', s, {'kind': 'quick', 'n': n, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test')
chk('default is automatic (0)', burst.get('')['lot'] == 0)
chk('0.05 saved', burst.save('', {'lot': 0.05})['lot'] == 0.05)
chk('0 clears it', burst.save('', {'lot': 0})['lot'] == 0)
chk('bad lots refused', all(bad({'lot': b}) for b in (0.001, -1, 101, 'x', True, None)))
burst.save('', {'lot': 0.05}); ids = make(3)
m = burst.meta(ids[0]); chk('group remembers the lot', m and m.get('lot') == 0.05)
chk('basket carries the lot', burst.basket(st.q('SELECT * FROM signals WHERE id=?', (ids[0],), True), '')['lot'] == 0.05)
st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3)
ids = make(3); D.go(e, clock, 2)
lots = [o['lots'] if 'lots' in o else o.get('volume') for o in fb.orders]
chk('3 orders at exactly 0.05 lot', len(fb.orders) == 3 and all(abs(x - 0.05) < 1e-9 for x in lots))
burst.save('', {'lot': 0.01})
clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); fb.info['XAUUSD']['vol_min'] = 0.1
ids = make(2); D.go(e, clock, 2)
lots = [o['lots'] if 'lots' in o else o.get('volume') for o in fb.orders]
chk('lot below the broker minimum is lifted to the minimum', len(fb.orders) == 2 and all(abs(x - 0.1) < 1e-9 for x in lots))
burst.save('', {'lot': 0})
badn = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if badn else 0)
