"""Confluence: trade only when MIN_CONFLUENCE enabled strategies agree on the side, with a regime filter:
reversion setups are skipped when ADX says strong trend, trend setups when ADX says dead range."""
from .strategies import ALL, REVERSION, TREND
from .indicators import atr, adx
from . import strategy_info as si

def _say(info, code, text, **kw):
    """Tell the caller WHY there is no setup. `info` is an optional dict the caller passes in; it never changes what evaluate returns."""
    if info is not None: info.clear(); info.update(dict(kw, code=code, text=text))

def _names(xs):
    xs = list(xs); return ', '.join(si.name(x) for x in xs[:3]) + (' and %d more' % (len(xs) - 3) if len(xs) > 3 else '')

def _filt_text(filt, ax, rev_max, trend_min):
    n = len(filt)
    kinds = {k for _, k in filt}
    why = ('ADX %.0f is a strong trend, so reversal setups are skipped above %g' % (ax, rev_max)) if kinds == {'rev'} else \
          ('ADX %.0f is a quiet market, so trend setups are skipped below %g' % (ax, trend_min)) if kinds == {'trend'} else \
          ('ADX %.0f: reversal setups are skipped in strong trends and trend setups in quiet markets' % ax)
    return '%d setup%s seen (%s) but skipped: %s.' % (n, '' if n == 1 else 's', _names([x for x, _ in filt]), why)

def evaluate(m15, h1, min_conf=2, rr=2.0, off=(), adx_trend_min=18.0, adx_rev_max=28.0, solo=(), info=None):
    if len(m15) < 120: _say(info, 'history', 'Not enough candle history yet (%d of 120 candles).' % len(m15)); return None
    ax = adx(m15)[-1]; hits = []; ran = 0; filt = []
    for fn in ALL:
        if fn.__name__ in off: continue
        ran += 1
        try: r = fn(m15, h1)
        except Exception as e: print('strategy error', fn.__name__, e); r = None
        if not r: continue
        if r['name'] in solo and not r.get('solo'): r = {**r, 'solo': True}          # admin switch 'may trade alone' (A3)
        if ax and r['name'] in REVERSION and ax > adx_rev_max: filt.append((r['name'], 'rev')); continue
        if ax and r['name'] in TREND and ax < adx_trend_min: filt.append((r['name'], 'trend')); continue
        hits.append(r)
    buys = [x for x in hits if x['side'] == 'buy']; sells = [x for x in hits if x['side'] == 'sell']
    if len(buys) == len(sells):
        if not hits and filt: _say(info, 'adx', _filt_text(filt, ax, adx_rev_max, adx_trend_min), ran=ran, adx=round(ax, 1), filtered=[n for n, _ in filt])
        elif not hits: _say(info, 'none', ('None of the %d strategies saw a setup on this candle.' % ran) if ran else 'All strategies are switched off.', ran=ran, adx=round(ax, 1))
        else: _say(info, 'split', 'The strategies disagreed: %s said buy, %s said sell, so it stayed out.' % (_names([x['name'] for x in buys]), _names([x['name'] for x in sells])), ran=ran, adx=round(ax, 1))
        return None
    grp, side = (buys, 'buy') if len(buys) > len(sells) else (sells, 'sell')
    if len(grp) < min_conf and not any(x.get('solo') for x in grp):
        _say(info, 'conf', 'Only %d strateg%s (%s) saw a %s, and %d must agree before it trades.' % (len(grp), 'y' if len(grp) == 1 else 'ies', _names([x['name'] for x in grp]), side, min_conf), ran=ran, adx=round(ax, 1), filtered=[n for n, _ in filt]); return None
    entry = m15[-1]['c']; a = atr(m15)[-1]
    sl = min(x['sl'] for x in grp) if side == 'buy' else max(x['sl'] for x in grp)   # widest = safest
    dist = abs(entry - sl)
    if not (0.5 * a <= dist <= 3.5 * a):
        _say(info, 'stop', 'A %s setup (%s) was found, but its stop loss was %.1f ATR away and the bot only allows 0.5 to 3.5.' % (side, _names([x['name'] for x in grp]), dist / a if a else 0.0), ran=ran, adx=round(ax, 1)); return None
    tp = entry + rr * dist if side == 'buy' else entry - rr * dist
    if len(grp) == 1 and grp[0].get('tp'):      # a lone strategy that brings its own target (video-1 setup)
        t = grp[0]['tp']
        if (side == 'buy' and t > entry) or (side == 'sell' and t < entry): tp = t
    why = {'agree': [x['name'] for x in grp], 'against': len(sells if side == 'buy' else buys), 'adx': round(ax, 1),
           'regime': 'strong trend' if ax > adx_rev_max else 'quiet' if ax < adx_trend_min else 'moderate',
           'atr': round(a, 5), 'sl_atr': round(dist / a, 2) if a else None, 'rr': round(abs(tp - entry) / dist, 2) if dist else None,
           'own_tp': bool(len(grp) == 1 and grp[0].get('tp') and tp == grp[0]['tp']), 'solo': len(grp) < min_conf, 'min_conf': min_conf}
    return {'side': side, 'entry': round(entry, 5), 'sl': round(sl, 5), 'tp': round(tp, 5),
            'strategy': '+'.join(x['name'] for x in grp), 'score': len(grp), 'adx': round(ax, 1), 'why': why}
