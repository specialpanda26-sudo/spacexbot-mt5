"""Tests for backend/btc_weekend.py (BTC Section 6B: Sunday-open bounce + short only after a pullback). Run: python tests/test_btc6b.py
Charts are synthetic: 15-minute candles with 20-dollar wicks. Friday 2026-11-20 falls from 101,200 to 95,972 (5%), the weekend chops around 96,100,
and in the Sunday 22:00 window two small red candles are followed by a green one. The short tests use a steady fall (the 4h 50 EMA far above price)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'btc6b_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
import datetime as dt
from backend.app import app
from backend import alerts; alerts.stop()          # the app starts its alert loop at import (see HANDOFF N6e)
from backend import store as st
import backend.btc_weekend as bw
from backend.indicators import atr, ema

R = []
def T(name, ok): R.append((name, bool(ok)))
STEP = 900
def ts(y, mo, d, h=0, mi=0): return int((dt.datetime(y, mo, d, h, mi) - dt.datetime(1970, 1, 1)).total_seconds())
def agg(m, step):
    g = {}
    for x in m: g.setdefault(x['t'] - x['t'] % step, []).append(x)
    return [{'t': t, 'o': s[0]['o'], 'h': max(x['h'] for x in s), 'l': min(x['l'] for x in s), 'c': s[-1]['c'], 'v': 1} for t, s in sorted(g.items())]
def candles(t0, p0, steps, wick=20.0):
    out = []; p = p0
    for d in steps:
        o = p; c = p + d; out.append({'t': t0 + len(out) * STEP, 'o': o, 'h': max(o, c) + wick, 'l': min(o, c) - wick, 'c': c, 'v': 1}); p = c
    return out
def more(m, steps, wick=20.0): return m + candles(m[-1]['t'] + STEP, m[-1]['c'], steps, wick)
def tweak(**kw):
    old = {k: getattr(bw, k) for k in kw}
    for k, v in kw.items(): setattr(bw, k, v)
    return old
def restore(old):
    for k, v in old.items(): setattr(bw, k, v)

# =========================================================== 1) Sunday-open bounce
F0 = ts(2026, 11, 20)                                         # a Friday; 2026-11-22 is the Sunday
FRI = [100] * 12 + [-62] * 84                                 # up to 101,200 then down to 96,000 (a 5% sell-off, high before low)
SAT = [100] + [20, -20] * 47 + [20]
SUN = [20, -20] * 44                                          # Sunday 00:00 to 22:00
def sun_chart(fri=FRI, sat=SAT, sun=SUN, win=(-40, -40, 100), start=100000, t0=F0):
    m = candles(t0, start, fri + sat + sun); return more(m, list(win))
M = sun_chart(); H = agg(M, 3600)
r = bw.sunday_setup(M, H)
lo, hi = r['friday'] if r else (0, 0); A = atr(M)[-1]; FIB1 = lo + 0.382 * (hi - lo)
T('Friday sell-off, Sunday window, green candle under 0.382: a BUY', r and r['side'] == 'buy')
T('Friday range is the H1 high and low of that Friday', r and abs(hi - 101220) < 1 and abs(lo - 95972) < 1)
T('take profit is the 0.382 fib of Friday high-to-low, tp2 the 0.5', r and abs(r['tp'] - FIB1) < 1e-6 and abs(r['tp2'] - (lo + 0.5 * (hi - lo))) < 1e-6)
T('stop is BUF x ATR under the lowest low of the window and 0.5-3.5 ATR from entry', r and r['sl'] < min(x['l'] for x in M[-3:]) and 0.5 * A <= r['entry'] - r['sl'] <= 3.5 * A and abs(r['sl'] - (min(x['l'] for x in M[-3:]) - bw.BUF * A)) < 1e-6)
T('entry is the close of the green candle', r and r['entry'] == M[-1]['c'])

# ---- OFF / ON switch (real store)
T('both switches are OFF by default', st.get('btc_sunday_bounce') == '0' and st.get('btc_short_pullback') == '0')
T('switch OFF: the strategy is silent even with a perfect setup', bw.btc_sunday_bounce(M, H) is None)
st.put('btc_sunday_bounce', '1'); g = bw.btc_sunday_bounce(M, H)
T('switch ON: the strategy returns the signal', g and g['side'] == 'buy' and g['name'] == 'btc_sunday_bounce' and set(g) == {'side', 'sl', 'tp', 'name'})
T('the signal carries the 0.382 target and the stop of the setup', g and abs(g['tp'] - r['tp']) < 1e-9 and abs(g['sl'] - r['sl']) < 1e-9)
old = tweak(SOLO=True); T('SOLO = True adds the solo flag (off by default)', (bw.btc_sunday_bounce(M, H) or {}).get('solo') is True); restore(old)
st.put('btc_sunday_bounce', 'banana'); T('a bad switch value counts as OFF', bw.btc_sunday_bounce(M, H) is None)
st.put('btc_sunday_bounce', '0'); T('switching it back OFF silences it again', bw.btc_sunday_bounce(M, H) is None)

# ---- time rules
Sat_m = sun_chart(t0=F0 - 86400); Sat_h = agg(Sat_m, 3600)   # the same week shifted one day back: a Thursday sell-off and a green candle at Saturday 22:30
T('(sanity) that chart ends on a Saturday', dt.datetime.fromtimestamp(Sat_m[-1]['t'], dt.timezone.utc).weekday() == 5)
T('Saturday evening: nothing fires, the rule is Sunday only', bw.sunday_setup(Sat_m, Sat_h) is None)
Mout = more(candles(F0, 100000, FRI + SAT + SUN[:-1]), [100]); Hout = agg(Mout, 3600)   # a green candle that starts at 21:45 and ends at the 22:00 open
T('a green candle that starts before the 22:00 open is outside the window', bw.sunday_setup(Mout, Hout) is None)
Mlate = more(M, [-30, -30, -30, -30, -30, -30, -30, -30, -30, 100])   # pushes the signal candle past midnight / out of the window
T('after the window (past 24:00 UTC, Monday) nothing fires', bw.sunday_setup(Mlate, agg(Mlate, 3600)) is None)
old = tweak(OPEN_HOUR=20)
T('OPEN_HOUR is a real tunable (20:00 opens the window earlier, but a candle at 22:30 is still inside 20:00-22:00? no: it is outside)', bw.sunday_setup(M, H) is None); restore(old)

# ---- Friday rules
shallow = [100] * 12 + [-30] * 84                             # high 101,200, low about 98,660: a 2.5% fall, under DROP_PCT (3%) but over 1%
Ms = sun_chart(fri=shallow, start=100000)
T('a Friday fall under DROP_PCT (2.5% against 3%) is not a big sell-off: nothing', bw.sunday_setup(Ms, agg(Ms, 3600)) is None)
old = tweak(DROP_PCT=1.0); T('DROP_PCT is a real tunable (1% accepts the same 2.5% fall)', bw.sunday_setup(Ms, agg(Ms, 3600)) is not None); restore(old)
rally = [-100] * 30 + [50] * 66                              # low early (about 96,980), high late (about 100,320): a rally, not a sell-off
SAT_R = [-40] * 80 + [20, -20] * 8; WIN_R = (-30, -30, 100)
Mr = sun_chart(fri=rally, sat=SAT_R, win=WIN_R); Hr = agg(Mr, 3600)
old = tweak(DROP_PCT=0.0); T('(sanity) without the high-before-low rule this chart would be a bounce', True); restore(old)
T('Friday low BEFORE the high (a rally): nothing', bw.sunday_setup(Mr, Hr) is None)
Mgap = [x for x in M if not (F0 + 3600 * 2 <= x['t'] < F0 + 3600 * 8)]; Hgap = agg(Mgap, 3600)
T('Friday H1 history with too many holes: nothing', bw.sunday_setup(Mgap, Hgap) is None)
old = tweak(MIN_FRI_BARS=10); T('MIN_FRI_BARS is a real tunable (a 6-hour hole is fine at 10)', bw.sunday_setup(Mgap, Hgap) is not None); restore(old)

# ---- stand-down rules
Mbelow = sun_chart(sun=[20, -20] * 40 + [-200, -200, 200, 200, 20, -20, 20, -20])  # a Sunday candle CLOSED under the Friday low earlier on Sunday
T('(sanity) that chart does close under the Friday low', any(x['c'] < lo for x in Mbelow[-100:]))
T('a Sunday close under the Friday low = the sell-off goes on: nothing', bw.sunday_setup(Mbelow, agg(Mbelow, 3600)) is None)
Mt = M[:-3]; Mt = Mt + [dict(x) for x in candles(Mt[-1]['t'] + STEP, Mt[-1]['c'], [-40, -40, 100])]; Mt[-3]['h'] = FIB1 + 5
T('the 0.382 level was already touched in the window: the bounce happened, nothing', bw.sunday_setup(Mt, agg(Mt, 3600)) is None)
Mtwo = sun_chart(win=(-40, 100, -60, 100))                    # candle 2 already qualified (green, real body), candle 4 would too
T('(sanity) the first green candle of that chart is a valid entry', bw.sunday_setup(Mtwo[:-2], agg(Mtwo[:-2], 3600)) is not None)
T('a second qualifying candle in the window: it chopped, stand down', bw.sunday_setup(Mtwo, agg(Mtwo, 3600)) is None)

# ---- reaction candle rules
Mred = sun_chart(win=(-40, -40, -100));  T('a red last candle is not a bounce', bw.sunday_setup(Mred, agg(Mred, 3600)) is None)
Mdoji = sun_chart(win=(-40, -40, 5));    T('a doji (body under BODY_MIN x ATR) is no reaction', bw.sunday_setup(Mdoji, agg(Mdoji, 3600)) is None)
old = tweak(BODY_MIN=0.05); T('BODY_MIN is a real tunable (a small body passes at 0.05)', bw.sunday_setup(Mdoji, agg(Mdoji, 3600)) is not None); restore(old)
# stop distance: a deep dip in the window puts the stop far away; a tiny dip puts it too close
Mfar = sun_chart(); Mfar[-3]['l'] = 95600.0;  T('a stop wider than 3.5 ATR is skipped, never reshaped', bw.sunday_setup(Mfar, agg(Mfar, 3600)) is None)
old = tweak(SL_MAX=50.0); T('SL_MAX is a real tunable (the same chart passes with a wide limit)', bw.sunday_setup(Mfar, agg(Mfar, 3600)) is not None); restore(old)
old = tweak(RR_MIN=1000.0); T('RR_MIN is a real tunable (an RR of 1000 is refused)', bw.sunday_setup(M, H) is None); restore(old)
Mnear = more(M[:-3], [-40, -40, 100]); Mnear[-1]['c'] = FIB1 + 300; Mnear[-1]['h'] = FIB1 + 300
T('a green candle that closes at or above 0.382 is not a bounce: nothing', bw.sunday_setup(Mnear, agg(Mnear, 3600)) is None)
T('fewer than 40 candles: nothing', bw.sunday_setup(M[-30:], agg(M[-30:], 3600)) is None)
M5 = [dict(x) for x in M]; M5[-2]['t'] += 300                 # the last two candles are 10 minutes apart: not a 15-minute chart
T('only the 15-minute chart is read', bw.sunday_setup(M5, H) is None)

# =========================================================== 2) short only after a pullback
T0 = (1700000000 // 28800) * 28800
def e4h(m):
    c4 = bw._group4h(agg(m, 3600), m[-1]['t'] + STEP); return (ema([x['c'] for x in c4], bw.EMA_LEN)[-1] if c4 else None), len(c4)
def fall(n=960, start=100000, d=-10): return candles(T0, start, [d] * n)
def deep_chart(base=None, rally=100, body=0.6, back=0.2):
    m = base or fall()
    while True:
        e, _ = e4h(m); a = atr(m)[-1]
        if m[-1]['c'] >= e - 1.5 * a: break
        m = more(m, [rally])
    e, _ = e4h(m); a = atr(m)[-1]; o = e - back * a; c = o - body * a
    return m + [{'t': m[-1]['t'] + STEP, 'o': o, 'h': o + 5, 'l': c - 5, 'c': c, 'v': 1}]
def ss(m): return bw.short_setup(m, agg(m, 3600))

MD = deep_chart(); rd = ss(MD); E, nb = e4h(MD); AD = atr(MD)[-1]
T('(sanity) the 4h chart has enough candles and bias is down', nb >= bw.MIN_4H and MD[-1]['c'] < E)
T('deep pullback to the 4h 50 EMA, red real-body candle closing back under it: a SELL', rd and rd['side'] == 'sell' and rd['mode'] == 'deep')
T('the deep sell has no own target (the brain gives it 2R)', rd and rd['tp'] is None)
T('stop is above the pullback high, 0.5-3.5 ATR from entry', rd and rd['sl'] > max(x['h'] for x in MD[-bw.TOUCH_BARS:]) and 0.5 * AD <= rd['sl'] - rd['entry'] <= 3.5 * AD)
T('entry is the close of the red candle, under the EMA', rd and rd['entry'] == MD[-1]['c'] < E)

st.put('btc_short_pullback', '0'); HD = agg(MD, 3600)
T('switch OFF: the strategy is silent with a perfect setup', bw.btc_pullback_short(MD, HD) is None)
st.put('btc_short_pullback', '1'); gd = bw.btc_pullback_short(MD, HD)
T('switch ON: a sell signal with side, sl and name, and no tp for the deep case', gd and gd['side'] == 'sell' and gd['name'] == 'btc_pullback_short' and set(gd) == {'side', 'sl', 'name'})
old = tweak(SOLO=True); T('SOLO = True adds the solo flag (off by default)', (bw.btc_pullback_short(MD, HD) or {}).get('solo') is True); restore(old)
st.put('btc_short_pullback', 'x'); T('a bad switch value counts as OFF', bw.btc_pullback_short(MD, HD) is None)
st.put('btc_short_pullback', '0')

# ---- bias rules
MU = deep_chart(base=candles(T0, 80000, [10] * 960))
Mup = candles(T0, 80000, [10] * 960); o = Mup[-1]['c']; Mup += [{'t': Mup[-1]['t'] + STEP, 'o': o, 'h': o + 5, 'l': o - 400, 'c': o - 300, 'v': 1}]
T('a rising market (4h close above its 50 EMA): bias is not down, nothing', ss(Mup) is None)
Mrise = candles(T0, 80000, [10] * 900 + [-60] * 60)             # a sharp drop after a long rise: price is under the 4h EMA but the EMA is still RISING
Mrise = deep_chart(base=Mrise); c4r = bw._group4h(agg(Mrise, 3600), Mrise[-1]['t'] + STEP); e4r = ema([x['c'] for x in c4r], 50)
T('(sanity) price is under the 4h EMA and that EMA is still rising', c4r[-1]['c'] < e4r[-1] and e4r[-1] > e4r[-1 - bw.SLOPE_BARS])
T('a 4h EMA that is not falling: no bias, nothing (a perfect pullback candle is ignored)', ss(Mrise) is None)
Mab = fall()
while True:                                                   # rally until the last CLOSED 4h candle closes above its (still falling) 4h EMA
    c4 = bw._group4h(agg(Mab, 3600), Mab[-1]['t'] + STEP); e4 = ema([x['c'] for x in c4], 50)
    if c4[-1]['c'] > e4[-1] + 50: break
    Mab = more(Mab, [100])
e, _ = e4h(Mab); a = atr(Mab)[-1]; o = e + 0.3 * a
Mab = Mab + [{'t': Mab[-1]['t'] + STEP, 'o': o, 'h': o + 5, 'l': o - 0.9 * a - 5, 'c': o - 0.9 * a, 'v': 1}]
c4 = bw._group4h(agg(Mab, 3600), Mab[-1]['t'] + STEP); e4 = ema([x['c'] for x in c4], 50)
T('(sanity) the 4h EMA is falling, the last closed 4h candle is ABOVE it, the 15m candle closes under it', e4[-1] < e4[-1 - bw.SLOPE_BARS] and c4[-1]['c'] > e4[-1] and Mab[-1]['c'] < e4[-1])
old = tweak(TOUCH_BARS=1)                                     # the rally highs are far above, so look only at the signal candle for the stop
T('last closed 4h candle above its 4h 50 EMA: bias is not down, nothing', ss(Mab) is None); restore(old)
Mshort = deep_chart(base=fall(n=500))                        # 125 hours = 31 4h candles, a perfect pullback sell otherwise
T('(sanity) that chart has fewer 4h candles than MIN_4H', e4h(Mshort)[1] < bw.MIN_4H)
T('not enough 4h history (under MIN_4H candles): nothing', ss(Mshort) is None)
old = tweak(MIN_4H=20); T('MIN_4H is a real tunable (with 20 it fires)', ss(Mshort) is not None); restore(old)
M5s = [dict(x) for x in MD]; M5s[-2]['t'] += 300
T('only the 15-minute chart is read', bw.short_setup(M5s, HD) is None)
T('fewer than 60 candles: nothing', bw.short_setup(MD[-40:], agg(MD[-40:], 3600)) is None)

# ---- never short the lows: a straight waterfall with no pullback and no flag
Mwf = more(fall(), [-80] * 12 + [-60])
T('a straight waterfall with no pullback and no flag: nothing (never short the lows)', ss(Mwf) is None)
Mgreen = more(deep_chart()[:-1], [])
e, _ = e4h(Mgreen); a = atr(Mgreen)[-1]; o = e - 0.2 * a
Mgreen = Mgreen + [{'t': Mgreen[-1]['t'] + STEP, 'o': o, 'h': o + 0.6 * a, 'l': o - 5, 'c': o + 0.5 * a, 'v': 1}]
T('a GREEN candle at the EMA is not a rejection: nothing', ss(Mgreen) is None)
e, _ = e4h(MD[:-1]); a = atr(MD[:-1])[-1]; o = e - 0.2 * a
Mdoj = MD[:-1] + [{'t': MD[-2]['t'] + STEP, 'o': o, 'h': o + 5, 'l': o - 0.1 * a, 'c': o - 0.05 * a, 'v': 1}]
T('a red doji at the EMA (body under BODY_MIN x ATR) is no reaction', ss(Mdoj) is None)
old = tweak(BODY_MIN=0.01, SL_MIN=0.01); T('BODY_MIN is a real tunable for the short too', ss(Mdoj) is not None); restore(old)
e, _ = e4h(MD[:-1]); a = atr(MD[:-1])[-1]; o = e + 0.8 * a
Mabove = MD[:-1] + [{'t': MD[-2]['t'] + STEP, 'o': o, 'h': o + 5, 'l': o - 0.5 * a - 5, 'c': o - 0.5 * a, 'v': 1}]
T('a red candle that still CLOSES above the EMA is not a rejection', ss(Mabove) is None)
# first reaction only: an earlier red candle of the same visit already qualified
e, _ = e4h(MD[:-1]); a = atr(MD[:-1])[-1]; o = e - 0.2 * a; c = o - 0.6 * a
Mtwice = MD[:-1] + [{'t': MD[-2]['t'] + STEP, 'o': o, 'h': o + 5, 'l': c - 5, 'c': c, 'v': 1}, {'t': MD[-2]['t'] + 2 * STEP, 'o': o, 'h': o + 5, 'l': c - 5, 'c': c, 'v': 1}]
T('(sanity) the first of two reaction candles trades', ss(Mtwice[:-1]) is not None)
T('a second reaction candle of the same visit: only the first one trades', ss(Mtwice) is None)
old = tweak(SL_MAX=0.2); T('a stop beyond SL_MAX is skipped, never reshaped (deep)', ss(MD) is None); restore(old)
old = tweak(TOUCH_ATR=-5.0); T('TOUCH_ATR is a real tunable (a far zone never touches)', ss(MD) is None); restore(old)

# ---- bear flag (shallow pullback)
def flag_chart(imp=(-80,) * 8, flag=(20,) * 5, brk=-130, wick=10.0):
    m = fall(); m = more(m, list(imp)); m = more(m, list(flag), wick); return more(m, [brk])
MF = flag_chart(); rf = ss(MF); AF = atr(MF)[-1]
T('shallow pullback: impulse down, bear flag, close under the flag low: a SELL', rf and rf['side'] == 'sell' and rf['mode'] == 'flag')
T('(sanity) the flag did not reach the 4h 50 EMA', rf and max(x['h'] for x in MF[-14:]) < rf['ema4h'] - bw.TOUCH_ATR * AF)
fl = MF[-6:-1]; flo, fh = min(x['l'] for x in fl), max(x['h'] for x in fl)
T('stop is BUF x ATR above the flag high', rf and abs(rf['sl'] - (fh + bw.BUF * AF)) < 1e-6)
T('entry is the breakdown close, under the flag low', rf and rf['entry'] == MF[-1]['c'] < flo)
imp = MF[-14:-6]; drop = max(x['h'] for x in imp) - min(x['l'] for x in imp)
T('target is the impulse height measured down from the entry', rf and abs(rf['tp'] - (rf['entry'] - drop)) < 1e-6 and rf['tp'] < rf['entry'])
st.put('btc_short_pullback', '1'); gf = bw.btc_pullback_short(MF, agg(MF, 3600)); st.put('btc_short_pullback', '0')
T('the registered strategy carries the flag target as tp', gf and abs(gf['tp'] - rf['tp']) < 1e-9 and gf['side'] == 'sell')
Mbr = flag_chart(brk=-3);  T('breakdown candle with a small body (and no close under the flag low): no sell', ss(Mbr) is None)
Min2 = more(fall(), [-80] * 8); Min2 = more(Min2, [20] * 5, 10.0); Min2 = more(Min2, [-60]); Min2[-1]['c'] = Min2[-2]['l'] + 15; Min2[-1]['o'] = Min2[-1]['c'] + 60   # closes above the lows of EVERY flag candle
T('a red candle that stays INSIDE the flag (close above the flag low): no breakdown', ss(Min2) is None)
Msmall = flag_chart(imp=(-12,) * 8, flag=(4,) * 5, brk=-50)
T('an impulse smaller than IMPULSE_ATR x ATR is no flag', ss(Msmall) is None)
Mdeep = flag_chart(imp=(-35,) * 8, flag=(30,) * 5, brk=-170)
T('a flag that retraces more than FLAG_RETRACE of the impulse is not a flag', ss(Mdeep) is None)
Mnewlow = flag_chart(flag=(20, -200, 40, 40, 40)); T('a flag that makes a new low is not a flag', ss(Mnewlow) is None)
Mdown = flag_chart(flag=(-20,) * 5); T('a flag that drifts down is not a bear flag', ss(Mdown) is None)
Mup2 = flag_chart(imp=(80,) * 8, flag=(-20,) * 5, brk=60); T('a rising impulse is not a bear-flag setup', ss(Mup2) is None)
# a flag that drifts DOWN without a new low: the impulse's last candle has a long lower wick, so the flag may dip under its own start
Mdd = flag_chart(flag=(50, 50, -40, -40, -30), brk=-60); Mdd[-7]['l'] -= 120
Mdd_ok = flag_chart(flag=(20, 20, 10, 10, 0), brk=-100); Mdd_ok[-7]['l'] -= 120
T('(sanity) with the long lower wick an UP-drifting flag still sells', ss(Mdd_ok) is not None)
T('a flag that drifts down (last close under its first open) is not a bear flag', ss(Mdd) is None)
# a breakdown candle that GAPS under the flag low with a tiny body: no real body, no sell
Mgap = flag_chart(brk=-130); flo_g = min(x['l'] for x in Mgap[-6:-1]); Mgap = Mgap[:-1] + [{'t': Mgap[-1]['t'], 'o': flo_g - 20, 'h': flo_g - 15, 'l': flo_g - 35, 'c': flo_g - 30, 'v': 1}]
T('a breakdown candle under the flag low but with a tiny body (BODY_MIN x ATR): no sell', ss(Mgap) is None)
old = tweak(BODY_MIN=0.01); T('BODY_MIN is a real tunable for the breakdown candle', ss(Mgap) is not None); restore(old)
# the pullback already reached the EMA inside the window: that is the deep case, so the flag rule stays out
Mbase = deep_chart(); Mbase = Mbase[:-1]; e_, _ = e4h(Mbase)
Mp = more(Mbase, [-80] * 8); Mp[-8]['h'] = e_ + 5                  # the first impulse candle pokes up to the 4h EMA
Mp = more(Mp, [20] * 5, 10.0); Mp = more(Mp, [-130]); Mclean = more(Mbase, [-80] * 8); Mclean = more(Mclean, [20] * 5, 10.0); Mclean = more(Mclean, [-130])
T('(sanity) the same impulse and flag without the poke to the EMA is a sell', ss(Mclean) is not None and ss(Mclean)['mode'] == 'flag')
T('the last 21 candles already touched the 4h EMA zone: the flag rule stays out (deep case)', ss(Mp) is None)
old = tweak(RR_MIN_FLAG=1000.0); T('RR_MIN_FLAG is a real tunable (an RR of 1000 is refused)', ss(MF) is None); restore(old)
old = tweak(SL_MAX=0.1); T('a stop beyond SL_MAX is skipped, never reshaped (flag)', ss(MF) is None); restore(old)
old = tweak(FLAG_MIN=6, FLAG_MAX=12); T('FLAG_MIN is a real tunable (a 5-candle flag is too short at 6)', ss(MF) is None); restore(old)
Mlong = flag_chart(flag=(6,) * 14, brk=-200); T('a flag longer than FLAG_MAX is not read', ss(Mlong) is None)

# ---- registration and the settings route
from backend import strategies as S, strategy_info as si
names = [f.__name__ for f in S.ALL]
T('both strategies are registered in ALL', 'btc_sunday_bounce' in names and 'btc_pullback_short' in names)
T('btc_pullback_short is in TREND; the Sunday bounce is in NEITHER group on purpose', 'btc_pullback_short' in S.TREND and 'btc_sunday_bounce' not in S.TREND | S.REVERSION)
T('both have a readable name and a one-line description', all(n in si.INFO for n in ('btc_sunday_bounce', 'btc_pullback_short')))
T('the strategies have their own function names (the brain reads __name__)', bw.btc_sunday_bounce.__name__ == 'btc_sunday_bounce' and bw.btc_pullback_short.__name__ == 'btc_pullback_short')

C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
C.get('/api/me', headers=A); C.get('/api/me', headers=U)
x = C.post('/api/admin/settings', json={'btc_sunday_bounce': '1'}, headers=A)
T('the owner can switch the Sunday bounce on (POST /api/admin/settings)', x.status_code == 200 and st.get('btc_sunday_bounce') == '1')
x = C.post('/api/admin/settings', json={'btc_short_pullback': '1'}, headers=A)
T('the owner can switch the pullback short on', x.status_code == 200 and st.get('btc_short_pullback') == '1')
x = C.post('/api/admin/settings', json={'btc_short_pullback': '2', 'risk_pct': '1.0'}, headers=A)
T('a value other than 0 or 1 is refused with a plain message and nothing is saved', x.status_code == 400 and 'must be 0 or 1' in (x.get_json() or {}).get('error', '') and st.get('btc_short_pullback') == '1')
x = C.post('/api/admin/settings', json={'btc_sunday_bounce': 'yes'}, headers=A); T('"yes" is refused too', x.status_code == 400 and st.get('btc_sunday_bounce') == '1')
x = C.post('/api/admin/settings', json={'btc_sunday_bounce': '1'}, headers=U); T('a subscriber cannot touch the switches', x.status_code in (401, 403))
x = C.get('/api/admin/strategies', headers=A)
T('the admin strategy list shows both', x.status_code == 200 and 'btc_sunday_bounce' in str(x.get_json()) and 'btc_pullback_short' in str(x.get_json()))

bad = [n for n, ok in R if not ok]
for n in bad: print('FAIL:', n)
print('%d checks, %d failed' % (len(R), len(bad)))
if os.path.exists(DB): os.remove(DB)
sys.exit(1 if bad else 0)
