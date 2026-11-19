"""R1: why the bot took a trade, in plain words. brain.evaluate() returns a 'why' dict; pack() saves it as JSON in signals.reason;
lines() turns it into sentences for the trade pop-up and short() into one line for the journal. Facts only: nothing here is invented, and a trade
saved before R1 has no reason (lines() = [], short() = ''), so the page says so instead of guessing."""
import json
from . import strategy_info as si

def pack(s):
    """A brain result -> JSON text for signals.reason. Never raises (a failure just means no reason is saved)."""
    try:
        w = dict(s.get('why') or {})
        w.setdefault('agree', [x for x in str(s.get('strategy') or '').split('+') if x])
        w.setdefault('adx', s.get('adx'))
        for k in ('side', 'entry', 'sl', 'tp', 'score'): w[k] = s.get(k)
        return json.dumps(w)[:1500]
    except Exception: return ''

def _load(raw):
    try: j = json.loads(raw) if raw else None
    except (TypeError, ValueError): return None
    return j if isinstance(j, dict) else None

def _n(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError): return None

def lines(raw, strategy=''):
    """Plain sentences, in order: the setup, the market, the stop, the target. [] when nothing was saved."""
    j = _load(raw)
    if not j: return []
    out = []; ag = [x for x in (j.get('agree') or []) if x] or [x for x in str(strategy or '').split('+') if x]
    names = ', '.join(si.name(x) for x in ag); side = str(j.get('side') or '').lower()
    if ag:
        k = len(ag); ag_n = int(_n(j.get('against')) or 0)
        t = ('%d strategies agreed on a %s: %s.' % (k, side, names)) if k > 1 else ('One strategy took this %s: %s.' % (side, names))
        if k == 1 and j.get('solo'): t += ' It is allowed to trade on its own.'
        if ag_n: t += ' %d other strateg%s pointed the other way.' % (ag_n, 'y' if ag_n == 1 else 'ies')
        out.append(t)
    if j.get('tf') == 'M5': out.append('Found on the 5-minute chart (fast scan). Its stop and target are sized from 5-minute candles.')
    adx = _n(j.get('adx')); rg = j.get('regime')
    if adx is not None:
        out.append('Market strength (ADX) was %.1f: %s.' % (adx, {'strong trend': 'a strong trend, so trend setups are favoured and reversal setups are skipped',
                   'quiet': 'a quiet, ranging market', 'moderate': 'a moderate market, both kinds of setup were allowed'}.get(rg, 'recorded for this trade')))
    sa = _n(j.get('sl_atr'))
    if sa is not None: out.append('The stop loss is %.1f x ATR (the normal candle range) from the entry; with several strategies the widest stop is used.' % sa)
    rr = _n(j.get('rr'))
    if rr is not None: out.append('The target is %s: %.1f times the distance to the stop.' % ('set by the strategy itself' if j.get('own_tp') else 'the usual reward-to-risk', rr))
    px = [(l, _n(j.get(k))) for l, k in (('entry', 'entry'), ('stop', 'sl'), ('target', 'tp'))]
    if all(v is not None for _, v in px): out.append('Planned prices: ' + ', '.join('%s %s' % (l, ('%.5f' % v).rstrip('0').rstrip('.')) for l, v in px) + '.')
    return out

def short(raw):
    """One short line for the journal list, or ''."""
    j = _load(raw)
    if not j: return ''
    ag = [x for x in (j.get('agree') or []) if x]; p = []
    if ag: p.append('%d strateg%s agreed' % (len(ag), 'y' if len(ag) == 1 else 'ies'))
    adx = _n(j.get('adx'))
    if adx is not None: p.append('ADX %.0f' % adx)
    rr = _n(j.get('rr'))
    if rr is not None: p.append('reward %.1fx risk' % rr)
    return ' · '.join(p)
