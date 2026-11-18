"""Video 3 (Data Trader, moving average strategy) - SECTION 3A: the 20/50 crossover, traded the careful way.
Rules from the video: only TWO moving averages (20 and 50) | use a HIGH time frame (daily, or 1 hour at the lowest) - lower frames are mostly range |
the market must be TRENDING (in a range the crossover gives false signals) | only trade a market that has a HISTORY of following its crossovers |
fast crosses above slow -> buy, fast crosses below slow -> sell | exit: ATR trailing stop (not coded yet - see docs/HANDOFF.md, section 3D); until then the stop is ATR-based and the brain's 2R target applies.
Time frame: the cross is read on the 1-hour candles (h) and fires on the 15-minute candle that closes together with that hour. If the main chart is already 1 hour or higher it is used directly.
Only COMPLETED higher-time-frame candles are used (no peeking at the hour that is still forming). The video gives no numbers: the tunables below are my assumptions."""
from .indicators import ema, atr, adx

FAST, SLOW = 20, 50
ADX_MIN = 20.0          # trending only: the higher-time-frame ADX must be at least this
REACT_BARS = 8          # a past cross 'reacted' if price, this many candles later, is beyond the cross close in the cross direction
REACT_RATIO = 0.6       # ...and at least this share of the past crosses reacted
MIN_CROSSES = 3         # need at least this many past crosses to judge the market's history (fewer = unproven = no trade)
HIST_CROSSES = 8        # look at this many most recent past crosses
SL_ATR = 1.5            # stop = this many higher-time-frame ATR from the entry (never wider than 3 M15 ATR so the brain accepts it)
HTF_MIN = 3600          # a chart with candles at least this long (seconds) is used as the higher time frame itself

def _crosses(c):
    """[(index, +1|-1)] where the fast EMA crossed the slow EMA, on candle index (cross seen at that candle's close)."""
    f, s = ema(c, FAST), ema(c, SLOW); out = []
    for i in range(SLOW + 1, len(c)):
        if f[i - 1] <= s[i - 1] and f[i] > s[i]: out.append((i, 1))
        elif f[i - 1] >= s[i - 1] and f[i] < s[i]: out.append((i, -1))
    return out

def _htf(m, h):
    """(completed higher-time-frame candles, True if the trigger is exactly the candle that just closed) or (None, False)."""
    if len(m) < 2: return None, False
    step = m[-1]['t'] - m[-2]['t']
    if step >= HTF_MIN: return m, True
    if not h or len(h) < SLOW + 20: return None, False
    end = m[-1]['t'] + step                                   # end of the current (closed) lower-time-frame candle
    done = [x for x in h if x['t'] + HTF_MIN <= end]
    if len(done) < SLOW + 20: return None, False
    gap = end - (done[-1]['t'] + HTF_MIN)                    # how long ago the last higher-time-frame candle closed
    return done, 0 <= gap < step

def ma_cross(m, h):
    H, fresh = _htf(m, h)
    if not H or not fresh: return None
    c = [x['c'] for x in H]; cr = _crosses(c)
    if not cr or cr[-1][0] != len(c) - 1: return None          # the cross must be on the candle that just closed
    i, d = cr[-1]
    ax = adx(H)[-1]
    if not ax or ax < ADX_MIN: return None                      # not trending -> stay out
    past = [(k, dd) for k, dd in cr[:-1] if k + REACT_BARS <= len(c) - 2][-HIST_CROSSES:]
    if len(past) < MIN_CROSSES: return None                     # no history to judge
    if sum(1 for k, dd in past if (c[k + REACT_BARS] - c[k]) * dd > 0) / len(past) < REACT_RATIO: return None   # this market does not follow its crossovers
    am = atr(m)[-1]; ah = atr(H)[-1]
    if not am or not ah: return None
    dist = min(SL_ATR * ah, 3.0 * am); e = m[-1]['c']
    if d > 0: return {'side': 'buy', 'sl': e - dist, 'name': 'ma_cross'}
    return {'side': 'sell', 'sl': e + dist, 'name': 'ma_cross'}
