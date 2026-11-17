"""Video 2 (Brad Goh, Price Action Course) - SECTION 2: key levels + candle pressure.
Rules from the video:  a level is support/resistance only after 2+ touches | a broken level flips role (swing highs AND lows are pooled,
so an old resistance that price retests from above counts as support) | only candles AT a key level matter, the rest is noise |
big body = momentum, long wick that closes back = rejection | trade with the trend (structure() from section 1), sideways = stay out.
Entry: rejection candle at the level (buy at support in an uptrend, sell at resistance in a downtrend). Stop beyond the wick.
Target: not set here, the brain's RR is used. The video gives no numbers, so the tunables below are my assumptions.
Reused by later sections: key_levels(), candle_kind()."""
from .indicators import atr, swings
from .pa_structure import structure

LEFT = RIGHT = 3        # swing sensitivity (same as section 1)
MIN_TOUCHES = 2         # video: at least two touches
CLUSTER = 0.5           # swing points within this many ATR of each other form one level
REACH = 0.5             # the trigger candle must come within this many ATR of the level
PIERCE = 0.5            # its wick may poke at most this many ATR through the level (it must close back)
WICK = 0.5              # rejection: wick is at least this fraction of the candle range
BIG_BODY = 0.6          # momentum: body is at least this fraction of the candle range
BUF = 0.1               # stop buffer, in ATR
TREND_ONLY = True       # True: buy only in an uptrend, sell only in a downtrend (video: trade with the trend)
WINDOW = 200

def key_levels(w, a, left=LEFT, right=RIGHT):
    """[(price, touches, index of the last touch)] - swing highs and lows pooled, so a broken level keeps its history."""
    groups = []
    for i, p, _ in sorted(((i, p, k) for i, p, k in swings(w, left, right)), key=lambda s: s[1]):
        if groups and abs(p - sum(g[0] for g in groups[-1]) / len(groups[-1])) <= CLUSTER * a: groups[-1].append((p, i))
        else: groups.append([(p, i)])
    return [(sum(p for p, _ in g) / len(g), len(g), max(i for _, i in g)) for g in groups]

def candle_kind(b):
    """'mom_up'|'mom_down' (big body), 'rej_up' (long lower wick = buyers rejected the low), 'rej_down' (long upper wick), 'weak'."""
    rng = b['h'] - b['l']
    if rng <= 0: return 'weak'
    body = abs(b['c'] - b['o']); lw = min(b['o'], b['c']) - b['l']; uw = b['h'] - max(b['o'], b['c'])
    if body / rng >= BIG_BODY: return 'mom_up' if b['c'] > b['o'] else 'mom_down'
    if lw / rng >= WICK and lw >= uw: return 'rej_up'
    if uw / rng >= WICK and uw > lw: return 'rej_down'
    return 'weak'

def _side(w, a, bull):
    n = len(w); b = w[-1]; want = 'rej_up' if bull else 'rej_down'
    if candle_kind(b) != want: return None
    if TREND_ONLY and structure(w, LEFT, RIGHT) != ('up' if bull else 'down'): return None
    reach = REACH * a
    for L, touches, last in sorted(key_levels(w, a), key=lambda s: abs(s[0] - (b['l'] if bull else b['h']))):
        if touches < MIN_TOUCHES: continue
        if bull:
            if not (L - PIERCE * a <= b['l'] <= L + reach and b['c'] > L): continue
            if any(x['c'] < L - CLUSTER * a for x in w[last + 1:n - 1]): continue          # level already broken -> no bounce
            if any(candle_kind(x) == want and x['l'] <= L + reach and x['c'] > L for x in w[-4:-1]): continue   # not the first rejection
            return {'side': 'buy', 'sl': b['l'] - BUF * a, 'name': 'pa_level'}
        if not (L - reach <= b['h'] <= L + PIERCE * a and b['c'] < L): continue
        if any(x['c'] > L + CLUSTER * a for x in w[last + 1:n - 1]): continue
        if any(candle_kind(x) == want and x['h'] >= L - reach and x['c'] < L for x in w[-4:-1]): continue
        return {'side': 'sell', 'sl': b['h'] + BUF * a, 'name': 'pa_level'}
    return None

def pa_level(m, h):
    if len(m) < 60: return None
    w = m[-WINDOW:]; a = atr(w)[-1]
    if not a: return None
    return _side(w, a, True) or _side(w, a, False)
