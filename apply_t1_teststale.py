"""Fixes 3 STALE tests (the app code is fine; the tests were written before later sections changed things):
 tests/test_push2.py   fake quiet_now took only (now); push.py now calls quiet_now(prefs, kind, now)
 tests/test_accounts.py  expected notification defaults without quiet_start / quiet_end (added by N2)
 tests/test_push3.py   could not import backend when run as `python tests/test_push3.py`
Each old text must be found the stated number of times or NOTHING is changed. Safe to run twice."""
import sys, os
EDITS = [
 ('tests/test_push2.py', 'push.quiet_now = lambda now=None: False', 'push.quiet_now = lambda *a, **k: False', 2, 'lambda *a, **k: False'),
 ('tests/test_push2.py', 'push.quiet_now = lambda now=None: True', 'push.quiet_now = lambda *a, **k: True', 1, 'lambda *a, **k: True'),
 ('tests/test_accounts.py', "j['prof']['n'] == {'trade': 1, 'risk': 1", "j['prof']['n'] == {'quiet_start': 22, 'quiet_end': 6, 'trade': 1, 'risk': 1", 1, "'quiet_start': 22, 'quiet_end': 6, 'trade': 1"),
 ('tests/test_push3.py', 'import unittest\nfrom unittest.mock import patch\n', "import os, sys, unittest\nsys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))\nfrom unittest.mock import patch\n", 1, 'sys.path.insert'),
]
if not os.path.isdir('tests'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
new = {}
for path, old, rep, cnt, marker in EDITS:
    t = new.get(path) if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: new[path] = t; continue
    if t.count(old) != cnt: print('STOP: expected', cnt, 'x in', path, '->', old[:50], 'found', t.count(old)); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
