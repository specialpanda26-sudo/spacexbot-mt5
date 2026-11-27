"""PL3: a managed plan is STRICT about its lot. If a market's broker minimum lot is bigger than the plan lot, the trade is refused instead of quietly using the bigger minimum.
Patches backend/burst.py only (the EA and the Windows app already obey the max_lot_soft flag the server sends). Safe to run twice."""
p = 'backend/burst.py'; s = open(p, encoding='utf-8').read()
if 'PL3' in s: print(p, 'already patched, skipping')
else:
    old = "    return 1 if get(uid)['max_lot'] <= 0 else 0"
    assert s.count(old) == 1, 'anchor missing'
    s = s.replace(old, "    if plan_active(uid): return 0          # PL3: a managed plan is strict: never lift the lot to a bigger broker minimum, refuse the trade\n    return 1 if get(uid)['max_lot'] <= 0 else 0")
    open(p, 'w', encoding='utf-8').write(s); print(p, 'patched')
