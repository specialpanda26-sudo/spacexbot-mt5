"""Video 5 (Brad Goh, gold scalping) - SECTION 5A: steps 1 + 2 = trend agreement, then demand / supply zones.
Rules from the video: step 1 - the 1-HOUR and the 15-MINUTE trend must AGREE, else no trade (a misalignment gives low-probability setups) |
step 2 - in an uptrend look only for DEMAND zones (buys), in a downtrend only for SUPPLY zones (sells) | a zone is an ORDER BLOCK (the last
opposite candle before an impulsive move that broke structure) or a FAIR VALUE GAP | zones are marked on the 1h and the 15m chart.
This file only FINDS the zones. It fires no trade (the wait for price + liquidity sweep + entry is section 5B/5C), so it is not registered in strategies.py yet.
Only COMPLETED 1-hour candles are used. The video gives no numbers: the tunables below are my assumptions."""
from .indicators import atr, swings
from .pa_structure import structure

LEFT = RIGHT = 3        # swing sensitivity (candles each side)
HTF = 3600              # the higher time frame is 1 hour
M15_WINDOW = 200        # candles of the main chart that are searched
H1_WINDOW = 120         # 1-hour candles that are searched
IMP_BARS = 3            # the impulsive move must happen within this many candles after the order-block candle
IMP_ATR = 1.5           # ...and close at least this many ATR beyond the order-block candle's far side
DISP_BODY = 0.8         # fair value gap: the middle candle's body must be at least this many ATR (real displacement)
FVG_ATR = 0.3           # fair value gap: the gap itself must be at least this many ATR
MAX_ZONES = 4           # newest zones kept per time frame

def _htf_done(m, h):
    """Completed 1-hour candles (the one still forming is left out), or None if the main chart is not below 1 hour or there is no 1h data."""
    if len(m) < 2 or not h: return None
    step = m[-1]['t'] - m[-2]['t']
    if step >= HTF: return None
    end = m[-1]['t'] + step
    done = [x for x in h if x['t'] + HTF <= end]
    return done if len(done) >= 20 else None

def bias(m, h):
    """Step 1: 'up' or 'down' only when the 1h structure and the 15m structure agree; otherwise None (stay out)."""
    if len(m) < 60: return None
    H = _htf_done(m, h)
    if not H: return None
    a = structure(m[-M15_WINDOW:]); b = structure(H[-H1_WINDOW:])
    return a if a == b and a in ('up', 'down') else None

def _order_blocks(w, a, bull, tf):
    out = []; n = len(w); sw = swings(w, LEFT, RIGHT); want = 'H' if bull else 'L'
    for i in range(7, n - 1):
        c = w[i]; nxt = w[i + 1]
        if not a[i]: continue
        if bull and not (c['c'] < c['o'] and nxt['c'] > nxt['o']): continue      # bearish candle, next one already goes our way = the LAST opposite candle
        if not bull and not (c['c'] > c['o'] and nxt['c'] < nxt['o']): continue
        prior = [p for k, p, kind in sw if kind == want and k + RIGHT <= i]
        if not prior: continue
        lvl = prior[-1]; imp = w[i + 1: i + 1 + IMP_BARS]
        if bull:
            if not (max(x['c'] for x in imp) - c['h'] >= IMP_ATR * a[i] and any(x['c'] > lvl for x in imp)): continue      # displacement AND structure broken
            if any(x['c'] < c['l'] for x in w[i + 1:]): continue                      # a close through the zone = used up
            touched = any(x['l'] <= c['h'] for x in w[i + 1 + IMP_BARS:])
        else:
            if not (c['l'] - min(x['c'] for x in imp) >= IMP_ATR * a[i] and any(x['c'] < lvl for x in imp)): continue
            if any(x['c'] > c['h'] for x in w[i + 1:]): continue
            touched = any(x['h'] >= c['l'] for x in w[i + 1 + IMP_BARS:])
        out.append({'side': 'buy' if bull else 'sell', 'kind': 'ob', 'tf': tf, 'lo': c['l'], 'hi': c['h'], 't': c['t'], 'touched': touched})
    return out

def _fvgs(w, a, bull, tf):
    out = []
    for j in range(2, len(w)):
        c0, c1, c2 = w[j - 2], w[j - 1], w[j]; ai = a[j - 1]
        if not ai or abs(c1['c'] - c1['o']) < DISP_BODY * ai: continue
        if bull:
            if not (c1['c'] > c1['o'] and c2['l'] - c0['h'] >= FVG_ATR * ai): continue
            lo, hi = c0['h'], c2['l']
            if any(x['c'] < lo for x in w[j + 1:]): continue
            touched = any(x['l'] <= hi for x in w[j + 1:])
        else:
            if not (c1['c'] < c1['o'] and c0['l'] - c2['h'] >= FVG_ATR * ai): continue
            lo, hi = c2['h'], c0['l']
            if any(x['c'] > hi for x in w[j + 1:]): continue
            touched = any(x['h'] >= lo for x in w[j + 1:])
        out.append({'side': 'buy' if bull else 'sell', 'kind': 'fvg', 'tf': tf, 'lo': lo, 'hi': hi, 't': c1['t'], 'touched': touched})
    return out

def find_zones(w, bull, tf='m15'):
    """Demand zones (bull=True) or supply zones (bull=False) in the candles w, newest first, at most MAX_ZONES. Zones already closed through are dropped."""
    if len(w) < 20: return []
    a = atr(w)
    z = _order_blocks(w, a, bull, tf) + _fvgs(w, a, bull, tf)
    z.sort(key=lambda q: q['t'], reverse=True)
    return z[:MAX_ZONES]

def touching(bar, z):
    """True when the candle's range overlaps the zone (price is back in the zone)."""
    return bar['l'] <= z['hi'] and bar['h'] >= z['lo']

def scan(m, h):
    """Steps 1 + 2 together. None = trends disagree or not enough data. Else {'bias': 'up'|'down', 'zones': [...]} - only demand zones when up, only supply zones when down."""
    d = bias(m, h)
    if d is None: return None
    bull = d == 'up'
    H = _htf_done(m, h)
    z = find_zones(m[-M15_WINDOW:], bull, 'm15') + find_zones(H[-H1_WINDOW:], bull, 'h1')
    z.sort(key=lambda q: q['t'], reverse=True)
    return {'bias': d, 'zones': z}
