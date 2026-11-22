"""Checks Rk4: the notification large icon file exists and is a real 128 px PNG with a transparent corner, the Android build copies it to res/drawable-nodpi, and the Java service uses it for alerts and the pinned notification. The small status-bar icon is untouched. No temp files. Run: python tests/test_rk4.py"""
import os, struct, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def rd(*p): return open(os.path.join(ROOT, *p), encoding='utf-8').read()
png = open(os.path.join(ROOT, 'android-wrapper', 'branding', 'ic_large_sxb.png'), 'rb').read()
T('the badge is a whole PNG (signature and end chunk)', png[:8] == b'\x89PNG\r\n\x1a\n' and png.endswith(b'IEND\xaeB`\x82'))
w, h = struct.unpack('>II', png[16:24])
T('it is 128 x 128 and small (under 20 KB)', (w, h) == (128, 128) and len(png) < 20000)
try:
    from PIL import Image
    im = Image.open(os.path.join(ROOT, 'android-wrapper', 'branding', 'ic_large_sxb.png')).convert('RGBA')
    T('the corner is transparent and the centre is opaque (a round badge)', im.getpixel((0, 0))[3] == 0 and im.getpixel((64, 64))[3] == 255)
    r, g, b, a = im.getpixel((20, 64)); T('the badge is the violet of the rocket outline', abs(r - 127) < 30 and abs(g - 97) < 30 and abs(b - 245) < 30)
except ImportError: print('SKIP picture checks: PIL not installed')
pr = rd('android-wrapper', 'prepare.py')
T('prepare.py copies it to res/drawable-nodpi inside patch_push', "'branding' / 'ic_large_sxb.png'" in pr and "'drawable-nodpi'" in pr and pr.index('def patch_push') < pr.index('ic_large_sxb') < pr.index('patch_manifest(); patch_version()'))
T('prepare.py only copies when the file exists', 'if lg.exists():' in pr)
T('the copy goes to res/drawable-nodpi/ic_large_sxb.png', "shutil.copy(lg, MAIN / 'res' / 'drawable-nodpi' / 'ic_large_sxb.png')" in pr)
j = rd('android-wrapper', 'native', 'LiveMessagingService.java')
T('the Java service has one helper and uses it twice (alert, pinned notification)', j.count('Bitmap largeIcon()') == 1 and j.count('b.setLargeIcon(') == 2)
T('the helper finds the resource by name and returns null when it is missing', 'getIdentifier("ic_large_sxb", "drawable", getPackageName())' in j and 'if (id == 0) return null;' in j)
T('the small status-bar icon is still ic_stat_sxb (not replaced)', j.count('"ic_stat_sxb"') == 2 and 'ic_large_sxb' not in rd('android-wrapper', 'launch_patch.py'))
T('the lock-screen public version has no large icon (balance stays hidden)', 'pub.setLargeIcon' not in j)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
