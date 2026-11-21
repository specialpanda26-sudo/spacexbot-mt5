"""Auto mode: the owner switches it on and the bot locks the tested setup by itself.
The owner only chooses three things: trade amount (risk_pct, percent of account per trade), take profit (rr: the target is rr times the stop distance)
and stop loss limit (max_stop_atr: the widest stop the bot may use, in ATR; setups with a wider stop are skipped).
ON locks: only the KEEP strategies, 2 must agree, no one-strategy trades, no burst, no 5-minute scan, one entry per trade, no auto-switching of strategies.
Nothing here claims it makes money. KEEP is the list that was positive in both halves of 2 years of hourly gold; the demo trades must confirm it."""
from . import store as st

KEEP = ('awesome_osc', 'heikin_flip', 'psar_flip', 'macd_cross', 'supertrend_e200')
MIN_AGREE = 2

def on(): return st.get('auto_mode') == '1'

def _f(k, lo, hi, d):
    try: return max(lo, min(hi, float(st.get(k))))
    except (TypeError, ValueError): return d

def rr():
    """Take profit as a multiple of the stop distance. Auto mode keeps it between 1 and 4; off = the old setting untouched."""
    return _f('rr', 1.0, 4.0, 2.0) if on() else st.fget('rr')

def max_stop():
    """Widest stop in ATR. 3.5 is what the bot always used, so with nothing set nothing changes."""
    return _f('max_stop_atr', 0.8, 5.0, 3.5)

def positions():
    """Positions one trade opens in auto mode, 1 to 5."""
    return int(_f('auto_positions', 1, 5, 1))

def lock(off, solo, min_conf):
    """-> (off, solo, min_conf) the way auto mode wants them. Auto mode off: returned unchanged."""
    if not on(): return off, solo, min_conf
    from . import strategies as S
    return {f.__name__ for f in S.ALL if f.__name__ not in KEEP}, set(), MIN_AGREE
