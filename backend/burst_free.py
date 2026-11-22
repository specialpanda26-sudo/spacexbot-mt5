"""BT4/BT7: burst with no strategy signal, capped. When burst is on and quiet, but no strategy sees a setup, the bot may still open ONE burst group on plain
short-term momentum (price above a rising 20 EMA = buy, below a falling one = sell). A strict hourly cap keeps it from firing all day: owner setting
burst_free_per_hour (default 2 groups an hour per person, 0 = off). Every other burst rule still applies (quiet minutes, loss limits, ceiling, news lock).
BT7 'trade every minute' (the person's own switch, off by default): the cap is the owner setting burst_minute_per_hour (default 30, 1 to 60) and, when
there is no clear momentum, the direction of the last 5 candles decides (a plain guess, never a tested edge).
Nothing here claims it makes money: it is a scalp on momentum, not a tested strategy. Only a demo run or tools/backtest.py can say how it does."""
import json, time
from . import store as st, indicators as ind

HOUR = 3600


def per_hour(minute=False):
    k, d, lo, hi = ('burst_minute_per_hour', 30, 1, 60) if minute else ('burst_free_per_hour', 2, 0, 12)
    try: v = int(float(st.get(k)))
    except (TypeError, ValueError): v = d
    return max(lo, min(hi, v))


def _key(uid, minute): return ('bmin:' if minute else 'bfree:') + (uid or '')


def _hist(uid, minute=False):
    try: j = json.loads(st.get(_key(uid, minute)) or '[]')
    except (TypeError, ValueError): j = []
    return [int(t) for t in j if isinstance(t, (int, float)) and not isinstance(t, bool)] if isinstance(j, list) else []


def used(uid='', now=None, minute=False):
    now = now or time.time(); return len([t for t in _hist(uid, minute) if now - t < HOUR])


def mark(uid='', now=None, minute=False):
    now = now or time.time(); st.put(_key(uid, minute), json.dumps([t for t in _hist(uid, minute) if now - t < HOUR] + [int(now)]))


def side(m):
    """'buy' / 'sell' / None from the last candles. Needs 30 candles and a clear move (at least 0.2 ATR over the last 3 candles), flat means None."""
    if not m or len(m) < 30: return None
    c = [x['c'] for x in m]; e = ind.ema(c, 20); a = ind.atr(m)[-1]
    if not a: return None
    mv = c[-1] - c[-4]
    if c[-1] > e[-1] and e[-1] > e[-4] and mv >= 0.2 * a: return 'buy'
    if c[-1] < e[-1] and e[-1] < e[-4] and -mv >= 0.2 * a: return 'sell'
    return None


def side_any(m):
    """BT7: the direction of the last 5 candles, however small ('buy' up, 'sell' down). None only when the price did not move at all."""
    if not m or len(m) < 30: return None
    mv = m[-1]['c'] - m[-6]['c']
    return 'buy' if mv > 0 else 'sell' if mv < 0 else None


def setup(uid, m, now=None, minute=False):
    """-> a setup dict shaped like brain.evaluate's, or None (cap reached, switched off, or no direction). Stop 1 ATR away, target 1 ATR away."""
    n = per_hour(minute)
    if n <= 0 or used(uid, now, minute) >= n: return None
    sd = side(m) or (side_any(m) if minute else None)
    if not sd: return None
    entry = m[-1]['c']; a = ind.atr(m)[-1]; ax = ind.adx(m)[-1]
    sl = entry - a if sd == 'buy' else entry + a; tp = entry + a if sd == 'buy' else entry - a
    why = {'agree': ['burst_free'], 'against': 0, 'adx': round(ax, 1), 'atr': round(a, 5), 'sl_atr': 1.0, 'rr': 1.0, 'own_tp': False, 'solo': True, 'min_conf': 1, 'free': True}
    return {'side': sd, 'entry': round(entry, 5), 'sl': round(sl, 5), 'tp': round(tp, 5), 'strategy': 'burst_free', 'score': 1, 'adx': round(ax, 1), 'why': why, 'free': True}
