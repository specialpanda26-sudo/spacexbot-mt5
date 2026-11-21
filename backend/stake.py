"""Section 1: a bigger stake on strong setups (Deriv). Settings (owner, /api/admin/settings):
  stake_on 1/0 (default 1) | stake_very_pct (default 40) | stake_strong_pct (default 15) | stake_max_risk_pct (default 10).
Strength: very = 3+ strategies agree with ADX 25+, or 2+ agree with ADX 40+. strong = 2+ agree with ADX 25+. Anything else keeps the normal sizing.
Stake = that share of the balance, as the Deriv stake (the margin). The stop loss and take profit stay. If the stop would lose more than
stake_max_risk_pct of the balance, the stake is reduced until it does not. Applies to the owner's own bot, and to subscribers only on demo accounts.
Single entries only (a multi-entry setup keeps its normal shared risk). Nothing here claims a bigger stake makes more money."""
from . import store as st

def _f(k, d):
    try: return float(st.get(k))
    except (TypeError, ValueError): return d

def tier(score, adx):
    try: sc = int(score or 0); ax = float(adx or 0)
    except (TypeError, ValueError): return ''
    if (sc >= 3 and ax >= 25) or (sc >= 2 and ax >= 40): return 'very'
    if sc >= 2 and ax >= 25: return 'strong'
    return ''

def mark(sid, uid, score, adx):
    """Called when a signal is created. Remembers the stake share for that signal. Never raises: a failure here must not lose the signal."""
    try:
        if str(st.get('stake_on')) != '1': return
        if uid and st.acct(uid).get('demo') is not True: return
        t = tier(score, adx)
        p = _f('stake_very_pct', 40.0) if t == 'very' else _f('stake_strong_pct', 15.0) if t == 'strong' else 0.0
        if 0 < p <= 50: st.put('stake:%s' % sid, p)
    except Exception as e: print('[stake] mark failed', repr(e)[:80])

def max_risk():
    """The loss cap (percent of balance) the EA must respect for a big-stake trade. Same limits as the admin setting."""
    return max(0.5, min(25.0, _f('stake_max_risk_pct', 10.0)))

def pct(sid):
    try: return max(0.0, min(50.0, float(st.get('stake:%s' % sid) or 0)))
    except (TypeError, ValueError): return 0.0

def size(entry, sl, tp, bal, stake_pct, mult):
    """(stake, stop_loss_money, take_profit_money) or None. Same multiplier maths as deriv._size: loss at the stop = stake x multiplier x stop distance."""
    try: entry, sl, tp, bal, stake_pct, mult = float(entry), float(sl), float(tp), float(bal), float(stake_pct), float(mult)
    except (TypeError, ValueError): return None
    if not entry or entry == sl or entry == tp or bal <= 0 or stake_pct <= 0: return None
    frac = abs(entry - sl) / entry
    stake = bal * stake_pct / 100.0
    cap = bal * _f('stake_max_risk_pct', 10.0) / 100.0
    if stake * mult * frac > cap: stake = cap / (mult * frac)
    stake = round(stake, 2); risk = round(stake * mult * frac, 2)
    if stake < 1 or stake > bal * 0.5 or risk <= 0 or risk >= stake: return None
    return stake, risk, round(risk * abs(tp - entry) / abs(entry - sl), 2)
