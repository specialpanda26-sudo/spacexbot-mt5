"""C4 apply: wires backend/guide.py + static/guide.js into the app. Needs those files and tests/test_c4.py pasted first (and C3 applied).
Every old text must appear exactly once or NOTHING is changed. Safe to run twice (marker check). Each file is written to .tmp then os.replace."""
import os, sys, subprocess
for f in ('backend/guide.py', 'static/guide.js', 'tests/test_c4.py', 'backend/roadmap.py'):
    if not os.path.exists(f): print('STOP: missing', f); sys.exit(1)
APP, IDX = 'backend/app.py', 'static/index.html'
ROUTE = '''@app.get('/api/guide')
@need(verified=True)
def guide_get(u):
    """C4: the cartoon how-to steps (same text the PDF guide will use)."""
    return jsonify(guide.view())

@app.get('/api/path')'''
E = [
 (APP, 'from . import btc_switch, tradeon, course, roadmap\n', 'from . import btc_switch, tradeon, course, roadmap, guide\n', 'course, roadmap, guide'),
 (APP, "@app.get('/api/path')", ROUTE, "@app.get('/api/guide')"),
 (IDX, '<script src="/static/roadmap.js"></script>', '<script src="/static/roadmap.js"></script><script src="/static/guide.js"></script>', '/static/guide.js'),
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
r = subprocess.run([sys.executable, 'tests/test_c4.py'], capture_output=True, text=True)
print((r.stdout.strip().splitlines() or ['no output'])[-1]); print(r.stderr[-300:]); sys.exit(r.returncode)
