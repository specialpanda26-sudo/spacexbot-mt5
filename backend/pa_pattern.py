"""Video 2 (Brad Goh, Price Action Course) - SECTION 4: the four chart patterns.
Rules from the video:  DOUBLE TOP -> sell, DOUBLE BOTTOM -> buy, HEAD AND SHOULDERS -> sell, INVERTED HEAD AND SHOULDERS -> buy.
Enter when price BREAKS THE NECKLINE (the low between the two tops / the line through the two dips of the head and shoulders), not before.
The two tops need NOT be the same height and the shoulders need not match either - "price can do whatever it wants".
Stop above the tops (right shoulder for head and shoulders). Target: the brain's RR (video: next key level).
Only the first candle that closes through the neckline triggers. The mirror (bottoms) is the same code run on negated prices.
The video gives no numbers, so the tunables below are my assumptions."""
from .indicators import atr, swings

LEFT = 3; RIGHT = 2     # swing sensitivity (a little quicker on the right so a sharp break is not missed)
TOP_TOL = 1.5           # the two tops may differ by this many ATR (video: they do not have to be equal)
HEAD_EXTRA = 0.5        # the head must stick out above BOTH shoulders by this many ATR
MIN_DEPTH = 2.0         # the dip down to the neckline must be at least this many ATR (no tiny wiggles)
PRIOR_MOVE = 3.0        # price must have risen this many ATR into the first peak (a reversal needs something to reverse)
PRIOR_BARS = 30         # ...measured over this many candles before it
MIN_GAP = 4; MAX_GAP = 60   # candles between two tops
MAX_AGE = 40            # the neckline break must come within this many candles of the last peak
BUF = 0.1               # stop buffer, in ATR
MAX_STOP = 8.0          # skip the trade if the stop would be wider than this many ATR
REPEAT = 5              # skip a trade if the same side already triggered in the last few candles (e.g. two overlapping neckline breaks)
INTACT = 0.5            # the pattern is dead if price goes more than this many ATR beyond the tops afterwards
WINDOW = 200

def _prior_ok(w, i, a): return w[i]['h'] - min(x['l'] for x in w[max(0, i - PRIOR_BARS):i]) >= PRIOR_MOVE * a

def _double_top(w, a):
    n = len(w); H = [s for s in swings(w, LEFT, RIGHT) if s[2] == 'H']
    for q in range(len(H) - 1, max(0, len(H) - 5), -1):
        (i1, h1, _), (i2, h2, _) = H[q - 1], H[q]
        if not (MIN_GAP <= i2 - i1 <= MAX_GAP and abs(h1 - h2) <= TOP_TOL * a and n - 1 - i2 <= MAX_AGE and i2 < n - 1): continue
        peak = max(h1, h2); seg = w[i1:i2 + 1]
        if max(x['h'] for x in seg) > peak: continue
        neck = min(x['l'] for x in seg)
        if min(h1, h2) - neck < MIN_DEPTH * a or not _prior_ok(w, i1, a): continue
        after = w[i2 + 1:]
        if max(x['h'] for x in after) > peak + INTACT * a: continue                    # the pattern is no longer intact
        if not (w[-1]['c'] < neck and all(x['c'] >= neck for x in after[:-1])): continue    # first close through the neckline only
        return {'sl': max(peak, max(x['h'] for x in after)) + BUF * a, 'pattern': 'double_top'}
    return None

def _head_shoulders(w, a):
    n = len(w); H = [s for s in swings(w, LEFT, RIGHT) if s[2] == 'H']
    for q in range(len(H) - 1, max(1, len(H) - 5), -1):
        (iL, hL, _), (iH, hH, _), (iR, hR, _) = H[q - 2], H[q - 1], H[q]
        if not (hH >= hL + HEAD_EXTRA * a and hH >= hR + HEAD_EXTRA * a and iR - iL <= 2 * MAX_GAP and n - 1 - iR <= MAX_AGE and iR < n - 1): continue
        i1 = min(range(iL, iH + 1), key=lambda j: w[j]['l']); i2 = min(range(iH, iR + 1), key=lambda j: w[j]['l'])
        if i2 <= i1: continue
        T1, T2 = w[i1]['l'], w[i2]['l']
        line = lambda j: T1 + (T2 - T1) * (j - i1) / (i2 - i1)                       # the neckline, sloped, extended to the right
        if min(hL - line(iL), hR - line(iR)) < MIN_DEPTH * a or not _prior_ok(w, iL, a): continue
        after = w[iR + 1:]
        if max(x['h'] for x in after) > hH: continue
        if not (w[-1]['c'] < line(n - 1) and all(w[j]['c'] >= line(j) for j in range(iR + 1, n - 1))): continue
        return {'sl': max(x['h'] for x in w[iR:]) + BUF * a, 'pattern': 'head_shoulders'}
    return None

def _neg(w): return [{'t': x['t'], 'o': -x['o'], 'h': -x['l'], 'l': -x['h'], 'c': -x['c'], 'v': x.get('v', 1)} for x in w]

def _raw(w):
    a = atr(w)[-1]
    if not a: return None
    for bull, ww in ((False, w), (True, _neg(w))):
        for f in (_head_shoulders, _double_top):
            r = f(ww, a)
            if not r: continue
            sl = -r['sl'] if bull else r['sl']; c = w[-1]['c']
            if abs(sl - c) > MAX_STOP * a: continue
            name = {'double_top': 'double_bottom', 'head_shoulders': 'inverse_head_shoulders'}[r['pattern']] if bull else r['pattern']
            return {'side': 'buy' if bull else 'sell', 'sl': sl, 'name': 'pa_pattern', 'pattern': name}
    return None

def signal(w):
    """Signal for the last candle of w, plus which pattern made it ('pattern' key)."""
    s = _raw(w)
    if s:
        for j in range(1, REPEAT + 1):
            r = _raw(w[:-j])
            if r and r['side'] == s['side']: return None
    return s

def pa_pattern(m, h):
    if len(m) < 60: return None
    s = signal(m[-WINDOW:])
    return {k: v for k, v in s.items() if k != 'pattern'} if s else None
