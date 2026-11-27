"""PL5: the tiny-account check (refuse a trade when the smallest lot would lose more than X% of the balance at the stop) becomes per account.
Plan accounts: OFF by default (0), the buyer may set their own percent (0-100). Everyone else: the owner's global setting (default 10), unchanged.
Patches backend/burst.py, backend/app.py and three test files. Safe to run twice."""
def patch(path, pairs, tag):
    s = open(path, encoding='utf-8').read()
    if tag in s: print(path, 'already patched, skipping'); return
    for old, new, n in pairs:
        assert s.count(old) == n, '%s anchor count %d != %d: %s' % (path, s.count(old), n, old[:50])
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s); print(path, 'patched')

patch('backend/burst.py', [
 ("def tiny_pct():\n", "def tiny_pct(uid=''):\n", 1),
 ("    \"\"\"LS5: refuse a trade when even the broker's smallest lot would lose more than this percent of the balance at the stop. 0 = check off. Default 10.\"\"\"\n",
  "    \"\"\"LS5: refuse a trade when even the broker's smallest lot would lose more than this percent of the balance at the stop. 0 = check off. Default 10.\n    PL5: an account with a managed plan uses its own number instead (default 0 = off).\"\"\"\n    if plan_active(uid): return float(get(uid)['tiny_pct'])\n", 1),
 ("            'plan_usd': _clamp(j.get('plan_usd'), 0, PLAN_MAX, 0, int),", "            'tiny_pct': round(_clamp(j.get('tiny_pct'), 0, 100, 0.0, float), 1),          # PL5: plan accounts only; 0 = check off\n            'plan_usd': _clamp(j.get('plan_usd'), 0, PLAN_MAX, 0, int),", 1),
 ("    if 'plan_usd' in d:          # PL1:", "    if 'tiny_pct' in d:          # PL5\n        try: tp5 = float('nan') if isinstance(d['tiny_pct'], bool) else float(d['tiny_pct'])\n        except (TypeError, ValueError): tp5 = float('nan')\n        if tp5 != tp5 or not (0 <= tp5 <= 100): raise ValueError('Tiny-account check must be from 0 (off) to 100 percent')\n        new['tiny_pct'] = round(tp5, 1)\n    if 'plan_usd' in d:          # PL1:", 1),
], 'PL5')
patch('backend/app.py', [("burst.tiny_pct()", "burst.tiny_pct(who)", 2)], 'burst.tiny_pct(who)')
patch('tests/test_lot_rules.py', [("app.count(\"['tiny_pct'] = burst.tiny_pct()\") == 2", "app.count(\"['tiny_pct'] = burst.tiny_pct(who)\") == 2", 1)], 'tiny_pct(who)')
patch('tests/mutate_lot_rules.py', [("\"; s['tiny_pct'] = burst.tiny_pct()\"", "\"; s['tiny_pct'] = burst.tiny_pct(who)\"", 1), ("\"; bk['tiny_pct'] = burst.tiny_pct()\"", "\"; bk['tiny_pct'] = burst.tiny_pct(who)\"", 1)], 'tiny_pct(who)')
patch('tests/test_burst1.py', [("'plan_usd': 0})", "'plan_usd': 0, 'tiny_pct': 0.0})", 1)], 'tiny_pct')
