"""Checks that no email can ask for a picture that does not exist: every img='name' in backend/mailer.py and every /static/email/x.gif in emails/*.html
has a real animated GIF in static/email/ (480 wide, loops, under 300 KB, really moves). Needs Pillow. Run: python tests/test_email_pics.py"""
import os, re, sys, glob
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
def rd(p): return open(p, encoding='utf-8').read()
need = set(re.findall(r"img='([a-z-]+)'", rd(os.path.join(ROOT, 'backend', 'mailer.py'))))
for f in glob.glob(os.path.join(ROOT, 'emails', '*.html')): need |= {n[:-4] for n in re.findall(r'/static/email/([a-z-]+\.gif)', rd(f))}
T('the emails ask for 5 pictures: ' + ', '.join(sorted(need)), len(need) == 5)
for n in sorted(need):
    p = os.path.join(ROOT, 'static', 'email', n + '.gif')
    if not os.path.exists(p): T(n + '.gif exists', False); continue
    im = Image.open(p)
    T(n + '.gif is an animated GIF, 480 wide, loops, under 300 KB', im.format == 'GIF' and im.n_frames >= 8 and im.size[0] == 480 and im.info.get('loop') == 0 and os.path.getsize(p) < 300 * 1024)
    f0, f1 = im.copy().convert('RGB'), (im.seek(im.n_frames // 2) or im.convert('RGB'))
    T(n + '.gif really moves (first and middle frame differ)', f0.tobytes() != f1.tobytes())
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
