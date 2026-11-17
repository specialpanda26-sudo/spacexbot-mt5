"""Tests for backend/pa_pattern.py (video 2, section 4). Run: python tests/test_pa4.py"""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.pa_pattern import pa_pattern, signal
from backend.indicators import atr

def bar(i, o, c, hi=None, lo=None):
    return {'t': 1700000000 + i * 900, 'o': o, 'h': hi if hi is not None else max(o, c) + 0.3, 'l': lo if lo is not None else min(o, c) - 0.3, 'c': c, 'v': 1}
def leg(a, b, n): return [a + (b - a) * k / n for k in range(n + 1)]
def build(legs):
    price = [legs[0][0]]
    for a, b, n in legs: price += leg(a, b, n)[1:]
    return [bar(-60 + k, price[0], price[0]) for k in range(30)] + [bar(i, price[i - 1], price[i]) for i in range(1, len(price))]
def flip(m): return [{'t': x['t'], 'o': 400 - x['o'], 'h': 400 - x['l'], 'l': 400 - x['h'], 'c': 400 - x['c'], 'v': 1} for x in m]
def fires(m, start=35):
    """[(index, signal)] for every candle of m that triggers a trade - walks the chart candle by candle like the live bot does"""
    return [(e, s) for e in range(start, len(m) + 1) for s in [signal(m[:e])] if s]
def only(m, pattern): return [e for e, s in fires(m) if s['pattern'] == pattern]
import backend.pa_pattern as pp
def only_with(m, pattern, **kw):
    old = {k: getattr(pp, k) for k in kw}
    for k, v in kw.items(): setattr(pp, k, v)
    try: return only(m, pattern)
    finally:
        for k, v in old.items(): setattr(pp, k, v)
def blocked_by(m, pattern, **kw):
    """no trade as built, but the SAME chart does trade once this one rule is relaxed -> that rule is what stops it"""
    return only(m, pattern) == [] and only_with(m, pattern, **kw) != []
R = []
def T(name, ok): R.append(ok); print(('PASS ' if ok else 'FAIL ') + name)

# double top: rise to 120, dip to 108 (neckline), second top 119 (NOT the same height), then a fall through the neckline
DT = build([(100, 120, 15), (120, 108, 8), (108, 119, 8), (119, 100, 12)])
f = fires(DT)
T('double top (second top a bit lower) -> exactly one sell, on the neckline break', len(f) == 1 and f[0][1]['side'] == 'sell' and f[0][1]['pattern'] == 'double_top')
e = f[0][0]; neck = min(x['l'] for x in DT[:e] if x['t'] > 0)
T('the trigger candle is the FIRST close below the neckline', DT[e - 1]['c'] < 107.8 and all(x['c'] >= 107.7 for x in DT[e - 9:e - 1]))
T('sell stop is above the tops', f[0][1]['sl'] > 120.3)
r = pa_pattern(DT[:e], [])
T('pa_pattern returns the standard signal dict', bool(r) and set(r) == {'side', 'sl', 'name'} and r['name'] == 'pa_pattern')
T('the wait before the break gives no trade (price still above the neckline)', not any(x < e for x, _ in f) and signal(DT[:e - 1]) is None)
DB = flip(DT); fb = fires(DB)
T('double bottom (mirror) -> exactly one buy, stop below the bottoms', len(fb) == 1 and fb[0][1]['side'] == 'buy' and fb[0][1]['pattern'] == 'double_bottom' and fb[0][1]['sl'] < 400 - 120.3)

T('tops far apart in height (120 vs 114) -> not a double top (TOP_TOL)', blocked_by(build([(100, 120, 15), (120, 108, 8), (108, 114, 8), (114, 98, 10)]), 'double_top', TOP_TOL=99))
T('shallow wiggle (dip of 3 points only) -> not a double top (MIN_DEPTH)', blocked_by(build([(100, 120, 15), (120, 117, 4), (117, 119, 4), (119, 105, 14)]), 'double_top', MIN_DEPTH=-9))
T('no real run-up into the first top -> not a double top (PRIOR_MOVE)', blocked_by(build([(117, 120, 3), (120, 108, 8), (108, 119, 8), (119, 100, 12)]), 'double_top', PRIOR_MOVE=-99))
T('price pushes above the tops first, then collapses -> the pattern failed (INTACT)', blocked_by(build([(100, 120, 15), (120, 108, 8), (108, 119, 8), (119, 112, 4), (112, 123, 4), (123, 100, 12)]), 'double_top', INTACT=99))

# head and shoulders: left shoulder 115, head 125, right shoulder 116 (shoulders differ), sloped neckline 108 -> 109, then a fall through it
HS = build([(100, 115, 12), (115, 108, 6), (108, 125, 10), (125, 109, 10), (109, 116, 6), (116, 98, 14)])
fh = fires(HS)
T('head and shoulders -> exactly one sell, on the neckline break', len(fh) == 1 and fh[0][1]['side'] == 'sell' and fh[0][1]['pattern'] == 'head_shoulders')
T('head and shoulders stop is above the right shoulder, below the head', 116.3 < fh[0][1]['sl'] < 125)
IH = flip(HS); fi = fires(IH)
T('inverted head and shoulders (mirror) -> exactly one buy', len(fi) == 1 and fi[0][1]['side'] == 'buy' and fi[0][1]['pattern'] == 'inverse_head_shoulders')
T('head barely higher than the shoulders -> not a head and shoulders (HEAD_EXTRA)', blocked_by(build([(100, 115, 12), (115, 108, 6), (108, 115.4, 6), (115.4, 109, 6), (109, 115, 6), (115, 98, 14)]), 'head_shoulders', HEAD_EXTRA=-99))
T('price rallies above the head after the right shoulder, then drops -> not a head and shoulders', only(build([(100, 112, 10), (112, 106, 5), (106, 118, 9), (118, 107, 9), (107, 113, 5), (113, 109, 3), (109, 119.5, 4), (119.5, 96, 16)]), 'head_shoulders') == []
  and len(only(build([(100, 112, 10), (112, 106, 5), (106, 118, 9), (118, 107, 9), (107, 113, 5), (113, 96, 16)]), 'head_shoulders')) == 1)
T('bounce back above the neckline for a while after the break, then down again -> no second trigger', len(only_with(build([(100, 120, 15), (120, 108, 8), (108, 119, 8), (119, 104, 10), (104, 111, 3), (111, 111.5, 8), (111.5, 95, 9)]), 'double_top', MAX_STOP=999)) == 1)
T('head and shoulders: bounce back above the neckline for a while, then down again -> no second trigger', len(only_with(build([(100, 115, 12), (115, 108, 6), (108, 125, 10), (125, 109, 10), (109, 116, 6), (116, 104, 8), (104, 112, 3), (112, 112.5, 8), (112.5, 90, 12)]), 'head_shoulders', MAX_STOP=999)) == 1)
T('two overlapping neckline breaks one candle apart -> only ONE trade (repeat guard)', len([1 for _, s in fires(build([(100, 115, 12), (115, 108, 6), (108, 115.2, 6), (115.2, 109, 6), (109, 116, 6), (116, 98, 14)])) if s['side'] == 'sell']) == 1)

random.seed(3); p = 2300.0; rnd = []
for i in range(1500):
    o = p; p += random.gauss(0, 1.4) + 2.2 * math.sin(i / 17); rnd.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
fired = 0
for e in range(100, 1500):
    x = pa_pattern(rnd[:e], [])
    if x: fired += 1; assert x['side'] in ('buy', 'sell') and x['sl'] > 0 and x['name'] == 'pa_pattern'
T('never crashes on random data (fired %d times)' % fired, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)

