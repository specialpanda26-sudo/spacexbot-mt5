"""DK1: the desktop app opens a burst basket and reports every entry. Run:  python tests/test_dk1.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import types
_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f          # reuse the fakes of test_desktop.py without running its own checks
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from desktop import basket
from backend import store as st, burst
ok = []
def chk(name, c): ok.append((name, bool(c)))

def clean(): st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")          # leftovers of the desktop test suite

def make(n=4, sym='XAUUSD', side='buy'):
    st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")          # leftovers of the desktop test suite
    s = {'side': side, 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}
    return burst.create('', sym, s, {'kind': 'quick', 'n': n, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test')

chk('comment parser', basket.sid_of('SXB12') == 12 and basket.sid_of('SXB12G5') == 12 and basket.gid_of('SXB12G5') == 5 and basket.sid_of('SXBx') == 0 and basket.sid_of('abc') == 0)
clean(); clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3)
ids = make(4); D.go(e, clock, 2)
chk('4 orders sent', len(fb.orders) == 4 and all(o['comment'].startswith('SXB') and 'G%d' % ids[0] in o['comment'] for o in fb.orders))
chk('all 4 reported open', all(D.sig(i)['status'] == 'open' for i in ids))
chk('known has all 4', set(e.known) == set(ids))
for p in list(fb.pos)[:2]: fb.close(p['pid'], -1.5, 'sl')
D.go(e, clock, 2)
chk('closes are reported', sum(1 for i in ids if D.sig(i)['status'] == 'closed') == 2)
n0 = len(fb.orders); D.go(e, clock, 2); chk('never placed twice', len(fb.orders) == n0)
clean(); clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); fb.acct['trade_allowed'] = False
ids = make(3); D.go(e, clock, 2)
chk('Algo Trading off -> all rejected with the reason', not fb.orders and all(D.sig(i)['status'] == 'rejected' and 'Algo Trading' in (D.sig(i)['note'] or '') for i in ids))
clean(); clock, fb, web, e, sf = D.rig(); D.go(e, clock, 3); fb.info['XAUUSD']['vol_min'] = 0.5
ids = make(5); D.go(e, clock, 2)
chk('min lot too big -> trimmed group, rest rejected', len(fb.orders) < 5 and sum(1 for i in ids if D.sig(i)['status'] == 'rejected') == 5 - len(fb.orders) or all(D.sig(i)['status'] == 'rejected' for i in ids))
bad = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if bad else 0)
