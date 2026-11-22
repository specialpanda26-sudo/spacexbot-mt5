"""C4 fix: the brand is Ogolla (two L), and the guide cartoons follow what the site already shows for the same topic. No new pictures.
Every old text must appear exactly once or NOTHING is changed. Safe to run twice (marker check). Each file is written to .tmp then os.replace."""
import os, sys, subprocess
for f in ('backend/guide.py', 'tests/test_c4.py', 'tests/test_c1.py', 'static/index.html'):
    if not os.path.exists(f): print('STOP: missing', f); sys.exit(1)
G, IDX, T1, T4 = 'backend/guide.py', 'static/index.html', 'tests/test_c1.py', 'tests/test_c4.py'
OLD4 = "T('brand line is Ogola Tech (double L)', j['brand'] == 'Powered by Ogola Tech' and 'Ogla' not in txt)\n"
NEW4 = """T('brand line is Ogolla Tech (two L, the owner is Ogolla)', j['brand'] == 'Powered by Ogolla Tech')
T('the one-L spelling is nowhere in the app files', not [f for f in glob.glob(os.path.join(ROOT, 'backend', '*.py')) + glob.glob(os.path.join(ROOT, 'static', '*.js')) + glob.glob(os.path.join(ROOT, 'emails', '*.html')) + [os.path.join(ROOT, 'static', 'index.html')] if 'Ogola' in open(f, encoding='utf-8').read()])
import backend.course as course
cm = {l['id']: l['art'] for l in course.LESSONS}; gm = {s['id']: s['art'] for s in guide.STEPS}
T('cartoons follow what the site already shows for the same topic', gm['signup'] == 'rocket' and gm['subscribe'] == 'coin' and gm['connect'] == 'plug' and gm['alerts'] == 'push' and gm['mode'] == cm['accounts'] and gm['signal'] == cm['signal'] and gm['safety'] == cm['rules'] and gm['start'] == cm['meet'])
"""
E = [
 (G, "'brand': 'Powered by Ogola Tech'", "'brand': 'Powered by Ogolla Tech'", "'brand': 'Powered by Ogolla Tech'"),
 (G, "S('signup', 'Sign up', 'mail',", "S('signup', 'Sign up', 'rocket',", "S('signup', 'Sign up', 'rocket',"),
 (G, "S('mode', 'Demo or real', 'shield',", "S('mode', 'Demo or real', 'plug',", "S('mode', 'Demo or real', 'plug',"),
 (G, "S('signal', 'Read a signal', 'doc',", "S('signal', 'Read a signal', 'phone',", "S('signal', 'Read a signal', 'phone',"),
 (IDX, 'Powered by Ogola Tech</span>', 'Powered by Ogolla Tech</span>', 'Powered by Ogolla Tech</span>'),
 (T1, 'the Ogola Tech credit', 'the Ogolla Tech credit', 'the Ogolla Tech credit'),
 (T1, 'footer credit Ogola Tech (double L)', 'footer credit Ogolla Tech (double L)', 'footer credit Ogolla Tech'),
 (T1, 'Powered by Ogola Tech</span>', 'Powered by Ogolla Tech</span>', 'Powered by Ogolla Tech</span>'),
 (T1, "'Ogla' not in S and 'Powered by Ogola Tech' in S)", "'Ogola' not in S and 'Powered by Ogolla Tech' in S)", "'Ogola' not in S and"),
 (T4, OLD4, NEW4, 'the one-L spelling is nowhere'),
]
data, bad = {}, False
for p, old, new, mark in E:
    s = data[p] if p in data else open(p, encoding='utf-8').read()
    data[p] = s
    if mark in s: print('skip (done):', mark[:40]); continue
    if s.count(old) != 1: print('STOP: need exactly once in', p, '->', old[:70].replace('\n', ' ')); bad = True; continue
    data[p] = s.replace(old, new)
if bad: print('Nothing was changed.'); sys.exit(1)
for p, s in data.items():
    if s != open(p, encoding='utf-8').read(): open(p + '.tmp', 'w', encoding='utf-8').write(s); os.replace(p + '.tmp', p); print('edited:', p)
ok = True
for t in ('tests/test_c4.py', 'tests/test_c1.py'):
    r = subprocess.run([sys.executable, t], capture_output=True, text=True); last = (r.stdout.strip().splitlines() or ['no output'])[-1]
    print(t + ':', last); ok = ok and r.returncode == 0
    if r.returncode: print(r.stdout[-400:], r.stderr[-300:])
sys.exit(0 if ok else 1)
