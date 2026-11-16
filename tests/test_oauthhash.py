"""Section 8 check: the page router must not rewrite Google's return address. Needs node. Run: python tests/test_oauthhash.py"""
import os, re, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
m = re.search(r'function sxOA\(v\)\{.*?\}', html)
if not m: print('FAIL sxOA() not found'); sys.exit(1)
cases = [('access_token=abc&expires_in=3600&token_type=bearer', True), ('error=access_denied&error_description=x', True), ('error_code=400', True),
         ('home', False), ('welcome', False), ('', False), ('admin', False), ('profile', False)]
js = m.group(0) + ';console.log(JSON.stringify(' + json.dumps([c[0] for c in cases]) + '.map(sxOA)))'
try: got = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=20).stdout)
except Exception as e: print('FAIL could not run node:', e); sys.exit(1)
res = [g == w for g, (_, w) in zip(got, cases)]
for (c, w), r in zip(cases, res): print(('PASS ' if r else 'FAIL ') + (c[:24] or '(empty)') + (' is a login return' if w else ' is a normal page'))
wired = 'var oa=sxOA(v);if(oa)v="welcome";' in html and '&&!oa)try{history.replaceState' in html
print(('PASS ' if wired else 'FAIL ') + 'router uses it and skips the rewrite'); res.append(wired)
print('\n%d/%d passed' % (sum(res), len(res))); sys.exit(0 if all(res) else 1)
