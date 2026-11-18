"""Tests for backend/gold_scalp_c.py (video 5, section 5C: conservative entry). Run: python tests/test_gs3.py
The 5A scan (trend agreement + zones) is replaced by a fixed answer, so these tests check ONLY the 5C rules: sweep, market shift, first pullback into the shift zone, stop, target."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.gold_scalp_c as gsc
from backend.gold_scalp_c import gold_scalp_c
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
def add(m, *cs):
    for o, h, l, c in cs: m = m + [{'t': m[-1]['t'] + STEP, 'o': o, 'h': h, 'l': l, 'c': c, 'v': 1}]
    return m
def flip(m): return [{'t': x['t'], 'o': 400 - x['o'], 'h': 400 - x['l'], 'l': 400 - x['h'], 'c': 400 - x['c'], 'v': 1} for x in m]
def zone(lo, hi, side='buy', tf='m15', t=T0 + 5 * STEP): return {'side': side, 'kind': 'ob', 'tf': tf, 'lo': lo, 'hi': hi, 't': t, 'touched': True}
def setscan(bias, zones): gsc.scan = lambda m, h: {'bias': bias, 'zones': zones}
ORIG_SCAN = gsc.scan

# base chart: up to 150 (swing high 150.3 = the target), pullback 140, bounce 144 (144.3), down 132 (swing low 131.7), bounce 135 (135.3 = the last internal high), down to 133
BASE = line(legs([(1, 110), (-1, 10), (1, 4), (-1, 12), (1, 3), (-0.5, 4)]))
LOW, HIGH, TOP = 131.7, 135.3, 144.3
ZN = zone(130.0, 134.0)                                           # demand zone around the swing low
SWEEP = (133.0, 133.6, 131.0, 132.4)                              # wick through 131.7, closes back above it (a down candle)
BOUNCE = (132.4, 133.5, 132.3, 133.4)                             # up candle
ZC = (133.4, 133.7, 132.7, 133.0)                                 # the LAST down candle before the shift = the zone that caused it: 132.7 - 133.7
SHIFT = (133.0, 136.2, 132.9, 136.0)                              # closes above the last internal high 135.3 = market shift
AWAY = (136.0, 136.4, 135.2, 135.3)                               # pulls away from the zone (closes at, not above, 135.3)
PULL = (135.0, 135.1, 133.2, 133.9)                               # back into the zone, closes above its low = the entry
SETUP = add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, PULL)
def go(m=SETUP, zones=None, bias='up'):
    setscan(bias, [ZN] if zones is None else zones); return gold_scalp_c(m, [])
def with_(m=SETUP, zones=None, bias='up', **kw):
    old = {k: getattr(gsc, k) for k in kw}
    for k, v in kw.items(): setattr(gsc, k, v)
    try: return go(m, zones, bias)
    finally:
        for k, v in old.items(): setattr(gsc, k, v)

# ---- the basic trade
r = go(); a = atr(SETUP)[-1]
T('sweep, market shift, then the first pullback into the shift zone: a BUY on the pullback candle', r and r['side'] == 'buy' and r['name'] == 'gold_scalp_c')
T('stop sits just beyond the sweep candle low (the protected low)', r and abs(r['sl'] - (131.0 - gsc.BUF * a)) < 1e-9)
T('target is the NEAREST unbroken swing high (144.3), not the broken 135.3 and not the older 150.3', r and abs(r['tp'] - TOP) < 1e-9)
T('signal is {side, sl, tp, name}; stop < entry < target; no solo flag by default', r and set(r) == {'side', 'sl', 'tp', 'name'} and r['sl'] < SETUP[-1]['c'] < r['tp'])
T('SOLO = True adds the solo flag', (with_(SOLO=True) or {}).get('solo') is True)

# ---- conservative: never on the sweep candle, the shift candle, or before the pullback
T('the sweep candle alone gives nothing (that is the aggressive entry, 5B)', go(add(BASE, SWEEP)) is None)
T('after the sweep, before the shift: nothing', go(add(BASE, SWEEP, BOUNCE, ZC)) is None)
T('the shift candle itself gives nothing (wait for the pullback)', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT)) is None)
T('after the shift, price pulling away from the zone: nothing', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY)) is None)
T('one trade per setup: the candle after the entry gives nothing', go(add(SETUP, (133.9, 135.0, 133.8, 134.8))) is None)

# ---- market shift rules
T('no market shift (never closes above the last internal high 135.3): nothing', go(add(BASE, SWEEP, BOUNCE, ZC, (133.0, 135.6, 132.9, 135.2), AWAY, PULL)) is None)
T('a WICK above the last internal high is not a shift (needs a close): nothing; the same candle closing above trades', go(add(BASE, SWEEP, BOUNCE, ZC, (133.0, 136.2, 132.9, 135.2), AWAY, PULL)) is None and go() is not None)
T('shift too late (more than SHIFT_BARS after the sweep): nothing, but trades once relaxed', with_(SHIFT_BARS=2) is None and with_(SHIFT_BARS=12) is not None)
S2 = add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, (135.4, 135.6, 135.0, 135.2), (135.2, 135.5, 134.9, 135.1), (135.1, 135.4, 134.8, 135.0), PULL)
T('pullback too late (more than PULL_BARS after the shift): nothing, but trades once relaxed', with_(S2, PULL_BARS=3, MIN_RR=0.0) is None and with_(S2, PULL_BARS=24, MIN_RR=0.0) is not None)   # MIN_RR off: the AWAY high 136.4 is now the nearer target

# ---- the pullback rules
T('a pullback that does not reach the zone: nothing', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, (135.0, 135.1, 134.2, 134.5))) is None)
T('only the FIRST return counts: a second visit to the zone gives nothing', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, PULL, (133.9, 135.6, 133.8, 135.4), (135.4, 135.5, 133.5, 134.0))) is None)
T('a candle that CLOSES through the zone (below its low 132.7) is a failed zone: nothing', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, (135.0, 135.1, 132.0, 132.5))) is None)
T('protected low broken (a wick under the sweep low 131.0) kills the setup', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, (135.0, 135.1, 130.9, 133.9))) is None)

# ---- sweep rules (same as 5B)
NOSWEEP = (133.0, 133.6, 131.9, 132.4)                            # wick stops above 131.7
T('no sweep (the wick stays above the swing low): nothing', go(add(BASE, NOSWEEP, BOUNCE, ZC, SHIFT, AWAY, PULL)) is None)
BREAK = (133.0, 133.6, 131.0, 131.5)                              # a close BELOW the level is a break
T('a close beyond the level is a break, not a sweep: nothing', go(add(BASE, BREAK, BOUNCE, ZC, SHIFT, AWAY, PULL)) is None)
T('a swing low that is too old (SWEEP_LOOK) is not used', with_(SWEEP_LOOK=3) is None)

# ---- zone rules (step 3)
T('no zone -> nothing', go(zones=[]) is None)
T('zone far from the sweep -> nothing', go(zones=[zone(100, 102)]) is None)
T('a 1-hour zone is not used (15-minute zones only)', go(zones=[zone(130.0, 134.0, tf='h1')]) is None)
T('a supply zone is not used for a buy', go(zones=[zone(130.0, 134.0, side='sell')]) is None)
T('the sweep must have been at the zone (a zone only touched later does not count)', go(zones=[zone(135.8, 136.3)]) is None)

# ---- step 1: trends must agree (5A, the real scan)
gsc.scan = ORIG_SCAN
T('1h and 15m do not agree / no 1h data (the real 5A scan): nothing', gold_scalp_c(SETUP, []) is None)
setscan(None, [])
T('scan says stay out: nothing', gold_scalp_c(SETUP, []) is None)
T('too little data: nothing', go(SETUP[:50]) is None and go([]) is None)

# ---- stop and target
T('a stop wider than 3.5 ATR is skipped, not reshaped; relax SL_MAX and it trades', with_(SL_MAX=0.1) is None and with_(SL_MAX=3.5) is not None)
T('a stop tighter than SL_MIN ATR is skipped', with_(SL_MIN=99.0) is None)
T('target closer than MIN_RR x the stop distance is skipped', with_(MIN_RR=99.0) is None)
T('no unbroken swing high above the entry at all -> nothing', with_(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, PULL), MIN_RR=0.0) is not None and go(add(line(legs([(1, 110), (-1, 10), (1, 4), (-1, 12), (1, 3), (-0.5, 4)])), SWEEP, BOUNCE, ZC, (133.0, 151.0, 132.9, 150.8), (150.8, 151.0, 149.0, 149.5), (149.5, 149.6, 133.0, 133.9))) is None)

# ---- rules found missing by the mutation check
TAKE = (133.0, 133.2, 130.5, 131.5)                              # an EARLIER candle that took the 131.7 low out (closed below it)
REC = [(131.5, 132.0, 131.4, 131.9), (131.9, 132.4, 131.8, 132.3), (132.3, 132.8, 132.2, 132.7), (132.7, 133.0, 132.6, 133.0)]
OLD = add(BASE, TAKE, *REC, SWEEP, BOUNCE, ZC, SHIFT, AWAY, PULL)
T('a low that was already taken out earlier is not liquidity any more: sweeping it again gives nothing', with_(OLD, MIN_RR=0.0) is None)
SPIKE = (133.0, 136.2, 132.9, 135.8)                             # closed above 135.3 BEFORE the sweep: that shift is already used
EARLY = add(BASE, SPIKE, (135.8, 135.9, 133.5, 133.6), (133.6, 133.7, 132.9, 133.0), SWEEP, BOUNCE, ZC, SHIFT, AWAY, PULL)
T('a shift that happened before the sweep does not count as the shift after it', with_(EARLY, MIN_RR=0.0) is None)
GAP = (132.6, 132.65, 132.1, 132.2)                              # a candle closing under the zone (132.7) without touching it or the protected low
T('a close through the zone ends it: a later return to the zone gives nothing', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, GAP, PULL)) is None)
T('...and the zone-holds case: the entry candle itself closing under the zone gives nothing', go(add(BASE, SWEEP, BOUNCE, ZC, SHIFT, AWAY, (133.5, 133.6, 132.5, 132.6))) is None)
UP2 = (133.0, 133.9, 132.9, 133.8)                               # an UP candle right before the shift: the zone is the last DOWN candle (ZC 132.7-133.7), not this one
TOUCH2 = (135.0, 135.1, 133.8, 134.0)                            # touches UP2's range (132.9-133.9) but not ZC's (132.7-133.7)
T('the zone is the last DOWN candle before the shift, not just the last candle', go(add(BASE, SWEEP, BOUNCE, ZC, UP2, (133.8, 136.2, 133.7, 136.0), AWAY, TOUCH2)) is None and go(add(BASE, SWEEP, BOUNCE, ZC, UP2, (133.8, 136.2, 133.7, 136.0), AWAY, PULL)) is not None)

# ---- the sell side is the exact mirror
F = flip(SETUP); fz = zone(400 - 134.0, 400 - 130.0, side='sell')
setscan('down', [fz]); s = gold_scalp_c(F, [])
T('downtrend, supply zone, swing HIGH swept, market shift DOWN, pullback into the zone: a SELL', s and s['side'] == 'sell' and s['name'] == 'gold_scalp_c')
T('sell stop is above the sweep candle high, target the nearest swing low below', s and s['sl'] > 400 - 131.0 and abs(s['tp'] - (400 - TOP)) < 1e-9 and s['tp'] < F[-1]['c'] < s['sl'])
T('mirror numbers match the buy exactly', s and r and abs(s['sl'] - (400 - r['sl'])) < 1e-9 and abs(s['tp'] - (400 - r['tp'])) < 1e-9)
setscan('down', [zone(130.0, 134.0, side='buy')])
T('a demand zone is not used for a sell', gold_scalp_c(F, []) is None)
setscan('up', [ZN])
T('bias up never gives a sell on the mirrored chart', gold_scalp_c(F, []) is None)

# ---- registered in the bot, and never two votes for one idea on the same candle
from backend import strategies as S, brain, strategy_info as si
T('registered in strategies.ALL and in the TREND group', any(f.__name__ == 'gold_scalp_c' for f in S.ALL) and 'gold_scalp_c' in S.TREND)
T('has a readable name in strategy_info', si.name('gold_scalp_c') == 'Sweep scalp (safe entry)')
only = tuple(f.__name__ for f in S.ALL if f.__name__ != 'gold_scalp_c')
setscan('up', [ZN])
T('with SOLO off the brain wants a second strategy to agree', brain.evaluate(SETUP, [], off=only) is None)
gsc.SOLO = True; setscan('up', [ZN]); b = brain.evaluate(SETUP, [], off=only); gsc.SOLO = False
T('with SOLO on the brain takes it alone, keeps the name and the video target', b and b['strategy'] == 'gold_scalp_c' and b['side'] == 'buy' and abs(b['tp'] - TOP) < 1e-4)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
