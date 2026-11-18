"""Section 3D: ATR trailing-stop exit simulation (video 3, Data Trader). Used by tools/backtest.py --trail.
The stop starts at the strategy's own stop and only ever moves in the trade's favour: it follows the best price reached minus mult x ATR.
Pessimistic rules: the stop is checked BEFORE the same bar can raise it, and a gap through the stop fills at the open (worse)."""

def trail_exit(side, entry, sl, bars, atr_val, mult=2.0, max_bars=200):
    """Returns (result_in_R, bars_used) or None if it cannot be simulated. R is measured against the original stop distance."""
    risk = abs(entry - sl)
    if risk <= 0 or not bars or atr_val <= 0 or mult <= 0: return None
    buy = side == 'buy'
    stop = sl; best = entry; used = 0; exit_px = None
    for b in bars[:max_bars]:
        used += 1
        if buy:
            if b['o'] <= stop: exit_px = b['o']; break           # gap through the stop
            if b['l'] <= stop: exit_px = stop; break
            best = max(best, b['h']); stop = max(stop, best - mult * atr_val)
        else:
            if b['o'] >= stop: exit_px = b['o']; break
            if b['h'] >= stop: exit_px = stop; break
            best = min(best, b['l']); stop = min(stop, best + mult * atr_val)
    if exit_px is None: exit_px = bars[min(len(bars), max_bars) - 1]['c']   # out of time: close at market
    r = (exit_px - entry) / risk if buy else (entry - exit_px) / risk
    return r, used
