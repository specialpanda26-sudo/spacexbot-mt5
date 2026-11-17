"""Video 2 (Brad Goh, Price Action Course) - SECTION 3: the three favourite candle patterns.
Rules from the video:  bullish/bearish ENGULFING (big body swallowing a small opposite candle) | THREE LINE STRIKE (one big candle engulfing the
previous three: its direction is the pressure, so it is traded WITH the trend: big red in a downtrend = sell, big green in an uptrend = buy) |
MORNING / EVENING STAR (big candle, small star, big candle back through the middle of the first).
The reversal patterns only count AT a key level (section 2 key_levels(): 2+ touches, not already broken): bullish at support, bearish at
resistance. Sideways market = stay out. Entry: the candle that completes the pattern. Stop beyond the whole pattern. Target: the brain's RR.
The video gives no numbers, so the tunables below are my assumptions."""
from .indicators import atr
from .pa_structure import structure
from .pa_level import key_levels

LEFT = RIGHT = 3        # swing sensitivity (same as sections 1 and 2)
MIN_TOUCHES = 2         # a key level needs at least two touches
CLUSTER = 0.5           # swing points within this many ATR form one level
REACH = 0.5             # the pattern's extreme must come within this many ATR of the level
PIERCE = 0.5            # ...and may poke at most this many ATR through it (it must close back)
BIG_BODY = 0.6          # momentum candle: body is at least this fraction of its range
MIN_RANGE = 0.6         # ...and its range is at least this many ATR (no tiny candles)
SMALL_PREV = 0.6        # engulfing: the engulfed body is at most this fraction of the engulfing body
STAR_SMALL = 0.35       # star: its body is at most this fraction of the first candle's body
OPEN_TOL = 0.1          # an open this many ATR beyond the previous close still counts (real charts gap a little)
BUF = 0.1               # stop buffer, in ATR
MAX_STOP = 4.0          # skip the trade if the stop would be wider than this many ATR
SKIP_SIDEWAYS = True    # video: stay out of a consolidation (applies to the reversal patterns)
STRIKE_NEEDS_LEVEL = False   # three line strike: True = also require a key level (default: trend only, as the video says)
WINDOW = 200

def _body(x): return abs(x['c'] - x['o'])
def _big(x, a, up):
    r = x['h'] - x['l']
    return r >= MIN_RANGE * a and _body(x) >= BIG_BODY * r and (x['c'] > x['o'] if up else x['c'] < x['o'])

def patterns(w, a):
    """[(name, side, candles used)] for every pattern completed by the last candle. Reused by later sections."""
    out = []; b = w[-1]; p = w[-2]; t = OPEN_TOL * a
    c1, c2 = w[-3], w[-2]; mid = (c1['o'] + c1['c']) / 2
    if _big(b, a, True) and _big(c1, a, False) and _body(c2) <= STAR_SMALL * _body(c1) and max(c2['o'], c2['c']) <= mid and b['c'] > mid: out.append(('morning_star', 'buy', 3))
    if _big(b, a, False) and _big(c1, a, True) and _body(c2) <= STAR_SMALL * _body(c1) and min(c2['o'], c2['c']) >= mid and b['c'] < mid: out.append(('evening_star', 'sell', 3))
    q = w[-4:-1]
    if len(q) == 3:
        if all(x['c'] < x['o'] for x in q) and q[1]['c'] < q[0]['c'] and q[2]['c'] < q[1]['c'] and _big(b, a, True) and b['o'] <= q[2]['c'] + t and b['c'] >= q[0]['o']: out.append(('three_line_strike', 'buy', 4))
        if all(x['c'] > x['o'] for x in q) and q[1]['c'] > q[0]['c'] and q[2]['c'] > q[1]['c'] and _big(b, a, False) and b['o'] >= q[2]['c'] - t and b['c'] <= q[0]['o']: out.append(('three_line_strike', 'sell', 4))
    if _big(b, a, True) and p['c'] < p['o'] and b['o'] <= p['c'] + t and b['c'] >= p['o'] and _body(p) <= SMALL_PREV * _body(b): out.append(('engulfing', 'buy', 2))
    if _big(b, a, False) and p['c'] > p['o'] and b['o'] >= p['c'] - t and b['c'] <= p['o'] and _body(p) <= SMALL_PREV * _body(b): out.append(('engulfing', 'sell', 2))
    return out

def at_level(w, a, side, k):
    """True if the pattern (its last k candles) sits on a real key level: support for a buy, resistance for a sell."""
    n = len(w); base = w[:n - k]; pat = w[n - k:]
    if len(base) < 40: return False
    ext = min(x['l'] for x in pat) if side == 'buy' else max(x['h'] for x in pat)     # levels come from BEFORE the pattern, it cannot confirm its own level
    for L, touches, last in sorted(key_levels(base, a), key=lambda s: abs(s[0] - ext)):
        if touches < MIN_TOUCHES: continue
        if side == 'buy':
            if not (L - PIERCE * a <= ext <= L + REACH * a and w[-1]['c'] > L): continue
            if any(x['c'] < L - CLUSTER * a for x in base[last + 1:]): continue          # level already broken -> no bounce
        else:
            if not (L - REACH * a <= ext <= L + PIERCE * a and w[-1]['c'] < L): continue
            if any(x['c'] > L + CLUSTER * a for x in base[last + 1:]): continue
        return True
    return False

def signal(w):
    """The signal for the last candle of w, plus which pattern made it ('pattern' key)."""
    a = atr(w)[-1]
    if not a: return None
    st = structure(w, LEFT, RIGHT)
    for name, side, k in patterns(w, a):
        if name == 'three_line_strike':
            if st != ('up' if side == 'buy' else 'down'): continue
            if STRIKE_NEEDS_LEVEL and not at_level(w, a, side, k): continue
        else:
            if SKIP_SIDEWAYS and st == 'side': continue
            if not at_level(w, a, side, k): continue
        pat = w[-k:]
        if side == 'buy': sl = min(x['l'] for x in pat) - BUF * a; dist = w[-1]['c'] - sl
        else: sl = max(x['h'] for x in pat) + BUF * a; dist = sl - w[-1]['c']
        if dist > MAX_STOP * a: continue
        return {'side': side, 'sl': sl, 'name': 'pa_candle', 'pattern': name}
    return None

def pa_candle(m, h):
    if len(m) < 60: return None
    w = m[-WINDOW:]; s = signal(w)
    if not s: return None
    for j in (1, 2, 3):                                  # not the first pattern in a row at this spot -> skip
        r = signal(w[:-j])
        if r and r['side'] == s['side']: return None
    return {k: v for k, v in s.items() if k != 'pattern'}
