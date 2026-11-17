"""Video 1 (Jason Graystone, Trading for Beginners Part 1): trend-pullback 'lower low, lower close' setup.
Runs on whatever candles the bot feeds it (closed candles). Sell side below; buy side is the mirror.
Rules (from the video):  1 downtrend (lower highs + lower lows)  2 last run = swing high -> swing low
3 pullback after the run  4 trigger = first candle in the pullback that makes a lower low AND closes below the previous candle's low
5 stop above the pullback high  6 target at the lowest close of the run  7 one trade per pullback (new low needed before the next)
Things the bot cannot do, so approximated (see NOTES): pending sell-stop entry -> enters at the trigger candle close;
'2 pips' buffer -> BUF x ATR so it works on gold and FX alike. All numbers below are tunable."""
from .indicators import atr, swings

LEFT = RIGHT = 3        # swing sensitivity
BUF = 0.1               # stop / target buffer, in ATR (video: 2 pips)
MIN_BARS = 2            # bars between the swing point and the trigger (a real pullback, not 1 candle)
MIN_DEPTH = 1.0         # pullback must retrace at least this many ATR (my assumption, not in the video)
MIN_RR = 1.5            # skip if target is closer than this x stop distance (my assumption, not in the video)
WINDOW = 200
SOLO = False            # False: needs another strategy to agree (bot's confluence rule). True: may trade alone. Backtest first.

def _side(w, a, bear):
    """bear=True looks for a short. Returns {'side','sl','tp','name'} or None."""
    n = len(w); sw = swings(w, LEFT, RIGHT)
    ext, opp = ('L', 'H') if bear else ('H', 'L')            # ext = swing the run ended on, opp = swing it started from
    e = [s for s in sw if s[2] == ext]; o = [s for s in sw if s[2] == opp]
    if len(e) < 2 or len(o) < 2: return None
    iE, pE, _ = e[-1]; starts = [s for s in o if s[0] < iE]
    if len(starts) < 2: return None
    iS, pS, _ = starts[-1]
    # trend: lower highs + lower lows (bear) / higher highs + higher lows (bull)
    if bear and not (pE < e[-2][1] and pS < starts[-2][1]): return None
    if not bear and not (pE > e[-2][1] and pS > starts[-2][1]): return None
    run = w[iS:iE + 1]; after = w[iE + 1:]
    if len(after) < MIN_BARS + 1: return None
    b, p = w[-1], w[-2]
    if bear:
        if min(x['l'] for x in after) < pE: return None                       # new low already made -> that is a new run
        ph = max(x['h'] for x in after)
        if ph - pE < MIN_DEPTH * a: return None
        trig = lambda x, y: x['l'] < y['l'] and x['c'] < y['l']
        if not trig(b, p): return None
        if any(trig(after[k], after[k - 1]) for k in range(1, len(after) - 1)): return None   # not the first trigger of this pullback
        e0 = b['c']; sl = ph + BUF * a; tp = min(x['c'] for x in run) + BUF * a
        if not (tp < e0 < sl) or (e0 - tp) < MIN_RR * (sl - e0): return None
        return {'side': 'sell', 'sl': sl, 'tp': tp, 'name': 'jg_pullback', **({'solo': True} if SOLO else {})}
    if max(x['h'] for x in after) > pE: return None
    pl = min(x['l'] for x in after)
    if pE - pl < MIN_DEPTH * a: return None
    trig = lambda x, y: x['h'] > y['h'] and x['c'] > y['h']
    if not trig(b, p): return None
    if any(trig(after[k], after[k - 1]) for k in range(1, len(after) - 1)): return None
    e0 = b['c']; sl = pl - BUF * a; tp = max(x['c'] for x in run) - BUF * a
    if not (sl < e0 < tp) or (tp - e0) < MIN_RR * (e0 - sl): return None
    return {'side': 'buy', 'sl': sl, 'tp': tp, 'name': 'jg_pullback', **({'solo': True} if SOLO else {})}

def jg_pullback(m, h):
    if len(m) < 60: return None
    w = m[-WINDOW:]; a = atr(w)[-1]
    if not a: return None
    return _side(w, a, True) or _side(w, a, False)
