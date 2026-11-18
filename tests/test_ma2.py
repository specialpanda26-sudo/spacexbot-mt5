"""Tests for backend/stoch.py and backend/ma_bounce.py (video 3, section 3B). Run: python tests/test_ma2.py"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.ma_bounce as mb
from backend.ma_bounce import ma_bounce
from backend.stoch import stoch
from backend.indicators import ema

def bars(prices, noise=0.3, seed=1):
    r = random.Random(seed); out = []
    for i, p in enumerate(prices):
        o = prices[i - 1] if i else p
        out.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + noise * r.random(), 'l': min(o, p) - noise * r.random(), 'c': p, 'v': 1})
    return out
def bar(i, o, c, h, l): return {'t': 1700000000 + i * 900, 'o': o, 'h': h, 'l': l, 'c': c, 'v': 1}
def legs(spec, start=100.0):
    p = [start]
    for d, n in spec:
        for _ in range(n): p.append(p[-1] + d)
    return p
def flip(m): return [{'t': x['t'], 'o': 400 - x['o'], 'h': 400 - x['l'], 'l': 400 - x['h'], 'c': 400 - x['c'], 'v': 1} for x in m]
def ma_now(m): return ema([x['c'] for x in m], mb.MA_LEN)[-1]
def cand(m, o=None, c=None, h=None, l=None, up=2.5, lo=-0.2):
    """next candle, placed relative to the MA: by default opens at the last close, dips to just under the MA and closes `up` higher (a rejection)"""
    y = ma_now(m); o = m[-1]['c'] if o is None else o; c = m[-1]['c'] + up if c is None else c
    return m + [bar(len(m), o, c, max(o, c) + 0.3 if h is None else h, min(m[-1]['c'] - 0.2, y + lo) if l is None else l)]
def fires(m, start=110): return [(e, ma_bounce(m[:e], [])) for e in range(start, len(m) + 1) if ma_bounce(m[:e], [])]
def with_(m, **kw):
    old = {k: getattr(mb, k) for k in kw}
    for k, v in kw.items(): setattr(mb, k, v)
    try: return fires(m)
    finally:
        for k, v in old.items(): setattr(mb, k, v)
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)

# ---- stochastic helper
up = bars(legs([(1, 40)])); dn = bars(legs([(-1, 40)]))
K, D = stoch(up); T('stochastic: a steadily rising market sits near 100, a falling one near 0', K[-1] > 90 and stoch(dn)[0][-1] < 10)
T('stochastic: always between 0 and 100, %D is the 3-candle average of %K', all(0 <= k <= 100 for k in K) and abs(D[-1] - sum(K[-3:]) / 3) < 1e-9)
T('stochastic: a flat market gives 50 (no divide by zero)', stoch([{'t': i, 'o': 5, 'h': 5, 'l': 5, 'c': 5, 'v': 1} for i in range(30)])[0][-1] == 50.0)

# ---- uptrend, 17-candle pullbacks that reach the 50 MA and bounce, final pullback ends at the MA with a bullish rejection
HIST = legs([(1, 60)] + [(-1, 17), (1, 40)] * 3 + [(-1, 13)])
B = cand(bars(HIST)); F = fires(B)
T('MA has bounced price before, stochastic oversold, bullish rejection at the MA -> exactly one buy, on that candle', len(F) == 1 and F[0][0] == len(B) and F[0][1]['side'] == 'buy')
T('stop is below the MA / the wick', F[0][1]['sl'] < B[-1]['l'] and F[0][1]['name'] == 'ma_bounce')
S = fires(flip(B))
T('mirror (falling MA = resistance, stochastic overbought) -> exactly one sell, and no buy', len(S) == 1 and S[0][1]['side'] == 'sell' and S[0][1]['sl'] > flip(B)[-1]['h'])
T('nothing happens before the candle reaches the MA', fires(bars(HIST)) == [])

# ---- every rule has teeth
T('stochastic gate: the same chart with OS below its %K -> no trade', with_(B, OS=-1.0) == [])
T('needs earlier bounces: the same chart demanding more bounces than it has -> no trade', with_(B, MIN_BOUNCES=99) == [])
SH = cand(bars(legs([(1, 60)] + [(-1, 6), (1, 40)] * 3 + [(-1, 14)])))
T('an MA that price has never bounced off is not trusted (MIN_BOUNCES): no trade, but it trades once that rule is relaxed', fires(SH) == [] and len(with_(SH, MIN_BOUNCES=0)) == 1)
T('MA must be rising (support): the same chart demanding a steeper slope than it has -> no trade', with_(B, MIN_SLOPE=99.0) == [])
T('the bounce must be real, not a wiggle (BOUNCE_ATR): demanding more than the earlier bounces gave -> no trade', with_(B, BOUNCE_ATR=99.0) == [])
T('touches in the same pullback count as ONE bounce (SEP): merge all touches into one (SEP=200) -> no trade', with_(B, SEP=200) == [])
ONE_B = cand(bars(legs([(1, 60), (-1, 17), (1, 40), (-1, 13)])))
T('only one earlier pullback = one bounce, not several (touch dedupe): no trade, but it trades if every touch candle counted (SEP=1)', fires(ONE_B) == [] and len(with_(ONE_B, SEP=1)) == 1)
T('too far from the MA (REACH) -> no trade', fires(cand(bars(HIST), l=ma_now(bars(HIST)) + 3.0)) == [])
T('wick pokes far through the MA (PIERCE) -> no trade', fires(cand(bars(HIST), l=ma_now(bars(HIST)) - 3.0)) == [])
yy = ma_now(bars(HIST))
T('closes below the MA (support broken), even as a bullish candle -> no trade', fires(cand(bars(HIST), o=yy - 0.6, c=yy - 0.3, h=yy, l=yy - 0.6)) == [])
T('bearish candle at the MA -> no trade', fires(cand(bars(HIST), c=bars(HIST)[-1]['c'] - 0.3, h=bars(HIST)[-1]['c'] + 0.1)) == [])
T('second candle in a row at the MA -> only the first one buys', len([1 for _, s in fires(cand(B, o=B[-1]['c'], c=B[-1]['c'] + 0.5, h=B[-1]['c'] + 0.8, l=ma_now(B) - 0.1)) if s['side'] == 'buy']) == 1)
DOWN = cand(bars(legs([(-1, 60)] + [(1, 17), (-1, 40)] * 3 + [(1, 13)])))
T('falling MA with price above it (not support): never a buy', not any(s['side'] == 'buy' for _, s in fires(DOWN)))
T('too little history -> nothing', ma_bounce(B[:60], []) is None and ma_bounce([], []) is None)

random.seed(4); p = 2300.0; rnd = []
for i in range(3000):
    o = p; p += random.gauss(0.02, 1.4); rnd.append({'t': 1700000000 + i * 900, 'o': o, 'h': max(o, p) + .5, 'l': min(o, p) - .5, 'c': p, 'v': 1})
n = 0
for e in range(100, 3000, 3):
    x = ma_bounce(rnd[:e], [])
    if x: n += 1; assert x['side'] in ('buy', 'sell') and x['sl'] > 0
T('never crashes on random data (%d signals)' % n, True)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
