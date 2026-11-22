"""Tests for backend/btc_range.py (BTC Section 6A: range + discount/premium entry). Run: python tests/test_btc6a.py
The chart below is built from 15-minute steps of 50 dollars (ATR about 100): a swing high H0 (61020), a swing low L (60180), a break of H0, a top T (61420),
a fall back inside the old range and a green reaction candle in the discount zone (below 60490). 1-hour candles are grouped from it."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.btc_range as br
from backend.btc_range import btc_range, setup
from backend.indicators import atr

R = []
def T(name, ok): R.append((name, bool(ok)))
T0, STEP = (1700000000 // 28800) * 28800, 900

def build(spec, start=60600.0, wick=20.0):
    p = [start]
    for d, n in spec:
        for _ in range(n): p.append(p[-1] + d)
    return [{'t': T0 + i * STEP, 'o': p[i - 1] if i else x, 'h': max(p[i - 1] if i else x, x) + wick, 'l': min(p[i - 1] if i else x, x) - wick, 'c': x, 'v': 1} for i, x in enumerate(p)]
def nxt(m, o, h, l, c): return m + [{'t': m[-1]['t'] + STEP, 'o': o, 'h': h, 'l': l, 'c': c, 'v': 1}]
def agg(m, step):
    g = {}
    for x in m: g.setdefault(x['t'] - x['t'] % step, []).append(x)
    return [{'t': t, 'o': s[0]['o'], 'h': max(x['h'] for x in s), 'l': min(x['l'] for x in s), 'c': s[-1]['c'], 'v': 1} for t, s in sorted(g.items())]
def flip(m, k=121000.0): return [{'t': x['t'], 'o': k - x['o'], 'h': k - x['l'], 'l': k - x['h'], 'c': k - x['c'], 'v': 1} for x in m]
def go(m, **kw):
    old = {k: getattr(br, k) for k in kw}
    for k, v in kw.items(): setattr(br, k, v)
    try: return btc_range(m, agg(m, 3600))
    finally:
        for k, v in old.items(): setattr(br, k, v)
def full(m, **kw):
    old = {k: getattr(br, k) for k in kw}
    for k, v in kw.items(): setattr(br, k, v)
    try: return setup(m, agg(m, 3600))
    finally:
        for k, v in old.items(): setattr(br, k, v)

SPEC = [(50, 8), (-50, 16), (50, 24), (-50, 19)]      # up to H0, down to L, up through H0 to the top, down into the discount zone
BASE = build(SPEC)                                      # last close 60450
M = nxt(BASE, 60440, 60510, 60400, 60490)               # green reaction candle: low in the discount zone, body 50
L, TOP, H0 = 60180.0, 61420.0, 61020.0
A = atr(M)[-1]

# ---- the basic trade
r = go(M); f = full(M)
T('range broken, back inside, green candle in the discount zone: a BUY', r and r['side'] == 'buy' and r['name'] == 'btc_range')
T('signal is {side, sl, tp, name}; no solo unless SOLO is on', r and set(r) == {'side', 'sl', 'tp', 'name'})
T('SOLO = True adds the solo flag (off by default)', (go(M, SOLO=True) or {}).get('solo') is True)
T('stop is just beyond the bottom swing (BUF x ATR below 60180)', r and abs(r['sl'] - (L - br.BUF * A)) < 1e-6 and r['sl'] < L)
T('target TP1 is the top of the range', r and abs(r['tp'] - TOP) < 1e-6 and r['sl'] < M[-1]['c'] < r['tp'])
T('setup() gives TP2 above the top, the range, rr and the frame (1h here: 8h and 4h have too few candles)', f and f['tp2'] > f['tp'] and f['range'] == (L, TOP) and f['tf'] == 3600 and f['rr'] >= br.RR_MIN)
T('a reaction below the 0.25 level is not a half trade', f and f['half'] is False)

# ---- only in the discount zone
T('price in the middle of the range: nothing', go(nxt(BASE, 60700, 61000, 60650, 60900)) is None)
T('reaction just above the discount zone (low 60500 > 60490): nothing', go(nxt(BASE, 60520, 60620, 60500, 60600)) is None)
T('zone edge: low 60490 (= 0.25 level) trades, low 60500 does not (stop rule widened so only the zone decides)', go(nxt(BASE, 60495, 60620, 60490, 60600), SL_MAX=9.0) is not None and go(nxt(BASE, 60495, 60620, 60500, 60600), SL_MAX=9.0) is None)
# ---- react, never anticipate
T('a RED candle in the zone is no reaction: nothing', go(nxt(BASE, 60490, 60500, 60400, 60440)) is None)
T('a tiny-body candle (consolidating) is no reaction: nothing', go(nxt(BASE, 60460, 60500, 60400, 60470)) is None)
T('...with BODY_MIN = 0 the same tiny candle is accepted (the rule is what blocks it)', go(nxt(BASE, 60460, 60500, 60400, 60470), BODY_MIN=0.0) is not None)
T('the candle BEFORE the reaction (still falling) gives nothing', go(BASE) is None)
# ---- first reaction of the visit only
SECOND = nxt(M, 60490, 60540, 60480, 60535)
T('a second green candle that also touches the zone gives nothing (stop rule widened so only the first-reaction rule decides)', go(SECOND, SL_MAX=9.0) is None and go(M, SL_MAX=9.0) is not None)
T('...but a green candle after a RED one in the zone is the first reaction', go(nxt(nxt(BASE, 60450, 60460, 60380, 60400), 60400, 60520, 60390, 60470), SL_MAX=9.0) is not None)
# ---- the range must be valid
T('a close below the bottom swing breaks the range: nothing', go(nxt(M[:-1], 60450, 60460, 60100, 60120)) is None)
C1 = agg(M, 3600)[:-1]
rg = br._bull_range(C1, [])
T('_bull_range finds bottom 60180, top 61420 and the broken swing high 61020', rg and (rg['lo'], rg['hi'], rg['brk']) == (L, TOP, H0))
T('no valid range until a close is back below the broken swing high (hour 13 closes 61050, hour 14 closes 60850)', br._bull_range(C1[:14], []) is None and br._bull_range(C1[:15], []) is not None)
T('...and a close back inside the still-forming candle counts (tail)', br._bull_range(C1[:14], [60900.0]) is not None)
T('...and none before the break at all', br._bull_range(C1[:9], []) is None)
def rng(C, tail=(), **kw):
    old = {k: getattr(br, k) for k in kw}
    for k, v in kw.items(): setattr(br, k, v)
    try: return br._bull_range(list(C), list(tail))
    finally:
        for k, v in old.items(): setattr(br, k, v)
T('too few candles on the frame: no range (MIN_BARS); the same 17 candles with a lower MIN_BARS have one', rng(C1, MIN_BARS=18) is None and rng(C1) is not None)
C15 = C1[:15]
T('a frame close below the bottom swing after the break kills the range', br._bull_range(C15, []) is not None and br._bull_range(C15 + [dict(C15[-1], t=C15[-1]['t'] + 3600, o=60400.0, h=60410.0, l=60090.0, c=60100.0)], []) is None)
T('...and so does a close below it inside the still-forming candle (tail)', br._bull_range(C15, [60100.0]) is None and br._bull_range(C15, [60400.0]) is not None)
# ---- stop and size rules (skipped, never reshaped)
T('range smaller than RANGE_MIN_ATR x ATR: skipped; trades when the rule is relaxed', go(M, RANGE_MIN_ATR=20.0) is None and go(M) is not None)
T('stop wider than the brain accepts (SL_MAX): skipped', go(M, SL_MAX=2.0) is None)
T('stop tighter than the brain accepts (SL_MIN): skipped', go(M, SL_MIN=5.0) is None)
T('RR to TP1 under RR_MIN: skipped', go(M, RR_MIN=99.0) is None)
SW = nxt(BASE, 60420, 60510, 60100, 60490)             # the reaction candle wicks under the bottom swing but closes back inside the range
fs = full(SW, SL_MAX=9.0)
T('wick below the bottom swing: the stop goes under that wick (beyond the swing AND the candle)', fs and fs['sl'] < 60100 and abs(fs['sl'] - (60100 - br.BUF * atr(SW)[-1])) < 1e-6)
# ---- the 50% trade is a flag, off by default
M5 = nxt(build([(50, 8), (-50, 16), (50, 24), (-50, 14)]), 60640, 60800, 60620, 60760)   # reaction only at about the 0.5 level (60800)
T('a reaction that only reaches the 0.5 level: nothing by default (stop rule widened so only the zone decides)', go(M5, SL_MAX=9.0, RR_MIN=1.0) is None)
f5 = full(M5, HALF_OK=True, SL_MAX=9.0, RR_MIN=1.0)   # at the 0.5 level with the stop under the bottom the reward is only about 1R, so RR_MIN must be lowered too
T('HALF_OK = True accepts it and marks half=True', f5 and f5['half'] is True and f5['side'] == 'buy')
T('HALF_OK = True still marks a deep reaction half=False', (full(M, HALF_OK=True, SL_MAX=9.0, RR_MIN=1.0) or {}).get('half') is False)
# ---- bearish mirror
MB = flip(M); rb = go(MB); fb = full(MB)
T('mirror chart (premium zone, range broken downwards): a SELL', rb and rb['side'] == 'sell')
T('mirror: stop above the top swing, target below, levels mirror exactly', rb and abs(rb['sl'] - (121000 - r['sl'])) < 1e-6 and abs(rb['tp'] - (121000 - r['tp'])) < 1e-6 and rb['tp'] < MB[-1]['c'] < rb['sl'])
T('mirror: range reported as (bottom, top) in real prices', fb and fb['range'] == (121000 - TOP, 121000 - L))
# ---- frames: 8h, 4h, 1h, 30m, with the step down only when no structure shows
HRS = agg(M, 3600)
T('1h candles are used closed only: a forming-hour candle with a crash in it is ignored', btc_range(M, HRS[:-1] + [dict(HRS[-1], l=1.0, c=1.0)]) is not None)
T('no 1h history: 8h, 4h, 1h have no candles, so it steps down to the 30m frame (built from the 15m candles) and trades', (btc_range(M, []) or {}).get('side') == 'buy' and setup(M, [])['tf'] == 1800)
T('frames limited to 8h and 4h (too few candles there): nothing', go(M, TFS=(28800, 14400)) is None)
T('frame 1h alone: trades', go(M, TFS=(3600,)) is not None)
T('frame 30m alone finds the same range', (full(M, TFS=(1800,)) or {}).get('range') == (L, TOP))
real = br._bull_range
def fake(C, tail):                                   # a valid range on the 4h frame that price is nowhere near
    return {'lo': 1.0, 'hi': 2.0, 'brk': 1.5} if len(C) > 1 and C[1]['t'] - C[0]['t'] == 14400 else real(C, tail)
br._bull_range = fake
try:
    T('a range on a higher frame that gives no entry stops the search: it does NOT drop to 1h to find another trade', go(M, TFS=(14400, 3600), MIN_BARS=3) is None)
finally:
    br._bull_range = real
T('control: the same call without the fake range trades on 1h', go(M, TFS=(14400, 3600), MIN_BARS=3) is not None)
# ---- grouping
sub = build([(10, 40)], start=100.0)
T('grouping: 30 candles of 15m make no 8h candle (32 are needed)', br._group(sub[:30], 900, 28800, T0 + 99999) == [] and len(br._group(sub, 900, 28800, T0 + 99999)) == 1)
g1 = br._group(sub, 900, 3600, T0 + 40 * 900)
T('grouping 15m to 1h: OHLC of the four candles', len(g1) == 10 and g1[0]['o'] == sub[0]['o'] and g1[0]['c'] == sub[3]['c'] and g1[0]['h'] == max(x['h'] for x in sub[:4]) and g1[0]['l'] == min(x['l'] for x in sub[:4]))
T('grouping: the hour still forming is left out', len(br._group(sub, 900, 3600, T0 + 39 * 900)) == 9)
ts = [g['t'] for g in br._group(sub[:5] + sub[6:12], 900, 3600, T0 + 99999)]
T('grouping: a missing small candle drops its hour (hour 1 lost its 2nd candle), the complete hours stay', ts == [T0, T0 + 7200])
# ---- guards
T('short chart: nothing', go(M[:30]) is None)
M30 = [dict(x, t=T0 + i * 1800) for i, x in enumerate(M)]; M10 = [dict(x, t=T0 + i * 600) for i, x in enumerate(M)]
T('not a 15-minute chart (30-minute and 10-minute candles, same shapes): nothing', btc_range(M30, agg(M30, 3600)) is None and btc_range(M10, agg(M10, 3600)) is None)
T('flat chart: nothing', go(build([(0, 80)])) is None)
# ---- registered
from backend import strategies as S, strategy_info as SI
T('registered in ALL and TREND, not REVERSION', btc_range in S.ALL and 'btc_range' in S.TREND and 'btc_range' not in S.REVERSION)
T('has a readable name and description', SI.name('btc_range') != 'Btc Range' and len(SI.desc('btc_range')) > 20)

bad = [n for n, ok in R if not ok]
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
print('%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
