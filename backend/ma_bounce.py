"""Video 3 (Data Trader) - SECTION 3B: the moving average as dynamic support / resistance, confirmed by the stochastic.
Rules from the video: the MA must be acting as support (or resistance): price came down to it and bounced MULTIPLE times before |
when price is back at the MA while the stochastic is OVERSOLD -> buy (support) | back at the MA while the stochastic is OVERBOUGHT -> sell (resistance).
The video does not say which MA or give numbers: MA_LEN and all tunables below are my assumptions. The mirror (resistance) is the same code run on negated prices
(a negated stochastic is 100 minus the real one, so 'oversold' there is 'overbought' here). Trades only with the MA's slope (support needs a rising MA)."""
from .indicators import ema, atr
from .stoch import stoch

MA_LEN = 50
LOOKBACK = 150          # look for past bounces this many candles back
MIN_BOUNCES = 2         # video: 'multiple times' -> at least this many earlier bounces off the MA
BOUNCE_BARS = 10        # a touch counts as a bounce if price rose this far within this many candles
BOUNCE_ATR = 1.5        # ...by at least this many ATR
SEP = 4                 # touches closer together than this many candles count as one
REACH = 0.5             # the candle must come within this many ATR of the MA
PIERCE = 0.5            # its wick may poke at most this many ATR through the MA (it must close back above)
OS = 20.0               # oversold: the stochastic %K was at or below this ...
STOCH_LOOK = 3          # ... at some point in the last this-many candles
SLOPE_BARS = 10         # the MA must be rising over this many candles (support) - falling for resistance
MIN_SLOPE = 0.0         # ...by more than this many ATR over those candles
BUF = 0.1               # stop buffer, ATR
WINDOW = 300

def _neg(w): return [{'t': x['t'], 'o': -x['o'], 'h': -x['l'], 'l': -x['h'], 'c': -x['c'], 'v': x.get('v', 1)} for x in w]

def _touch(x, ma, a): return x['l'] <= ma + REACH * a and x['l'] >= ma - PIERCE * a and x['c'] > ma

def _bounces(w, ma, A):
    """indexes of earlier candles that touched the MA from above and were followed by a real bounce"""
    n = len(w); out = []
    for i in range(max(MA_LEN, n - 1 - LOOKBACK), n - 1 - BOUNCE_BARS):
        if out and i - out[-1] < SEP: continue
        if _touch(w[i], ma[i], A[i]) and max(x['h'] for x in w[i + 1: i + 1 + BOUNCE_BARS]) - w[i]['c'] >= BOUNCE_ATR * A[i]: out.append(i)
    return out

def _side(w):
    """buy signal on the last candle of w (support case), or None."""
    n = len(w)
    if n < MA_LEN + SLOPE_BARS + 5: return None
    c = [x['c'] for x in w]; ma = ema(c, MA_LEN); A = atr(w); a = A[-1]; b = w[-1]
    if not a or ma[-1] - ma[-1 - SLOPE_BARS] <= MIN_SLOPE * a: return None                        # the MA must be rising
    if not _touch(b, ma[-1], a) or b['c'] <= b['o']: return None                 # reaches the MA, closes above it, bullish candle
    if any(_touch(x, ma[n - 4 + j], a) or x['l'] <= ma[n - 4 + j] for j, x in enumerate(w[-4:-1])): return None   # not the first candle at the MA
    if len(_bounces(w, ma, A)) < MIN_BOUNCES: return None                         # the MA has not proven itself as support
    K, _ = stoch(w)
    if min(K[-STOCH_LOOK:]) > OS: return None                                     # stochastic must be oversold
    return {'side': 'buy', 'sl': min(b['l'], ma[-1]) - BUF * a, 'name': 'ma_bounce'}

def ma_bounce(m, h):
    if len(m) < MA_LEN + 40: return None
    w = m[-WINDOW:]; r = _side(w)
    if r: return r
    r = _side(_neg(w))
    if r: return {'side': 'sell', 'sl': -r['sl'], 'name': 'ma_bounce'}
