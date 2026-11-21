"""Checks Section 1: all GitHub links in the page and the update check name the SAME repo, and the Android build runs when app files change.
Run: python tests/test_release.py"""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
def rd(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
idx, upd, wf = rd('static/index.html'), rd('static/update.js'), rd('.github/workflows/android.yml')
repos = set(re.findall(r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)/releases', idx))
T('the page links to exactly one repo', len(repos) == 1)
m = re.search(r'var REPO = "([^"]+)"', upd)
T('the update check uses that same repo', bool(m) and repos == {m.group(1)})
T('no link has a stray dot or space in the repo name', all(re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', r) for r in repos))
T('Android build runs when static/ changes', "- 'static/**'" in wf)
T('Android build runs when backend/ changes', "- 'backend/**'" in wf)
T('Android build still runs when android-wrapper/ changes', "- 'android-wrapper/**'" in wf)
T('the release is the latest one', 'make_latest: true' in wf)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
