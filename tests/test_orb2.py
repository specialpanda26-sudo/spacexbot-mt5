"""Tests for backend/orb_entry.py (video 4, section 4B). Run: python tests/test_orb2.py"""
import os, sys, calendar
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.orb_entry as oe
import backend.orb_range as orb
import backend.strategies as S
import backend.strategy_info as SI
from backend.orb_entry import entry, orb_entry
from backend.indicators import atr

R = []
def T(name, ok): R.append((name, bool(ok)))
def utc(y, mo, d, h, mi): return calendar.timegm((y, mo, d, h, mi, 0))
SUMMER = utc(2026, 7, 15, 13, 30)      # 9:30 New York

def bar(t, o, c, w=0.1, hi=None, lo=None):
    return {'t': t, 'o': o, 'h': hi if hi is not None else max(o, c) + w, 'l': lo if lo is not None else min(o, c) - w, 'c': c, 'v': 1}
def day(t0, post, step=300, rng=None, pre_n=30):
    """Quiet history, the range (9:30-9:45), then post = list of (o, c[, hi[, lo]]). Default range 99.9 - 101.1."""
    out = []
    for k in range(pre_n):
        o = 100.0 if k % 2 == 0 else 100.3
        c = 100.3 if k % 2 == 0 else 100.0
        out.append(bar(t0 - (pre_n - k) * step, o, c))
    if rng is None: rng = [(100.2, 100.8), (100.8, 100.4), (100.4, 100.7)] if step == 300 else [(100.2, 100.7)]
    t = t0
    for p in rng: out.append(bar(t, p[0], p[1], 0.3, p[2] if len(p) > 2 else None, p[3] if len(p) > 3 else None)); t += step
    for p in post: out.append(bar(t, p[0], p[1], hi=p[2] if len(p) > 2 else None, lo=p[3] if len(p) > 3 else None)); t += step
    return out
def mirror(c): return [{'t': x['t'], 'o': 200 - x['o'], 'h': 200 - x['l'], 'l': 200 - x['h'], 'c': 200 - x['c'], 'v': 1} for x in c]

# Red candle (100.7 -> 100.3, zone 100.2 - 100.8), then three big green candles with NO gaps between them (so only the order block is a zone).
OB = (100.7, 100.3)
PUSH = [(100.3, 101.2, 101.3, 100.2), (101.2, 102.0, 102.1, 100.8), (102.0, 102.8, 102.9, 101.2)]
BACK = [(102.8, 102.0), (102.0, 101.2), (101.2, 100.6)]          # price comes back down; the last one closes red inside the zone (no hold)
GO = (100.6, 100.95)                                              # green, touches the zone, closes in its upper half = the entry
def scen(extra=(), push=PUSH, back=BACK, ob=OB, **kw): return day(SUMMER, [ob] + list(push) + list(back) + list(extra), **kw)
def last(extra=()): return scen([GO] + list(extra))

e = entry(last())
T('entry: the first candle that touches the zone and holds is a BUY', e and e['side'] == 'buy' and e['kind'] == 'ob')
T('entry: the zone is the last red candle before the push (its low to its high)', e and abs(e['zone'][0] - 100.2) < 1e-9 and abs(e['zone'][1] - 100.8) < 1e-9)
T('entry: the entry price is the close of that candle', e and abs(e['entry'] - 100.95) < 1e-9)
cc = last(); a = atr(cc)[-1]
T('entry: stop sits just under the zone low', e and abs(e['sl'] - (100.2 - 0.1 * a)) < 1e-9 and e['sl'] < 100.2)
T('entry: target is 1.6 R for a push of 3 candles', e and abs((e['tp'] - e['entry']) - 1.6 * (e['entry'] - e['sl'])) < 1e-9 and e['rr'] == 1.6)
T('entry: stop is within the brain\'s 0.5 to 3.5 ATR', e and 0.5 * a <= e['entry'] - e['sl'] <= 3.5 * a)
T('entry: no engulfing candle needed (bonus only)', e and e['engulf'] is False)
eg = entry(scen([(100.6, 100.5), (100.45, 100.95)]))                       # a red candle then a green one whose body covers it
T('entry: an engulfing candle sets the bonus flag', eg and eg['engulf'] is True and eg['kind'] == 'ob')
T('entry: not before the candle holds (the red close inside the zone gives nothing)', entry(scen()) is None)
T('entry: only the FIRST holding candle fires (the next candle gives nothing)', entry(last([(100.95, 101.3)])) is None)
T('entry: a push that is still running gives nothing', entry(day(SUMMER, [OB] + PUSH)) is None and entry(day(SUMMER, [OB] + PUSH[:2])) is None)
T('entry: price that never comes back gives nothing', entry(scen(back=[(102.8, 102.7), (102.7, 102.9), (102.9, 102.8)])) is None)
T('entry: a green candle that closes in the LOWER half of the zone is no hold', entry(scen([(100.3, 100.45)])) is None)
DP = (100.7, 100.3, 100.8, 98.5)                                           # a deep zone, 98.5 - 100.8 (middle 99.65): room for a valid stop
T('entry: deep zone, a green candle closing in its lower half is no hold', entry(scen(ob=DP, extra=[(99.0, 99.5)])) is None)
dz = entry(scen(ob=DP, extra=[(99.0, 99.8)]))
T('entry: deep zone, the same candle closing above the middle holds', dz and dz['kind'] == 'ob' and abs(dz['entry'] - 99.8) < 1e-9)
ge = entry(scen([(100.3, 100.45), (100.35, 100.9)]))
T('entry: engulfing needs a RED candle before it (a green one before does not count)', ge and ge['engulf'] is False)
up_half = entry(scen([(100.4, 100.7)]))
T('entry: a close in the upper half of the zone, below its top, holds', up_half and up_half['kind'] == 'ob' and abs(up_half['entry'] - 100.7) < 1e-9)
T('entry: a red candle closing in the zone is no hold', entry(scen([(100.8, 100.6)])) is None)
dead = scen([(100.6, 100.1), (100.1, 100.7)])
T('entry: a close below the zone uses it up (no later entry)', entry(dead) is None)
wick = scen([(100.6, 100.9, 101.0, 99.5)])                                 # wicks to 99.5, far under the zone, closes at 100.9
ew = entry(wick)
T('entry: a wick through the zone that closes back up still holds, stop under the wick', ew and ew['sl'] < 99.5)
T('entry: a candle that does not touch the zone is no entry', entry(scen([(101.3, 101.8)])) is None)

# --- no zone ---
g = [(100.2, 100.4), (100.4, 100.6), (100.6, 100.7)]
noob = day(SUMMER, [(100.7, 100.75)] + PUSH + BACK + [GO], rng=g)          # no red candle in the 3 candles before the push, no gaps
old = day(SUMMER, [(100.7, 100.75)] + PUSH + [(102.8, 102.0), (102.0, 101.2), (101.2, 100.5), (100.5, 100.2), (100.2, 100.6)], rng=g)   # comes back down into an OLD red candle (the overnight one, 99.9 - 100.4)
T('zone: a red candle from long before the push is not the zone', entry(old) is None)
two = entry(day(SUMMER, [OB, (100.3, 100.45)] + PUSH + [(102.8, 102.0), (102.0, 101.2), (101.2, 100.6)] + [GO]))
T('zone: the red candle may be a few candles before the push (a small green one in between)', two and two['kind'] == 'ob' and abs(two['zone'][0] - 100.2) < 1e-9)
T('zone: no red candle before the push = no order block, so no entry', entry(noob) is None)

# --- fair value gap ---
GAPS = [(100.3, 101.2), (101.2, 102.0), (102.0, 102.8)]                    # gap 1: 100.8 - 101.1, gap 2: 101.3 - 101.9 (plus the order block)
fb = [(102.8, 102.0), (102.0, 101.5), (101.5, 101.0), (101.0, 101.3)]
fv = entry(day(SUMMER, [OB] + GAPS + fb))
T('fvg: price comes back and holds a gap = entry on the gap', fv and fv['side'] == 'buy' and fv['kind'] == 'fvg')
T('fvg: stop is the range midline when that is below the gap and near enough', fv and abs(fv['sl'] - 100.5) < 1e-9)
far = day(SUMMER, [OB] + GAPS + fb, rng=[(100.2, 100.8), (100.8, 100.4), (100.4, 100.7, None, 90.0)])
ff = entry(far); af = atr(far)[-1]
T('fvg: midline too far for the brain (over 3.5 ATR) = stop just under the gap', ff and ff['kind'] == 'fvg' and abs(ff['sl'] - (100.8 - 0.1 * af)) < 1e-9)
f2 = entry(day(SUMMER, [OB] + GAPS + [(102.8, 102.3), (102.3, 101.8), (101.7, 101.95)]))
T('fvg: the LAST gap of the push is a zone too', f2 and f2['kind'] == 'fvg' and abs(f2['zone'][0] - 101.3) < 1e-9 and abs(f2['zone'][1] - 101.9) < 1e-9)
tiny = [(100.3, 101.2, 101.3, 100.2), (101.2, 102.0, 102.1, 100.85), (102.0, 102.8, 102.9, 101.35)]      # gaps of 0.05, the push itself is big
ct = day(SUMMER, [OB] + tiny); dt_ = orb.scan(ct)['disp']
T('fvg: a gap smaller than 0.2 ATR is not a zone (but the order block still is)', dt_ and [z['kind'] for z in oe._zones(ct, atr(ct), dt_)] == ['ob'])
tall = [(100.2, 100.8), (100.8, 100.4), (100.4, 100.7, 104.0)]                        # tall range: 99.9 - 104.0, midline 101.95
tp_ = [OB, (100.3, 104.5, 104.6, 100.2), (104.5, 105.5, 105.6, 104.3), (105.5, 106.5, 106.6, 105.4), (106.5, 105.0), (105.0, 104.0), (104.0, 103.0), (103.0, 103.4)]
tl = day(SUMMER, tp_, rng=tall); etl = entry(tl)
T('fvg: midline above the bottom of the gap is never the stop (stop goes under the gap)', etl and etl['kind'] == 'fvg' and abs(etl['sl'] - (100.8 - 0.1 * atr(tl)[-1])) < 1e-9 and etl['sl'] < 101.95)
T('fvg: a close below a gap uses that gap up (the lower zone still lives)', fv and fv['zone'][0] < 101.3)

# --- target ---
c4 = scen(push=PUSH + [(102.8, 103.6, 103.7, 102.7)], back=[(103.6, 102.8), (102.8, 102.0), (102.0, 101.2), (101.2, 100.6)])
e4 = entry(c4 + [bar(c4[-1]['t'] + 300, 100.6, 100.95)])
T('target: a push of 4 big candles gets 2.2 R', e4 and e4['rr'] == 2.2 and abs((e4['tp'] - e4['entry']) - 2.2 * (e4['entry'] - e4['sl'])) < 1e-9)
dp = DP                                                                    # the target (about 105) is above the push high (102.9)
ctl = entry(scen(ob=dp, back=[(102.8, 102.9, 103.0, 102.7)] + BACK, extra=[GO]))
ctl_w = entry(scen(ob=dp, extra=[(100.6, 100.95, 106.0, 100.5)]))
T('target: the entry candle itself wicking past the target is no trade either', ctl_w is None)
T('target: control - deep zone, price stays under the target = entry', ctl and ctl['tp'] > 102.9)
T('target: price already reached the target before it came back = no trade', entry(scen(ob=dp, back=[(102.8, 102.9, 105.2, 102.7)] + BACK, extra=[GO])) is None)

# --- stop distance ---
wide = scen(ob=(100.7, 100.3, 100.8, 94.0), extra=[GO])
T('stop: wider than 3.5 ATR is skipped, not reshaped', entry(wide) is None)
tight = scen(ob=(100.95, 100.9, 100.99, 100.89), push=[(100.9, 101.7, 101.8, 100.89), (101.7, 102.5, 102.6, 101.5), (102.5, 103.3, 103.4, 102.4)], back=[(103.3, 102.0), (102.0, 101.1), (101.1, 100.98)], extra=[(100.97, 101.0, 101.0, 100.9)])
T('stop: tighter than 0.5 ATR is skipped', entry(tight) is None)

# --- time rules ---
slow = scen(back=[(102.8, 102.9)] * 40 + BACK, extra=[GO])                  # 40 quiet candles = 200 minutes before the return
T('time: a return later than 3 hours after the push gives nothing', entry(slow) is None)
fast = scen(back=[(102.8, 102.9)] * 20 + BACK, extra=[GO])                  # 100 minutes
T('time: a return within 3 hours still works', entry(fast) is not None)
import datetime as _dt
t16 = orb.ny_epoch(_dt.datetime(2026, 7, 15).date(), 16, 0)
def timed(go_t):
    """Order block + push, then quiet candles up to go_t, then the way back and the entry candle starting at go_t (5-minute candles)."""
    c = day(SUMMER, [OB] + PUSH)
    while c[-1]['t'] + 300 * 4 < go_t: c.append(bar(c[-1]['t'] + 300, 102.8, 102.9))
    t = go_t - 300 * 3
    for o, cl in BACK + [GO]: c.append(bar(t, o, cl)); t += 300
    return c
oe.WAIT_SEC = 10 ** 9                                                       # so only the 16:00 rule is tested here
T('time: an entry candle that opens at 15:55 New York is allowed', entry(timed(t16 - 300)) is not None)
T('time: an entry candle at or after 16:00 New York gives nothing', entry(timed(t16)) is None)
oe.WAIT_SEC = 10800

# --- sells ---
sm = mirror(last()); es = entry(sm)
T('sell: a push down gives a SELL on the supply zone', es and es['side'] == 'sell' and es['kind'] == 'ob')
T('sell: stop above the zone, target below the entry, 1.6 R', es and es['sl'] > es['zone'][1] and es['tp'] < es['entry'] and abs((es['entry'] - es['tp']) - 1.6 * (es['sl'] - es['entry'])) < 1e-9)
T('sell: entry and zone are the mirror of the buy', es and abs(es['entry'] - (200 - 100.95)) < 1e-9 and abs(es['zone'][0] - (200 - 100.8)) < 1e-9 and abs(es['zone'][1] - (200 - 100.2)) < 1e-9)
fm = entry(mirror(day(SUMMER, [OB] + GAPS + fb)))
T('sell: a gap entry uses the mirrored range midline as the stop', fm and fm['side'] == 'sell' and fm['kind'] == 'fvg' and abs(fm['sl'] - (200 - 100.5)) < 1e-9)
T('sell: mirror of the no-hold case gives nothing', entry(mirror(scen())) is None)
T('sell: a push down never gives a buy', all((entry(mirror(x)) or {'side': 'sell'})['side'] == 'sell' for x in (last(), scen([(100.6, 100.9)]), wick)))

# --- the registered strategy ---
m = last(); s = orb_entry(m, [])
T('strategy: returns side, stop, target and its name', s and set(s) == {'side', 'sl', 'tp', 'name'} and s['name'] == 'orb_entry' and s['side'] == 'buy')
T('strategy: the same numbers as entry()', s and abs(s['sl'] - e['sl']) < 1e-9 and abs(s['tp'] - e['tp']) < 1e-9)
T('strategy: too little data = None, empty = None', orb_entry(m[:20], []) is None and orb_entry([], []) is None)
m25 = scen([GO], pre_n=10)
T('strategy: a valid setup on fewer than 30 candles is left alone', len(m25) < 30 and entry(m25) is not None and orb_entry(m25, []) is None)
T('strategy: no entry candle = None', orb_entry(scen(), []) is None)
T('strategy: may not trade alone by default', 'solo' not in s and oe.SOLO is False)
m15 = day(SUMMER, [(100.7, 100.3)] + [(100.3, 101.3, 101.4, 100.2), (101.3, 102.3, 102.4, 100.9), (102.3, 103.3, 103.4, 101.3)] + [(103.3, 102.0), (102.0, 101.0), (101.0, 100.6)] + [(100.5, 100.95)], step=900, rng=[(100.2, 100.7)])
T('strategy: also works on 15m candles', entry(m15) is not None and entry(m15)['kind'] == 'ob')
bad = 0
for k in range(40):
    try: orb_entry(day(SUMMER, [(100.7, 100.3 + 0.1 * k)] * k), [])
    except Exception: bad += 1
T('strategy: never raises on odd data', bad == 0)

# --- registration ---
names = [f.__name__ for f in S.ALL]
T('registered once in strategies.ALL', names.count('orb_entry') == 1)
T('registered in the TREND group', 'orb_entry' in S.TREND and 'orb_entry' not in S.REVERSION)
T('has a name (1-32 chars) and a description (1-140 chars) in strategy_info', 'orb_entry' in SI.INFO and 1 <= len(SI.INFO['orb_entry'][0]) <= 32 and 1 <= len(SI.INFO['orb_entry'][1]) <= 140)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
