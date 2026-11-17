"""Windows .exe pieces: the launcher (desktop_app.py), the build workflow, the Connect-tab download card, the README.
No Windows, no tkinter, no MetaTrader 5 needed (stand-ins are used).  Run:  python tests/test_exe.py   (exit code 1 on any failure)"""
import os, sys, re, types, tempfile, subprocess, shutil
from unittest import mock
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, ROOT)
HOME = tempfile.mkdtemp(prefix='sxbexe_'); os.environ['SXB_HOME'] = HOME
import desktop_app

R = []
def T(name):
    def deco(f):
        try: f(); R.append((name, True, ''))
        except Exception as e: R.append((name, False, repr(e)[:200]))
        return f
    return deco
def read(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f: return f.read()

def stand_ins(tk=True, mt=True):
    """Fake tkinter and MetaTrader5 so the self-test result does not depend on this computer."""
    m = {}
    t = types.ModuleType('tkinter'); t.Tk = lambda: mock.MagicMock()
    m['tkinter'] = t if tk else None
    m['MetaTrader5'] = types.ModuleType('MetaTrader5') if mt else None
    return mock.patch.dict(sys.modules, m)

@T('selftest: everything present -> PASS written, exit 0')
def _():
    p = os.path.join(HOME, 'st1.txt')
    with stand_ins(): rc = desktop_app.selftest(p)
    t = open(p).read(); assert rc == 0 and 'SELFTEST PASS' in t and 'ok   desktop.gui' in t and 'ok   a window can be created' in t, t

@T('selftest: a missing part -> names it, FAIL, exit 1')
def _():
    p = os.path.join(HOME, 'st2.txt')
    with stand_ins(mt=False): rc = desktop_app.selftest(p)
    t = open(p).read(); assert rc == 1 and 'FAIL MetaTrader5' in t and 'SELFTEST FAIL' in t, t

@T('selftest: no usable window system -> FAIL, exit 1')
def _():
    p = os.path.join(HOME, 'st3.txt')
    with stand_ins(tk=False): rc = desktop_app.selftest(p)
    assert rc == 1 and 'SELFTEST FAIL' in open(p).read()

@T('selftest: result file cannot be written -> exit 1, no crash')
def _():
    with stand_ins(): assert desktop_app.selftest(HOME) == 1          # HOME is a folder, not a file

@T('main: --selftest FILE runs the self-test and opens no window')
def _():
    p = os.path.join(HOME, 'st4.txt')
    def no_window(): raise AssertionError('window opened')
    with stand_ins(): rc = desktop_app.main(['--selftest', p], window=no_window)
    assert rc == 0 and os.path.exists(p)

@T('main: window closes normally -> 0 and no alert')
def _():
    with mock.patch.object(desktop_app, 'alert') as a: assert desktop_app.main([], window=lambda: 0) == 0; assert not a.called

@T('main: window fails (returns 1) -> person is told, with where the details are')
def _():
    with mock.patch.object(desktop_app, 'alert') as a:
        assert desktop_app.main([], window=lambda: 1) == 1; assert a.called and 'crash.log' in a.call_args[0][0]

@T('main: window raises -> crash.log written, alert shown, exit 1, no traceback escapes')
def _():
    def boom(): raise RuntimeError('kaboom')
    with mock.patch.object(desktop_app, 'alert') as a: rc = desktop_app.main([], window=boom)
    assert rc == 1 and a.called and 'kaboom' in open(os.path.join(HOME, 'crash.log')).read()

@T('alert: harmless on a computer without Windows message boxes')
def _():
    desktop_app.alert('hello')

@T('workflow: Windows, one-file, no console, self-test, own release tag, not "latest"')
def _():
    w = read('.github', 'workflows', 'desktop.yml')
    for need in ('runs-on: windows-latest', '--onefile', '--noconsole', '--name spacexbot-desktop', 'desktop_app.py', '--selftest', 'tag_name: desktop-latest',
                 'make_latest: false', 'files: dist/spacexbot-desktop.exe', 'contents: write', "python-version: '3.12'", 'SHA-256', 'Run anyway'):
        assert need in w, need
    assert 'secrets.' not in w and 'make_latest: true' not in w
    try:
        import yaml; d = yaml.safe_load(w); assert d['jobs']['exe']['runs-on'] == 'windows-latest' and d['permissions']['contents'] == 'write'
    except ImportError: pass

@T('workflow: the Android release is still the "latest" one, so its download link keeps working')
def _():
    a = read('.github', 'workflows', 'android.yml'); assert 'make_latest: true' in a
    assert 'releases/latest/download/spacexbot.apk' in read('static', 'index.html')

@T('connect tab: one Windows card, Windows-only, never on phones or in the Android app')
def _():
    h = read('static', 'index.html'); assert h.count('W.id = "winapp"') == 1
    i = h.index('Windows app card on the Connect tab'); s = h[h.rindex('<script>', 0, i):h.index('</script>', i)]
    for need in ('Windows NT', 'Capacitor', 'Android', 'iPhone', 'download/desktop-latest/spacexbot-desktop.exe', 'Download for Windows', 'protected your PC', 'do not promise profit'):
        assert need in s, need

@T('connect tab: the new script is valid JavaScript')
def _():
    h = read('static', 'index.html'); i = h.index('Windows app card on the Connect tab'); s = h[h.rindex('<script>', 0, i) + 8:h.index('</script>', i)]
    n = shutil.which('node')
    if not n: assert s.count('{') == s.count('}') and s.count('(') == s.count(')'); return
    f = os.path.join(HOME, 'card.js'); open(f, 'w').write(s)
    r = subprocess.run([n, '--check', f], capture_output=True, text=True); assert r.returncode == 0, r.stderr[:200]

@T('connect tab: the card really runs: Windows PC gets it, phone / Android app / Mac do not')
def _():
    n = shutil.which('node')
    if not n: return
    h = read('static', 'index.html'); i = h.index('Windows app card on the Connect tab'); s = h[h.rindex('<script>', 0, i) + 8:h.index('</script>', i)]
    drv = ("function run(ua, cap){var made=[];var vc={insertBefore:function(e){made.push(e)}};var els={'view-connect':vc};"
           "var doc={getElementById:function(i){return els[i]||null},createElement:function(){return {}}};"
           "(function(window,navigator,document){" + s + "})({Capacitor:cap},{userAgent:ua},doc);return made.length}"
           "var W='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120';"
           "var out=[run(W),run('Mozilla/5.0 (Linux; Android 14; Pixel) Chrome/120 Mobile'),run('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)'),run('Mozilla/5.0 (Macintosh; Intel Mac OS X)'),"
           "run(W,{isNativePlatform:function(){return true}}),run('Mozilla/5.0 (Windows NT 10.0) AppleWebKit; wv)')];console.log(out.join(','))")
    f = os.path.join(HOME, 'drive.js'); open(f, 'w').write(drv)
    r = subprocess.run([n, f], capture_output=True, text=True); assert r.stdout.strip() == '1,0,0,0,0,0', (r.stdout, r.stderr[:200])

@T('connect tab: link points at the same file name the workflow builds')
def _():
    assert re.search(r'releases/download/desktop-latest/(spacexbot-desktop\.exe)"', read('static', 'index.html'))
    assert 'name spacexbot-desktop' in read('.github', 'workflows', 'desktop.yml')

@T('readme: Windows section says how to use it, SmartScreen, antivirus, demo first, not tested live')
def _():
    r = read('README.md')
    for need in ('## Windows app (laptop mode)', 'SmartScreen', 'Run anyway', 'desktop-latest', 'Antivirus', 'demo', 'crash.log', 'Not tested on a live terminal'): assert need in r, need
    assert r.index('## Windows app (laptop mode)') < r.index('## Android app')

@T('nothing secret in the launcher or the workflow')
def _():
    for p in (('desktop_app.py',), ('.github', 'workflows', 'desktop.yml')):
        t = read(*p); assert not re.search(r'sxb_[A-Za-z0-9]{8,}|sk_live|password\s*=', t), p

w = max(len(n) for n, _, _ in R)
for n, ok, err in R: print(('PASS ' if ok else 'FAIL ') + n.ljust(w), '' if ok else ' <- ' + err)
bad = [n for n, ok, _ in R if not ok]; print(f'\n{len(R) - len(bad)}/{len(R)} passed'); sys.exit(1 if bad else 0)
