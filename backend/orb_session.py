"""Video 4 (Trade with Pat, 9:30 opening range breakout) - SECTION 4C: the session analysis that chooses the ORB direction.
Rules (from the owner's plan): the ASIA session draws a range (its high and low) | LONDON then sweeps the Asia high or the Asia low | New York usually
REVERSES London's direction (London swept the high = New York sells, London swept the low = New York buys) | if London swept BOTH sides of the Asia range,
expect CONTINUATION in London's direction, not a reversal | no sweep = no opinion.
What is in this file:
  analyse(c)          the session read for the UTC day of the LAST candle: {'date','asia':(lo,hi),'swept_high','swept_low','london_dir','kind','bias'}
                      kind = 'reversal' | 'continuation' | None, bias = 'buy' | 'sell' | None. None when the data is not enough (see below).
  with_session(fn)    wraps ANY strategy: its trade is kept only when its side equals the session bias (no bias = dropped).
  orb_session         registered strategy = orb_entry wrapped in with_session, silent unless the setting orb_session is 1.
Not proven, and the video gives no numbers: every tunable below is an ASSUMPTION. Only tools/backtest.py --solo on real data can say if it works.
Assumptions: Asia = 00:00-07:00 UTC, London = 07:00-12:00 UTC (fixed UTC hours, like london_breakout; London daylight saving is NOT followed). A sweep = a London
candle whose WICK goes beyond the Asia high/low by at least SWEEP_ATR x ATR (a close beyond is not needed, and it may stay beyond). 'London's direction' when both
sides were swept = the London close against the London open. The analysis exists only once the London window is over (the last candle is at or after 12:00 UTC),
on Monday to Friday; at least COVER of the Asia and London candles must be present.
The ATR is read at the last Asia candle, so the answer for a day never changes as the day goes on.
Honest limits: it only reads candles of 15 minutes or finer (the chart steps orb_range accepts). It does not veto OTHER strategies (the brain was not touched).
When the switch is ON, an ORB trade that agrees with the session gets a SECOND vote (orb_entry + orb_session), so it can reach min_confluence 2 by itself;
an ORB trade against the session or with no session bias keeps its single vote and needs another strategy as before. Strategies do not see the symbol,
so the switch is global (gold, forex or BTC candles alike; Asia and London hours mean little for BTC)."""
import datetime as dt
from .indicators import atr
from .orb_entry import orb_entry

ASIA = (0, 7)              # UTC hours [start, end)
LONDON = (7, 12)           # UTC hours [start, end)
SWEEP_ATR = 0.1            # the wick must go beyond the Asia high/low by this many ATR (ties and tiny pokes are no sweep)
COVER = 0.8                # share of the expected candles that must be present in the Asia window and in the London window
SOLO = False

def on(key='orb_session'):
    """The switch lives in the store (default '0'). Anything wrong reading it = OFF."""
    try:
        from . import store as st
        return str(st.get(key)) == '1'
    except Exception:
        return False

def analyse(c):
    """The session read for the UTC day of the last candle, or None (not enough data, weekend, London not over, no usable Asia range)."""
    if len(c) < 30: return None
    step = c[-1]['t'] - c[-2]['t']
    if step <= 0 or step > 900 or 900 % step: return None
    t = c[-1]['t']; d0 = t - t % 86400
    if dt.datetime.fromtimestamp(t, dt.timezone.utc).weekday() > 4: return None          # Monday to Friday only
    a0, a1 = d0 + ASIA[0] * 3600, d0 + ASIA[1] * 3600
    l0, l1 = d0 + LONDON[0] * 3600, d0 + LONDON[1] * 3600
    if t < l1: return None                                                                  # London is not over yet
    asia = [x for x in c if a0 <= x['t'] < a1]; lon = [x for x in c if l0 <= x['t'] < l1]
    if len(asia) < COVER * (a1 - a0) / step or len(lon) < COVER * (l1 - l0) / step: return None
    hi = max(x['h'] for x in asia); lo = min(x['l'] for x in asia)
    ia = max(i for i, x in enumerate(c) if x['t'] < a1)                                    # last candle of the Asia window: the ATR is read here
    a = atr(c)[ia]
    if not a: return None
    sh = any(x['h'] > hi + SWEEP_ATR * a for x in lon)
    sl = any(x['l'] < lo - SWEEP_ATR * a for x in lon)
    ld = lon[-1]['c'] - lon[0]['o']; ldir = 'up' if ld > 0 else 'down' if ld < 0 else None
    kind = bias = None
    if sh and sl:                                                                           # both sides swept: continuation in London's direction
        if ldir: kind = 'continuation'; bias = 'buy' if ldir == 'up' else 'sell'
    elif sh: kind = 'reversal'; bias = 'sell'                                               # London took the high: New York is expected to go down
    elif sl: kind = 'reversal'; bias = 'buy'
    return {'date': dt.datetime.fromtimestamp(d0, dt.timezone.utc).strftime('%Y-%m-%d'), 'asia': (lo, hi), 'swept_high': sh, 'swept_low': sl, 'london_dir': ldir, 'kind': kind, 'bias': bias}

def with_session(fn, name=None):
    """Wrap ANY strategy: its trade is kept only when its side is the session bias. No session read, or no bias (None never equals a side) = dropped."""
    nm = name or fn.__name__ + '_session'
    def wrapped(m, h):
        r = fn(m, h)
        if not r: return None
        s = analyse(m)
        if not s or r['side'] != s['bias']: return None
        return dict(r, name=nm)
    wrapped.__name__ = nm
    return wrapped

_wrapped = with_session(orb_entry, 'orb_session')

def orb_session(m, h):
    """Registered strategy. Silent unless the setting orb_session is 1."""
    if not on('orb_session'): return None
    r = _wrapped(m, h)
    if r and SOLO: r = dict(r, solo=True)
    return r
