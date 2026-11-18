"""Tests for backend/gold_scalp.py (video 5, section 5B). Run: python tests/test_gs2.py
The 5A scan (trend agreement + zones) is replaced by a fixed answer here, so these tests check ONLY the 5B rules: zone visit, liquidity sweep, stop, target."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.gold_scalp as gsx
from backend.gold_scalp import gold_scalp
from backend.indicators import atr

R = []
def T(name, ok): R.append((name, bool(ok)))
T0, STEP = 1700000000, 900
def legs(spec, start=40.0):
    p = [start]
    for d, n in spec:
        for _ in range(n): p.append(p[-1] + d)
    return p
def line(prices, wick=0.3):
    return [{'t': T0 + i * STEP, 'o': prices[i - 1] if i else p, 'h': max(prices[i - 1] if i else p, p) + wick, 'l': min(prices[i - 1] if i else p, p) - wick, 'c': p, 'v': 1} for i, p in enumerate(prices)]
def nxt(m, o, h, l, c): return m + [{'t': m[-1]['t'] + STEP, 'o': o, 'h': h, 'l': l, 'c': c, 'v': 1}]
def flip(m): return [{'t': x['t'], 'o': 400 - x['o'], 'h': 400 - x['l'], 'l': 400 - x['h'], 'c': 400 - x['c'], 'v': 1} for x in m]
def zone(lo, hi, side='buy', tf='m15', t=T0 + 5 * STEP): return {'side': side, 'kind': 'ob', 'tf': tf, 'lo': lo, 'hi': hi, 't': t, 'touched': True}
def setscan(bias, zones): gsx.scan = lambda m, h: {'bias': bias, 'zones': zones}
ORIG_SCAN = gsx.scan

# base chart: strong rise to 130, pullback to 122 (swing low, candle low 121.7), rise to 134 (swing high, 134.3), pullback down to 123
BASE = line(legs([(1, 90), (-1, 8), (1, 12), (-1, 11)]))
LVL, TOP = 121.7, 134.3
ZN = zone(LVL - 1.0, LVL + 1.0)                                    # 120.7 - 122.7, around the swing low
def sweep(m=None, o=None, h=123.3, l=121.0, c=122.4):             # the sweep candle: wick through 121.7, closes back above it
    m = BASE if m is None else m
    return nxt(m, m[-1]['c'] if o is None else o, h, l, c)
M = sweep()
def go(m=M, zones=None, bias='up'):
    setscan(bias, [ZN] if zones is None else zones); return gold_scalp(m, [])
def with_(m=M, zones=None, bias='up', **kw):
    old = {k: getattr(gsx, k) for k in kw}
    for k, v in kw.items(): setattr(gsx, k, v)
    try: return go(m, zones, bias)
    finally:
        for k, v in old.items(): setattr(gsx, k, v)

# ---- the basic trade
r = go()
T('uptrend, price in a demand zone, swing low swept (wick through, close back above): a BUY on that very candle', r and r['side'] == 'buy' and r['name'] == 'gold_scalp')
a = atr(M)[-1]
T('stop sits just beyond the sweep candle low (the protected low)', r and abs(r['sl'] - (121.0 - gsx.BUF * a)) < 1e-9 and r['sl'] < 121.0)
T('target is the swing high (nearest unbroken one above)', r and abs(r['tp'] - TOP) < 1e-9)
T('signal is {side, sl, tp, name}; stop < entry < target; no "solo" unless SOLO is on', r and set(r) == {'side', 'sl', 'tp', 'name'} and r['sl'] < M[-1]['c'] < r['tp'])
T('SOLO = True adds the solo flag (still off by default)', (with_(SOLO=True) or {}).get('solo') is True)
T('aggressive entry: the candle BEFORE the sweep gives nothing', go(BASE) is None)
T('one trade per sweep: the next candle (price recovering) gives nothing', go(nxt(M, 122.4, 124.0, 122.2, 123.8)) is None)

# ---- step 4: it must be a SWEEP
T('no sweep: the wick stops above the swing low -> no trade', go(sweep(l=121.9)) is None)
T('a close BEYOND the level is a break, not a sweep -> no trade (same wick, closing back above it trades)', go(sweep(l=120.0, c=121.5)) is None and go(sweep(l=120.0, c=122.4)) is not None)
T('a one-tick poke through the level is not a sweep (SWEEP_MIN): no trade, but trades once that rule is relaxed', go(sweep(l=121.68)) is None and with_(sweep(l=121.68), SWEEP_MIN=0.0) is not None)
T('a swing low that is too old is not used (SWEEP_LOOK) -> no trade', with_(SWEEP_LOOK=3) is None)
# the same level swept a SECOND time: the first sweep already took that liquidity
S1 = M + line([123.4, 124.4, 125.4, 126.4, 125.4, 124.4, 123.4], 0.3)
for i, x in enumerate(S1[len(M):]): x['t'] = M[-1]['t'] + STEP * (i + 1)
S1[len(M)]['o'] = M[-1]['c']
S2 = nxt(S1, 123.2, 123.5, 121.3, 122.6)                             # dips below 121.7 again (but not below 121.0), closes back above
T('a level that was already swept earlier is not liquidity any more: second dip through it -> no trade', go(S2) is None)

# ---- step 3: price must be back at a 15-minute zone
T('no zone -> no trade', go(zones=[]) is None)
T('zone far from price -> no trade', go(zones=[zone(110, 112)]) is None)
T('a zone touched a few candles ago still counts (price was there within ZONE_BARS)', go(zones=[zone(124.2, 125.0)]) is not None)
T('...but only within ZONE_BARS candles: same zone with ZONE_BARS=1 -> no trade', with_(zones=[zone(124.2, 125.0)], ZONE_BARS=1) is None)
T('a 1-hour zone is not used (15-minute points of interest only)', go(zones=[zone(LVL - 1, LVL + 1, tf='h1')]) is None)
T('a supply zone is not used for a buy', go(zones=[zone(LVL - 1, LVL + 1, side='sell')]) is None)
T('the zone must not be a brand-new one that price has not come back to (MIT_GAP): no trade, but trades once that rule is relaxed',
  go(zones=[zone(LVL - 1, LVL + 1, t=M[-1]['t'] - 2 * STEP)]) is None and with_(zones=[zone(LVL - 1, LVL + 1, t=M[-1]['t'] - 2 * STEP)], MIT_GAP=0) is not None)

# ---- step 1: trends must agree (5A), the real scan
gsx.scan = ORIG_SCAN
T('1h and 15m do not agree / no 1h data (the real 5A scan) -> no trade', gold_scalp(M, []) is None)
setscan(None, [])
T('scan says stay out -> no trade', gold_scalp(M, []) is None)
T('too little data -> no trade', go(M[:50]) is None and go([]) is None)

# ---- step 5: stop and target
T('a sweep candle with a huge wick (stop wider than 3.5 ATR) is skipped, not reshaped', go(sweep(l=110.0)) is None)
T('...that is the SL_MAX rule: relax it (and MIN_RR, a 12-point stop cannot reach 1R here) and the same candle trades', with_(sweep(l=110.0), SL_MAX=50.0) is None and with_(sweep(l=110.0), SL_MAX=50.0, MIN_RR=0.0) is not None)
T('a stop tighter than SL_MIN ATR is skipped', with_(SL_MIN=99.0) is None)
T('target closer than MIN_RR x the stop distance is skipped', with_(MIN_RR=99.0) is None)
# a lower swing high (unbroken) between the entry and the 134.3 high: the nearest one is the target
NR = line(legs([(1, 90), (-1, 8), (1, 12), (-1, 4), (1, 3), (-1, 4)]))     # bounce high 133.3 is below 134.3, both unbroken
r2 = go(sweep(NR))
T('NEAREST swing high is the target, not the highest', r2 and abs(r2['tp'] - 133.3) < 1e-9)
# a swing high that price already traded through is not a target any more
BR = line(legs([(1, 90), (-1, 8), (1, 12), (-1, 4), (1, 6), (-1, 7)]))     # bounce goes to 136, past the old 134 high: 134.3 is broken, 136.3 is the target
r3 = go(sweep(BR))
T('a swing high that was already broken is not a target (136.3 is)', r3 and abs(r3['tp'] - 136.3) < 1e-9)
T('no swing high above the entry at all -> no trade', go(sweep(line(legs([(1, 90), (-1, 8), (1, 2), (-1, 3)])))) is None)

# a swing high BELOW the entry is no target: the first swing high ABOVE the entry is (here 130.3, with a small unbroken high at 125.3 under the entry)
LO = line(legs([(1, 90), (-1, 8), (1, 3), (-1, 3)]))
r4 = (lambda: (setscan('up', [ZN]), setattr(gsx, 'MIN_RR', 0.5), gold_scalp(sweep(LO, h=126.3, c=126.0), []))[2])(); gsx.MIN_RR = 1.0
T('a swing high below the entry is not a target: the nearest one ABOVE the entry is', r4 and abs(r4['tp'] - 130.3) < 1e-9 and r4['tp'] > 126.0)

# ---- the sell side is the exact mirror
F = flip(M); fz = zone(400 - (LVL + 1.0), 400 - (LVL - 1.0), side='sell')
setscan('down', [fz]); s = gold_scalp(F, [])
T('downtrend, supply zone, swing HIGH swept (wick above, close back below): a SELL', s and s['side'] == 'sell' and s['name'] == 'gold_scalp')
T('sell stop is above the sweep candle high, target is the nearest swing low below', s and s['sl'] > F[-1]['h'] and abs(s['tp'] - (400 - TOP)) < 1e-9 and s['tp'] < F[-1]['c'] < s['sl'])
T('mirror numbers match the buy exactly', s and r and abs(s['sl'] - (400 - r['sl'])) < 1e-9 and abs(s['tp'] - (400 - r['tp'])) < 1e-9)
T('bias down never gives a buy, bias up never gives a sell', s['side'] == 'sell' and r['side'] == 'buy')
setscan('down', [zone(LVL - 1, LVL + 1, side='buy')])
T('a demand zone is not used for a sell', gold_scalp(F, []) is None)

# ---- registered in the bot
from backend import strategies as S, brain
T('registered in strategies.ALL and in the TREND group', any(f.__name__ == 'gold_scalp' for f in S.ALL) and 'gold_scalp' in S.TREND)
T('the brain accepts it alone when SOLO is on (stop inside 0.5-3.5 ATR, its own target is kept)',
  (lambda: (setattr(gsx, 'SOLO', True), setscan('up', [ZN]), brain.evaluate(M, [], off=tuple(f.__name__ for f in S.ALL if f.__name__ != 'gold_scalp')))[2])() is not None)
gsx.SOLO = False
b = brain.evaluate(M, [], off=tuple(f.__name__ for f in S.ALL if f.__name__ != 'gold_scalp'))
T('with SOLO off the brain wants a second strategy to agree', b is None)
gsx.SOLO = True; setscan('up', [ZN]); b = brain.evaluate(M, [], off=tuple(f.__name__ for f in S.ALL if f.__name__ != 'gold_scalp')); gsx.SOLO = False
T('brain trade keeps the strategy name and the video target', b and b['strategy'] == 'gold_scalp' and b['side'] == 'buy' and abs(b['tp'] - TOP) < 1e-4)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
