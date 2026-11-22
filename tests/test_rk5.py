"""Checks Rk5: the 5 email cartoons use the rocket look (violet outline, yellow hair, blue body, shifted fill) and the legal pages swap to the new art. Needs Pillow.
Run: python tests/test_rk5.py"""
import os, re, sys, warnings
warnings.simplefilter('ignore')
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
tool = open(os.path.join(ROOT, 'tools', 'make_email_gifs.py'), encoding='utf-8').read()
page = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('tool uses the violet outline and the shifted fill', "'#7F61F5'" in tool and 'SH = ' in tool and '3.5, -3.5' in tool)
T('tool no longer uses the old dark-haired character colours', 'HAIR_BODY' not in tool and 'SURF2' not in tool)
def near(c, t, d=40): return all(abs(a - b) <= d for a, b in zip(c, t))
for n in ('signin', 'verify', 'reset', 'alert', 'receipt'):
    p = os.path.join(ROOT, 'static', 'email', n + '.gif'); im = Image.open(p); im.seek(im.n_frames - 1); px = im.convert('RGB').getdata()
    cnt = {k: 0 for k in ('violet', 'yellow', 'blue')}
    for c in px:
        if near(c, (127, 97, 245)): cnt['violet'] += 1
        elif near(c, (255, 212, 59)) or near(c, (240, 168, 0), 45): cnt['yellow'] += 1
        elif near(c, (47, 134, 224)): cnt['blue'] += 1
    T(n + '.gif has violet outlines, a yellow cap and a blue body', cnt['violet'] > 800 and cnt['yellow'] > 200 and cnt['blue'] > 1500)
T('legal page cartoons (doc, cookie) are swapped to the new art by fixArt', 'var ILM={plug:"plug",doc:"doc",cookie:"cookie"' in page and 'IL2.doc=' in page and 'IL2.cookie=' in page)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
