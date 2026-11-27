"""LS6 mutation proof: breaks each lot rule on a COPY of the project, runs tests/test_lot_rules.py, and demands it goes red.
Run: python tests/mutate_lot_rules.py   (last line: N mutations, M survived; exit 1 if any survived). Your files are never touched."""
import os, sys, shutil, subprocess, tempfile
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
M = [
 ('0.06 cap raised to 0.14', 'backend/burst.py', 'SAFE_MAX_LOT = 0.06', 'SAFE_MAX_LOT = 0.14'),
 ('smallest tier cap too big', 'backend/burst.py', 'TIERS = ((30, 0.01),', 'TIERS = ((30, 0.05),'),
 ('tiers ignored (auto uses the plain cap)', 'backend/burst.py', 'return min(top, tier_cap(_balance(uid)))', 'return top'),
 ('perfect setup step can pass the cap', 'backend/burst.py', 'return min(top_lot(uid), round(base + LOT_STEP, 2))', 'return round(base + LOT_STEP, 2)'),
 ('perfect step is two lot steps, not one', 'backend/burst.py', 'LOT_STEP = 0.01', 'LOT_STEP = 0.02'),
 ('perfect step ignores the guards AND the cap', 'backend/burst.py', "or g['lot_mode'] != 'auto' or g['max_lot'] > 0: return base\n    return min(top_lot(uid), round(base + LOT_STEP, 2))", "or False: return base\n    return round(base + LOT_STEP, 2)"),
 ('perfect setup never gets the step', 'backend/burst.py', "if not perfect or", "if True or"),
 ('single path ignores setup strength', 'backend/app.py', "s['max_lot'] = burst.strength_cap(who, burst.is_perfect(s.get('score')))", "s['max_lot'] = burst.eff_max_lot(who)"),
 ('burst path ignores BIG kind', 'backend/app.py', "bk['max_lot'] = burst.strength_cap(who, bk.get('kind') == 'big')", "bk['max_lot'] = burst.eff_max_lot(who)"),
 ('server stops sending tiny_pct (single)', 'backend/app.py', "; s['tiny_pct'] = burst.tiny_pct(who)", ""),
 ('server stops sending tiny_pct (burst)', 'backend/app.py', "; bk['tiny_pct'] = burst.tiny_pct(who)", ""),
 ('desktop tiny check never refuses', 'desktop/engine.py', "if loss > acct['balance'] * pct / 100.0 + 1e-9:", "if loss > 1e18:"),
 ('desktop single trade skips the tiny check', 'desktop/engine.py', "        why = self.tiny_why(sig, i, acct, price, sl)          # LS5\n        if why: return why\n", ""),
 ('desktop burst group skips the tiny check', 'desktop/basket.py', "    why = e.tiny_why(bk, i, acct, price, sl)          # LS5\n    if why: return why\n", ""),
 ('desktop ignores the biggest lot', 'desktop/engine.py', "            cap = min(cap, ml)", "            cap = cap"),
 ('EA single trade skips the tiny check', 'ea/SpaceXBridge.mq5', "   if(tinyPct > 0)\n   {  // LS5: tiny-account check: even", "   if(false)\n   {  // LS5: tiny-account check: even"),
 ('EA burst group skips the tiny check', 'ea/SpaceXBridge.mq5', "   if(tinyPct > 0)\n   {  // LS5: tiny-account check for the whole group", "   if(false)\n   {  // LS5: tiny-account check for the whole group"),
 ('EA poll stops passing tiny_pct to the burst call', 'ea/SpaceXBridge.mq5', 'StringToDouble(JStr(res, "max_lot_soft")), StringToDouble(JStr(res, "tiny_pct")));\n      return;', 'StringToDouble(JStr(res, "max_lot_soft")), 0);\n      return;'),
]
def run(d):
    env = dict(os.environ); env['PYTHONDONTWRITEBYTECODE'] = '1'
    p = subprocess.run([sys.executable, 'tests/test_lot_rules.py'], cwd=d, capture_output=True, text=True, timeout=600, env=env)
    return p.returncode, p.stdout
base = tempfile.mkdtemp(prefix='sxb_mut_'); survived = 0
try:
    for name, f, old, new in M:
        d = os.path.join(base, 'p'); shutil.rmtree(d, ignore_errors=True); shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns('.git', 'node_modules', '__pycache__'))
        p = os.path.join(d, f); s = open(p, encoding='utf-8').read()
        if s.count(old) < 1: print('SKIP (anchor missing)', name); survived += 1; continue
        open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
        rc, out = run(d); red = rc != 0
        print('caught  ' if red else 'SURVIVED', name); survived += 0 if red else 1
finally: shutil.rmtree(base, ignore_errors=True)
print('%d mutations, %d survived' % (len(M), survived)); sys.exit(1 if survived else 0)
