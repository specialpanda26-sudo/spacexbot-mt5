"""D4c: move acctPick() inside the A4 block so the card code runs on its own (test_sigtext). Run: python apply_d4c_fix.py
Safe to run twice. If an old text is not found exactly once, NOTHING is changed."""
import os, sys, subprocess
I = 'static/index.html'
t = open(I, encoding='utf-8').read()
s = t.find('  function acctPick() {'); e = t.find('\n  }\n', s) + 5
if t.count('function acctPick()') != 1 or s < 0 or e < 5: print('STOP: acctPick not found exactly once. Nothing was changed.'); sys.exit(1)
fn = t[s:e]
if t.find('/*A4-start*/') < s < t.find('/*A4-end*/') and t.count('var ACCT = "FBS";') == 1: print('skip (already inside A4)')
else:
    fn = fn.replace('ACCT === n', '(typeof ACCT !== "undefined" ? ACCT : "FBS") === n')
    t2 = t[:s] + t[e:]
    if t2.count('/*A4-start*/') != 1: print('STOP: A4 marker not found once. Nothing was changed.'); sys.exit(1)
    t2 = t2.replace('/*A4-start*/', '/*A4-start*/\n' + fn, 1)
    open(I + '.new', 'w', encoding='utf-8').write(t2); os.replace(I + '.new', I); print('edited:', I)
bad = []
for f in ('test_sigtext.py', 'test_d4b.py', 'test_d4.py', 'test_d3b.py'):
    r = subprocess.run([sys.executable, 'tests/' + f], capture_output=True, text=True, timeout=120)
    print(f, (r.stdout.strip().splitlines() or ['?'])[-1])
    if r.returncode: bad.append(f)
print('RESULT:', 'PASS' if not bad else 'FAILED: ' + ', '.join(bad))
