"""Video 5 (Brad Goh, gold scalping) - SECTION 5C: the CONSERVATIVE entry for 5B.
Rules from the video: steps 1-3 as in 5A/5B (1h and 15m trend agree, price at a 15-MINUTE zone of that side) | step 4 - a LIQUIDITY SWEEP of a swing low (buys) / swing high (sells),
a wick through it and a close back | then do NOT enter on the sweep candle: wait for a MARKET SHIFT = a candle CLOSES beyond the last internal high (buys) / low (sells) that stood before the sweep |
then wait for price to PULL BACK into the zone that caused the shift (the last opposite candle before the shift candle) and enter when it comes back | stop beyond the protected low / high (the sweep candle) |
target = the NEAREST unbroken 15m swing high (buys) / swing low (sells), at least 1R. The video warns that this version misses trades: price often shifts and never pulls back.
Extra rules I added so one setup is one trade: the pullback must be the FIRST return to the zone, it must come within PULL_BARS candles of the shift, and the setup dies when the protected low / high is broken or a candle closes through the zone.
It never fires on the sweep candle or on the shift candle (that is 5B). The sell side is the buy side run on mirrored prices. The brain only accepts stops 0.5 to 3.5 ATR away, so a wider one is skipped, never reshaped.
The video gives no numbers: the tunables below are my assumptions. Not proven: only tools/backtest.py --solo on real data can say if it works."""
from .indicators import atr, swings
from .gs_zones import scan, touching
from .gold_scalp import _neg, _at_zone, LEFT, RIGHT, WINDOW, SWEEP_LOOK, SWEEP_MIN, HIGH_LOOK, BUF, SL_MIN, SL_MAX, MIN_RR

SHIFT_BARS = 12         # the market shift must close within this many candles after the sweep candle
PULL_BARS = 24          # the pullback into the shift zone must come within this many candles after the shift candle
SOLO = False            # False: needs another strategy to agree (bot's confluence rule). True: may trade alone. Backtest first.
NAME = 'gold_scalp_c'

def _setup(w, near, a):
    """Conservative BUY on the last candle of w, or None. near(k) says whether a sweep on candle k happened at a 15m zone. Returns (sl, tp)."""
    n = len(w); e = w[-1]['c']; sw = swings(w[:-1], LEFT, RIGHT)
    highs = [(i, p) for i, p, kd in sw if kd == 'H']; lows = [(i, p) for i, p, kd in sw if kd == 'L']
    for k in range(n - 3, max(n - 2 - PULL_BARS - SHIFT_BARS, 30), -1):                 # k = sweep candle; room for a shift candle and an entry candle after it
        sb = w[k]
        lvl = None
        for i, p in reversed([x for x in lows if x[0] + RIGHT < k and k - x[0] <= SWEEP_LOOK]):
            if any(x['l'] < p for x in w[i + 1:k]): continue                              # taken out earlier: no liquidity left
            if sb['l'] < p - SWEEP_MIN * a and sb['c'] > p: lvl = p; break                # wick through it, closed back above
        if lvl is None: continue
        if not near(k): continue                                                          # step 3: the sweep was not at a 15m zone
        hh = [(i, p) for i, p in highs if i + RIGHT < k]
        if not hh: continue
        hi, H = hh[-1]                                                                    # the last internal high before the sweep
        if any(x['c'] > H for x in w[hi + 1:k + 1]): continue                             # price already closed above it: the shift was earlier, not after this sweep
        s = next((j for j in range(k + 1, min(k + 1 + SHIFT_BARS, n - 1)) if w[j]['c'] > H), None)   # the market shift candle
        if s is None or n - 1 - s > PULL_BARS: continue
        if any(x['l'] < sb['l'] for x in w[k + 1:]): continue                             # protected low broken: setup is dead
        j = next((q for q in range(s - 1, k - 1, -1) if w[q]['c'] < w[q]['o']), None)     # the last opposite candle before the shift = the zone that caused it
        if j is None: continue
        zlo, zhi = w[j]['l'], w[j]['h']
        if any(x['c'] < zlo for x in w[s + 1:]): continue                                 # a close through the zone: used up
        if any(touching(x, {'lo': zlo, 'hi': zhi}) for x in w[s + 1:n - 1]): continue     # the FIRST return only
        b = w[-1]
        if not touching(b, {'lo': zlo, 'hi': zhi}): continue                              # price is back in the zone (a close through it was ruled out above, so the zone holds)
        sl = sb['l'] - BUF * a; dist = e - sl
        if not (SL_MIN * a <= dist <= SL_MAX * a): continue
        tops = [p for i, p, kd in sw if kd == 'H' and p > e and n - 1 - i <= HIGH_LOOK and not any(x['h'] > p for x in w[i + 1:n - 1])]
        if not tops: continue
        tp = min(tops)                                                                    # the NEAREST unbroken swing high above the entry
        if tp - e < MIN_RR * dist: continue
        return sl, tp
    return None

def gold_scalp_c(m, h):
    if len(m) < 60: return None
    r = scan(m, h)
    if not r: return None                                                                 # 1h and 15m disagree, or no 1h data: stay out
    up = r['bias'] == 'up'; side = 'buy' if up else 'sell'
    zones = [z for z in r['zones'] if z['tf'] == 'm15' and z['side'] == side]
    if not zones: return None
    w = m[-WINDOW:]; a = atr(m)[-1]
    if not a: return None
    near = lambda k: _at_zone(w[:k + 1], zones)                                           # zones are in real prices, so this check always runs on the real candles
    res = _setup(w, near, a) if up else _setup(_neg(w), near, a)
    if not res: return None
    sl, tp = res
    solo = {'solo': True} if SOLO else {}
    if up: return {'side': 'buy', 'sl': sl, 'tp': tp, 'name': NAME, **solo}
    return {'side': 'sell', 'sl': -sl, 'tp': -tp, 'name': NAME, **solo}
