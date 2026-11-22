import sys, os
EDITS = [
 ('tools/make_email_gifs.py', "fill = None if step == 2 else col[step]; stroke = K if step == 2 else None",
  "fill = None if step == 2 else col[1 - step]; stroke = K if step == 2 else None          # ART9b", 'ART9b'),
 ('tests/test_rk5.py', "elif near(c, (47, 134, 224)): cnt['blue'] += 1",
  "elif near(c, (47, 134, 224)) or near(c, (86, 182, 255)): cnt['blue'] += 1          # ART9b", 'ART9b'),
]
if not all(os.path.isfile(p) for p, *_ in EDITS): print('STOP: run this from the repo folder'); sys.exit(1)
new = {}
for p, old, rep, mark in EDITS:
    t = open(p, encoding='utf-8', newline='').read()
    if mark in t: print('already applied'); sys.exit(0)
    if t.count(old) != 1: print('STOP: cannot find exactly once in', p); sys.exit(1)
    new[p] = t.replace(old, rep)
for p, t in new.items(): open(p, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
