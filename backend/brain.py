"""Confluence: trade only when MIN_CONFLUENCE enabled strategies agree on the side, with a regime filter:
reversion setups are skipped when ADX says strong trend, trend setups when ADX says dead range."""
from .strategies import ALL, REVERSION, TREND
from .indicators import atr, adx

def evaluate(m15, h1, min_conf=2, rr=2.0, off=(), adx_trend_min=18.0, adx_rev_max=28.0):
    if len(m15) < 120: return None
    ax = adx(m15)[-1]; hits = []
    for fn in ALL:
        if fn.__name__ in off: continue
        try: r = fn(m15, h1)
        except Exception as e: print('strategy error', fn.__name__, e); r = None
        if not r: continue
        if ax and r['name'] in REVERSION and ax > adx_rev_max: continue
        if ax and r['name'] in TREND and ax < adx_trend_min: continue
        hits.append(r)
    buys = [x for x in hits if x['side'] == 'buy']; sells = [x for x in hits if x['side'] == 'sell']
    if len(buys) == len(sells): return None
    grp, side = (buys, 'buy') if len(buys) > len(sells) else (sells, 'sell')
    if len(grp) < min_conf and not any(x.get('solo') for x in grp): return None
    entry = m15[-1]['c']; a = atr(m15)[-1]
    sl = min(x['sl'] for x in grp) if side == 'buy' else max(x['sl'] for x in grp)   # widest = safest
    dist = abs(entry - sl)
    if not (0.5 * a <= dist <= 3.5 * a): return None
    tp = entry + rr * dist if side == 'buy' else entry - rr * dist
    if len(grp) == 1 and grp[0].get('tp'):      # a lone strategy that brings its own target (video-1 setup)
        t = grp[0]['tp']
        if (side == 'buy' and t > entry) or (side == 'sell' and t < entry): tp = t
    return {'side': side, 'entry': round(entry, 5), 'sl': round(sl, 5), 'tp': round(tp, 5),
            'strategy': '+'.join(x['name'] for x in grp), 'score': len(grp), 'adx': round(ax, 1)}
