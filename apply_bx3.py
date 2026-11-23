"""apply_bx3.py: makes the live-profit reading and its test safe on a slow phone. Run inside the repo folder: python apply_bx3.py
Every old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import os, sys, subprocess
PAIRS = [
('backend/openlive.py',
r'''FRESH = 150          # seconds a saved figure still counts (the Deriv round runs about every 60 s)
''',
r'''FRESH = 150          # seconds a saved figure still counts (the Deriv round runs about every 60 s)
SKEW = 5             # a reading saved up to this many seconds AFTER the caller's clock was taken still counts (a slow caller)
'''),
('backend/openlive.py',
r'''    if not 0 <= now - float(j['t']) <= FRESH: return None
''',
r'''    if not -SKEW <= now - float(j['t']) <= FRESH: return None
'''),
('tests/test_bx1.py',
r'''deriv._track(S(), UID, {'demo': True, 'currency': 'USD'})
g = openlive.get(UID)
''',
r'''deriv._track(S(), UID, {'demo': True, 'currency': 'USD'})
NOW = time.time()          # a slow phone spent seconds above; the reading was saved after the old NOW
g = openlive.get(UID)
'''),
]
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, t): open(p + '.tmp', 'w', encoding='utf-8').write(t); os.replace(p + '.tmp', p)
if not os.path.isdir('backend'): sys.exit('Run this inside the spacexbot-mt5 folder (the one with backend/).')
plan, todo, bad = {}, 0, []
for f, o, n in PAIRS:
    t = plan[f] if f in plan else rd(f)
    if n in t: plan[f] = t; continue
    if t.count(o) != 1: bad.append('%s: old text found %d times: %s' % (f, t.count(o), o[:60].replace(chr(10), ' '))); continue
    plan[f] = t.replace(o, n); todo += 1
if bad: sys.exit('NOTHING CHANGED. Problems:\n' + '\n'.join(bad))
for f, t in plan.items():
    if t != rd(f): wr(f, t)
print('applied %d changes' % todo if todo else 'already applied, nothing to do')
r = 0
for t in ('tests/test_bx1.py', 'tests/test_bx2.py', 'tests/test_live3.py'):
    p = subprocess.run([sys.executable, t], capture_output=True, text=True); last = (p.stdout.strip().splitlines() or ['?'])[-1]
    print(('OK   ' if p.returncode == 0 else 'FAIL ') + t + '  ' + last); r |= p.returncode
print('ALL GOOD' if r == 0 else 'SOMETHING FAILED: send me the FAIL lines'); sys.exit(r)
