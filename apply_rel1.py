"""Section 1 (release): every download link and the update check use the repo this folder is pushed to (git remote origin),
and the Android build now runs when the app's web files or server files change, so each push makes a new release."""
import re, subprocess, sys
OLD = 'specialpanda26-sudo/spacexbot-mt5'
try: url = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], text=True).strip()
except Exception: sys.exit('STOP: run this inside the repo folder (git remote origin not found)')
m = re.search(r'github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$', url)
if not m: sys.exit('STOP: origin is not a github.com address: ' + url)
NEW = m.group(1) + '/' + m.group(2)
for p in ('static/update.js', 'static/index.html'):
    s = open(p, encoding='utf-8').read()
    if OLD in s:
        s = s.replace(OLD, NEW); open(p, 'w', encoding='utf-8').write(s); print(p, ': repo set to', NEW)
    else: print(p, ': already ok')
p = '.github/workflows/android.yml'; s = open(p, encoding='utf-8').read()
old = "    paths:\n      - 'android-wrapper/**'\n"
if "- 'static/**'" in s: print(p, ': already ok')
elif s.count(old) != 1: sys.exit('STOP: cannot find the paths block exactly once')
else:
    s = s.replace(old, old + "      - 'static/**'\n      - 'backend/**'\n"); open(p, 'w', encoding='utf-8').write(s); print(p, ': now runs on static/ and backend/ changes')
