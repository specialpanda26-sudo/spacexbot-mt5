"""DK2: the desktop app closes a burst group at its target, on give-back and at the loss limit. Run:  python tests/test_dk2.py"""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from desktop import basket
from desktop.engine import Engine
from desktop.client import Client
from desktop.broker import BrokerError
from backend import store as st, burst
ok = []
def chk(name, c): ok.append((name, bool(c)))
def clean(): st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")

def patch(fb):          # the fake MT5 learns the two new calls
    fb.pl = {}; fb.pl_err = False
    def positions_pl(magic):
        if fb.pl_err: raise BrokerError('x')
        return [dict(p, pl=fb.pl.get(p['pid'], 0.0), type=0, volume=0.04, ticket=p['pid']) for p in fb.pos]
    def close_position(pos, dev, magic): fb.close(pos['pid'], fb.pl.get(pos['pid'], 0.0), 'other'); return True
    fb.positions_pl, fb.close_position = positions_pl, close_position
    return fb

def rig():
    clean(); clock, fb, web, e, sf = D.rig(); patch(fb); D.go(e, clock, 3); return clock, fb, web, e, sf
def make(n=4):
    clean(); s = {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}
    return burst.create('', 'XAUUSD', s, {'kind': 'quick', 'n': n, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test')
def setpl(fb, total):
    for p in fb.pos: fb.pl[p['pid']] = total / max(1, len(fb.pos))

# 1 target: 4 entries x 0.50 = 2.00
clock, fb, web, e, sf = rig(); ids = make(4); D.go(e, clock, 2)
g = e.groups[ids[0]]; chk('group remembered with target 2.00', g['t'] == 2.0 and len(g['sids']) == 4)
setpl(fb, 1.0); D.go(e, clock, 1); chk('below target: nothing closed', len(fb.pos) == 4)
setpl(fb, 2.4); D.go(e, clock, 3)
chk('target reached: all 4 closed', not fb.pos)
chk('closes reported as basket with the group profit', all(D.sig(i)['status'] == 'closed' and st.get('closedby:%d' % i) == 'basket' for i in ids))
# 2 give-back 40%: arms at 30% of the target (0.60)
clock, fb, web, e, sf = rig(); ids = make(4); D.go(e, clock, 2)
setpl(fb, 1.2); D.go(e, clock, 1); chk('profit rising: still open', len(fb.pos) == 4)
setpl(fb, 0.9); D.go(e, clock, 1); chk('small dip (25%): still open', len(fb.pos) == 4)
setpl(fb, 0.6); D.go(e, clock, 3); chk('profit fell 50% from its best: group closed', not fb.pos and all(st.get('closedby:%d' % i) == 'basket' for i in ids))
# 3 give-back does not fire before it is armed
clock, fb, web, e, sf = rig(); ids = make(4); D.go(e, clock, 2)
setpl(fb, 0.3); D.go(e, clock, 1); setpl(fb, 0.05); D.go(e, clock, 1); chk('not armed (best 0.30 < 0.60): no give-back close', len(fb.pos) == 4)
# 4 loss limit
clock, fb, web, e, sf = rig(); ids = make(4); D.go(e, clock, 2); e.groups[ids[0]]['l'] = 3.0
setpl(fb, -2.0); D.go(e, clock, 1); chk('loss under the limit: open', len(fb.pos) == 4)
setpl(fb, -3.5); D.go(e, clock, 3); chk('loss limit: group closed', not fb.pos)
# 5 restart keeps the rules
clock, fb, web, e, sf = rig(); ids = make(4); D.go(e, clock, 2); setpl(fb, 1.2); D.go(e, clock, 1)
e2 = Engine(e.cfg, fb, Client('http://t', 'ownerkey', web), sf, clock, lambda m: None)
chk('restart: target and best profit remembered', e2.groups[ids[0]]['t'] == 2.0 and e2.groups[ids[0]]['p'] == 1.2)
# 6 unreadable positions never close anything
clock, fb, web, e, sf = rig(); ids = make(4); D.go(e, clock, 2); setpl(fb, 5.0); fb.pl_err = True; D.go(e, clock, 2)
chk('unreadable positions: nothing closed, no crash', len(fb.pos) == 4)
fb.pl_err = False; D.go(e, clock, 2); chk('readable again: closes', not fb.pos)
# 7 a plain trade is never touched
clock, fb, web, e, sf = rig(); i = D.new_signal(); D.go(e, clock, 2); fb.pl[fb.pos[0]['pid']] = 999.0; D.go(e, clock, 2)
chk('single trade not closed by the group watch', len(fb.pos) == 1)
# 8 finished groups are forgotten
clock, fb, web, e, sf = rig(); ids = make(4); D.go(e, clock, 2); setpl(fb, 2.5); D.go(e, clock, 3); clock.now += 200; D.go(e, clock, 2)
chk('finished group forgotten', not e.groups)
bad = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if bad else 0)
