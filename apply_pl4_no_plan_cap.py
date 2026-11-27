"""PL4: a managed plan is no longer capped at 0.06 lot. Lot per entry = one 0.01 for each $10 of plan ($10 -> 0.01 ... $60 -> 0.06 as before, $100 -> 0.10, $1000 -> 1.00).
Patches backend/burst.py and tests/test_plan_lot.py. Safe to run twice."""
p = 'backend/burst.py'; s = open(p, encoding='utf-8').read()
if 'PL4' in s: print(p, 'already patched, skipping')
else:
    pairs = [
     ("never above SAFE_MAX_LOT. Bad/zero plan -> 0.0 (no plan).\"\"\"", "no upper cap (PL4). Bad/zero plan -> 0.0 (no plan).\"\"\""),
     ("    return round(min(SAFE_MAX_LOT, max(SMALLEST_LOT, int(v // 10) * LOT_STEP)), 2)", "    return round(max(SMALLEST_LOT, int(v // 10) * LOT_STEP), 2)          # PL4: no 0.06 cap for a plan"),
     ("(one 0.01 for each $10 of plan, never above %g). Your account balance does not change this.' % (g['plan_usd'], eff, SAFE_MAX_LOT)", "(one 0.01 for each $10 of plan). Your account balance does not change this.' % (g['plan_usd'], eff)"),
    ]
    for old, new in pairs:
        assert s.count(old) == 1, 'anchor missing: ' + old[:50]
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s); print(p, 'patched')
t = 'tests/test_plan_lot.py'; u = open(t, encoding='utf-8').read()
if '(99, 0.09)' in u: print(t, 'already patched, skipping')
else:
    a = "(99, 0.06), (100, 0.06), (1000, 0.06)"; assert u.count(a) == 1, 'test anchor missing'
    open(t, 'w', encoding='utf-8').write(u.replace(a, "(99, 0.09), (100, 0.10), (200, 0.20), (1000, 1.0)")); print(t, 'patched')
