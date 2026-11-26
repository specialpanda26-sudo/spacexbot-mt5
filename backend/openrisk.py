"""Total stop-loss ceiling for a managed account size (Section 2).
A person who picked a size on the Account-size card ($10 ... $60, presets.py) manages THAT much money, whatever the balance on the screen is.
 - basis      = the smaller of the size and the balance. Every new setup's risk percent is turned into a percent of the balance that equals the same
                percent of the basis, so a $10 size on a $1000 balance risks 1% of $10 = $0.10 a setup, not $10. The EA already sizes lots from the
                risk_pct it is sent, so nothing changes in the EA.
 - ceiling    = size x 50% (presets.OPEN_RISK_PCT): the most ALL open entries together may lose if every stop loss hit, however many setups are open.
 - used       = the worst case of everything open or on the way (open, pending, sent), in USD: each entry's risk percent x the balance.
 - waiting    = when no room is left for even one more entry the gate says 'open stop-loss ceiling reached' and the bot WAITS. Trades are NEVER closed
                because of this ceiling; every trade keeps its own stop loss and take profit.
 - fit()      = a normal setup keeps the risk of ONE entry at (setup risk / entries wanted). When the room left is smaller than the whole setup, fewer
                entries open so the total fits (3 of 6 entries use half the risk); none fit = wait.
Nobody who has not picked a size is touched: managed() is None, every function returns the old behaviour. The owner / admin scope is never managed.
Nothing here claims it makes money: it only limits how much can be at risk at once. With a small risk per setup (1% of the size) the ceiling is a
hard backstop that rarely binds; it matters when the person raises the risk per trade or opens many setups."""
from . import store as st

EPS = 1e-9


def managed(uid=''):
    """The size (10..60) this person manages, or None (nobody picked one, or the owner scope)."""
    if not uid: return None
    from . import presets
    try: return presets.active(uid)
    except Exception: return None


def balance(uid=''):
    try: b = float((st.acct(uid) or {}).get('balance') or 0)
    except (TypeError, ValueError): b = 0.0
    return b if b == b and b > 0 else 0.0


def basis(uid=''):
    """The money the bot manages: the size, or the balance when that is smaller. Without a size it is simply the balance."""
    s, b = managed(uid), balance(uid)
    return min(float(s), b) if s and b > 0 else (float(s) if s else b)


def eff_base(uid, base):
    """The setup's risk percent as a percent of the BALANCE (what the EA multiplies). Unmanaged, or balance not above the size: unchanged."""
    s, b = managed(uid), balance(uid)
    if not s or b <= s: return float(base)
    return round(float(base) * s / b, 4)


def ceiling_usd(uid=''):
    """The most all open entries together may lose, in USD (0 = no ceiling because no size is picked)."""
    s = managed(uid)
    if not s: return 0.0
    from . import presets
    return round(s * presets.OPEN_RISK_PCT / 100.0, 2)


def used_usd(uid=''):
    """Worst-case loss of every entry open or on the way, in USD."""
    b = balance(uid)
    if b <= 0: return 0.0
    r = st.q("SELECT COALESCE(SUM(risk_pct),0) p FROM signals WHERE COALESCE(uid,'')=? AND status IN('open','pending','sent')", (uid or '',), True)
    try: p = float(r['p'] or 0)
    except (TypeError, ValueError): p = 0.0
    return round(b * p / 100.0, 2)


def room_usd(uid=''):
    """USD still free under the ceiling, or None when there is no ceiling."""
    c = ceiling_usd(uid)
    return None if c <= 0 else round(max(0.0, c - used_usd(uid)), 2)


def fit(uid, base, n):
    """-> (entries, risk percent of ONE entry). Unmanaged: (n, the normal shared risk), exactly as before. Managed: the entry risk is the setup risk / n and as many
    entries open as fit under the ceiling (0 = none fit, wait)."""
    n = max(1, int(n or 1))
    if not managed(uid): return n, (float(base) if n <= 1 else round(float(base) / n, 4))
    per = round(eff_base(uid, base) / n, 4); b = balance(uid); room = room_usd(uid)
    if b <= 0 or per <= 0 or room is None: return n, per          # balance not known yet: nothing can be measured, the gate and the EA's own checks still apply
    k = int((room + EPS) // (b * per / 100.0))
    return max(0, min(n, k)), per


def total_fits(uid, base):
    """For a group that shares ONE normal risk (burst, cycle): does that whole risk fit in the room left? Unmanaged: always True."""
    if not managed(uid): return True
    b, room = balance(uid), room_usd(uid)
    if b <= 0 or room is None: return True
    return eff_base(uid, base) * b / 100.0 <= room + EPS


def full(uid=''):
    """True when the person manages a size and no room is left for even the smallest entry (one entry of a setup of the most entries they allow)."""
    if not managed(uid): return False
    from . import links, multi
    b, room = balance(uid), room_usd(uid)
    if b <= 0 or room is None: return False
    base = links.risk(uid) if uid else st.fget('risk_pct')
    one = eff_base(uid, base) / max(1, multi.cap(uid)) * b / 100.0
    return room + EPS < one


def view(uid=''):
    """What the card shows."""
    s = managed(uid)
    if not s: return {'managed': None}
    c, u = ceiling_usd(uid), used_usd(uid)
    return {'managed': s, 'ceiling_usd': c, 'used_usd': u, 'room_usd': round(max(0.0, c - u), 2), 'waiting': bool(full(uid))}
