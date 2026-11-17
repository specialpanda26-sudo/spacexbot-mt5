"""Video 2 (Brad Goh, Price Action Course) - SECTION 5: trendlines.
Rules from the video:  UPTREND line joins the higher lows, DOWNTREND line joins the lower highs (not the lows!) | a line needs 2+ touches |
BOUNCE: price comes back to the line and rejects it -> trade in the trend's direction (buy the uptrend line, sell the downtrend line) |
BREAK: a close through the line WITH strong momentum (big candle) can signal a reversal -> trade the other way, no retest needed (it does not always retest) |
a wick through the line that closes back inside is a FAKE-OUT -> no trade | if you cannot draw a clean line, do not force it (section 1 structure covers that case).
Entry: first candle that bounces / breaks. Stop beyond the candle (bounce: beyond the wick, break: above the break candle). Target: the brain's RR.
The mirror (downtrend line) is the same code run on negated prices. The video gives no numbers, so the tunables below are my assumptions.
Reuses: structure() from section 1, candle_kind() from section 2."""
from .indicators import atr, swings
from .pa_structure import structure
from .pa_level import candle_kind

LEFT = RIGHT = 3        # swing sensitivity (same as sections 1-2)
MIN_GAP = 5; MAX_GAP = 80   # candles between the two points the line is drawn through
MAX_AGE = 60            # the second point must be at most this many candles old
TOUCH_TOL = 0.5         # a swing low within this many ATR of the line counts as a touch
MIN_TOUCHES = 2         # video: at least two touches (the two points that draw the line count)
REACH = 0.5             # bounce: the candle must come within this many ATR of the line
PIERCE = 0.5            # bounce: its wick may poke at most this many ATR through the line (it must close back inside)
MOM_BODY = 0.6          # break: the candle body is at least this fraction of its range (big candle, momentum)
MOM_ATR = 0.8           # break: ...and at least this many ATR long
BREAK_MARGIN = 0.2      # break: must close at least this many ATR beyond the line
TREND_ONLY = True       # True: the line only counts while section 1 structure agrees (uptrend line needs an uptrend)
BUF = 0.1               # stop buffer, in ATR
MAX_STOP = 8.0          # skip the trade if the stop would be wider than this many ATR
WINDOW = 200

def _neg(w): return [{'t': x['t'], 'o': -x['o'], 'h': -x['l'], 'l': -x['h'], 'c': -x['c'], 'v': x.get('v', 1)} for x in w]

def uptrend_line(w, a):
    """(i1, p1, i2, p2) of the newest valid line through two rising swing lows, or None.
    Valid = rising, 2+ touches, nothing closed below it since the first point, no low far below it between the points.
    Reused by the tests; the downtrend line is uptrend_line(_neg(w))."""
    n = len(w); L = [(i, p) for i, p, k in swings(w, LEFT, RIGHT) if k == 'L']
    for q in range(len(L) - 1, 0, -1):
        i2, p2 = L[q]
        if n - 1 - i2 > MAX_AGE: break
        for r in range(q - 1, max(-1, q - 4), -1):                       # pair with one of the 3 previous swing lows
            i1, p1 = L[r]
            if not (MIN_GAP <= i2 - i1 <= MAX_GAP and p2 > p1): continue
            ln = lambda j: p1 + (p2 - p1) * (j - i1) / (i2 - i1)
            if any(w[j]['l'] < ln(j) - PIERCE * a for j in range(i1, n - 1)): continue       # a low well below the line -> not this line
            if any(w[j]['c'] < ln(j) for j in range(i1, n - 1)): continue                    # already broken before the last candle
            touches = sum(1 for i, p in L if i1 <= i < n and abs(p - ln(i)) <= TOUCH_TOL * a)
            if touches < MIN_TOUCHES: continue
            return (i1, p1, i2, p2)
    return None

def _side(w, a):
    """Look at the uptrend line of w (the last candle is the trigger). Returns {'kind', 'dir', 'sl'} or None.
    kind 'bounce' -> dir 'buy' (with the trend), kind 'break' -> dir 'sell' (reversal)."""
    n = len(w); b = w[-1]
    if TREND_ONLY and structure(w, LEFT, RIGHT) != 'up': return None
    t = uptrend_line(w, a)
    if not t: return None
    i1, p1, i2, p2 = t; ln = lambda j: p1 + (p2 - p1) * (j - i1) / (i2 - i1); y = ln(n - 1)
    body = abs(b['c'] - b['o']); rng = b['h'] - b['l']
    # BREAK: first close through the line, with momentum (big bearish candle). No retest asked for.
    if b['c'] < y - BREAK_MARGIN * a and b['c'] < b['o'] and rng > 0 and body / rng >= MOM_BODY and body >= MOM_ATR * a:
        return {'kind': 'break', 'dir': 'sell', 'sl': b['h'] + BUF * a}
    # BOUNCE: the candle reaches the line, pokes through by little or not at all, closes back above it as a bullish rejection / momentum candle
    if b['l'] <= y + REACH * a and b['l'] >= y - PIERCE * a and b['c'] > y and candle_kind(b) in ('rej_up', 'mom_up') and b['c'] > b['o']:
        if any(x['l'] <= ln(n - 4 + j) + REACH * a and x['c'] > ln(n - 4 + j) for j, x in enumerate(w[-4:-1])): return None   # not the first candle at the line
        return {'kind': 'bounce', 'dir': 'buy', 'sl': min(b['l'], y) - BUF * a}
    return None            # includes the fake-out: wick through the line, close back inside, too deep to be a bounce

def signal(w):
    """Signal for the last candle of w, plus 'kind' ('bounce' | 'break') and 'line' ('up' | 'down')."""
    a = atr(w)[-1]
    if not a or len(w) < 30: return None
    for down, ww in ((False, w), (True, _neg(w))):
        r = _side(ww, a)
        if not r: continue
        buy = (r['dir'] == 'buy') != down                          # mirror: negated prices flip the direction
        sl = -r['sl'] if down else r['sl']
        if abs(sl - w[-1]['c']) > MAX_STOP * a: continue
        return {'side': 'buy' if buy else 'sell', 'sl': sl, 'name': 'pa_trendline', 'kind': r['kind'], 'line': 'down' if down else 'up'}
    return None

def pa_trendline(m, h):
    if len(m) < 60: return None
    s = signal(m[-WINDOW:])
    return {k: v for k, v in s.items() if k not in ('kind', 'line')} if s else None
