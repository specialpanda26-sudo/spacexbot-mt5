"""Video 2, section 1: registers pa_bos. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import sys
EDITS = [
 ('backend/strategies.py', "ALL = [jg_pullback,", "from .pa_structure import pa_bos\nALL = [pa_bos, jg_pullback,", 'from .pa_structure import pa_bos'),
]
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) or open(path, encoding='utf-8', newline='').read()
    if marker in t: print('already applied:', path, marker[:40]); new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:50]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
