"""Step B2 apply script. Adds the Windows download card to static/index.html and the Windows section to README.md.
Checks every old text appears exactly once. If anything does not fit, NOTHING is changed. Safe to run twice. Then runs all tests."""
import os, sys, subprocess

HTML_NEW = r'''<script>
/* ---- Windows app card on the Connect tab. Shown only on a Windows PC, never on phones or in the Android app. ---- */
(function () {
  try {
    var c = window.Capacitor, native = !!(c && c.isNativePlatform && c.isNativePlatform()), ua = navigator.userAgent;
    if (native || !/Windows NT/.test(ua) || /Android|; wv\)|iPhone|iPad|iPod/.test(ua)) return;
    var vc = document.getElementById("view-connect"); if (!vc || document.getElementById("winapp")) return;
    var W = document.createElement("div"); W.className = "card"; W.id = "winapp";
    W.innerHTML = '<div class="card-head"><h2>Windows app</h2></div>' +
      '<p class="note">Runs your bot on this PC with your own MetaTrader 5. Free. It only trades while the app and MetaTrader 5 are both open and logged in. Try a demo account first.</p>' +
      '<a class="btn primary block" href="https://github.com/specialpanda26-sudo/spacexbot-mt5./releases/download/desktop-latest/spacexbot-desktop.exe" rel="noopener">Download for Windows</a>' +
      '<p class="note">Windows may say "Windows protected your PC" because this free app has no paid signature. Choose More info, then Run anyway, only if you got the file from here. Signals are not advice and do not promise profit.</p>';
    var after = document.getElementById("phonec") || document.getElementById("mt5c");
    vc.insertBefore(W, after ? after.nextSibling : vc.firstChild);
  } catch (e) {}
})();
</script>

''' + '</body></html>'
README_NEW = r'''## Windows app (laptop mode)
A small window for a Windows PC that runs the same bot as the EA, with no MQL5 needed. It uses your own MetaTrader 5 and your personal key. Free.
- **Get the .exe:** GitHub > Actions > Build Windows app > Run workflow (it also builds by itself when `desktop/` changes on main). The file appears under Releases as **desktop-latest > spacexbot-desktop.exe**. The Connect tab has a **Download for Windows** card, shown only on a Windows PC. The repo must be public for visitors to download. The Android release stays the "latest" one; this one is kept apart on purpose so both links keep working.
- **Use it:** open MetaTrader 5 on the PC, log in to a **demo** account, switch **Algo Trading** on. Open the app, paste your server address and personal key (Connect tab > Make my key), press **Start**. Leave "Allow REAL-money accounts" off until you have watched it on demo for weeks.
- **Windows SmartScreen:** the first run may say *Windows protected your PC*. That is because the .exe has no paid code-signing certificate (they cost money, and this project stays free) and it is new, so Windows has no reputation for it yet. It does not mean the file is infected. Choose **More info > Run anyway**, but only for a file you downloaded from your own spaceXBot site or Releases page. You can compare the SHA-256 printed in the release notes with `Get-FileHash .\spacexbot-desktop.exe` in PowerShell.
- **Antivirus:** apps made with PyInstaller are sometimes flagged by antivirus programs even when harmless. If yours blocks it, do not turn your antivirus off. Run from source instead: install Python 3.12 from python.org (tick "Add to PATH"), then in the project folder `pip install requests MetaTrader5` and `python -m desktop.gui`.
- **If the window will not open:** look for `crash.log` in the `.spacexbot` folder inside your Windows user folder and send it to support.
- **Not tested on a live terminal.** The window logic is tested with fakes. The connection to a real MetaTrader 5 has not been run yet. Start on a demo account.

''' + '## Android app\n'
EDITS = [('static/index.html', 'W.id = "winapp"', '</body></html>', HTML_NEW),
         ('README.md', '## Windows app (laptop mode)', '## Android app\n', README_NEW)]
NEEDED = ['desktop_app.py', '.github/workflows/desktop.yml', 'tests/test_exe.py', 'desktop/gui.py', 'desktop/presenter.py']
TESTS = ['all', 'desktop', 'mail', 'admin', 'accounts', 'sbauth', 'locked', 'authjs', 'oauthhash', 'gui', 'exe']

def rd(p):
    with open(p, encoding='utf-8', newline='') as f: return f.read()

def main():
    miss = [p for p in NEEDED if not os.path.exists(p)]
    if miss: print('STOPPED. Missing files (paste them first): ' + ', '.join(miss) + '\nNothing was changed.'); return 1
    plan, bad = [], []
    for path, marker, old, new in EDITS:
        t = rd(path)
        if marker in t: print('already done: ' + path); continue
        n = t.count(old)
        if n != 1: bad.append('%s: expected the anchor text exactly once, found %d times' % (path, n)); continue
        plan.append((path, t.replace(old, new)))
    if bad: print('STOPPED. Nothing was changed.\n' + '\n'.join(bad)); return 1
    for path, text in plan:
        with open(path + '.part', 'w', encoding='utf-8', newline='') as f: f.write(text)
    for path, _ in plan: os.replace(path + '.part', path); print('changed: ' + path)
    print('\nRunning all tests...')
    failed = []
    for t in TESTS:
        r = subprocess.run([sys.executable, 'tests/test_%s.py' % t], capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or ['(no output)'])[-1]
        print('%-10s %s' % (t, last)); 
        if r.returncode: failed.append(t)
    print('\nRESULT: ' + ('ALL TESTS PASSED' if not failed else 'FAILED: ' + ', '.join(failed)))
    return 1 if failed else 0

sys.exit(main())
