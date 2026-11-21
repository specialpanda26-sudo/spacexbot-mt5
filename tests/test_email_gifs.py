"""Checks the email cartoons: every picture an email asks for exists, is a real animated GIF (480 wide, loops, small enough). Needs Pillow.
Run: python tests/test_email_gifs.py"""
import os, re, sys, glob
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
need = set()
for f in glob.glob(os.path.join(ROOT, 'emails', '*.html')): need |= set(re.findall(r'/static/email/([a-z-]+\.gif)', open(f, encoding='utf-8').read()))
T('the 3 emails ask for 3 pictures', len(need) == 3)
for n in sorted(need):
    p = os.path.join(ROOT, 'static', 'email', n)
    if not os.path.exists(p): T(n + ' exists', False); continue
    im = Image.open(p)
    T(n + ' is an animated GIF, 480 wide, loops forever', im.format == 'GIF' and im.n_frames >= 8 and im.size[0] == 480 and im.info.get('loop') == 0)
    T(n + ' is under 300 KB', os.path.getsize(p) < 300 * 1024)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
