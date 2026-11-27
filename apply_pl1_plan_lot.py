"""PL1: managed account plan -> lot per entry ($10 -> 0.01 ... $60 -> 0.06). Patches backend/burst.py and tests/test_burst1.py. Safe to run twice."""
p = 'backend/burst.py'; s = open(p, encoding='utf-8').read()
if 'PL1' in s:
    print('burst.py already patched, skipping')
else:
    def rep(old, new):
        global s
        assert s.count(old) == 1, 'anchor missing: ' + old[:50]
        s = s.replace(old, new)
    rep("LOT_MODES = ('smallest', 'fixed', 'auto')",
        "LOT_MODES = ('smallest', 'fixed', 'auto', 'plan')\nPLAN_MIN, PLAN_MAX = 10, 1000          # PL1: managed account plan in USD. Lot per entry = plan / 1000 ($10 -> 0.01, $20 -> 0.02 ... $60 -> 0.06), never above SAFE_MAX_LOT")
    rep("def get(uid=''):\n    \"\"\"The person's choices",
        'def plan_lot(plan):\n'
        '    """PL1: lot per entry for a managed plan of `plan` USD: one 0.01 step per $10, rounded DOWN, at least 0.01, never above SAFE_MAX_LOT. Bad/zero plan -> 0.0 (no plan)."""\n'
        '    try: v = float(plan)\n'
        '    except (TypeError, ValueError): return 0.0\n'
        '    if v != v or v < PLAN_MIN: return 0.0\n'
        '    return round(min(SAFE_MAX_LOT, max(SMALLEST_LOT, int(v // 10) * LOT_STEP)), 2)\n\n\n'
        "def get(uid=''):\n    \"\"\"The person's choices")
    rep("'lot_mode': _mode(j),          # LS1: smallest | fixed | auto",
        "'lot_mode': _mode(j),          # LS1: smallest | fixed | auto | plan (PL1)\n            'plan_usd': _clamp(j.get('plan_usd'), 0, PLAN_MAX, 0, int),          # PL1: 0 = no managed plan")
    rep("    m = j.get('lot_mode')\n    if m in LOT_MODES: return m",
        "    if _clamp(j.get('plan_usd'), 0, PLAN_MAX, 0, int) >= PLAN_MIN: return 'plan'          # PL1: a managed plan always decides the lot\n    m = j.get('lot_mode')\n    if m in LOT_MODES and m != 'plan': return m")
    rep("    g = get(uid); top = top_lot(uid)\n    if g['max_lot'] > 0 or g['lot_mode'] != 'auto': return top",
        "    g = get(uid); top = top_lot(uid)\n    if g['lot_mode'] == 'plan': return plan_lot(g['plan_usd'])          # PL1: the plan IS the ceiling, whatever the account balance is\n    if g['max_lot'] > 0 or g['lot_mode'] != 'auto': return top")
    rep("    g = get(uid)\n    if g['lot_mode'] == 'smallest': return SMALLEST_LOT",
        "    g = get(uid)\n    if g['lot_mode'] == 'plan': return plan_lot(g['plan_usd'])          # PL1\n    if g['lot_mode'] == 'smallest': return SMALLEST_LOT")
    rep("    if g['lot_mode'] == 'smallest': msg = 'Every MT5 trade uses the smallest lot",
        "    if g['lot_mode'] == 'plan': msg = 'Managed $%d plan: every entry uses %g lot (one 0.01 for each $10 of plan, never above %g). Your account balance does not change this.' % (g['plan_usd'], eff, SAFE_MAX_LOT)          # PL1\n    elif g['lot_mode'] == 'smallest': msg = 'Every MT5 trade uses the smallest lot")
    rep("    if 'lot_mode' in d:          # LS1\n",
        "    if 'plan_usd' in d:          # PL1: 0 = no plan, else a whole number of USD from PLAN_MIN to PLAN_MAX\n"
        "        pv = d['plan_usd']\n"
        "        if not (isinstance(pv, bool) or not isinstance(pv, (int, float, str))) and str(pv).strip() in ('', '0'): pv = 0\n"
        "        if pv != 0: pv = _whole(pv, PLAN_MIN, PLAN_MAX, 'Managed plan (USD)')\n"
        "        new['plan_usd'] = pv\n"
        "        if pv >= PLAN_MIN: new['lot_mode'] = 'plan'\n"
        "        elif cur.get('lot_mode') == 'plan' or _mode(cur) == 'plan': new['lot_mode'] = 'auto'\n"
        "    if 'lot_mode' in d and not (new.get('plan_usd', cur.get('plan_usd', 0)) or 0) >= PLAN_MIN:          # LS1 (ignored while a plan is active: the plan decides)\n")
    open(p, 'w', encoding='utf-8').write(s); print('burst.py patched')
t = 'tests/test_burst1.py'; u = open(t, encoding='utf-8').read()
if "'plan_usd': 0})" in u: print('test_burst1 already patched, skipping')
else:
    a = "'lot': 0.0, 'max_lot': 0.0, 'lot_mode': 'auto'})"
    assert u.count(a) == 1, 'test_burst1 anchor missing'
    open(t, 'w', encoding='utf-8').write(u.replace(a, "'lot': 0.0, 'max_lot': 0.0, 'lot_mode': 'auto', 'plan_usd': 0})")); print('test_burst1 patched')
