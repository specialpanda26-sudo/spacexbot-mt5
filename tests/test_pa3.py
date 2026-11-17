"""Tests for backend/pa_candle.py (video 2, section 3). Run: python tests/test_pa3.py"""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.pa_candle import pa_candle, signal, patterns, at_level
from backend.indicators import atr

def bar(i, o, c, hi=None, lo=None):
    return {'t': 1700000000 + i * 900, 'o': o, 'h': hi if hi is not None else max(o, c) + 0.3, 'l': lo if lo is not None else min(o, c) - 0.3, 'c': c, 'v': 1}
def leg(a, b, n): return [a + (b - a) * k / n for k in range(n + 1)]
def build(legs):
    price = [legs[0][0]]
    for a, b, n in legs: price += leg(a, b, n)[1:]
    return [bar(-60 + k, price[0], price[0]) for k in range(30)] + [bar(i, price[i - 1], price[i]) for i in range(1, len(price))]
def flip(m): return [{'t': x['t'], 'o': 400 - x['o'], 'h': 400 - x['l'], 'l': 400 - x['h'], 'c': 400 - x['c'], 'v': 1} for x in m]
def kind(m): s = signal(m); return (s['side'], s['pattern']) if s else None
def has(m, name, side):
    """the named pattern is detected on the last candle AND passes every filter (level, trend, stop)"""
    import backend.pa_candle as pc
    s = signal(m)
    if s and s['pattern'] == name and s['side'] == side: return True
    keep = pc.patterns
    try:
        pc.patterns = lambda w, a: [x for x in keep(w, a) if x[0] == name and x[1] == side]       # isolate this pattern
        s = signal(m)
    finally: pc.patterns = keep
    return bool(s) and s['pattern'] == name and s['side'] == side
R = []
def T(name, ok): R.append(ok); print(('PASS ' if ok else 'FAIL ') + name)

# uptrend; 110 was resistance, price broke it and retested it from above = flipped support with 2 touches (same fixture as section 2)
UP = [(100, 110, 10), (110, 104, 6), (104, 120, 12), (120, 110.2, 10), (110.2, 130, 14), (130, 112, 10)]
base = build(UP)
ENG = [bar(900, 112, 111.4, hi=112.1, lo=110.9), bar(901, 111.4, 113.6, hi=113.8, lo=110.4)]      # small red, then a big green one swallowing it
STAR = [bar(900, 112.2, 110.4, hi=112.3, lo=110.3), bar(901, 110.3, 110.1, hi=110.5, lo=109.7), bar(902, 110.2, 112.4, hi=112.5, lo=110.1)]
m = base + ENG
r = pa_candle(m, [])
T('bullish engulfing at a 2-touch support -> buy', bool(r) and r['side'] == 'buy' and r['name'] == 'pa_candle' and has(m, 'engulfing', 'buy'))
T('buy stop is below the pattern low', bool(r) and r['sl'] < 110.4)
ms = base + STAR
T('morning star at support -> buy', has(ms, 'morning_star', 'buy') and pa_candle(ms, [])['side'] == 'buy')
T('evening star at resistance (mirror) -> sell, stop above', has(flip(ms), 'evening_star', 'sell') and pa_candle(flip(ms), [])['sl'] > 400 - 109.7)
T('bearish engulfing at resistance (mirror) -> sell', has(flip(m), 'engulfing', 'sell'))

mid = base[:-5]; c0 = mid[-1]['c']
T('same engulfing in the middle of nowhere (no level) -> no trade', pa_candle(mid + [bar(900, c0, c0 - 0.6, hi=c0 + 0.1, lo=c0 - 1.1), bar(901, c0 - 0.6, c0 + 1.6, hi=c0 + 1.8, lo=c0 - 1.4)], []) is None)
ONE = build([(103, 120, 12), (120, 106, 8), (106, 120, 6), (120, 110.2, 6), (110.2, 130, 14), (130, 112, 10)])       # only ONE touch at 110
T('level with only one touch -> no trade', pa_candle(ONE + ENG, []) is None)
BRK = build(UP[:-1] + [(130, 106, 12), (106, 112, 3)])                                                              # closes below the level -> broken
mb = BRK + ENG; ok_ = base + ENG
T('level already broken by closes below it -> not a support any more (no trade)', at_level(mb, atr(mb)[-1], 'buy', 2) is False and at_level(ok_, atr(ok_)[-1], 'buy', 2) is True and at_level(flip(mb), atr(flip(mb))[-1], 'sell', 2) is False and at_level(flip(ok_), atr(flip(ok_))[-1], 'sell', 2) is True and pa_candle(mb, []) is None)
T('engulfed candle not small (video: big swallows SMALL) -> no engulfing', pa_candle(base + [bar(900, 112, 109.6, hi=112.1, lo=109.5), bar(901, 109.6, 112.6, hi=112.8, lo=109.4)], []) is None)
T('big green candle that does not engulf the red one -> no trade', pa_candle(base + [bar(900, 112, 111.4, hi=112.1, lo=110.9), bar(901, 111.4, 111.9, hi=112.0, lo=110.4)], []) is None)
T('star whose third candle does not close past the middle of the first -> no trade', pa_candle(base + STAR[:2] + [bar(902, 110.2, 110.9, hi=111.1, lo=110.1)], []) is None)
T('second pattern right after the first one -> no trade', signal(m + [bar(902, 113.6, 113.0, hi=113.7, lo=110.6), bar(903, 113.0, 116.0, hi=116.0, lo=111.4)]) is not None
  and pa_candle(m + [bar(902, 113.6, 113.0, hi=113.7, lo=110.6), bar(903, 113.0, 116.0, hi=116.0, lo=111.4)], []) is None)

# three line strike: pullback of three red candles inside an uptrend, then one big green candle swallowing all three (no key level needed)
UPT = base[:-3]; t3 = UPT[-1]['c']
STRIKE = [bar(900, t3, t3 - 1.8), bar(901, t3 - 1.8, t3 - 3.6), bar(902, t3 - 3.6, t3 - 5.4), bar(903, t3 - 5.4, t3 + 0.6, hi=t3 + 0.7, lo=t3 - 5.5)]
T('three line strike (big green swallows 3 red) in an uptrend -> buy', has(UPT + STRIKE, 'three_line_strike', 'buy') and bool(pa_candle(UPT + STRIKE, [])))
T('three line strike mirror: big red in a downtrend -> sell', has(flip(UPT + STRIKE), 'three_line_strike', 'sell'))
DN = flip(UPT); d3 = DN[-1]['c']
WRONG = [bar(900, d3, d3 - 1.8), bar(901, d3 - 1.8, d3 - 3.6), bar(902, d3 - 3.6, d3 - 5.4), bar(903, d3 - 5.4, d3 + 0.6, hi=d3 + 0.7, lo=d3 - 5.5)]
T('big green three line strike in a DOWNtrend -> no trade (trade with the trend)', not has(DN + WRONG, 'three_line_strike', 'buy'))
T('strike that is not three same-direction candles -> no trade', not has(UPT + [STRIKE[0], bar(901, t3 - 1.8, t3 - 1.0), STRIKE[2], STRIKE[3]], 'three_line_strike', 'buy'))

bs = build([(100, 110, 6), (110, 100, 6), (100, 110, 6), (110, 100, 6), (100, 110, 6), (110, 100, 6)])
ls = bs[-1]['c']
T('sideways market -> stay out (engulfing at the range low)', pa_candle(bs + [bar(900, ls, ls - 0.6, hi=ls + 0.1, lo=ls - 1.0), bar(901, ls - 0.6, ls + 1.6, hi=ls + 1.8, lo=ls - 0.9)], []) is None)
T('pattern list is empty on plain candles', patterns(base, atr(base)[-1]) == [])

random.seed(3); p = 2300.0; rnd = []
for i in range(1500):
    o = p; p += random.gauss(0, 1.4) + 2.2 * math.sin(i / 17); rnd.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
fired = 0
for e in range(100, 1500):
    x = pa_candle(rnd[:e], [])
    if x: fired += 1; assert x['side'] in ('buy', 'sell') and x['sl'] > 0 and x['name'] == 'pa_candle'
T('never crashes on random data (fired %d times)' % fired, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
