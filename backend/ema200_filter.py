"""Video 3 (Data Trader, moving average strategy) - SECTION 3C: the 200 EMA filter.
Rule from the video: price ABOVE the 200 EMA -> only buys, price BELOW it -> only sells. The video says this lifts the Parabolic SAR win rate (38% -> 46%) and
the Supertrend win rate (39% -> 48%). Those numbers are the video's claim, NOT proven here: only tools/backtest.py --solo on real data can say.
What is in this file:
  with_ema200(fn, name, skip_if)  wraps ANY strategy: a buy is dropped unless the last close is above the 200 EMA, a sell unless it is below.
  psar_raw        Parabolic SAR flip with NO trend gate of its own (the existing psar_flip already has a 50/200 trend gate, so wrapping it would change nothing).
  supertrend_flip Supertrend (ATR 10, x3) changes direction. New indicator, kept here because indicators.py must not be edited.
Registered in strategies.py as psar_e200 and supertrend_e200 (TREND group). psar_e200 is told to stay silent when psar_flip fires on the same candle,
so one SAR flip never counts as two votes in the brain's confluence. The 200 EMA is read on the main (15-minute) chart: the video gives no chart, so that is my assumption."""
from .indicators import ema, atr, psar

EMA_LEN = 200            # the filter line
MIN_BARS = 220           # history needed: 200 EMA plus warm-up
ST_N, ST_MULT = 10, 3.0  # Supertrend settings (the usual 10 / 3)
SL_MIN_ATR = 0.8         # supertrend stop is kept between these many 15-minute ATR from entry, so the brain (0.5 to 3.5 ATR) accepts it
SL_MAX_ATR = 3.0

def with_ema200(fn, name=None, skip_if=()):
    nm = name or fn.__name__ + '_e200'
    def wrapped(m, h):
        if len(m) < MIN_BARS: return None
        r = fn(m, h)
        if not r: return None
        e = ema([x['c'] for x in m], EMA_LEN)[-1]; c = m[-1]['c']
        if r['side'] == 'buy' and not c > e: return None       # below the 200 EMA: no buys
        if r['side'] == 'sell' and not c < e: return None      # above the 200 EMA: no sells
        for other in skip_if:                                  # another strategy already votes for this same signal
            if other(m, h): return None
        return dict(r, name=nm)
    wrapped.__name__ = nm
    return wrapped

def supertrend(b, n=ST_N, mult=ST_MULT):
    """-> [(line, dir)] with dir +1 (line under price, uptrend) or -1. Standard Supertrend."""
    a = atr(b, n); out = []; fu = fl = 0.0; d = 1
    for i, x in enumerate(b):
        mid = (x['h'] + x['l']) / 2; up, lo = mid + mult * a[i], mid - mult * a[i]
        if i == 0: fu, fl = up, lo
        else:
            pc = b[i - 1]['c']; pfu, pfl = fu, fl
            fu = up if (up < pfu or pc > pfu) else pfu
            fl = lo if (lo > pfl or pc < pfl) else pfl
            if d < 0 and x['c'] > pfu: d = 1
            elif d > 0 and x['c'] < pfl: d = -1
        out.append((fl if d > 0 else fu, d))
    return out

def psar_raw(m, h):
    if len(m) < MIN_BARS: return None
    s = psar(m[-120:]); a = atr(m)[-1]
    if s[-2][1] < 0 < s[-1][1]: return {'side': 'buy', 'sl': min(s[-1][0], min(x['l'] for x in m[-4:])) - 0.1 * a, 'name': 'psar_raw'}
    if s[-2][1] > 0 > s[-1][1]: return {'side': 'sell', 'sl': max(s[-1][0], max(x['h'] for x in m[-4:])) + 0.1 * a, 'name': 'psar_raw'}

def supertrend_flip(m, h):
    if len(m) < MIN_BARS: return None
    s = supertrend(m[-150:]); a = atr(m)[-1]; e = m[-1]['c']
    if not a: return None
    if s[-2][1] < 0 < s[-1][1]: return {'side': 'buy', 'sl': e - min(max(e - s[-1][0], SL_MIN_ATR * a), SL_MAX_ATR * a), 'name': 'supertrend_flip'}
    if s[-2][1] > 0 > s[-1][1]: return {'side': 'sell', 'sl': e + min(max(s[-1][0] - e, SL_MIN_ATR * a), SL_MAX_ATR * a), 'name': 'supertrend_flip'}
