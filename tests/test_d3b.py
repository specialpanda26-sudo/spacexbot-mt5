"""D3b tests: the running-trades card script. Run: python tests/test_d3b.py"""
import os, re, shutil, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
rd = lambda *p: open(os.path.join(ROOT, *p), encoding='utf-8').read()
js, ix = rd('static', 'running.js'), rd('static', 'index.html')
T('page loads running.js once', ix.count('<script src="/static/running.js"></script>') == 1)
T('loaded after guide.js', ix.index('/static/guide.js') < ix.index('/static/running.js'))
T('reads GET /api/assist', '"/api/assist"' in js and 'j.running' in js)
T('says what the list is and is not', 'cannot see your MT5 app' in js and 'tapped Take on' in js)
T('could not load, with Try again', 'Could not load' in js and 'data-rn="retry"' in js)
T('no colours written', not re.search(r'#[0-9a-fA-F]{3,6}\b', js))
T('no browser storage', 'localStorage' not in js and 'sessionStorage' not in js)
T('hidden for the owner and unverified people', 'u.admin' in js and 'u.verified' in js)
if shutil.which('node'): T('valid JavaScript', subprocess.run(['node', '--check', os.path.join(ROOT, 'static', 'running.js')], capture_output=True).returncode == 0)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
