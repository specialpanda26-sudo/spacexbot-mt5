"""DK3: the desktop app sends 5-minute candles like the EA does. Without them the server's burst scan only had 15-minute candles from the PC
app, so it looked for a burst chance once per 15 minutes instead of once per 5. Only ADDS (needs DK1). Safe to run twice."""
import os
R = os.path.dirname(os.path.abspath(__file__))
def rd(p): return open(os.path.join(R, p), encoding='utf-8').read()
def wr(p, s): open(os.path.join(R, p), 'w', encoding='utf-8').write(s)
assert os.path.exists(os.path.join(R, 'desktop', 'basket.py')), 'Run apply_dk1_basket.py first'

ADD = '''

# ---------------- DK3: 5-minute candles ----------------
def rates_m5(e, name, off):
    """The 5-minute candles for the server's burst scan (the EA sends them too: 450 on the first push, then the newest 14). [] when MT5 cannot give them,
    so the 15-minute and 1-hour candles still go."""
    try: r = e.b.rates(name, 'M5', 450 if e.first_push else 14)
    except Exception as x: e.log('%s 5-minute candles: %s' % (name, x)); return []
    return [[q[0] - off] + q[1:] for q in (r or [])]
'''
TEST = r'''"""DK3: 5-minute candles reach the server. Run:  python tests/test_dk3.py"""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import bars
ok = []
def chk(name, c): ok.append((name, bool(c)))

def with_m5(fb, fail=False):
    old = fb.rates
    def rates(sym, tf, count):
        if tf != 'M5': return old(sym, tf, count)
        if fail: raise RuntimeError('no M5')
        last = int(fb.clock.now // 300) * 300 - 300
        return [[last - (count - 1 - k) * 300 + fb.off * 60, 2300.0 + k * 0.01, 2300.5 + k * 0.01, 2299.5, 2300.2, 5] for k in range(count)]
    fb.rates = rates; return fb

bars._d.clear(); clock, fb, web, e, sf = D.rig(off=180); with_m5(fb); D.go(e, clock, 4)
m5 = bars.get('XAUUSD', 'M5'); m15 = bars.get('XAUUSD', 'M15')
chk('first push: 450 five-minute candles reach the server', len(m5) >= 400)
chk('five-minute candles are 5 minutes apart and in UTC', len(m5) > 2 and m5[-1]['t'] - m5[-2]['t'] == 300 and m5[-1]['t'] <= int(clock.now))
chk('15-minute candles still go', len(m15) >= 400)
bars._d.clear(); clock, fb, web, e, sf = D.rig(off=180); with_m5(fb, fail=True); D.go(e, clock, 4)
chk('MT5 cannot give 5-minute candles: 15-minute candles still go, no crash', len(bars.get('XAUUSD', 'M15')) >= 400 and not bars.get('XAUUSD', 'M5'))
bad = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if bad else 0)
'''
p = 'desktop/broker.py'; s = rd(p); o = s
a = "{'M15': m.TIMEFRAME_M15, 'H1': m.TIMEFRAME_H1}[tf]"
if a in s and 'TIMEFRAME_M5' not in s: s = s.replace(a, "{'M5': m.TIMEFRAME_M5, 'M15': m.TIMEFRAME_M15, 'H1': m.TIMEFRAME_H1}[tf]")
if s != o: wr(p, s)
p = 'desktop/basket.py'; s = rd(p); o = s
if 'def rates_m5' not in s: s = s.rstrip('\n') + '\n' + ADD
if s != o: wr(p, s)
p = 'desktop/engine.py'; s = rd(p); o = s
a = "            if m15: out[canon] = {'M15': [[r[0] - off] + r[1:] for r in m15], 'H1': [[r[0] - off] + r[1:] for r in h1]}\n"
if 'basket.rates_m5' not in s:
    assert s.count(a) == 1, 'candle line not found'
    s = s.replace(a, "            if m15:\n                out[canon] = {'M15': [[r[0] - off] + r[1:] for r in m15], 'H1': [[r[0] - off] + r[1:] for r in h1]}\n                m5 = basket.rates_m5(self, n, off)          # DK3\n                if m5: out[canon]['M5'] = m5\n")
if s != o: wr(p, s)
wr('tests/test_dk3.py', TEST)
print('DK3 applied. Now run:  python tests/test_dk3.py && python tests/test_dk2.py && python tests/test_dk1.py && python tests/test_desktop.py | tail -1')
