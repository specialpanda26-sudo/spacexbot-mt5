"""D4b tests: the account picker and label. Run: python tests/test_d4b.py"""
import os, re, shutil, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
rd = lambda *p: open(os.path.join(ROOT, *p), encoding='utf-8').read()
ix, js = rd('static', 'index.html'), rd('static', 'running.js')
T('picker function defined once', ix.count('function acctPick()') == 1)
T('picker shown above Take it', 'h += acctPick() + \'<div class="jrow"><button class="btn primary" data-act="take"' in ix)
T('both accounts offered', '["FBS", "Deriv MT5"]' in ix)
T('choice handled on tap', 'a === "acct"' in ix and 'data-act="acct"' in ix)
T('take sends the account', '{ id: id, acct: ACCT }' in ix)
T('running card shows the account', 't.acct' in js)
T('no colours written in running.js', not re.search(r'#[0-9a-fA-F]{3,6}\b', js))
if shutil.which('node'): T('running.js valid JavaScript', subprocess.run(['node', '--check', os.path.join(ROOT, 'static', 'running.js')], capture_output=True).returncode == 0)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
