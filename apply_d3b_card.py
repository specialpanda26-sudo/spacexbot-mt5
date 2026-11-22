"""D3b: load static/running.js. Run from the repo folder: python apply_d3b_card.py
Safe to run twice. If the old text is not found exactly once, NOTHING is changed. Runs only the related tests."""
import os, sys, subprocess
P = 'static/index.html'; OLD = '<script src="/static/guide.js"></script>'; NEW = OLD + '<script src="/static/running.js"></script>'; MK = '/static/running.js'
if not os.path.exists('static/running.js'): print('STOP: static/running.js is missing. Paste File 1 first.'); sys.exit(1)
t = open(P, encoding='utf-8').read()
if MK in t: print('skip (already there):', P)
elif t.count(OLD) != 1: print('STOP: guide.js tag found %d times. Nothing was changed.' % t.count(OLD)); sys.exit(1)
else:
    open(P + '.new', 'w', encoding='utf-8').write(t.replace(OLD, NEW, 1)); os.replace(P + '.new', P); print('edited:', P)
fails = []
for f in ('test_d3.py', 'test_d3b.py', 'test_c4.py', 'test_l1.py'):
    r = subprocess.run([sys.executable, 'tests/' + f], capture_output=True, text=True, timeout=300)
    print(f, (r.stdout.strip().splitlines() or ['?'])[-1])
    if r.returncode: fails.append(f)
print('RESULT:', 'RELATED TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
