"""Tests for backend/pa_structure.py (video 2, section 1). Run: python tests/test_pa1.py"""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.pa_structure import pa_bos, structure

def bar(i, o, c, hi=None, lo=None):
    return {'t': 1700000000 + i * 900, 'o': o, 'h': hi if hi is not None else max(o, c) + 0.3, 'l': lo if lo is not None else min(o, c) - 0.3, 'c': c, 'v': 1}
def leg(a, b, n): return [a + (b - a) * k / n for k in range(n + 1)]
def build(legs, flip=False):
    price = [legs[0][0]]
    for a, b, n in legs: price += leg(a, b, n)[1:]
    if flip: price = [400 - x for x in price]
    return [bar(-60 + k, price[0], price[0]) for k in range(30)] + [bar(i, price[i - 1], price[i]) for i in range(1, len(price))]
R = []
def T(name, ok): R.append(ok); print(('PASS ' if ok else 'FAIL ') + name)

UP = [(100, 120, 10), (120, 112, 6), (112, 135, 10), (135, 126, 6), (126, 150, 10)]
T('structure: higher highs + higher lows -> up', structure(build(UP)) == 'up')
T('structure: lower highs + lower lows -> down', structure(build(UP, flip=True)) == 'down')
SIDE = [(100, 110, 6), (110, 100, 6), (100, 110, 6), (110, 100, 6), (100, 110, 6), (110, 100, 6)]
T('structure: sideways -> side (stay out)', structure(build(SIDE)) == 'side')

# uptrend with higher lows (112, 126), then breaks 126, retests it, makes a LOWER HIGH (<150), then a bearish trigger
BEAR = UP + [(150, 124, 8), (124, 130, 4), (130, 128, 2)]
def with_trigger(base, flip=False):
    m = build(base, flip); l = m[-1]; d = -1 if not flip else 1
    return m, m + [bar(999, l['c'], l['c'] - 6 * (1 if not flip else -1), hi=l['c'] + (0.3 if not flip else 0), lo=None)]
m0, m = with_trigger(BEAR)
T('retest made, no trigger candle yet -> no trade', pa_bos(m0, []) is None)
r = pa_bos(m, [])
T('break of last higher low + lower high + bearish candle -> sell', bool(r) and r['side'] == 'sell')
T('sell: stop above the retest high', bool(r) and r['sl'] > 130)
m_no_break = build(UP + [(150, 128, 8), (128, 136, 4), (136, 129, 3)])
T('no close below the higher low -> no trade', pa_bos(m_no_break, []) is None)
m_hh = build(UP + [(150, 124, 8), (124, 158, 6), (158, 150, 3)])
T('retest makes a NEW HIGH (trend not broken) -> no trade', pa_bos(m_hh, []) is None)
m_wait = build(UP + [(150, 124, 8)])
T('first break only, no retest yet -> no trade (wait)', pa_bos(m_wait, []) is None)
mb0, mb = with_trigger(BEAR, True); rb = pa_bos(mb, [])
T('bullish mirror -> buy, stop below', bool(rb) and rb['side'] == 'buy' and rb['sl'] < 400 - 130)
m2 = m + [bar(1000, m[-1]['c'], m[-1]['c'] - 1.5, hi=m[-1]['c'], lo=m[-1]['c'] - 1.8)]
T('second trigger candle after the first -> no trade', pa_bos(m2, []) is None)
random.seed(2); p = 2300.0; rnd = []
for i in range(1500):
    o = p; p += random.gauss(0, 1.4) + 2.2 * math.sin(i / 17); rnd.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
fired = 0
for e in range(100, 1500):
    r = pa_bos(rnd[:e], [])
    if r: fired += 1; assert r['side'] in ('buy', 'sell') and r['sl'] > 0
T('never crashes on random data (fired %d times)' % fired, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
