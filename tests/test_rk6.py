"""Checks Rk6: four new notification pictures (update, soon, ended, linked) are drawn, differ from each other, and the right push kinds use them. Needs Pillow.
Run: python tests/test_rk6.py"""
import io, os, sys, hashlib, warnings
warnings.simplefilter('ignore')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, ROOT)
from PIL import Image
from backend import notifart, pushcopy
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
NEW = ('update', 'soon', 'ended', 'linked')
T('the 4 new names are known', all(n in notifart.NAMES for n in NEW))
T('an unknown name still gives nothing', notifart.png('nope') is None)
hs = {}
for n in notifart.NAMES:
    b = notifart.png(n); im = Image.open(io.BytesIO(b)); hs[n] = hashlib.md5(b).hexdigest()
    T(n + ' is a 1024x512 PNG', im.size == (1024, 512))
T('all pictures are different from each other', len(set(hs.values())) == len(hs))
def violet(n):
    im = Image.open(io.BytesIO(notifart.png(n))).convert('RGB'); return sum(1 for c in im.getdata() if all(abs(a - b) < 30 for a, b in zip(c, (127, 97, 245))))
for n in NEW: T(n + ' has the violet outline and the character', violet(n) > 3000)
for kind, want in ((26, 'linked'), (28, 'linked'), (29, 'update'), (42, 'soon'), (43, 'soon'), (44, 'ended')):
    T('kind %d uses %s.png' % (kind, want), pushcopy.compose(kind, sym='X')[2].endswith('/notif/%s.png' % want))
for kind in (2, 3, 11, 20, 38, 40):
    T('kind %d keeps its old picture' % kind, pushcopy.compose(kind, sym='X')[2].split('/')[-1][:-4] in notifart.NAMES[:8])
T('every kind points at a picture that exists', all((pushcopy.compose(k, sym='X', side='buy', entry=1, sl=1, tp=1)[2] or 'x/hi.png').split('/')[-1][:-4] in notifart.NAMES for k in pushcopy.T))
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
