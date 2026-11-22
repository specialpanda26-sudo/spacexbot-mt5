"""Rule-based entries. Each returns {'side','sl','name'} or None. Inputs: closed candles
(dicts t,o,h,l,c,v; t = UTC epoch). Concepts follow the Tania PDF (S/R retest, FVG, trend,
2+ reasons) and quant-trading (London breakout, Bollinger, RSI)."""
import datetime as dt
from .indicators import ema, rsi, atr, bollinger, swings, macd as _macd, psar as _psar, heikin as _heikin

def _trend(m, h):
    c = [x['c'] for x in m]
    e50, e200 = ema(c, 50)[-1], ema(c, 200)[-1]
    up, dn = e50 > e200 and c[-1] > e200, e50 < e200 and c[-1] < e200
    if len(h) >= 200:
        hc = [x['c'] for x in h]; a, b = ema(hc, 50)[-1], ema(hc, 200)[-1]
        up &= a > b; dn &= a < b
    return up, dn

def ema_pullback(m, h):
    if len(m) < 220: return None
    c = [x['c'] for x in m]; e21 = ema(c, 21)[-1]; r = rsi(c)[-1]; a = atr(m)[-1]; b = m[-1]
    up, dn = _trend(m, h)
    if up and min(x['l'] for x in m[-4:]) <= e21 + 0.2 * a and b['c'] > b['o'] and b['c'] > e21 and 45 < r < 68:
        return {'side': 'buy', 'sl': min(x['l'] for x in m[-6:]) - 0.2 * a, 'name': 'ema_pullback'}
    if dn and max(x['h'] for x in m[-4:]) >= e21 - 0.2 * a and b['c'] < b['o'] and b['c'] < e21 and 32 < r < 55:
        return {'side': 'sell', 'sl': max(x['h'] for x in m[-6:]) + 0.2 * a, 'name': 'ema_pullback'}

def sr_retest(m, h):
    """Level touched 2+ times, broken by a close, then retested and rejected (PDF sections 3-4)."""
    if len(m) < 120: return None
    a = atr(m)[-1]; tol = 0.5 * a; w = m[-150:]; n = len(w)
    pts = [p for i, p, _ in swings(w) if i < n - 6]
    levels = []
    for p in sorted(pts):
        if levels and abs(p - levels[-1][0]) < tol:
            levels[-1][1].append(p); levels[-1][0] = sum(levels[-1][1]) / len(levels[-1][1])
        else: levels.append([p, [p]])
    b = w[-1]
    for L, ps in levels:
        if len(ps) < 2: continue
        for k in range(n - 30, n - 3):
            pc, cc = w[k - 1]['c'], w[k]['c']
            if pc < L < cc and all(x['c'] > L - tol for x in w[k + 1:]) and b['l'] <= L + tol and b['c'] > L and b['c'] > b['o']:
                return {'side': 'buy', 'sl': min(x['l'] for x in w[-5:]) - 0.2 * a, 'name': 'sr_retest'}
            if pc > L > cc and all(x['c'] < L + tol for x in w[k + 1:]) and b['h'] >= L - tol and b['c'] < L and b['c'] < b['o']:
                return {'side': 'sell', 'sl': max(x['h'] for x in w[-5:]) + 0.2 * a, 'name': 'sr_retest'}

def fvg_retrace(m, h):
    """Fair value gap in trend direction; price returns into the gap and rejects (PDF FVG page)."""
    if len(m) < 220: return None
    a = atr(m)[-1]; b = m[-1]; up, dn = _trend(m, h); n = len(m)
    for i in range(n - 2, n - 40, -1):
        c0, c2 = m[i - 2], m[i]
        if up and c2['l'] - c0['h'] >= 0.3 * a:
            lo, hi = c0['h'], c2['l']
            if all(x['c'] > lo for x in m[i + 1:]) and b['l'] <= hi and b['c'] > (lo + hi) / 2 and b['c'] > b['o']:
                return {'side': 'buy', 'sl': lo - 0.2 * a, 'name': 'fvg_retrace'}
        if dn and c0['l'] - c2['h'] >= 0.3 * a:
            lo, hi = c2['h'], c0['l']
            if all(x['c'] < hi for x in m[i + 1:]) and b['h'] >= lo and b['c'] < (lo + hi) / 2 and b['c'] < b['o']:
                return {'side': 'sell', 'sl': hi + 0.2 * a, 'name': 'fvg_retrace'}

def london_breakout(m, h):
    """Asian range 00-07 UTC, first close beyond it 07-10 UTC (quant-trading London Breakout)."""
    if len(m) < 60: return None
    b = m[-1]; t = dt.datetime.utcfromtimestamp(b['t'])
    if not (7 <= t.hour < 10): return None
    day = t.date()
    rng = [x for x in m if dt.datetime.utcfromtimestamp(x['t']).date() == day and dt.datetime.utcfromtimestamp(x['t']).hour < 7]
    if len(rng) < 12: return None
    hi, lo = max(x['h'] for x in rng), min(x['l'] for x in rng); a = atr(m)[-1]
    if not (0.5 * a <= hi - lo <= 5 * a): return None
    p = m[-2]['c']
    if b['c'] > hi and p <= hi: return {'side': 'buy', 'sl': (hi + lo) / 2, 'name': 'london_breakout'}
    if b['c'] < lo and p >= lo: return {'side': 'sell', 'sl': (hi + lo) / 2, 'name': 'london_breakout'}

def bb_reversion(m, h):
    if len(m) < 60: return None
    c = [x['c'] for x in m]; mid, up, lo = bollinger(c); r = rsi(c); a = atr(m)[-1]; b, p = m[-1], m[-2]
    if p['c'] < lo[-2] and b['c'] > lo[-1] and b['c'] > b['o'] and r[-1] < 42:
        return {'side': 'buy', 'sl': min(p['l'], b['l']) - 0.2 * a, 'name': 'bb_reversion'}
    if p['c'] > up[-2] and b['c'] < up[-1] and b['c'] < b['o'] and r[-1] > 58:
        return {'side': 'sell', 'sl': max(p['h'], b['h']) + 0.2 * a, 'name': 'bb_reversion'}



def macd_cross(m, h):
    """MACD histogram crosses zero in the direction of the EMA50/200 trend (quant-trading MACD)."""
    if len(m) < 220: return None
    c = [x['c'] for x in m]; _, _, hist = _macd(c); a = atr(m)[-1]; up, dn = _trend(m, h)
    if up and hist[-2] <= 0 < hist[-1]: return {'side': 'buy', 'sl': min(x['l'] for x in m[-8:]) - 0.2 * a, 'name': 'macd_cross'}
    if dn and hist[-2] >= 0 > hist[-1]: return {'side': 'sell', 'sl': max(x['h'] for x in m[-8:]) + 0.2 * a, 'name': 'macd_cross'}

def heikin_flip(m, h):
    """Heikin-Ashi colour flip with no wick on the new candle's open side (quant-trading Heikin-Ashi), with the trend."""
    if len(m) < 220: return None
    ha = _heikin(m[-60:]); a = atr(m)[-1]; up, dn = _trend(m, h); p, b = ha[-2], ha[-1]; tol = 0.05 * a
    if up and p['c'] < p['o'] and b['c'] > b['o'] and abs(b['o'] - b['l']) <= tol:
        return {'side': 'buy', 'sl': min(x['l'] for x in m[-6:]) - 0.2 * a, 'name': 'heikin_flip'}
    if dn and p['c'] > p['o'] and b['c'] < b['o'] and abs(b['h'] - b['o']) <= tol:
        return {'side': 'sell', 'sl': max(x['h'] for x in m[-6:]) + 0.2 * a, 'name': 'heikin_flip'}

def psar_flip(m, h):
    """Parabolic SAR just flipped, in the direction of the higher trend (quant-trading Parabolic SAR)."""
    if len(m) < 220: return None
    s = _psar(m[-120:]); a = atr(m)[-1]; up, dn = _trend(m, h)
    if up and s[-2][1] < 0 < s[-1][1]: return {'side': 'buy', 'sl': min(s[-1][0], min(x['l'] for x in m[-4:])) - 0.1 * a, 'name': 'psar_flip'}
    if dn and s[-2][1] > 0 > s[-1][1]: return {'side': 'sell', 'sl': max(s[-1][0], max(x['h'] for x in m[-4:])) + 0.1 * a, 'name': 'psar_flip'}

def awesome_osc(m, h):
    """AO zero-line cross or 'saucer' continuation, with the trend (quant-trading Awesome Oscillator)."""
    if len(m) < 220: return None
    mid = [(x['h'] + x['l']) / 2 for x in m]; f, s = ema(mid, 5), ema(mid, 34); ao = [a - b for a, b in zip(f, s)]
    a = atr(m)[-1]; up, dn = _trend(m, h)
    if up and (ao[-2] <= 0 < ao[-1] or (ao[-1] > ao[-2] < ao[-3] and min(ao[-3:]) > 0)):
        return {'side': 'buy', 'sl': min(x['l'] for x in m[-8:]) - 0.2 * a, 'name': 'awesome_osc'}
    if dn and (ao[-2] >= 0 > ao[-1] or (ao[-1] < ao[-2] > ao[-3] and max(ao[-3:]) < 0)):
        return {'side': 'sell', 'sl': max(x['h'] for x in m[-8:]) + 0.2 * a, 'name': 'awesome_osc'}

def dual_thrust(m, h):
    """Break of today's open +/- 0.5 x the prior-2-day range (quant-trading Dual Thrust). 07-17 UTC only."""
    if len(m) < 300: return None
    b, p = m[-1], m[-2]; t = dt.datetime.utcfromtimestamp(b['t'])
    if not (7 <= t.hour < 17): return None
    day = lambda x: dt.datetime.utcfromtimestamp(x['t']).date()
    today = [x for x in m if day(x) == t.date()]
    if len(today) < 8: return None
    prior_days = sorted({day(x) for x in m if day(x) < t.date()})[-2:]
    prior = [x for x in m if day(x) in prior_days]
    if len(prior) < 100: return None
    rng = max(max(x['h'] for x in prior) - min(x['c'] for x in prior), max(x['c'] for x in prior) - min(x['l'] for x in prior))
    a = atr(m)[-1]
    if not (0.8 * a <= 0.5 * rng <= 12 * a): return None
    o = today[0]['o']; up_, lo_ = o + 0.5 * rng, o - 0.5 * rng
    if b['c'] > up_ >= p['c']: return {'side': 'buy', 'sl': max(o, b['c'] - 3 * a), 'name': 'dual_thrust'}
    if b['c'] < lo_ <= p['c']: return {'side': 'sell', 'sl': min(o, b['c'] + 3 * a), 'name': 'dual_thrust'}

def star_reversal(m, h):
    """Shooting star at a 10-bar high with RSI stretched / hammer at a 10-bar low (quant-trading Shooting Star)."""
    if len(m) < 60: return None
    c = [x['c'] for x in m]; r = rsi(c)[-1]; a = atr(m)[-1]; b = m[-1]; body = abs(b['c'] - b['o']) or 1e-9
    top, bot = max(b['o'], b['c']), min(b['o'], b['c']); uw, lw = b['h'] - top, bot - b['l']
    if uw >= 2 * body and lw <= 0.3 * body and b['h'] >= max(x['h'] for x in m[-11:-1]) and r > 62 and b['h'] - b['l'] >= 0.6 * a:
        return {'side': 'sell', 'sl': b['h'] + 0.2 * a, 'name': 'star_reversal'}
    if lw >= 2 * body and uw <= 0.3 * body and b['l'] <= min(x['l'] for x in m[-11:-1]) and r < 38 and b['h'] - b['l'] >= 0.6 * a:
        return {'side': 'buy', 'sl': b['l'] - 0.2 * a, 'name': 'star_reversal'}

from .jg_pullback import jg_pullback
from .pa_structure import pa_bos; from .pa_level import pa_level; from .pa_candle import pa_candle; from .pa_pattern import pa_pattern; from .pa_trendline import pa_trendline; from .ma_cross import ma_cross; from .ma_bounce import ma_bounce
from .ema200_filter import with_ema200, psar_raw, supertrend_flip
from .gold_scalp import gold_scalp
from .gold_scalp_c import gold_scalp_c
from .orb_entry import orb_entry
from .orb_session import orb_session
from .btc_range import btc_range
from .btc_weekend import btc_sunday_bounce, btc_pullback_short
psar_e200 = with_ema200(psar_raw, 'psar_e200', skip_if=(psar_flip,)); supertrend_e200 = with_ema200(supertrend_flip, 'supertrend_e200')
ALL = [pa_level, pa_bos, pa_candle, pa_pattern, pa_trendline, ma_cross, ma_bounce, psar_e200, supertrend_e200, gold_scalp, gold_scalp_c, orb_entry, orb_session, btc_range, btc_sunday_bounce, btc_pullback_short, jg_pullback, ema_pullback, sr_retest, fvg_retrace, london_breakout, bb_reversion, macd_cross, heikin_flip, psar_flip, awesome_osc, dual_thrust, star_reversal]
# regime groups: reversion setups are skipped in strong trends; trend setups are skipped in dead ranges
REVERSION = {'bb_reversion', 'star_reversal'}
TREND = {'pa_level', 'jg_pullback', 'ema_pullback', 'fvg_retrace', 'macd_cross', 'heikin_flip', 'psar_flip', 'dual_thrust', 'london_breakout', 'ma_cross', 'ma_bounce', 'psar_e200', 'supertrend_e200', 'gold_scalp', 'gold_scalp_c', 'orb_entry', 'orb_session', 'btc_range', 'btc_pullback_short'}

try:
    from . import taught; taught.load(ALL, REVERSION, TREND)
except Exception as e: print('taught strategies not loaded:', e)
