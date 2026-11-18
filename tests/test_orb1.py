"""Tests for backend/orb_range.py (video 4, section 4A). Run: python tests/test_orb1.py"""
import os, sys, calendar
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.orb_range as orb
from backend.orb_range import opening_range, displacement, scan, ny_local, ny_epoch, _ny_local_rule

R = []
def T(name, ok): R.append((name, bool(ok)))
def utc(y, mo, d, h, mi): return calendar.timegm((y, mo, d, h, mi, 0))
SUMMER = utc(2026, 7, 15, 13, 30)      # 9:30 New York in July = 13:30 UTC (daylight saving)
WINTER = utc(2026, 1, 14, 14, 30)      # 9:30 New York in January = 14:30 UTC

def bar(t, o, c, w=0.1, hi=None, lo=None):
    return {'t': t, 'o': o, 'h': hi if hi is not None else max(o, c) + w, 'l': lo if lo is not None else min(o, c) - w, 'c': c, 'v': 1}

def day(t0, step=300, post=(), rng=None, pre_n=30):
    """Quiet history before 9:30, the range candles (9:30-9:45), then 'post' = list of (o, c) or (o, c, hi). Range 99.9 - 101.1 unless rng is given."""
    out = []
    for k in range(pre_n):
        o = 100.0 if k % 2 == 0 else 100.3
        c = 100.3 if k % 2 == 0 else 100.0
        out.append(bar(t0 - (pre_n - k) * step, o, c))
    if rng is None:
        rng = [(100.2, 100.8), (100.8, 100.4), (100.4, 100.7)] if step == 300 else [(100.2, 100.7)]
    t = t0
    for o, c in rng: out.append(bar(t, o, c, 0.3)); t += step
    for p in post:
        out.append(bar(t, p[0], p[1], hi=p[2] if len(p) > 2 else None)); t += step
    return out
def mirror(c): return [{'t': x['t'], 'o': 200 - x['o'], 'h': 200 - x['l'], 'l': 200 - x['h'], 'c': 200 - x['c'], 'v': 1} for x in c]

UP3 = [(100.7, 101.5), (101.5, 102.3), (102.3, 103.1)]        # three big green candles, all closing above the range high 101.1

# --- New York clock, summer and winter ---
T('clock: July 9:30 New York is 13:30 UTC', ny_epoch(datetime(2026, 7, 15).date(), 9, 30) == SUMMER)
T('clock: January 9:30 New York is 14:30 UTC', ny_epoch(datetime(2026, 1, 14).date(), 9, 30) == WINTER)
T('clock: the day after spring-forward (9 Mar 2026) is already 13:30 UTC', ny_epoch(datetime(2026, 3, 9).date(), 9, 30) == utc(2026, 3, 9, 13, 30))
T('clock: the day before spring-forward (6 Mar 2026) is still 14:30 UTC', ny_epoch(datetime(2026, 3, 6).date(), 9, 30) == utc(2026, 3, 6, 14, 30))
T('clock: the day after fall-back (2 Nov 2026) is 14:30 UTC', ny_epoch(datetime(2026, 11, 2).date(), 9, 30) == utc(2026, 11, 2, 14, 30))
T('clock: the day before fall-back (30 Oct 2026) is still 13:30 UTC', ny_epoch(datetime(2026, 10, 30).date(), 9, 30) == utc(2026, 10, 30, 13, 30))
T('clock: ny_local turns 13:30 UTC in July into 9:30', ny_local(SUMMER) == datetime(2026, 7, 15, 9, 30))
T('clock: ny_local turns 14:30 UTC in January into 9:30', ny_local(WINTER) == datetime(2026, 1, 14, 9, 30))
bad = 0
for k in range(0, 366 * 2 * 48):
    t = utc(2025, 1, 1, 0, 0) + k * 1800
    if _ny_local_rule(t) != ny_local(t): bad += 1
T('clock: the built-in daylight-saving rule agrees with the machine clock for 2025 and 2026 (every 30 minutes)', bad == 0)

# --- the opening range ---
r = opening_range(day(SUMMER, 300, UP3))
T('range: high and low of the three 5m candles 9:30-9:45 (summer)', r and abs(r['hi'] - 101.1) < 1e-9 and abs(r['lo'] - 99.9) < 1e-9)
T('range: midline is halfway', r and abs(r['mid'] - 100.5) < 1e-9)
T('range: starts at 9:30 New York and lasts 15 minutes', r and r['t0'] == SUMMER and r['t1'] == SUMMER + 900)
r = opening_range(day(WINTER, 300, UP3))
T('range: the same in winter, 14:30 UTC', r and r['t0'] == WINTER and abs(r['hi'] - 101.1) < 1e-9)
r15 = opening_range(day(SUMMER, 900, [(100.7, 101.5)]))
T('range: one 15m candle at 9:30 is the range', r15 and abs(r15['hi'] - 101.0) < 1e-9 and abs(r15['lo'] - 99.9) < 1e-9)
T('range: not finished at 9:40 = None', opening_range(day(SUMMER, 300, [])[:-1]) is None)
T('range: a 15m chart whose last candle is the 9:30 one = None (the range is only final once 9:45 has started)', opening_range(day(SUMMER, 900, [])) is None)
T('range: a missing 5m candle inside 9:30-9:45 = None', opening_range(day(SUMMER, 300, UP3)[:31] + day(SUMMER, 300, UP3)[32:]) is None)
T('range: the candle at 9:30 must be there (data starting at 9:35 = None)', opening_range(day(SUMMER, 300, UP3)[31:]) is None)
T('range: a 1-hour chart = None', opening_range(day(SUMMER, 3600, [(100.7, 101.5)])) is None)
T('range: candles ahead of 9:30 (overnight) are not in the range', opening_range(day(SUMMER, 300, UP3, pre_n=60))['lo'] > 99.0)
c = day(SUMMER, 300, UP3); wk = [dict(x, t=x['t'] + 3 * 86400) for x in c]
T('range: a Saturday has no range', opening_range(wk) is None)
T('range: uses the day of the LAST candle (next day without its 9:30 candle = None)', opening_range(c + [bar(SUMMER + 86400 + 4 * 3600, 100, 101)]) is None)

# --- displacement: up ---
c = day(SUMMER, 300, UP3); r = opening_range(c); d = displacement(c, r)
T('disp: three big green candles closing above the range = buy', d and d['side'] == 'buy' and d['n'] == 3)
T('disp: the run starts at the first big candle (right after the range)', d and d['start'] == 33 and d['end'] == 35)
T('disp: break level is the range high', d and abs(d['level'] - 101.1) < 1e-9)
T('disp: scan() gives range and displacement together', scan(c) and scan(c)['disp']['side'] == 'buy' and scan(c)['range']['hi'] == r['hi'])
T('disp: works the same in winter', displacement(day(WINTER, 300, UP3), opening_range(day(WINTER, 300, UP3))) is not None)
T('disp: four big candles are a run of four', displacement(*(lambda c: (c, opening_range(c)))(day(SUMMER, 300, UP3 + [(103.1, 103.9)])))['n'] == 4)
c2 = day(SUMMER, 300, UP3[:2]); T('disp: only two big candles = not enough', displacement(c2, opening_range(c2)) is None)
cs = day(SUMMER, 300, [(101.0, 101.15), (101.15, 101.3), (101.3, 101.45)])
T('disp: small candles drifting out of the range do not count (no big bodies)', displacement(cs, opening_range(cs)) is None)
cw = day(SUMMER, 300, [(100.7, 100.9, 102.0), (100.9, 101.0, 102.0), (101.0, 100.9, 102.0), (100.9, 100.8, 102.0)])
T('disp: wicks above the range with closes inside it do not count', displacement(cw, opening_range(cw)) is None)
cb = day(SUMMER, 300, [(100.7, 101.5), (101.5, 102.3), (102.3, 101.9), (101.9, 102.7)])
T('disp: a red candle breaks the run (green, green, red, green)', displacement(cb, opening_range(cb)) is None)
ci = day(SUMMER, 300, [(100.7, 100.9), (100.9, 101.0), (101.0, 101.7), (101.7, 102.5), (102.5, 103.3)])
T('disp: it may start a few candles after the range', displacement(ci, opening_range(ci)) and displacement(ci, opening_range(ci))['start'] == 35)
cin = day(SUMMER, 300, [(100.4, 100.65), (100.65, 100.9), (100.9, 101.0)], rng=[(100.2, 100.8), (100.8, 100.4), (100.4, 100.7)])
T('disp: big candles that stay inside the range do not count', displacement(cin, opening_range(cin)) is None)
# the 9:30-9:45 candles themselves are never a displacement
cr = day(SUMMER, 300, [(102.0, 103.0)], rng=[(99.9, 100.6), (100.6, 101.3), (101.3, 102.0)])      # 3 big green candles INSIDE 9:30-9:45, then 1 more after
T('disp: the range candles (9:30-9:45) are never counted as the push', displacement(cr, opening_range(cr)) is None)

# --- structure: a wick above the range raises the bar ---
sp = [(100.7, 100.9, 102.5)]
low3 = sp + [(100.9, 101.4), (101.4, 101.9), (101.9, 102.4)]
high3 = sp + [(100.9, 101.4), (101.4, 101.9), (101.9, 102.7)]
cl = day(SUMMER, 300, low3); ch = day(SUMMER, 300, high3)
T('structure: closes above the range but below the recent wick high do not break structure', displacement(cl, opening_range(cl)) is None)
lw = sp + [(100.9, 101.4), (101.4, 101.9), (101.9, 102.4, 103.2)]; cw2 = day(SUMMER, 300, lw)
T('structure: a wick above the recent high is not enough, the CLOSE must be (up)', displacement(cw2, opening_range(cw2)) is None)
dh = displacement(ch, opening_range(ch))
T('structure: a close above the recent wick high is a displacement', dh and dh['side'] == 'buy' and abs(dh['level'] - 102.5) < 1e-9)

# --- displacement: down (mirror image) ---
cd = mirror(day(SUMMER, 300, UP3)); rd = opening_range(cd); dd = displacement(cd, rd)
T('disp: mirror image gives a sell', dd and dd['side'] == 'sell' and dd['n'] == 3 and abs(dd['level'] - (200 - 99.9)) > 0 and abs(dd['level'] - rd['lo']) < 1e-9)
cdw = mirror(day(SUMMER, 300, [(100.7, 100.9, 102.0), (100.9, 101.0, 102.0), (101.0, 100.9, 102.0), (100.9, 100.8, 102.0)]))
T('disp: sell side, wick-only below the range does not count', displacement(cdw, opening_range(cdw)) is None)
cdl = mirror(day(SUMMER, 300, low3)); cdh = mirror(day(SUMMER, 300, high3)); cdw2 = mirror(cw2)
T('structure: a wick below the recent low is not enough, the CLOSE must be (down)', displacement(cdw2, opening_range(cdw2)) is None)
T('structure: sell side, a close below the recent wick low is needed', displacement(cdl, opening_range(cdl)) is None and displacement(cdh, opening_range(cdh)) is not None)

# --- session window and days ---
t16 = ny_epoch(datetime(2026, 7, 15).date(), 16, 0)
late = day(SUMMER, 300, [(100.7, 100.8)] * 80)                # quiet until after 16:00
for i, (o, cc) in enumerate(UP3): late.append(bar(t16 + i * 300, o + 0.1 * i, cc + 0.1 * i))
T('window: a push after 16:00 New York is ignored', displacement(late, opening_range(late)) is None)
yest = day(SUMMER - 86400, 300, UP3); today = day(SUMMER, 300, [(100.7, 100.8)])
T('window: yesterday\'s push is not today\'s displacement', displacement(yest + today, opening_range(yest + today)) is None)
T('window: nothing but the range = no displacement yet', displacement(day(SUMMER, 300, []), opening_range(day(SUMMER, 300, []))) is None)
T('data: too few candles = None', displacement(day(SUMMER, 300, UP3, pre_n=5), opening_range(day(SUMMER, 300, UP3, pre_n=5))) is None)
T('data: displacement(None) = None', displacement(day(SUMMER, 300, UP3), None) is None)
T('scan: no finished range = None', scan(day(SUMMER, 300, [])[:-1]) is None)
c = day(SUMMER, 300, [(100.7, 100.8)])
T('scan: range but no push gives disp None', scan(c) and scan(c)['range'] and scan(c)['disp'] is None)
# the run keeps growing, its start does not move
a3 = displacement(day(SUMMER, 300, UP3), opening_range(day(SUMMER, 300, UP3))); a4 = displacement(*(lambda c: (c, opening_range(c)))(day(SUMMER, 300, UP3 + [(103.1, 103.9)])))
T('disp: a longer run keeps the same start', a3['start'] == a4['start'] and a4['end'] == a3['end'] + 1)
# 15-minute chart
c15 = day(SUMMER, 900, [(100.7, 101.6), (101.6, 102.5), (102.5, 103.4)]); d15 = displacement(c15, opening_range(c15))
T('disp: also works on 15m candles', d15 and d15['side'] == 'buy' and d15['n'] == 3)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
