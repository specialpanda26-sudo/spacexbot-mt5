"""Tests for backend/ma_cross.py (video 3, section 3A). Run: python tests/test_ma1.py"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.ma_cross as mc
from backend.ma_cross import ma_cross

def bars(prices, step=3600, noise=0.3, seed=1, t0=1700000000):
    r = random.Random(seed); out = []
    for i, p in enumerate(prices):
        o = prices[i - 1] if i else p
        out.append({'t': t0 + i * step, 'o': o, 'h': max(o, p) + noise * r.random(), 'l': min(o, p) - noise * r.random(), 'c': p, 'v': 1})
    return out
def legs(spec, start=100.0):
    p = [start]
    for d, n in spec:
        for _ in range(n): p.append(p[-1] + d)
    return p
def flip(prices): return [400 - x for x in prices]
def fires(m, h=lambda e: [], start=80): return [(e, ma_cross(m[:e], h(e))) for e in range(start, len(m) + 1) if ma_cross(m[:e], h(e))]
def with_(m, **kw):
    old = {k: getattr(mc, k) for k in kw}
    for k, v in kw.items(): setattr(mc, k, v)
    try: return fires(m)
    finally:
        for k, v in old.items(): setattr(mc, k, v)
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)

TREND = legs([(1, 60), (-1, 60)] * 4)               # strong 60-candle trends, crosses at 87, 145, 205, 265, 325, 385, 445
M = bars(TREND); F = fires(M)
T('trending market with a history of following its crosses: trades the 4th cross on (4 trades)', [e for e, _ in F] == [266, 326, 386, 446])
T('fast crosses above slow -> buy, below -> sell (alternating legs)', [s['side'] for _, s in F] == ['buy', 'sell', 'buy', 'sell'])
T('exactly one trade per cross (never on the other candles of the leg)', len(F) == 4 and all(F[i + 1][0] - F[i][0] == 60 for i in range(3)))
T('buy stop is below the price, sell stop above', all((s['sl'] < M[e - 1]['c']) == (s['side'] == 'buy') for e, s in F))
from backend.indicators import atr
T('stop is never wider than 3 ATR of the trading chart (the brain would refuse it)', all(abs(s['sl'] - M[e - 1]['c']) <= 3.0 * atr(M[:e])[-1] + 1e-9 for e, s in F))
T('returns the standard signal dict', all(set(s) == {'side', 'sl', 'name'} and s['name'] == 'ma_cross' for _, s in F))
T('mirror (price flipped): same candles, opposite sides', [(e, s['side']) for e, s in fires(bars(flip(TREND)))] == [(e, 'sell' if s['side'] == 'buy' else 'buy') for e, s in F])
T('too little history -> nothing', ma_cross(M[:60], []) is None and ma_cross([], []) is None)

# rules have teeth: the same chart does not trade once a rule is tightened
T('ADX gate (trending only): same chart with ADX_MIN above its ADX -> no trade', with_(M, ADX_MIN=99.0) == [])
T('history needs enough past crosses (MIN_CROSSES)', with_(M, MIN_CROSSES=99) == [])
T('history must be followed (REACT_RATIO above 100%) -> no trade', with_(M, REACT_RATIO=1.01) == [])

# a market that does NOT follow its crossovers: 16-candle swings, so price reverses right after every cross, then one long clean trend
MN = bars(legs([(1, 16), (-1, 16)] * 7 + [(1, 90)])); crn = mc._crosses([x['c'] for x in MN]); lastx = crn[-1][0] + 1
T('a market that reverses after its crosses is NOT traded, even when a clean trend finally starts (history rule)', not any(e == lastx for e, _ in fires(MN)))
T('...and that one rule is what stops it: only REACT_RATIO=0 is relaxed, and now the same cross trades', any(e == lastx for e, _ in with_(MN, REACT_RATIO=0.0)))

# choppy market: many crosses, no follow-through -> no trades; relax every rule and it trades (so those rules are what stop it)
CH = bars(legs([(1.5, 12), (-1.5, 12)] * 12))
T('choppy market -> no trades', fires(CH) == [])
T('...and it only trades once the trending, history and ADX rules are all relaxed', len(with_(CH, REACT_RATIO=0.0, ADX_MIN=0.0, MIN_CROSSES=0)) > 0)

# 15-minute chart + 1-hour candles: one trade, on the 15-minute candle that closes together with the hour that made the cross, never early
def m15_from_hourly(prices, seed=2):
    r = random.Random(seed); out = []
    for i in range(1, len(prices)):
        a, b = prices[i - 1], prices[i]
        for k in range(4):
            o = a + (b - a) * k / 4; c = a + (b - a) * (k + 1) / 4
            out.append({'t': 1700000000 + (i - 1) * 3600 + k * 900 - 3600, 'o': o, 'h': max(o, c) + 0.1 * r.random(), 'l': min(o, c) - 0.1 * r.random(), 'c': c, 'v': 1})
    return out
HP = TREND; H = bars(HP); M15 = m15_from_hourly(HP)
for x in M15: x['t'] += 3600                               # hourly candle i spans t0+i*3600 ... +3600, its 4 quarters follow in order
M15 = [dict(x, t=1700000000 + (i // 4) * 3600 + (i % 4) * 900 + 3600) for i, x in enumerate(M15)]
hf = lambda e: [x for x in H if x['t'] <= M15[e - 1]['t']]      # like the backtest: includes the hour that is STILL FORMING
F15 = fires(M15, hf, 300)
cross_hours = [i for i, _ in mc._crosses([x['c'] for x in H])]
T('15m chart + 1h candles: one trade per cross, on the 15m candle that closes with that hour', len(F15) > 0 and all((M15[e - 1]['t'] + 900) == H[cross_hours[[k for k in range(len(cross_hours)) if H[cross_hours[k]]['t'] + 3600 == M15[e - 1]['t'] + 900][0]]]['t'] + 3600 for e, _ in F15))
T('...and never twice in the same hour', len(set(e // 4 for e, _ in F15)) == len(F15))
T('no 1h candles -> a 15m chart does not trade the crossover (video: lower time frames are mostly range)', fires(M15, lambda e: [], 300) == [])
def with_forming(e):                               # the feed already contains the NEXT hour, just opened, with a wild price
    done = [x for x in H if x['t'] + 3600 <= M15[e - 1]['t'] + 900]
    return done + [{'t': M15[e - 1]['t'] + 900, 'o': done[-1]['c'], 'h': 999.0, 'l': 1.0, 'c': 1.0, 'v': 1}]
T('an hour that has just opened (still forming) in the feed is ignored: the trade still comes on the right candle', [e for e, _ in F15] == [e for e, _ in fires(M15, with_forming, 300)])
T('hour still forming is not used: same trades whether or not it is included', [e for e, _ in F15] == [e for e, _ in fires(M15, lambda e: [x for x in H if x['t'] + 3600 <= M15[e - 1]['t'] + 900], 300)])

random.seed(3); p = 2300.0; rnd = []
for i in range(3000):
    o = p; p += random.gauss(0, 1.4); rnd.append({'t': 1700000000 + i * 3600, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
n = 0
for e in range(100, 3000, 3):
    x = ma_cross(rnd[:e], [])
    if x: n += 1; assert x['side'] in ('buy', 'sell') and x['sl'] > 0
T('never crashes on random data (%d signals)' % n, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
