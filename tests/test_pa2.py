"""Tests for backend/pa_level.py (video 2, section 2). Run: python tests/test_pa2.py"""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.pa_level import pa_level, key_levels, candle_kind
from backend.indicators import atr

def bar(i, o, c, hi=None, lo=None):
    return {'t': 1700000000 + i * 900, 'o': o, 'h': hi if hi is not None else max(o, c) + 0.3, 'l': lo if lo is not None else min(o, c) - 0.3, 'c': c, 'v': 1}
def leg(a, b, n): return [a + (b - a) * k / n for k in range(n + 1)]
def build(legs):
    price = [legs[0][0]]
    for a, b, n in legs: price += leg(a, b, n)[1:]
    return [bar(-60 + k, price[0], price[0]) for k in range(30)] + [bar(i, price[i - 1], price[i]) for i in range(1, len(price))]
def flip(m): return [{'t': x['t'], 'o': 400 - x['o'], 'h': 400 - x['l'], 'l': 400 - x['h'], 'c': 400 - x['c'], 'v': 1} for x in m]
R = []
def T(name, ok): R.append(ok); print(('PASS ' if ok else 'FAIL ') + name)

# uptrend; 110 was resistance (swing high 110.3), price broke it, retested it from above (swing low 109.9) = a flipped support with 2 touches
UP = [(100, 110, 10), (110, 104, 6), (104, 120, 12), (120, 110.2, 10), (110.2, 130, 14), (130, 112, 10)]
base = build(UP); last = base[-1]['c']
REJ = bar(900, last, last + 0.5, hi=last + 0.9, lo=109.4)            # long lower wick at the level, closes back above it
m = base + [REJ]
r = pa_level(m, [])
T('support with 2 touches, uptrend, rejection wick -> buy', bool(r) and r['side'] == 'buy' and r['name'] == 'pa_level')
T('buy stop is below the wick low', bool(r) and r['sl'] < 109.4)
lv = key_levels(m[-200:], atr(m[-200:])[-1])
T('the flipped level has 2+ touches', any(abs(p - 110.1) < 0.6 and t >= 2 for p, t, _ in lv))
T('a big-body candle at the level is momentum, not rejection -> no trade', pa_level(base + [bar(900, last, 109.6, hi=last + 0.1, lo=109.5)], []) is None)
T('candle in the middle of nowhere (no level) -> no trade', pa_level(base[:-5] + [bar(900, base[-6]['c'], base[-6]['c'] + 0.4, hi=base[-6]['c'] + 0.5, lo=base[-6]['c'] - 2)], []) is None)
T('candle kinds: wick / momentum / weak', candle_kind(bar(0, 10, 10.3, hi=10.4, lo=9)) == 'rej_up' and candle_kind(bar(0, 10, 12, hi=12.1, lo=9.9)) == 'mom_up' and candle_kind(bar(0, 10, 10.5, hi=11, lo=9.5)) == 'weak')

ONE = [(103, 120, 12), (120, 106, 8), (106, 120, 6), (120, 110.2, 6), (110.2, 130, 14), (130, 112, 10)]      # only ONE touch at 110
b1 = build(ONE); l1 = b1[-1]['c']
T('only one touch -> not a level -> no trade', pa_level(b1 + [bar(900, l1, l1 + 0.5, hi=l1 + 0.9, lo=109.4)], []) is None)
BRK = UP[:-1] + [(130, 106, 12), (106, 112, 3)]                                   # closes below the level, drifts back up -> level broken
bb = build(BRK); lb = bb[-1]['c']
T('level already broken by closes below it -> no bounce trade', pa_level(bb + [bar(900, lb, lb + 0.5, hi=lb + 0.9, lo=lb - 2)], []) is None)
T('second rejection candle right after the first -> no trade', pa_level(m + [bar(901, m[-1]['c'], m[-1]['c'] + 0.4, hi=m[-1]['c'] + 0.8, lo=109.5)], []) is None)

mir = flip(m); rm = pa_level(mir, [])
T('mirror: resistance in a downtrend, upper wick -> sell, stop above', bool(rm) and rm['side'] == 'sell' and rm['sl'] > 400 - 109.4)
SIDE = [(100, 110, 6), (110, 100, 6), (100, 110, 6), (110, 100, 6), (100, 110, 6), (110, 100, 6)]
bs = build(SIDE); ls = bs[-1]['c']
T('sideways market -> stay out', pa_level(bs + [bar(900, ls, ls + 0.5, hi=ls + 0.6, lo=99.0)], []) is None)

random.seed(3); p = 2300.0; rnd = []
for i in range(1500):
    o = p; p += random.gauss(0, 1.4) + 2.2 * math.sin(i / 17); rnd.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
fired = 0
for e in range(100, 1500):
    x = pa_level(rnd[:e], [])
    if x: fired += 1; assert x['side'] in ('buy', 'sell') and x['sl'] > 0
T('never crashes on random data (fired %d times)' % fired, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
