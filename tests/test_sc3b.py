"""SC3b checks: the floating screen assistant uses the app's own icon as its bubble and the WEBSITE'S OWN cartoons on its card (nothing drawn separately).
1) ScreenLogic.java is compiled and run with plain javac: which cartoon every server answer gets (mirrors pick() in static/screen.js).
2) The Android sources are checked as text: bubble = ic_large_sxb, card = sxart_<pic>, eye while reading, fallbacks, no hand-drawn cartoon.
3) tools/make_screen_art.py draws the pictures from window.IL2 of the real page (run in a real Chromium when playwright is installed).
4) screen_patch.py copies the icon and the pictures into the app (twice, and with none present); android.yml draws them before the build.
Run: python tests/test_sc3b.py"""
import os, re, sys, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); WR = os.path.join(ROOT, 'android-wrapper'); NAT = os.path.join(WR, 'native')
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def rd(p): return open(p, encoding='utf-8').read()
def code(s): return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', s, flags=re.S))
L, S, SJ = rd(os.path.join(NAT, 'ScreenLogic.java')), rd(os.path.join(NAT, 'OverlayService.java')), rd(os.path.join(ROOT, 'static', 'screen.js'))
S0 = code(S)

# ---------------- 1) which cartoon each answer gets ----------------
CHECK = r'''
package com.spacexbot.app;
public class PicCheck {
    static void t(String n, boolean ok) { System.out.println((ok ? "PASS " : "FAIL ") + n); }
    static String bot(String code, String text) { return "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"" + code + "\",\"text\":\"" + text + "\"}}"; }
    static String pic(int st, String js) { return ScreenLogic.verdict(st, js).pic; }
    public static void main(String[] a) {
        t("pic: no connection = cx, sign in again = lock", "cx".equals(pic(0, "")) && "lock".equals(pic(401, "{}")));
        t("pic: 429 = wait, 402 = coin, 403 = off, other errors = cx", "wait".equals(pic(429, "{}")) && "coin".equals(pic(402, "{}")) && "off".equals(pic(403, "{}")) && "cx".equals(pic(500, "x")) && "cx".equals(pic(502, "{}")));
        t("pic: a chart that cannot be read = off", "off".equals(pic(200, "{\"read\":{\"readable\":false}}")) && "off".equals(pic(200, "garbage")));
        t("pic: read but the bot gave no answer = wait", "wait".equals(pic(200, "{\"read\":{\"readable\":true},\"bot\":null}")));
        t("pic: the bot agrees = ok", "ok".equals(pic(200, bot("agree", "The bot agrees."))));
        t("pic: blocked = shield, blocked by the weekend / Friday night / Bitcoin rests = sleep", "shield".equals(pic(200, bot("blocked", "cannot work right now: loss limit hit"))) && "sleep".equals(pic(200, bot("blocked", "no trades at the weekend"))) && "sleep".equals(pic(200, bot("blocked", "Friday night risk"))) && "sleep".equals(pic(200, bot("blocked", "Bitcoin rests"))) && "sleep".equals(pic(200, bot("blocked", "WEEKEND"))));
        t("pic: disagree, no setup, bot only, no data and a newer code = wait", "wait".equals(pic(200, bot("disagree", "x"))) && "wait".equals(pic(200, bot("no_setup", "x"))) && "wait".equals(pic(200, bot("bot_only", "x"))) && "wait".equals(pic(200, bot("no_data", "x"))) && "wait".equals(pic(200, bot("something_new", "x"))));
        boolean all = true; for (String p : ScreenLogic.PICS) all = all && p != null && p.matches("[a-z]+");
        t("pics: the list is plain lower-case names", all && ScreenLogic.PICS.length == 9);
        boolean in = true; for (int s : new int[]{0, 401, 402, 403, 429, 500}) { in = in && java.util.Arrays.asList(ScreenLogic.PICS).contains(pic(s, "{}")); }
        in = in && java.util.Arrays.asList(ScreenLogic.PICS).contains(pic(200, bot("agree", "x"))) && java.util.Arrays.asList(ScreenLogic.PICS).contains(pic(200, bot("blocked", "weekend")));
        t("pics: every picture a verdict names is in the list", in);
    }
}
'''
if not shutil.which('javac') or not shutil.which('java'): print('SKIP javac not installed (the text checks below still run)')
else:
    B = os.path.join(HERE, '_sc3b_build'); shutil.rmtree(B, ignore_errors=True); d = os.path.join(B, 'com', 'spacexbot', 'app'); os.makedirs(d)
    shutil.copy(os.path.join(NAT, 'ScreenLogic.java'), os.path.join(d, 'ScreenLogic.java')); open(os.path.join(d, 'PicCheck.java'), 'w').write(CHECK)
    c = subprocess.run(['javac', '-d', os.path.join(B, 'out'), os.path.join(d, 'ScreenLogic.java'), os.path.join(d, 'PicCheck.java')], capture_output=True, text=True)
    T('ScreenLogic.java still compiles with plain javac', c.returncode == 0)
    if c.returncode != 0: print(c.stderr[-1500:])
    else:
        r = subprocess.run(['java', '-cp', os.path.join(B, 'out'), 'com.spacexbot.app.PicCheck'], capture_output=True, text=True, timeout=60)
        for line in r.stdout.splitlines():
            if line.startswith(('PASS ', 'FAIL ')): print(line); R.append(line.startswith('PASS '))
        T('the picture check ran to the end', r.returncode == 0 and len([l for l in r.stdout.splitlines() if l.startswith(('PASS', 'FAIL'))]) == 9)
    shutil.rmtree(B, ignore_errors=True)

# the phone and the website panel choose the same cartoon: every pic name in screen.js' pick() is in the phone's list, and the other way round
js_pics = set(w for e in re.findall(r'pic: ([^,]*),', SJ) for w in re.findall(r'"([a-z]+)"', e)); java_pics = set(re.findall(r'"([a-z]+)"', L[L.find('PICS = {'):L.find('};', L.find('PICS = {'))]))
T('website panel and phone use the same cartoon names (the phone adds lock for "sign in again")', js_pics <= java_pics and java_pics - js_pics == {'lock'})

# ---------------- 2) the Android sources, as text ----------------
T('bubble: the picture is the app\'s own icon ic_large_sxb, clipped to a circle', 'pic("ic_large_sxb")' in S0 and 'clipPath' in S0 and 'drawBitmap(icon' in S0)
T('bubble: the ring colour still shows the last answer, sky while reading', 'working ? ScreenLogic.SKY : ring' in S0)
T('bubble: if the icon is missing from a build it draws the plain eye, never nothing', 'icon != null' in S0 and 'drawOval' in S0)
T('card: the cartoon is the file sxart_<pic> chosen by the verdict', 'pic("sxart_" + v.pic)' in S0)
T('card: if a picture is missing the card shows words only', 'cardPic.setVisibility(View.GONE)' in S0)
T('card: pictures are looked up by name in the app\'s own drawables (no file, no network)', 'getIdentifier(name, "drawable", getPackageName())' in S0 and 'decodeResource' in S0)
T('card: while a read is under way the eye cartoon shows, AFTER the picture was taken (the card is not in the picture)', 0 < S0.find('acquireLatestImage()') < S0.find('Looking at your chart') and S0.count('"eye"') == 2 and re.search(r'if \(card != null\) card\.setVisibility\(View\.GONE\);\s*bubble\.setVisibility\(View\.INVISIBLE\);', S0) is not None)
T('card: the eye card stays until the answer replaces it (60 s at most), answers go away after 12 s', 'v.pic.equals("eye") ? 60000 : 12000' in S0)
T('card: the "not advice" line is still on every card', 'A read of your screen, not advice.' in S0)
T('nothing is hand-drawn on the card: no Path, rect or oval for a cartoon (only the bubble\'s plain-eye fallback)', S0.count('drawOval') == 1 and 'drawRect' not in S0 and 'drawArc' not in S0 and 'drawLine' not in S0)
T('the picture of the screen is still never written to disk or logged', not re.search(r'FileOutputStream|openFileOutput|getCacheDir|getFilesDir|Log\.', S0))
T('every Verdict made in the service names a cartoon', len(re.findall(r'new ScreenLogic\.Verdict\(', S0)) == 4 and all(re.search(r', "(wait|cx|eye)"\)', x) for x in re.findall(r'new ScreenLogic\.Verdict\([^;]*;', S)))

# ---------------- 3) the art maker ----------------
M = rd(os.path.join(ROOT, 'tools', 'make_screen_art.py')); idx = rd(os.path.join(ROOT, 'static', 'index.html'))
props = re.search(r"PROPS = \(([^)]*)\)", M); props = re.findall(r"'([a-z]+)'", props.group(1)) if props else []
T('art maker draws exactly the cartoons the phone can ask for', sorted(props) == sorted(re.findall(r'"([a-z]+)"', L[L.find('PICS = {'):L.find('};', L.find('PICS = {'))])))
T('every one of them is a prop of the website (IL2.<name> in static/index.html)', all(re.search(r'IL2\.%s\s*=' % p, idx) for p in props))
T('art maker takes them from window.IL2 of the real page, still pose, transparent, nothing leaves the computer', 'window.IL2[k]' in M and "reduced_motion='reduce'" in M and 'omit_background=True' in M and "startswith(host)" in M and '127.0.0.1' in M)
try:
    import playwright  # noqa
    have = True
except Exception: have = False
if not have: print('SKIP playwright not installed (the art maker is not run)')
else:
    out = os.path.join(HERE, '_sc3b_art'); shutil.rmtree(out, ignore_errors=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'make_screen_art.py'), out], capture_output=True, text=True, timeout=180)
    T('art maker runs in a real Chromium on the real page', r.returncode == 0 and 'drew' in r.stdout)
    if r.returncode != 0: print((r.stdout + r.stderr)[-1500:])
    from PIL import Image
    files = sorted(os.listdir(out)) if os.path.isdir(out) else []
    T('one PNG per cartoon', files == sorted('sxart_%s.png' % p for p in props))
    good = True; sizes = []
    for f in files:
        im = Image.open(os.path.join(out, f)).convert('RGBA'); a = im.getchannel('A'); sizes.append(os.path.getsize(os.path.join(out, f)))
        opaque = sum(1 for v in a.tobytes() if v > 200); corner = im.getpixel((1, 1))[3]
        good = good and im.size == (360, 255) and corner == 0 and 2500 < opaque < 60000
    T('each picture is 360 x 255, has a clear background and real drawing in it', good and len(files) == len(props))
    T('each picture is small (under 40 KB)', bool(sizes) and max(sizes) < 40000)
    ims = [Image.open(os.path.join(out, f)).convert('RGBA').tobytes() for f in files]
    T('the cartoons differ from each other', len(set(ims)) == len(ims))
    # the character of the website (blue body, yellow hair) is on every card
    def has(im, rgb, tol=40):
        raw = im.tobytes(); return any(abs(r-rgb[0]) < tol and abs(g-rgb[1]) < tol and abs(b-rgb[2]) < tol for r, g, b, al in zip(raw[0::4], raw[1::4], raw[2::4], raw[3::4]) if al > 200)
    T('the website\'s character is in the pictures (not an invented one)', all(has(Image.open(os.path.join(out, f)).convert('RGBA'), (0x56, 0xB6, 0xFF)) for f in files[:3]))
    shutil.rmtree(out, ignore_errors=True)

# ---------------- 4) the build ----------------
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('screen_patch', os.path.join(WR, 'screen_patch.py')); sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
def fake(name, art):
    tree = Path(HERE) / name; shutil.rmtree(tree, ignore_errors=True); main = tree / 'src' / 'main'; main.mkdir(parents=True)
    (main / 'AndroidManifest.xml').write_text('<?xml version="1.0"?>\n<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n    <application>\n    </application>\n</manifest>\n', encoding='utf-8')
    here = tree / 'wr'; shutil.copytree(WR, here, ignore=shutil.ignore_patterns('art', '__pycache__'))
    if art:
        (here / 'branding' / 'art').mkdir(parents=True, exist_ok=True)
        for p in ('eye', 'ok', 'lock'): (here / 'branding' / 'art' / ('sxart_%s.png' % p)).write_bytes(b'\x89PNG fake ' + p.encode())
    return tree, main, here
tree, main, here = fake('_sc3b_t1', True); sp.run(main, here, 'com.spacexbot.app'); sp.run(main, here, 'com.spacexbot.app')
res = main / 'res' / 'drawable-nodpi'
T('patch: the app icon and the pictures are copied into the app', (res / 'ic_large_sxb.png').exists() and all((res / ('sxart_%s.png' % p)).exists() for p in ('eye', 'ok', 'lock')))
T('patch: the copies are the real files', (res / 'ic_large_sxb.png').read_bytes() == (Path(WR) / 'branding' / 'ic_large_sxb.png').read_bytes() and (res / 'sxart_ok.png').read_bytes().endswith(b'ok'))
T('patch: running it twice changes nothing and the service is declared once', (main / 'AndroidManifest.xml').read_text(encoding='utf-8').count('.OverlayService') == 1)
shutil.rmtree(tree, ignore_errors=True)
tree, main, here = fake('_sc3b_t2', False); sp.run(main, here, 'com.spacexbot.app')
T('patch: with no pictures the build still works (the card shows words only) and the icon is still copied', (main / 'res' / 'drawable-nodpi' / 'ic_large_sxb.png').exists() and not list((main / 'res' / 'drawable-nodpi').glob('sxart_*')))
shutil.rmtree(tree, ignore_errors=True)
Y = rd(os.path.join(ROOT, '.github', 'workflows', 'android.yml'))
T('android.yml draws the pictures BEFORE prepare.py copies them', 0 < Y.find('tools/make_screen_art.py') < Y.find('python3 prepare.py'))
T('android.yml: a failed drawing step never fails the APK build', re.search(r'Screen assistant cartoons[^\n]*\n\s+working-directory: \.\n\s+continue-on-error: true', Y) is not None)
T('android.yml installs the browser for it (playwright + chromium)', 'pip install playwright' in Y and 'playwright install --with-deps chromium' in Y)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
