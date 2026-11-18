"""Readable names + one-line descriptions for every strategy (admin panel, alerts, signal cards). Facts only: no promise of profit.
EVERY strategy registered in backend/strategies.py needs a line here - tests/test_sinfo.py fails when one is missing, so add the line when you add a strategy.
Strategies you teach through the taught/ folder have no line here and fall back to a name made from their id."""

INFO = {
    'pa_level': ('Key level reaction', 'Price reacts at a support or resistance level that was touched 2+ times, with the trend (video 2).'),
    'pa_bos': ('Break of structure retest', 'Trend breaks, price retests the broken level and fails to make a new extreme (video 2).'),
    'pa_candle': ('Candle patterns', 'Engulfing, three line strike and morning/evening star, traded with the trend (video 2).'),
    'pa_pattern': ('Chart patterns', 'Double top/bottom and head and shoulders, entered when the neckline breaks (video 2).'),
    'pa_trendline': ('Trendline', 'Bounce off a trendline with 2+ touches, or a strong close through it (video 2).'),
    'ma_cross': ('20/50 EMA cross', 'The 20 EMA crosses the 50 EMA on the 1h chart, only in a trending market that followed past crosses (video 3).'),
    'ma_bounce': ('MA bounce', 'Price returns to the 50 MA that held before, with the stochastic oversold/overbought and a rejection (video 3).'),
    'psar_e200': ('Parabolic SAR + 200 EMA', 'Parabolic SAR flip, buys only above the 200 EMA and sells only below it (video 3).'),
    'supertrend_e200': ('Supertrend + 200 EMA', 'Supertrend changes direction, buys only above the 200 EMA and sells only below it (video 3).'),
    'gold_scalp': ('Liquidity sweep scalp', 'In a 15m demand/supply zone, price sweeps a swing low/high and closes back; 1h and 15m trends agree (video 5).'),
    'gold_scalp_c': ('Sweep scalp (safe entry)', 'Same as the sweep scalp, but waits for a market shift and a pullback into the zone that caused it before entering (video 5).'),
    'jg_pullback': ('Trend pullback', 'First lower-low (or higher-high) candle after a pullback in a clear trend (video 1).'),
    'ema_pullback': ('EMA pullback', 'Pullback to the 21 EMA in an EMA 50/200 trend, with RSI not stretched.'),
    'sr_retest': ('Level retest', 'A level touched 2+ times is broken, then retested and rejected.'),
    'fvg_retrace': ('Fair value gap retrace', 'Price returns into a fair value gap in the trend direction and rejects it.'),
    'london_breakout': ('London breakout', 'First close beyond the Asian range (00-07 UTC) during the London morning.'),
    'bb_reversion': ('Bollinger reversion', 'Close back inside the Bollinger band after an extreme, with RSI stretched. Skipped in strong trends.'),
    'macd_cross': ('MACD cross', 'MACD histogram crosses zero in the direction of the EMA 50/200 trend.'),
    'heikin_flip': ('Heikin-Ashi flip', 'Heikin-Ashi colour flip with no wick on the open side, with the trend.'),
    'psar_flip': ('Parabolic SAR flip', 'Parabolic SAR flips in the direction of the higher trend.'),
    'awesome_osc': ('Awesome Oscillator', 'Zero-line cross or saucer of the Awesome Oscillator, with the trend.'),
    'dual_thrust': ('Dual Thrust breakout', "Break of today's open by half the previous two days' range, 07-17 UTC."),
    'star_reversal': ('Shooting star / hammer', 'Shooting star at a 10-bar high or hammer at a 10-bar low with RSI stretched. Skipped in strong trends.'),
}

def _pretty(sid): return str(sid).replace('_', ' ').strip().capitalize() or 'Strategy'

def name(sid): return INFO[sid][0] if sid in INFO else _pretty(sid)
def desc(sid): return INFO[sid][1] if sid in INFO else 'Custom strategy you taught the bot.'

def label(strategy):
    """'ma_cross+gold_scalp' (what a signal stores) -> '20/50 EMA cross + Liquidity sweep scalp'."""
    parts = [p for p in str(strategy or '').split('+') if p]
    return ' + '.join(name(p) for p in parts)

def alert_body(strategy, entry, sl, tp):
    """Text of a new-signal alert (email + log): readable strategy name, entry, stop-loss and the target."""
    nm = label(strategy)
    return (nm + ': ' if nm else '') + 'Entry %s  SL %s  Target %s' % (entry, sl, tp)

def group(sid, trend, reversion):
    return 'trend' if sid in trend else 'reversion' if sid in reversion else 'other'

def listing(ids, trend, reversion, off=(), results=None, solo=()):
    """One row per strategy for the admin panel: id, name, desc, group, on (not switched off), and its closed-trade results (n, wins, win_rate, avg, pnl) or None."""
    res = results or {}; out = []
    for sid in ids:
        r = res.get(sid)
        out.append({'id': sid, 'name': name(sid), 'desc': desc(sid), 'group': group(sid, trend, reversion), 'on': sid not in off, 'solo': sid in solo,
                    'n': r['n'] if r else 0, 'wins': r['wins'] if r else 0, 'win_rate': r['win_rate'] if r else None,
                    'avg': (r.get('avg') if r.get('avg') is not None else round(r['pnl'] / r['n'], 2)) if r else None, 'pnl': r['pnl'] if r else None})
    return out
