"""BTC Section 6B - two OPTIONAL weekend rules from the owner's videos 2 and 3. Both are OFF until the owner turns them on:
  setting btc_sunday_bounce = 1   -> strategy btc_sunday_bounce
  setting btc_short_pullback = 1  -> strategy btc_pullback_short
Neither video gives usable numbers (dated price levels, an order book we do not have), so every tunable below is an ASSUMPTION. Not proven: only tools/backtest.py --solo on real BTC candles can say.

1) btc_sunday_bounce (video 2, Sunday-open bounce, BUY only)
   After a big Friday sell-off, draw the fib from the Friday high down to the Friday low. In the first hours after the Sunday open look for a bounce toward 0.382 (TP) and 0.5 (tp2, setup() only).
   - Friday (UTC day) H1 candles: the high must come BEFORE the low, and the drop must be at least DROP_PCT of the high. Fewer than MIN_FRI_BARS H1 candles of that Friday = no setup.
   - Window: Sunday from OPEN_HOUR (UTC) for WINDOW_H hours (CME futures open Sunday 22:00 UTC in summer; Bitcoin has no real open, so this is an assumption). Nothing fires outside it.
   - Entry = the FIRST green candle in the window with a real body (BODY_MIN x 15m ATR) that closes below the 0.382 level. Stand down (video: "he left when it chopped"): when any Sunday candle closed under the Friday low,
     when the 0.382 level was already touched in the window, or when an earlier candle of the window already qualified.
   - Stop under the lowest low of the window, BUF x ATR further; stop must be 0.5-3.5 ATR away (the brain's rule) and the reward to 0.382 at least RR_MIN. Take profit fast = 0.382.
   - NOT coded: stop to break-even after the first move (the EA / brain manage exits), the order-book reading, a sell version after a Friday rally (the video does not show one).
2) btc_pullback_short (video 3, short-or-do-nothing, SELL only)
   Bias down = the last closed 4h candle is under its 4h 50 EMA and that EMA is falling over SLOPE_BARS 4h candles (4h candles are grouped from the 1h candles). Never short the lows: with the bias down a sell fires only after a pullback:
   - DEEP pullback (price came back up to the 4h 50 EMA): sell into strength = the FIRST red candle with a real body that touched the EMA zone (EMA minus TOUCH_ATR x ATR) and closed back under the EMA. Stop above the pullback high. No own target (the brain uses its 2R).
   - SHALLOW pullback (never reached the EMA): wait for the bear-flag breakdown. Impulse = IMP_BARS 15m candles whose high-to-low range is at least IMPULSE_ATR x ATR; flag = FLAG_MIN..FLAG_MAX candles after it that retrace at most
     FLAG_RETRACE of the impulse, never make a new low and drift up; breakdown = a red candle with a real body that closes under the flag low. Stop above the flag high; target = the impulse height measured from the entry (needs RR_MIN).
   - A straight waterfall with no pullback and no flag fires nothing.
   - The stock-market link from the video cannot be read by this bot. Strategies do not see the symbol, so the switch is global: it also runs on gold or forex candles (gold and forex are shut on weekends anyway, the Sunday rule is BTC-only in practice).
Both are generic (they work on any 15-minute candles with 1-hour candles beside them) and are registered by apply_btc6b.py: btc_pullback_short in TREND, btc_sunday_bounce in NEITHER group (a bounce after a sell-off is a counter-move in a strong trend, the REVERSION regime filter would silence it). Neither is SOLO."""
import datetime as dt
from .indicators import atr, ema

# ---- Sunday-open bounce (assumptions)
DROP_PCT = 3.0             # the Friday high-to-low fall must be at least this many percent of the high
MIN_FRI_BARS = 20          # of the 24 Friday H1 candles
OPEN_HOUR = 22             # UTC hour of the Sunday open
WINDOW_H = 2               # hours after the open in which the bounce may be bought (22:00 to midnight UTC: the rule is Sunday only, so a window cannot run into Monday)
FIB_TP, FIB_TP2 = 0.382, 0.5
BODY_MIN = 0.3             # the reaction candle body must be at least this many 15m ATR
BUF = 0.1                  # stop buffer, 15m ATR
SL_MIN, SL_MAX = 0.5, 3.5  # the brain's accepted stop distance, 15m ATR
RR_MIN = 1.0               # the bounce is a quick trade: TP at 0.382 must pay at least this many times the stop
# ---- pullback short (assumptions)
EMA_LEN = 50               # the 4h moving average (EMA, same kind as ma_bounce)
MIN_4H = 60                # 4h candles needed (50 plus warm-up) = 240 H1 candles
SLOPE_BARS = 6             # the 4h EMA must be lower than this many 4h candles ago
TOUCH_ATR = 0.5            # price within this many 15m ATR under the EMA counts as touching it
TOUCH_BARS = 8             # the pullback high is looked for in this many 15m candles
IMP_BARS = 8               # impulse length, 15m candles
IMPULSE_ATR = 4.0          # the impulse must fall at least this many 15m ATR
FLAG_MIN, FLAG_MAX = 3, 12 # flag length, 15m candles
FLAG_RETRACE = 0.5         # the flag may give back at most this share of the impulse
SOLO = False

def on(key):
    """The switch lives in the store (default '0'). Anything wrong reading it = OFF."""
    try:
        from . import store as st
        return str(st.get(key)) == '1'
    except Exception:
        return False

def _group4h(h, end):
    from .btc_range import _group
    return _group(h, 3600, 14400, end) if h else []

# ------------------------------------------------------------ 1) Sunday-open bounce
def friday_range(h, sunday_t):
    """(high, low, fri_candles) of the Friday that precedes the Sunday of sunday_t, or None. The low must come after the high and the fall must be big."""
    fri0 = sunday_t - sunday_t % 86400 - 2 * 86400                       # the UTC day two days before that Sunday
    fri = [x for x in h if fri0 <= x['t'] < fri0 + 86400]
    if len(fri) < MIN_FRI_BARS: return None
    hi = max(x['h'] for x in fri); lo = min(x['l'] for x in fri)
    ih = max(i for i, x in enumerate(fri) if x['h'] == hi); il = min(i for i, x in enumerate(fri) if x['l'] == lo)
    if il <= ih: return None                                              # the high must come first: a sell-off, not a rally
    if (hi - lo) / hi * 100 < DROP_PCT: return None
    return hi, lo

def sunday_setup(m, h):
    """Full bounce setup on the last 15m candle, or None: {'side','entry','sl','tp','tp2','friday':(lo,hi),'rr'}."""
    if len(m) < 40 or m[-1]['t'] - m[-2]['t'] != 900: return None
    b = m[-1]
    if dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).weekday() != 6: return None                                      # Sunday only
    sun0 = b['t'] - b['t'] % 86400; w0 = sun0 + OPEN_HOUR * 3600
    if not (w0 <= b['t'] < w0 + WINDOW_H * 3600): return None
    fr = friday_range(h, b['t'])
    if not fr: return None
    hi, lo = fr; R = hi - lo; t1 = lo + FIB_TP * R; t2 = lo + FIB_TP2 * R
    a = atr(m)[-1]
    if not a: return None
    sunday = [x for x in m if sun0 <= x['t'] <= b['t']]; win = [x for x in sunday if x['t'] >= w0]
    if any(x['c'] < lo for x in sunday): return None                      # the sell-off continues: no bounce
    if any(x['h'] >= t1 for x in win): return None                        # the bounce already happened
    def react(x): return x['c'] - x['o'] >= BODY_MIN * a                   # green with a real body (it is under 0.382 because no window candle touched it)
    if not react(b): return None
    if any(react(x) for x in win[:-1]): return None                       # first reaction only: it chopped, stand down
    e = b['c']; sl = min(x['l'] for x in win) - BUF * a; dist = e - sl
    if not (SL_MIN * a <= dist <= SL_MAX * a): return None
    if (t1 - e) / dist < RR_MIN: return None
    return {'side': 'buy', 'entry': e, 'sl': sl, 'tp': t1, 'tp2': t2, 'friday': (lo, hi), 'rr': (t1 - e) / dist}

def btc_sunday_bounce(m, h):
    """Registered strategy. Silent unless the setting btc_sunday_bounce is 1."""
    if not on('btc_sunday_bounce'): return None
    r = sunday_setup(m, h)
    if not r: return None
    out = {'side': 'buy', 'sl': r['sl'], 'tp': r['tp'], 'name': 'btc_sunday_bounce'}
    if SOLO: out['solo'] = True
    return out

# ------------------------------------------------------------ 2) short only after a pullback
def short_setup(m, h):
    """Setup on the last 15m candle, or None: {'side':'sell','entry','sl','tp' (None for a deep pullback),'mode':'deep'|'flag','ema4h'}."""
    if len(m) < 60 or m[-1]['t'] - m[-2]['t'] != 900: return None
    a = atr(m)[-1]
    if not a: return None
    C4 = _group4h(h, m[-1]['t'] + 900)
    if len(C4) < MIN_4H: return None
    e4 = ema([x['c'] for x in C4], EMA_LEN)
    E = e4[-1]
    if not (C4[-1]['c'] < E and E < e4[-1 - SLOPE_BARS]): return None    # bias is not down: do nothing
    b = m[-1]; body = b['o'] - b['c']
    if body < BODY_MIN * a: return None                                   # the entry candle must be red with a real body
    zone = E - TOUCH_ATR * a
    # ---- deep pullback: sell into strength at the 4h 50 EMA
    def react(x): return x['h'] >= zone and x['o'] - x['c'] >= BODY_MIN * a and x['c'] < E     # red with a real body, touched the zone, closed back under the EMA
    if b['h'] >= zone:
        if not react(b): return None
        for j in range(len(m) - 2, -1, -1):                              # first reaction of this visit only
            if m[j]['h'] < zone: break
            if react(m[j]): return None
        ph = max(x['h'] for x in m[-TOUCH_BARS:]); sl = ph + BUF * a; e = b['c']; dist = sl - e
        if not (SL_MIN * a <= dist <= SL_MAX * a): return None
        return {'side': 'sell', 'entry': e, 'sl': sl, 'tp': None, 'mode': 'deep', 'ema4h': E}
    # ---- shallow pullback: wait for the bear-flag breakdown
    k = len(m) - 1
    if max(x['h'] for x in m[-(IMP_BARS + FLAG_MAX + 1):]) >= zone: return None     # it reached the EMA within the whole look-back: that is the deep case, not a flag
    for n in range(FLAG_MAX, FLAG_MIN - 1, -1):                          # the LONGEST flag that fits first: a short one would swallow part of the impulse
        s = k - n - IMP_BARS
        if s < 0: break
        imp = m[s:k - n]; fl = m[k - n:k]
        ihi = max(x['h'] for x in imp); ilo = min(x['l'] for x in imp); drop = ihi - ilo
        if drop < IMPULSE_ATR * a: continue
        fh = max(x['h'] for x in fl); flo = min(x['l'] for x in fl)
        if flo < ilo: continue                                           # a flag never makes a new low
        if (fh - ilo) / drop > FLAG_RETRACE: continue                    # a deep retrace is not a flag
        if not fl[-1]['c'] > fl[0]['o']: continue                        # a bear flag drifts up
        if not b['c'] < flo: continue                                    # breakdown = a close under the flag low
        e = b['c']; sl = fh + BUF * a; dist = sl - e
        if not (SL_MIN * a <= dist <= SL_MAX * a): continue
        tp = e - drop
        if (e - tp) / dist < RR_MIN_FLAG: continue
        return {'side': 'sell', 'entry': e, 'sl': sl, 'tp': tp, 'mode': 'flag', 'ema4h': E}
    return None

RR_MIN_FLAG = 1.5          # the measured move must pay at least this many times the stop

def btc_pullback_short(m, h):
    """Registered strategy. Silent unless the setting btc_short_pullback is 1."""
    if not on('btc_short_pullback'): return None
    r = short_setup(m, h)
    if not r: return None
    out = {'side': 'sell', 'sl': r['sl'], 'name': 'btc_pullback_short'}
    if r['tp'] is not None: out['tp'] = r['tp']
    if SOLO: out['solo'] = True
    return out
