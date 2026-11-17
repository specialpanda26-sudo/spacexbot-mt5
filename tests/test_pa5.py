"""Tests for backend/pa_trendline.py (video 2, section 5). Run: python tests/test_pa5.py"""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.pa_trendline as pt
from backend.pa_trendline import pa_trendline, signal, uptrend_line, _neg
from backend.indicators import atr

def bar(i, o, c, hi=None, lo=None):
    return {'t': 1700000000 + i * 900, 'o': o, 'h': hi if hi is not None else max(o, c) + 0.3, 'l': lo if lo is not None else min(o, c) - 0.3, 'c': c, 'v': 1}
def leg(a, b, n): return [a + (b - a) * k / n for k in range(n + 1)]
def build(legs):
    price = [legs[0][0]]
    for a, b, n in legs: price += leg(a, b, n)[1:]
    return [bar(-60 + k, price[0], price[0]) for k in range(30)] + [bar(i, price[i - 1], price[i]) for i in range(1, len(price))]
def flip(m): return [{'t': x['t'], 'o': 400 - x['o'], 'h': 400 - x['l'], 'l': 400 - x['h'], 'c': 400 - x['c'], 'v': 1} for x in m]
def fires(m, start=35): return [(e, s) for e in range(start, len(m) + 1) for s in [signal(m[:e])] if s]
def only(m, kind): return [e for e, s in fires(m) if s['kind'] == kind]
def only_with(m, kind, **kw):
    old = {k: getattr(pt, k) for k in kw}
    for k, v in kw.items(): setattr(pt, k, v)
    try: return only(m, kind)
    finally:
        for k, v in old.items(): setattr(pt, k, v)
def blocked_by(m, kind, **kw):
    """no trade as built, but the SAME chart does trade once this one rule is relaxed -> that rule is what stops it"""
    return only(m, kind) == [] and only_with(m, kind, **kw) != []
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)

# base: higher lows 110 -> 122 (line through them), higher highs 120 -> 132 -> 134, then the chart walks back down to just above the line
BASE = [(100, 120, 15), (120, 110, 8), (110, 132, 12), (132, 122, 8), (122, 134, 6)]
def uptrend_chart(base=BASE, approach=6):
    """returns (chart so far, index of the next candle, line value there). The chart is the base plus a gentle walk down to the line."""
    m = build(base); a = atr(m)[-1]; t = uptrend_line(m, a)
    assert t, 'fixture: no line'
    i1, p1, i2, p2 = t; ln = lambda j: p1 + (p2 - p1) * (j - i1) / (i2 - i1)
    n = len(m) + approach; y = ln(n)
    top = m[-1]['c']; end = y + 3.0
    for k in range(1, approach + 1):
        o = m[-1]['c']; c = top + (end - top) * k / approach
        m.append(bar(len(m), o, c))
    return m, ln, a
def candle(m, o, c, hi, lo): return m + [bar(len(m), o, c, hi, lo)]

m, ln, a = uptrend_chart(); n = len(m); y = ln(n)
T('fixture: uptrend line draws through the two higher lows', uptrend_line(m, a) is not None and uptrend_line(m, a)[3] > uptrend_line(m, a)[1])
# BOUNCE: dips to the line, long lower wick, closes back above, bullish
BN = candle(m, y + 3.0, y + 3.4, y + 3.8, y - 0.2)
f = fires(BN)
T('uptrend line bounce (rejection wick at the line) -> exactly one buy, on that candle', len(f) == 1 and f[0][0] == len(BN) and f[0][1]['side'] == 'buy' and f[0][1]['kind'] == 'bounce' and f[0][1]['line'] == 'up')
T('bounce stop is below the wick', f[0][1]['sl'] < y - 0.2)
r = pa_trendline(BN, [])
T('pa_trendline returns the standard signal dict', bool(r) and set(r) == {'side', 'sl', 'name'} and r['name'] == 'pa_trendline')
T('before the line is reached there is no trade', signal(m) is None)
BS = flip(BN); fs = fires(BS)
T('downtrend line (mirror: join the lower HIGHS) bounce -> exactly one sell', len(fs) == 1 and fs[0][1]['side'] == 'sell' and fs[0][1]['line'] == 'down' and fs[0][1]['sl'] > 400 - (y - 0.2))

# no second line to draw -> nothing to trade (needs 2 touches)
ONE = build([(100, 130, 25), (130, 118, 6), (118, 128, 6), (128, 119, 6)])
T('only one low, no line can be drawn -> no trade (needs two touches)', uptrend_line(ONE, atr(ONE)[-1]) is None and fires(ONE) == [])
# lower low -> that pair is not an uptrend line
T('second low is LOWER than the first -> no uptrend line', uptrend_line(build([(100, 130, 25), (130, 118, 8), (118, 128, 8), (128, 112, 8), (112, 120, 6)]), 2.0) is None)

# BREAK: big bearish candle closes well below the line, no retest needed
BK = candle(m, y + 3.0, y - 2.6, y + 3.2, y - 2.9)
fk = fires(BK)
T('big bearish candle through the uptrend line -> one sell (break) with no retest', len(fk) == 1 and fk[0][0] == len(BK) and fk[0][1]['side'] == 'sell' and fk[0][1]['kind'] == 'break')
T('break stop is above the break candle', fk[0][1]['sl'] > y + 3.2)
T('mirror: big bullish break of a downtrend line -> one buy', [s['side'] for _, s in fires(flip(BK))] == ['buy'])
T('a small candle that closes just under the line is no break (momentum, MOM_ATR)', blocked_by(candle(m, y + 0.6, y - 0.6, y + 0.8, y - 0.8), 'break', MOM_ATR=0.0, BREAK_MARGIN=0.0))
T('a break needs a body, not a long wick (MOM_BODY)', blocked_by(candle(m, y + 1.0, y - 2.0, y + 3.0, y - 3.0), 'break', MOM_BODY=0.0))
T('close only just under the line (BREAK_MARGIN)', blocked_by(candle(m, y + 3.0, y - 0.1, y + 3.2, y - 0.3), 'break', BREAK_MARGIN=-9))
FK = candle(m, y + 2.0, y + 1.4, y + 2.4, y - 1.8)
T('FAKE-OUT: wick pokes well through the line and closes back inside -> no trade at all', fires(FK) == [] )
T('a second candle closing below the line gives NO second break (first close only)', len(fires(candle(BK, y - 2.6, y - 5.5, y - 2.4, y - 5.8))) == 1)
T('the wick fake-out only trades as a bounce if it is shallow (PIERCE)', blocked_by(candle(m, y + 2.0, y + 2.6, y + 3.0, y - 1.2), 'bounce', PIERCE=3.0))

# sideways structure (lower highs while lows rise) -> stay out, even though a rising line exists
SW = [(100, 125, 15), (125, 110, 8), (110, 122, 12), (122, 118, 8), (118, 121, 5)]
ms, lns, a2 = uptrend_chart(SW, 6); ys = lns(len(ms))
T('rising lows but falling highs (sideways) -> stay out (TREND_ONLY)', blocked_by(candle(ms, ys + 3.0, ys + 3.4, ys + 3.8, ys - 0.2), 'bounce', TREND_ONLY=False))

# a candle that touched the line a moment ago is not the first touch (no repeat on consecutive candles)
T('two candles in a row at the line -> only the first one buys', len([1 for _, s in fires(candle(BN, y + 3.4 + 0.6, y + 3.9, y + 4.3, y + 0.2)) if s['side'] == 'buy']) == 1)
# the line must still be intact: a close below it earlier kills it
def broken_then_back(close_below):
    """break candle at index n (closes below the line, or just above it for the control), a 9-candle recovery well above the line, then a touch"""
    c = candle(m, y + 3.0, y - 2.6 if close_below else y + 0.4, y + 3.2, y - 2.9 if close_below else y - 0.3)
    top = ln(len(c) + 9) + 6.0
    for k in range(1, 10): c.append(bar(len(c), c[-1]['c'], c[-1]['c'] + (top - c[-1]['c']) / (10 - k)))
    for k in range(1, 6): c.append(bar(len(c), c[-1]['c'], c[-1]['c'] - (c[-1]['c'] - (ln(len(c) + 6) + 3.0)) / (6 - k) if k < 5 else c[-1]['c'] - 0.3))
    t = uptrend_line(c, atr(c)[-1])
    f = (lambda j: t[1] + (t[3] - t[1]) * (j - t[0]) / (t[2] - t[0])) if t else ln           # the line as it stands now (a newer low may have redrawn it)
    yy = f(len(c))
    return candle(c, yy + 3.0, yy + 3.4, yy + 3.8, yy - 0.2)
BB = broken_then_back(True); CB = broken_then_back(False)
T('control: same chart, but the earlier candle only wicked the line (closed above) -> the line lives, bounce buys', 'bounce' in [s['kind'] for _, s in fires(CB)])
def after_dip(close):
    """the line as seen two candles after a candle that dips to the line and closes at `close` (low always within the wick allowance)"""
    c = candle(m, y + 3.0, close, y + 3.2, min(close, y) - 0.1)
    c = candle(c, c[-1]['c'], c[-1]['c'] + 2.0, c[-1]['c'] + 2.3, c[-1]['c'] - 0.1)
    return uptrend_line(c, atr(c)[-1])
T('control: a candle dips to the line but closes above it -> the line is still alive', after_dip(y + 0.3) is not None)
T('a candle that CLOSES under the line (only slightly) kills it, so no bounce can use the broken line later', after_dip(y - 0.4) is None)
# 2) consecutive candles at the line: the second also looks like a perfect rejection but is not the first
y2 = ln(len(BN)); two = candle(BN, y + 3.4, y2 + 3.5, y2 + 3.9, y2 - 0.2)
T('the second candle at the line is also a clean rejection, but only the first one buys (not the first touch)', [e for e, s in fires(two) if s['side'] == 'buy'] == [len(BN)])
# 3) the candle at the line must show buyers (rejection wick or big bullish body), a weak candle does not count
T('weak bullish candle touching the line (no wick, no body) -> no bounce', fires(candle(m, y + 0.5, y + 0.7, y + 1.3, y + 0.3)) == [])

random.seed(5); p = 2300.0; rnd = []
for i in range(1500):
    o = p; p += random.gauss(0, 1.4) + 2.2 * math.sin(i / 17); rnd.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
fired = 0
for e in range(100, 1500):
    x = pa_trendline(rnd[:e], [])
    if x: fired += 1; assert x['side'] in ('buy', 'sell') and x['sl'] > 0 and x['name'] == 'pa_trendline'
T('never crashes on random data (fired %d times)' % fired, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
