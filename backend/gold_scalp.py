"""Video 5 (Brad Goh, gold scalping) - SECTION 5B: steps 3 + 4 + 5, the AGGRESSIVE entry.
Rules from the video: step 1+2 (section 5A, gs_zones.scan) - 1h and 15m trend agree, only demand zones for buys / supply zones for sells |
step 3 - do nothing until price comes back into a 15-MINUTE zone | step 4 - being in the zone is not enough: wait for a LIQUIDITY SWEEP, price takes out a
recent swing low (buys) / swing high (sells) with a wick and CLOSES back on the other side; a close beyond the level is a break, not a sweep |
aggressive entry = right after the sweep candle | stop beyond the sweep candle (the protected low / high) | step 5 - target the NEAREST 15m swing high (buys) / swing low (sells).
A swing that was already taken out earlier is not liquidity any more, so each sweep fires once, on the sweep candle only. The sell side is the buy side run on mirrored prices.
The brain only accepts stops 0.5 to 3.5 ATR away, so a sweep candle outside that range is skipped, never reshaped. The conservative entry (market shift, then pullback) is section 5C.
The video gives no numbers: the tunables below are my assumptions. Not proven: only tools/backtest.py --solo on real data can say if it works."""
from .indicators import atr, swings
from .gs_zones import scan, touching

LEFT = RIGHT = 3        # swing sensitivity (candles each side)
WINDOW = 200            # candles searched
SWEEP_LOOK = 40         # the swept swing low / high may be at most this many candles old
SWEEP_MIN = 0.05        # the wick must go at least this many ATR through the level (a one-tick poke is not a sweep)
ZONE_BARS = 6           # price must have been in the zone within this many candles (the sweep candle included)
MIT_GAP = 3             # only candles this many candles after the zone formed count as coming back to it
HIGH_LOOK = 100         # the target swing high / low may be at most this many candles old
BUF = 0.1               # stop buffer beyond the sweep candle, in ATR
SL_MIN, SL_MAX = 0.5, 3.5   # the brain's accepted stop distance, in ATR
MIN_RR = 1.0            # skip when the nearest target is closer than this x the stop distance
SOLO = False            # False: needs another strategy to agree (bot's confluence rule). True: may trade alone. Backtest first.

def _neg(w): return [{'t': x['t'], 'o': -x['o'], 'h': -x['l'], 'l': -x['h'], 'c': -x['c'], 'v': x.get('v', 1)} for x in w]

def _buy(w, a):
    """Sweep + stop + target for a BUY on the last candle of w, or None. Returns (sl, tp)."""
    n = len(w); b = w[-1]; sw = swings(w[:-1], LEFT, RIGHT); e = b['c']
    lows = [(i, p) for i, p, k in sw if k == 'L' and n - 1 - i <= SWEEP_LOOK]
    lvl = None
    for i, p in reversed(lows):                                                  # newest swing low first
        if any(x['l'] < p for x in w[i + 1:n - 1]): continue                     # already taken out earlier: no liquidity left there
        if b['l'] < p - SWEEP_MIN * a and b['c'] > p: lvl = p; break              # wick through it and closed back above
    if lvl is None: return None
    sl = b['l'] - BUF * a; dist = e - sl
    if not (SL_MIN * a <= dist <= SL_MAX * a): return None
    tops = [p for i, p, k in sw if k == 'H' and p > e and n - 1 - i <= HIGH_LOOK and not any(x['h'] > p for x in w[i + 1:n - 1])]
    if not tops: return None
    tp = min(tops)                                                               # the NEAREST unbroken swing high above the entry
    if tp - e < MIN_RR * dist: return None
    return sl, tp

def _at_zone(m, zones):
    """True when price was back inside one of the zones within the last ZONE_BARS candles (not on the zone's own forming candles)."""
    step = m[-1]['t'] - m[-2]['t']
    for z in zones:
        if any(touching(x, z) and x['t'] > z['t'] + MIT_GAP * step for x in m[-ZONE_BARS:]): return True
    return False

def gold_scalp(m, h):
    if len(m) < 60: return None
    r = scan(m, h)
    if not r: return None                                                        # 1h and 15m disagree, or no 1h data: stay out
    up = r['bias'] == 'up'; side = 'buy' if up else 'sell'
    zones = [z for z in r['zones'] if z['tf'] == 'm15' and z['side'] == side]    # 15-minute points of interest only
    if not zones or not _at_zone(m, zones): return None                          # step 3: price has not come back to a zone
    w = m[-WINDOW:]; a = atr(m)[-1]
    if not a: return None
    res = _buy(w, a) if up else _buy(_neg(w), a)
    if not res: return None
    sl, tp = res
    solo = {'solo': True} if SOLO else {}
    if up: return {'side': 'buy', 'sl': sl, 'tp': tp, 'name': 'gold_scalp', **solo}
    return {'side': 'sell', 'sl': -sl, 'tp': -tp, 'name': 'gold_scalp', **solo}
