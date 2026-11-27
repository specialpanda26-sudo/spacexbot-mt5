"""LS4: setup-strength lot scaling. Automatic mode only: a normal setup keeps the base lot ceiling (the balance tier), a perfect setup
(burst_big_score or more strategies agree) gets one step (0.01) higher, never above the person's biggest lot. A typed biggest lot,
Smallest and Fixed are never raised. Nothing is removed. Safe to run twice."""
import sys
B, A = 'backend/burst.py', 'backend/app.py'
b = open(B, encoding='utf-8').read(); a = open(A, encoding='utf-8').read()
if 'LS4-start' in b: print('already done'); sys.exit(0)

anchor = "def lot_now(uid=''):"
add = '''# LS4-start
LOT_STEP = 0.01


def is_perfect(score):
    """LS4: a perfect setup = at least burst_big_score strategies agree (the same bar as a BIG burst)."""
    try: return int(score or 0) >= big_score()
    except (TypeError, ValueError): return False


def strength_cap(uid='', perfect=False):
    """LS4: the biggest lot for ONE trade given how strong the setup is. Normal setup = eff_max_lot (the base). Perfect setup in automatic mode
    with no typed biggest lot = one step (0.01) above the base, never above top_lot. Smallest, Fixed and a typed biggest lot are never raised."""
    g = get(uid); base = eff_max_lot(uid)
    if not perfect or g['lot_mode'] != 'auto' or g['max_lot'] > 0: return base
    return min(top_lot(uid), round(base + LOT_STEP, 2))
# LS4-end


'''
if anchor not in b: print('burst.py anchor missing'); sys.exit(1)
b = b.replace(anchor, add + anchor, 1)

pairs = [
 ("SELECT id,symbol,side,sl,tp,risk_pct FROM signals WHERE status='pending' AND COALESCE(uid,'')=? ORDER BY id LIMIT 1",
  "SELECT id,symbol,side,sl,tp,risk_pct,score FROM signals WHERE status='pending' AND COALESCE(uid,'')=? ORDER BY id LIMIT 1"),
 ("bk['max_lot'] = burst.eff_max_lot(who);", "bk['max_lot'] = burst.strength_cap(who, bk.get('kind') == 'big');"),
 ("s['max_lot'] = burst.eff_max_lot(who);", "s['max_lot'] = burst.strength_cap(who, burst.is_perfect(s.get('score')));"),
]
for o, n in pairs:
    if o not in a: print('app.py anchor missing:', o[:50]); sys.exit(1)
    a = a.replace(o, n, 1)
open(B, 'w', encoding='utf-8').write(b); open(A, 'w', encoding='utf-8').write(a); print('LS4 applied')
