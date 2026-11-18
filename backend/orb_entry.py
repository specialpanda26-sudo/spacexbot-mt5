"""Video 4 (Trade with Pat, 9:30 opening range breakout) - SECTION 4B: the entry after the displacement.
Rules from the video: section 4A finds the New York range and the displacement (3 or 4 big candles that CLOSE beyond the range) | in that push there is an
ENTRY MODEL: a level of DEMAND (for a push up) = the last RED candle before the big push, drawn like an order block, or a FAIR VALUE GAP inside the push |
then WAIT for price to come back to that level and give a reaction: wicks into it that it respects are a good sign | a bullish ENGULFING candle is liked but
RARE, it is a bonus and not required: 'a lot of the time I'm just entering when I see the demand zone holding' | stop below the demand zone (even a big one);
with a fair value gap the stop is around the MIDLINE of the range (or below the gap) | target about 1.5-1.6 R, about 2-2.2 R when the structure is very strong.
Sell side = the buy side on mirrored prices (supply = the last GREEN candle before a push down). Same video, same file: a push down only ever gives sells.
How the rules are built (the video gives no numbers, all tunables are assumptions kept at the top):
- the zone is alive until a candle CLOSES through its far side (a close below a demand zone = used up);
- 'holds' = a candle that touches the zone, is not red, and closes in the upper half of the zone or above it; the FIRST such candle after the push is the entry,
  so a zone fires once; the entry is that candle's close; the stop goes under the zone AND under that candle's wick (a wick through the zone is no hold for the stop);
- with a fair value gap the stop is the range midline when that is below the gap and within the brain's 0.5 to 3.5 ATR, else just below the gap;
- skipped (never reshaped): stop outside 0.5-3.5 ATR (what the brain accepts), entry later than WAIT_SEC after the push, entry at/after 16:00 New York,
  or price that already went past the push high and reached the target before it came back (the trade has played out).
- 4C (session analysis) will choose the direction later; this file takes whichever way the push went.
Not proven: only tools/backtest.py --solo on real data can say if it works. The brain gives it a fixed 2R target unless it trades alone (SOLO)."""
from datetime import datetime
from .indicators import atr
from . import orb_range as orb

ZONE_BACK = 3           # the opposite-colour candle before the push is searched this many candles back
FVG_ATR = 0.2           # a fair value gap must be at least this many ATR tall (assumption)
HOLD_FRAC = 0.5         # a holding candle closes at or above this fraction of the zone height (the middle)
BUF = 0.1               # stop buffer beyond the zone / wick, in ATR
SL_MIN, SL_MAX = 0.5, 3.5   # the brain's accepted stop distance, in ATR
RR = 1.6                # video: about 1.5 to 1.6
RR_STRONG = 2.2         # video: about 2 to 2.2 when the structure is very strong; assumption: a push of 4 or more big candles
STRONG_N = 4
WAIT_SEC = 10800        # assumption: the return must come within 3 hours of the push
SOLO = False            # False: needs another strategy to agree (the bot's confluence rule). True: may trade alone. Backtest first.

def _neg(c): return [{'t': x['t'], 'o': -x['o'], 'h': -x['l'], 'l': -x['h'], 'c': -x['c'], 'v': x.get('v', 1)} for x in c]

def _zones(c, a, d):
    """Entry zones of a push UP: the last red candle before it (order block), then every bullish fair value gap inside it. [{'kind','lo','hi'}]"""
    st, en = d['start'], d['end']; out = []
    for j in range(st - 1, max(st - 1 - ZONE_BACK, -1), -1):
        if c[j]['c'] < c[j]['o']: out.append({'kind': 'ob', 'lo': c[j]['l'], 'hi': c[j]['h']}); break
    for j in range(max(st + 1, 2), en + 1):
        c0, c2 = c[j - 2], c[j]
        if c2['l'] - c0['h'] >= FVG_ATR * a[j - 1]: out.append({'kind': 'fvg', 'lo': c0['h'], 'hi': c2['l']})
    return out

def _hit(c, en, z):
    """Index of the first candle after the push that touches the zone and holds it. None if the zone is used up first (a close below it) or never held."""
    for k in range(en + 1, len(c)):
        x = c[k]
        if x['c'] < z['lo']: return None
        if x['l'] <= z['hi'] and x['c'] >= x['o'] and x['c'] >= z['lo'] + HOLD_FRAC * (z['hi'] - z['lo']): return k
    return None

def _buy(c, r, d):
    """A BUY entry on the LAST candle of c, or None. c / r / d describe a push UP (mirror them for sells)."""
    last = len(c) - 1; en = d['end']                              # a push that is still running has no candle after it, so nothing can hold yet
    a = atr(c); x = c[last]
    stop_t = orb.ny_epoch(datetime.strptime(r['date'], '%Y-%m-%d').date(), orb.END_H, orb.END_M)
    if x['t'] >= stop_t or x['t'] - d['t_end'] > WAIT_SEC: return None
    hits = [z for z in _zones(c, a, d) if _hit(c, en, z) == last]
    if not hits: return None
    z = hits[0]; e = x['c']; ai = a[-1]
    if not ai: return None
    low = min(z['lo'], x['l'])
    sl = low - BUF * ai
    if z['kind'] == 'fvg' and r['mid'] < low and SL_MIN * ai <= e - r['mid'] <= SL_MAX * ai: sl = r['mid']
    dist = e - sl
    if not (SL_MIN * ai <= dist <= SL_MAX * ai): return None
    rr = RR_STRONG if d['n'] >= STRONG_N else RR
    tp = e + rr * dist
    top = max(c[k]['h'] for k in range(d['start'], en + 1))
    if tp > top and any(c[k]['h'] >= tp for k in range(en + 1, last + 1)): return None     # price already went past the push high and all the way to the target before it came back
    p = c[last - 1]
    engulf = p['c'] < p['o'] and x['c'] > x['o'] and x['c'] >= p['o'] and x['o'] <= p['c']
    return {'entry': e, 'sl': sl, 'tp': tp, 'kind': z['kind'], 'engulf': engulf, 'rr': rr, 'zone': (z['lo'], z['hi'])}

def entry(c):
    """The 4B entry on the last candle of c (any step that divides 15 minutes), or None. Returns {'side','entry','sl','tp','kind' ('ob'|'fvg'),
    'engulf' (bonus flag), 'rr', 'zone'}."""
    s = orb.scan(c)
    if not s or not s['disp']: return None
    r, d = s['range'], s['disp']
    if d['side'] == 'buy':
        res = _buy(c, r, d)
        return {'side': 'buy', **res} if res else None
    rm = {'mid': -r['mid'], 'date': r['date']}
    res = _buy(_neg(c), rm, dict(d, side='buy'))
    if not res: return None
    return {'side': 'sell', 'entry': -res['entry'], 'sl': -res['sl'], 'tp': -res['tp'], 'kind': res['kind'], 'engulf': res['engulf'], 'rr': res['rr'], 'zone': (-res['zone'][1], -res['zone'][0])}

def orb_entry(m, h):
    """Registered strategy (main chart = 15-minute candles)."""
    if len(m) < 30: return None
    res = entry(m)
    if not res: return None
    out = {'side': res['side'], 'sl': res['sl'], 'tp': res['tp'], 'name': 'orb_entry'}
    if SOLO: out['solo'] = True
    return out
