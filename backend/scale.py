"""Auto-scale: open more entries on a setup ONLY while recent setups have been winning. Pure maths on closed trades, no guessing.
Rule (all must hold): at least MIN_SETUPS recent setups, win rate >= WIN_RATE, net profit > 0, and the last 2 setups not both losses.
Setups opened together (same grp) count as one. Past wins do not predict the next trade: the entries still SHARE one trade's risk,
so total risk stays the same. A single loss streak turns it off again on the very next signal."""
from . import store as st, risk

MIN_SETUPS, LOOK, WIN_RATE = 8, 12, 0.6

def recent(uid='', strategy=''):
    rows = st.q("SELECT pnl,closed,grp,strategy FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? ORDER BY closed DESC LIMIT ?", (uid, LOOK * 12))
    if strategy: rows = [r for r in rows if strategy in (r['strategy'] or '').split('+')]
    return risk._setups(rows)[:LOOK]

def hot(uid='', strategy=''):
    """-> (bool, plain sentence). The sentence says why, so the journal / status can show it."""
    s = recent(uid, strategy); n = len(s)
    if n < MIN_SETUPS: return False, 'Only %d recent setup%s (needs %d) so it keeps to one entry.' % (n, '' if n == 1 else 's', MIN_SETUPS)
    w = sum(1 for x in s if x['pnl'] > 0); net = sum(x['pnl'] for x in s)
    if net <= 0: return False, 'Last %d setups lost money overall, so it keeps to one entry.' % n
    if w / n < WIN_RATE: return False, 'Won %d of the last %d setups (needs %d%%), so it keeps to one entry.' % (w, n, int(WIN_RATE * 100))
    if s[0]['pnl'] <= 0 and s[1]['pnl'] <= 0: return False, 'The last 2 setups lost, so it keeps to one entry.'
    return True, 'Won %d of the last %d setups and is net positive, so more entries are allowed.' % (w, n)
