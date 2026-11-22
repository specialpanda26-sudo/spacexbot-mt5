"""Video 1 (ETM FX, "Bitcoin Institutional Strategy") - SECTION 6A: the range / discount-premium entry.
Rules from the video: BTC moves in supply and demand | price BREAKS a swing high, comes back INSIDE the old range, reaches for a demand point and
breaks the range again | the range = a swing high and a swing low: the broken swing high is valid once price breaks it and then comes back inside the
previous range; the NEW high is the top of the range, the swing low that forced the move is the bottom | fib on that range: 0, 0.25, 0.5, 0.75, 1;
bottom quarter = DISCOUNT (buy only there), top quarter = PREMIUM (sell only there) | REACT, never anticipate: wait for the reaction candle |
operating time frame = the one where the swings are clear: start at 8h, and if no structure shows go DOWN a step (8h, 4h, 1h, 30m) |
entry: price is back inside the range and reaches the extreme level; stop just beyond the swing (the origin of the extreme level);
TP1 = the other end of the range, TP2 = clear the liquidity beyond it | a 50% trade: price sometimes only reaches the 0.5 level and reacts |
price that just sits and consolidates after the reaction is a bad sign.
How the rules are built (the video gives no numbers, every tunable is an assumption kept at the top):
- the bot only has 15-minute (m) and 1-hour (h) candles. 4h and 8h candles are GROUPED from the 1-hour candles (on UTC 4h / 8h boundaries), 30m from the 15m
  candles. A group counts only when ALL its small candles exist and it is already closed (no peeking at the candle still forming).
  Fewer than MIN_BARS candles on a frame = no structure on that frame (_bull_range finds nothing) = go one frame lower. A short H1 history (under 8 x MIN_BARS hours) means no 8h range: nothing breaks, it just goes lower.
- bullish range: a swing high H0, a later CLOSE above it (the break), the highest high since the break = the top, the last swing low before the break = the
  bottom. It is valid only when price has since CLOSED back below H0 (inside the old range) and nothing has closed below the bottom. The newest valid one is used.
  Bearish = the same on mirrored prices.
- if a valid range exists on a frame, THIS frame is traded or nothing is: it never drops lower to look for a different setup (it only drops when there is no structure).
- entry = the 15m candle that touches the discount zone (bottom LEVEL of the range), is a green candle with a real body (BODY_MIN x ATR: a doji is price 'consolidating',
  no reaction) and is the FIRST such candle of this visit. The entry is its close. HALF_OK = True also accepts a reaction at the 0.5 level; the signal then carries half=True (off by default).
  Note: with the stop under the bottom, an entry at the 0.5 level pays only about 1R to the top, so HALF_OK needs a lower RR_MIN (and usually a wider SL_MAX) to ever fire.
- stop = beyond the bottom swing (or the candle's own wick, if that went lower), BUF x ATR further. target TP1 = the top of the range; TP2 (setup() only) = TP2_EXT x range above it.
- skipped (never reshaped): range smaller than RANGE_MIN_ATR x the 15m ATR, stop outside 0.5-3.5 ATR (what the brain accepts), RR to TP1 under RR_MIN.
  With the 15m ATR of BTC, 8h and 4h ranges are usually far too wide for that stop rule: most trades will come from the 1h and 30m frames. Not proven: only tools/backtest.py --solo on real BTC candles can say.
- break-even after TP1 (the video says: moderate) is not coded: the EA / brain manage exits.
The brain gives a lone strategy its own target (tp) and a fixed 2R otherwise. Not registered as solo unless SOLO is True."""
from .indicators import atr, swings

LEFT = RIGHT = 2            # swing sensitivity on the operating frame (candles each side)
TFS = (28800, 14400, 3600, 1800)   # operating frames in seconds: 8h, 4h, 1h, 30m - tried in this order
MIN_BARS = 12               # fewer closed candles than this on a frame = no structure there
LOOK = 60                   # the structure is searched in the last LOOK candles of the frame
LEVEL = 0.25                # discount = the bottom quarter, premium = the top quarter
HALF_OK = False             # also accept a reaction at the 0.5 level (flag half=True)
RANGE_MIN_ATR = 6.0         # a range must be at least this many 15m ATR tall
BODY_MIN = 0.3              # the reaction candle body must be at least this many 15m ATR
BUF = 0.1                   # stop buffer beyond the swing, in 15m ATR
SL_MIN, SL_MAX = 0.5, 3.5   # the brain's accepted stop distance, in 15m ATR
RR_MIN = 1.5                # entry to TP1 must pay at least this many times the stop
TP2_EXT = 0.25             # TP2 = the top + this share of the range
SOLO = False                # False: needs another strategy to agree (the bot's confluence rule). True: may trade alone. Backtest first.

def _neg(c):
    return [{'t': x['t'], 'o': -x['o'], 'h': -x['l'], 'l': -x['h'], 'c': -x['c'], 'v': x.get('v', 0)} for x in c]

def _group(src, sub, step, end):
    """Closed candles of `step` seconds grouped from `src` candles of `sub` seconds: only groups with ALL their small candles that ended by `end`."""
    n = step // sub; g = {}
    for x in src:
        g.setdefault(x['t'] - x['t'] % step, []).append(x)
    out = []
    for t in sorted(g):
        s = g[t]
        if len(s) != n or t + step > end: continue
        s.sort(key=lambda x: x['t'])
        out.append({'t': t, 'o': s[0]['o'], 'h': max(x['h'] for x in s), 'l': min(x['l'] for x in s), 'c': s[-1]['c'], 'v': sum(x.get('v', 0) for x in s)})
    return out

def _frame(m, h, tf, step, end):
    if tf >= 3600: return _group(h, 3600, tf, end) if h else []
    return _group(m, step, tf, end) if tf % step == 0 else []

def _bull_range(C, tail):
    """C = closed candles of the frame, tail = closes of the main-chart candles after the last one (inside the still-forming candle).
    Returns {'lo','hi','brk'} (bottom, top, the swing high that was broken) or None."""
    w = C[-LOOK:]
    if len(w) < MIN_BARS: return None
    sw = swings(w, LEFT, RIGHT)
    highs = [(i, p) for i, p, k in sw if k == 'H']; lows = [(i, p) for i, p, k in sw if k == 'L']
    for iH, H0 in reversed(highs):
        k = next((j for j in range(iH + 1, len(w)) if w[j]['c'] > H0), None)
        if k is None: continue                                              # never broken: not a range yet
        lb = [(i, p) for i, p in lows if i < k]
        if not lb: continue
        iL, L = lb[-1]                                                      # the swing low that forced the move
        if L >= H0: continue
        top = max(x['h'] for x in w[k:])
        iT = next(j for j in range(k, len(w)) if w[j]['h'] == top)
        if any(x['c'] < L for x in w[iL + 1:]) or any(c < L for c in tail): continue      # the bottom was broken: no range
        if not any(x['c'] < H0 for x in w[iT + 1:]) and not any(c < H0 for c in tail): continue   # price has not come back inside the old range
        return {'lo': L, 'hi': top, 'brk': H0}
    return None

def _entry(rg, m, a):
    """Bullish entry on the last 15m candle of m, or None."""
    L, T = rg['lo'], rg['hi']; R = T - L
    if R < RANGE_MIN_ATR * a: return None
    zone_hi = L + (0.5 if HALF_OK else LEVEL) * R
    def react(x): return x['l'] <= zone_hi and x['c'] > x['o'] and x['c'] - x['o'] >= BODY_MIN * a
    b = m[-1]
    if not react(b): return None
    for j in range(len(m) - 2, -1, -1):                                     # first reaction of this visit only
        if m[j]['l'] > zone_hi: break
        if react(m[j]): return None
    e = b['c']; sl = min(L, b['l']) - BUF * a; dist = e - sl
    if not (SL_MIN * a <= dist <= SL_MAX * a): return None
    if (T - e) / dist < RR_MIN: return None                                 # also refuses an entry at or above the top (negative reward)
    return {'entry': e, 'sl': sl, 'tp': T, 'tp2': T + TP2_EXT * R, 'half': b['l'] > L + LEVEL * R, 'range': (L, T), 'rr': (T - e) / dist}

def setup(m, h):
    """Full setup on the last 15m candle, or None: {'side','entry','sl','tp','tp2','half','range','rr','tf' (seconds of the frame used)}."""
    if len(m) < 40: return None
    step = m[-1]['t'] - m[-2]['t']
    if step != 900: return None                                             # built for the 15-minute main chart
    a = atr(m)[-1]
    if not a: return None
    end = m[-1]['t'] + step
    for tf in TFS:
        C = _frame(m, h, tf, step, end)
        if not C: continue                                                  # no candles on this frame: one frame lower
        tail = [x['c'] for x in m if x['t'] >= C[-1]['t'] + tf]
        found = False
        for sign in (1, -1):
            cc = C if sign > 0 else _neg(C); tl = tail if sign > 0 else [-c for c in tail]
            rg = _bull_range(cc, tl)
            if not rg: continue
            found = True
            res = _entry(rg, m if sign > 0 else _neg(m), a)
            if not res: continue
            if sign > 0: return dict(res, side='buy', tf=tf)
            return {'side': 'sell', 'entry': -res['entry'], 'sl': -res['sl'], 'tp': -res['tp'], 'tp2': -res['tp2'], 'half': res['half'],
                    'range': (-res['range'][1], -res['range'][0]), 'rr': res['rr'], 'tf': tf}
        if found: return None                                               # a range exists here: trade it or stay out, never drop lower
    return None

def btc_range(m, h):
    """Registered strategy (main chart = 15-minute candles, h = 1-hour candles)."""
    res = setup(m, h)
    if not res: return None
    out = {'side': res['side'], 'sl': res['sl'], 'tp': res['tp'], 'name': 'btc_range'}
    if SOLO: out['solo'] = True
    return out
