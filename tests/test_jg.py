"""Tests for backend/jg_pullback.py (video 1 setup). Run: python tests/test_jg.py"""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.jg_pullback import jg_pullback

def bar(i, o, c, hi=None, lo=None):
    return {'t': 1700000000 + i * 900, 'o': o, 'h': hi if hi is not None else max(o, c) + 0.3, 'l': lo if lo is not None else min(o, c) - 0.3, 'c': c, 'v': 1}
def leg(a, b, n): return [a + (b - a) * k / n for k in range(n + 1)]
def build(legs, flip=False):
    price = [legs[0][0]]
    for a, b, n in legs: price += leg(a, b, n)[1:]
    if flip: price = [400 - x for x in price]
    return [bar(-60 + k, price[0], price[0]) for k in range(30)] + [bar(i, price[i - 1], price[i]) for i in range(1, len(price))]
BEAR = [(150, 130, 10), (130, 138, 6), (138, 115, 10), (115, 122, 6), (122, 100, 10), (100, 111, 8)]
R = []
def T(name, ok): R.append(ok); print(('PASS ' if ok else 'FAIL ') + name)

m = build(BEAR); l = m[-1]
T('no trigger candle -> no trade', jg_pullback(m, []) is None)
trig = bar(999, l['c'] - 0.1, l['l'] - 1.5, hi=l['c'], lo=l['l'] - 1.8)
r = jg_pullback(m + [trig], [])
T('bearish: lower-low lower-close in a pullback -> sell', bool(r) and r['side'] == 'sell')
T('sell: stop above pullback high, target below entry, rr >= 1.5', bool(r) and r['sl'] > trig['c'] > r['tp'] and (trig['c'] - r['tp']) >= 1.5 * (r['sl'] - trig['c']))
T('sell: target is near the lowest close of the run (~100)', bool(r) and 99 < r['tp'] < 102)
weak = bar(999, l['c'] - 0.1, l['c'] + 0.2, hi=l['c'] + 0.3, lo=l['l'] - 1.8)   # lower low but closes UP
T('lower low but close not below previous low -> no trade', jg_pullback(m + [weak], []) is None)
second = bar(1000, trig['c'] + 0.2, trig['l'] - 1.0, hi=trig['c'] + 0.3, lo=trig['l'] - 1.2)
T('second trigger in the same pullback -> no trade (one trade per pullback)', jg_pullback(m + [trig, trig_ := bar(1000, trig['c'], trig['c'] + 0.3), second], []) is None)
newlow = bar(999, l['c'], 98.0, hi=l['c'], lo=97.5)
T('price already broke the last low -> no trade (that is a new run)', jg_pullback(m + [newlow], []) is None)
mb = build(BEAR, flip=True); lb = mb[-1]
tb = bar(999, lb['c'] + 0.1, lb['h'] + 1.5, hi=lb['h'] + 1.8, lo=lb['c'])
rb = jg_pullback(mb + [tb], [])
T('bullish mirror -> buy, stop below, target above', bool(rb) and rb['side'] == 'buy' and rb['sl'] < tb['c'] < rb['tp'])
random.seed(1); p = 2300.0; rnd = []
for i in range(1500):
    o = p; p += random.gauss(0, 1.4) + 2.2 * math.sin(i / 17); rnd.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
fired = 0
for e in range(100, 1500):
    r = jg_pullback(rnd[:e], [])
    if r: fired += 1; assert r['side'] in ('buy', 'sell') and r['sl'] > 0 and r['tp'] > 0
T('never crashes on random data (fired %d times)' % fired, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
