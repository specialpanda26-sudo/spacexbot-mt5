"""Video 2 (Brad Goh, Price Action Course) - SECTION 1: market structure + break of structure (BOS).
Rules from the video:  uptrend = higher highs + higher lows | downtrend = lower highs + lower lows | else sideways = stay out.
BOS reversal (from an uptrend): price CLOSES below the last higher low, comes back up to retest it, and fails to make a new high
(a LOWER HIGH) -> downtrend confirmed -> sell. The mirror (from a downtrend) is a buy. Do not trade the first break, wait for the retest.
Entry: first bearish/bullish candle after the retest that closes beyond the previous candle. Stop beyond the retest extreme.
Target: not set here, the brain's RR is used. Tunables are at the top (the video gives no numbers, so these are my assumptions)."""
from .indicators import atr, swings

LEFT = RIGHT = 3        # swing sensitivity (candles each side)
BUF = 0.1               # stop buffer, in ATR
RETEST_TOL = 0.5        # the retest must come back within this many ATR of the broken level
MAX_BREAK_AGE = 30      # the break must be this recent (candles)
MIN_RETEST_BARS = 2     # candles between the break and the trigger
WINDOW = 200

def structure(w, left=LEFT, right=RIGHT):
    """'up' | 'down' | 'side' from the last two swing highs and last two swing lows. Reused by later sections."""
    sw = swings(w, left, right)
    h = [p for _, p, k in sw if k == 'H'][-2:]; l = [p for _, p, k in sw if k == 'L'][-2:]
    if len(h) < 2 or len(l) < 2: return 'side'
    if h[1] > h[0] and l[1] > l[0]: return 'up'
    if h[1] < h[0] and l[1] < l[0]: return 'down'
    return 'side'

def _bos(w, a, bear):
    """bear=True: uptrend broke down, look for the sell. bear=False: mirror."""
    n = len(w); sw = swings(w, LEFT, RIGHT)
    want, other = ('L', 'H') if bear else ('H', 'L')       # want = the level that gets broken, other = the opposite swing
    lv = [s for s in sw if s[2] == want]
    for q in range(len(lv) - 1, 0, -1):                     # newest candidate first
        iL, pL, _ = lv[q]; pPrev = lv[q - 1][1]
        if (bear and pL <= pPrev) or (not bear and pL >= pPrev): continue          # must be a HIGHER low (bear) / LOWER high (bull)
        # first close beyond the level after it formed
        k = next((j for j in range(iL + 1, n) if (w[j]['c'] < pL if bear else w[j]['c'] > pL)), None)
        if k is None or n - 1 - k > MAX_BREAK_AGE or n - 1 - k < MIN_RETEST_BARS + 1: continue
        if any((x['l'] < pL - a) if bear else (x['h'] > pL + a) for x in w[iL + 1:k]): continue   # level was not intact
        ot = [s for s in sw if s[2] == other and s[0] < k]
        if len(ot) < 2: continue
        if bear and not ot[-1][1] > ot[-2][1]: continue    # before the break it must have been an uptrend (higher highs)
        if not bear and not ot[-1][1] < ot[-2][1]: continue
        lastExt = ot[-1][1]                                 # the high (bear) / low (bull) the retest has to fail to beat
        after = w[k + 1:]
        if len(after) < MIN_RETEST_BARS: continue
        b, p = w[-1], w[-2]
        if bear:
            ph = max(x['h'] for x in after[:-1])
            if not (pL - RETEST_TOL * a <= ph < lastExt): continue          # retested the level, but made a LOWER HIGH
            if not (b['c'] < b['o'] and b['c'] < p['l'] and b['c'] < pL): continue
            if any(after[j]['c'] < after[j]['o'] and after[j]['c'] < after[j - 1]['l'] and after[j]['c'] < pL for j in range(1, len(after) - 1)): continue  # not the first trigger
            return {'side': 'sell', 'sl': max(ph, b['h']) + BUF * a, 'name': 'pa_bos'}
        pl = min(x['l'] for x in after[:-1])
        if not (lastExt < pl <= pL + RETEST_TOL * a): continue
        if not (b['c'] > b['o'] and b['c'] > p['h'] and b['c'] > pL): continue
        if any(after[j]['c'] > after[j]['o'] and after[j]['c'] > after[j - 1]['h'] and after[j]['c'] > pL for j in range(1, len(after) - 1)): continue
        return {'side': 'buy', 'sl': min(pl, b['l']) - BUF * a, 'name': 'pa_bos'}
    return None

def pa_bos(m, h):
    if len(m) < 60: return None
    w = m[-WINDOW:]; a = atr(w)[-1]
    if not a: return None
    return _bos(w, a, True) or _bos(w, a, False)
