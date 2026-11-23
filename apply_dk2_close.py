"""DK2: the Windows desktop app closes a burst group the way the EA does: at the group profit target, when the profit starts to go away
(give-back guard), or at the group loss limit. Checked about once a second. Closes are reported with reason 'basket', the closing price and
the group profit, so the server's next-group cycle works. Only ADDS (needs DK1). Safe to run twice."""
import os, sys
R = os.path.dirname(os.path.abspath(__file__))
def rd(p): return open(os.path.join(R, p), encoding='utf-8').read()
def wr(p, s): open(os.path.join(R, p), 'w', encoding='utf-8').write(s)
assert os.path.exists(os.path.join(R, 'desktop', 'basket.py')), 'Run apply_dk1_basket.py first (DK1 must be in place)'

BROKER_ADD = '''
    def positions_pl(self, magic):
        """Open positions of this bot with their live profit (profit + swap, same as the EA's basket watch)."""
        m = self._mt(); r = m.positions_get()
        if r is None: raise BrokerError('could not read open positions (%s)' % (m.last_error(),))
        return [{'pid': p.identifier, 'ticket': p.ticket, 'comment': p.comment, 'symbol': p.symbol, 'pl': float(p.profit + p.swap),
                 'type': p.type, 'volume': p.volume} for p in r if p.magic == magic]

    def close_position(self, pos, deviation, magic):
        """Close one position at market. True when MT5 accepted the close."""
        m = self._mt(); k = m.symbol_info_tick(pos['symbol']); i = m.symbol_info(pos['symbol'])
        if k is None or i is None: return False
        buy = pos['type'] == m.POSITION_TYPE_BUY          # closing a buy = selling at the bid
        fill = m.ORDER_FILLING_IOC if i.filling_mode & 2 else m.ORDER_FILLING_FOK if i.filling_mode & 1 else m.ORDER_FILLING_RETURN
        r = m.order_send({'action': m.TRADE_ACTION_DEAL, 'symbol': pos['symbol'], 'volume': pos['volume'], 'position': pos['ticket'],
                          'type': m.ORDER_TYPE_SELL if buy else m.ORDER_TYPE_BUY, 'price': k.bid if buy else k.ask, 'deviation': deviation,
                          'magic': magic, 'type_time': m.ORDER_TIME_GTC, 'type_filling': fill})
        return r is not None and r.retcode in (m.TRADE_RETCODE_DONE, m.TRADE_RETCODE_PLACED)
'''

BASKET_ADD = '''

# ---------------- DK2: closing the group ----------------
import time
ARM = 30          # percent: the give-back guard only starts once the group profit reached this share of its target (EA: BasketArmPct)


def _num(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError): return d


def _register(e, bk, gid, placed, acct):
    """Remember the group's rules (target, give-back, loss limit in money) so the watch can close it. Saved with the app's state."""
    if not placed: return
    tgt, each, loss = _num(bk.get('tgt')), _num(bk.get('each')), _num(bk.get('loss'))
    e.groups[gid] = {'t': round(tgt if tgt > 0 else each * len(placed), 2), 'b': int(_num(bk.get('gb'))), 'p': 0.0,
                     'l': round(acct['balance'] * loss / 100.0, 2) if loss > 0 else 0.0, 'x': 0, 's': None, 'o': e.clock(), 'sids': [s for s, _ in placed]}
    e._save()


def _group_of(e, sid):
    for g in e.groups.values():
        if sid in (g.get('sids') or ()): return g
    return None


def close_extra(e, sid, info):
    """What the 'closed' report carries. A trade the group watch closed says 'basket' (with the group profit); the closing price is sent when known."""
    out = {'pnl': info['pnl'], 'reason': info['reason']}
    if info.get('price'): out['price'] = info['price']
    g = _group_of(e, sid)
    if g is not None and g.get('x'):
        out['reason'] = 'basket'
        if g.get('s') is not None: out['gpnl'] = round(g['s'], 2)
    return out


def _close(e, ps):
    for p in ps:
        try: e.b.close_position(p, e.cfg['deviation'], e.cfg['magic'])
        except Exception as x: e.log('group close failed for %s: %s (will retry)' % (p.get('ticket'), x.__class__.__name__))


def manage(e):
    """One look at every open group. Same rules as ManageBaskets in the EA: loss limit first, then target, then give-back."""
    if not e.groups: return
    try: pos = e.b.positions_pl(e.cfg['magic'])
    except BrokerError: return
    except Exception as x: e.log('group watch: %s' % x.__class__.__name__); return
    live = {}
    for p in pos:
        g = gid_of(p['comment'])
        if g: live.setdefault(g, []).append(p)
    now = e.clock(); dirty = False
    for gid, m in list(e.groups.items()):
        ps = live.get(gid, [])
        if not ps:          # nothing left: forget it once every close was reported
            if not any(s in e.known for s in m.get('sids', ())) and now - (m.get('x') or m.get('o') or 0) > (60 if m.get('x') else 120): del e.groups[gid]; dirty = True
            continue
        if m.get('x'): _close(e, ps); continue          # already closing: finish it (retry what failed)
        total = round(sum(p['pl'] for p in ps), 2)
        if total > m['p']: m['p'] = total; dirty = True
        why = None
        if m['l'] > 0 and total <= -m['l']: why = 'hit its loss limit'
        elif m['t'] > 0 and total >= m['t']: why = 'reached its target'
        elif m['b'] > 0 and m['t'] > 0 and m['p'] >= m['t'] * ARM / 100.0 and total <= m['p'] * (1 - m['b'] / 100.0): why = 'is giving the profit back'
        if why:
            m['x'] = now; m['s'] = total; dirty = True
            e.log('burst group %d %s: %+.2f (best %+.2f, target %.2f) - closing the group' % (gid, why, total, m['p'], m['t'])); _close(e, ps)
    if dirty: e._save()


def pause(e, stop, secs):
    """Wait `secs` between passes, but look at the open groups about once a second (a small target can come and go within one pass)."""
    end = time.time() + secs
    while not stop.is_set():
        left = end - time.time()
        if left <= 0: break
        if e.groups:
            try: manage(e)
            except Exception as x: e.log('group watch error: %s' % x.__class__.__name__)
        stop.wait(min(1.0, max(0.05, left)))
'''

TEST = r"""\"\"\"DK2: the desktop app closes a burst group at its target, on give-back and at the loss limit. Run:  python tests/test_dk2.py\"\"\"
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
""".replace('\\"\\"\\"', '"""')

# ---- broker.py: two new calls + the closing price
p = 'desktop/broker.py'; s = rd(p); o = s
if 'def positions_pl' not in s: s = s.rstrip('\n') + '\n' + BROKER_ADD
a = "'reason': 'tp' if r == m.DEAL_REASON_TP else 'sl' if r == m.DEAL_REASON_SL else 'other'}"
if a in s and "'price': float(outs[-1].price)" not in s: s = s.replace(a, a[:-1] + ", 'price': float(outs[-1].price)}")
if s != o: wr(p, s)
# ---- basket.py: the group watch + remember the rules when a group opens
p = 'desktop/basket.py'; s = rd(p); o = s
a = "    e.log('burst group %d: %d of %d %s %s opened"
if '_register(e, bk, gid, placed, acct)' not in s: assert s.count(a) == 1, 'basket.py open line not found'; s = s.replace(a, "    _register(e, bk, gid, placed, acct)          # DK2\n" + a)
if 'def manage' not in s: s = s.rstrip('\n') + '\n' + BASKET_ADD
if s != o: wr(p, s)
# ---- engine.py: saved state, close report, one look per pass, a look every second while waiting
p = 'desktop/engine.py'; s = rd(p); o = s
a = "        self.outbox = list(s.get('outbox') or []); self.done = list(s.get('done') or [])[-50:]\n"
if 'self.groups =' not in s: assert s.count(a) == 1, 'init line not found'; s = s.replace(a, a + "        self.groups = {int(k): v for k, v in (s.get('groups') or {}).items() if isinstance(v, dict)}          # DK2: open burst groups\n")
a = "'done': self.done, 'offset_min': self.offset})"
if "'groups': self.groups" not in s: assert s.count(a) == 1, 'save line not found'; s = s.replace(a, "'done': self.done, 'offset_min': self.offset, 'groups': self.groups})")
a = "self._queue(sid, 'closed', pnl=info['pnl'], reason=info['reason'])"
if a in s: s = s.replace(a, "self._queue(sid, 'closed', **basket.close_extra(self, sid, info))")
a = "        if isinstance(bk, dict): basket.run(self, bk, acct, res.get('bot') is True)\n"
if 'basket.manage(self)' not in s: assert s.count(a) == 1, 'basket line not found'; s = s.replace(a, a + "        basket.manage(self)          # DK2: close a group at its target / give-back / loss limit\n")
a = "            stop.wait(self.cfg['poll_seconds'] if not fails else min(60, self.cfg['poll_seconds'] * 2 ** min(fails, 5)))"
if 'basket.pause(' not in s: assert s.count(a) == 1, 'wait line not found'; s = s.replace(a, "            basket.pause(self, stop, self.cfg['poll_seconds'] if not fails else min(60, self.cfg['poll_seconds'] * 2 ** min(fails, 5)))")
if s != o: wr(p, s)
os.makedirs(os.path.join(R, 'tests'), exist_ok=True); wr('tests/test_dk2.py', TEST)
print('DK2 applied. Now run:  python tests/test_dk2.py && python tests/test_dk1.py && python tests/test_desktop.py | tail -1')
