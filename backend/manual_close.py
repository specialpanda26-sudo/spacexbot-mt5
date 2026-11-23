"""MC1: owner switch 'I close the profits myself' (setting manual_close = 1, default 0, admin page checkbox).
When it is ON, for the OWNER only (uid '' or a signed-in admin's uid; subscribers are never touched):
 - MT5: the take-profit sent to the broker is moved far away (far_tp), a burst group gets a target no one reaches and no give-back guard, so the bot never banks a profit.
 - Deriv: no take_profit is put on the contract, and a group is not sold at its profit target (its live profit is still read, so the card and Floating P/L keep working).
Losses are NOT touched: the stop loss, the group loss limit, the daily and weekly limits and the streak stop all work as before.
Remember: with this ON nobody closes a winning trade except you. Switch it OFF when you are away."""
from . import store as st, limits

FAR = 1e9          # a group profit target nobody reaches
MULT = 20          # how many times the old stop-to-target distance the far take-profit is placed from the target


def on(uid=''):
    return st.get('manual_close') == '1' and limits._owner(uid)


def on_sig(sig):
    try: u = sig['uid']
    except (KeyError, IndexError, TypeError): u = ''
    return on(u or '')


def far_tp(side, sl, tp):
    """The same side of the price, but far away, so the broker never closes the trade at a profit. Unreadable numbers are returned unchanged."""
    try: sl, tp = float(sl), float(tp)
    except (TypeError, ValueError): return tp
    d = abs(tp - sl)
    if not d: return tp
    if str(side).lower() == 'buy': return round(tp + MULT * d, 5)
    return round(max(tp - MULT * d, tp * 0.05), 5)
