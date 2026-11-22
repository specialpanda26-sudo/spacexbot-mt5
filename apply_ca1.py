"""C-AUTH 1 apply: wires backend/deriv_oauth.py into the app (two routes). Needs that file and tests/test_ca1.py pasted first (and C4 applied).
Every old text must appear exactly once or NOTHING is changed. Safe to run twice (marker check). Each file is written to .tmp then os.replace."""
import os, sys, subprocess
for f in ('backend/deriv_oauth.py', 'tests/test_ca1.py', 'backend/guide.py'):
    if not os.path.exists(f): print('STOP: missing', f); sys.exit(1)
APP = 'backend/app.py'
ROUTES = '''@app.get('/api/deriv/login')
@need(verified=True)
def deriv_login(u):
    """C-AUTH 1: the address of Deriv's own login page for this person (PKCE, trade scope only)."""
    url, why = deriv_oauth.start(u['uid'])
    if why: return jsonify(error=why), 503
    return jsonify(url=url)

@app.get('/auth/deriv/callback')
def deriv_callback():
    """Deriv sends the browser back here. The person is found from the one-time state, never from the address."""
    ok, _ = deriv_oauth.finish(request.args.get('state', ''), request.args.get('code', ''), request.args.get('error', ''))
    return redirect('/?deriv=' + ('ok' if ok else 'fail') + '#connect')

@app.get('/api/deriv/login-status')
@need(verified=True)
def deriv_login_status(u): return jsonify(deriv_oauth.status(u['uid']))

@app.get('/api/guide')'''
E = [
 (APP, 'from . import btc_switch, tradeon, course, roadmap, guide\n', 'from . import btc_switch, tradeon, course, roadmap, guide, deriv_oauth\n', 'roadmap, guide, deriv_oauth'),
 (APP, "@app.get('/api/guide')", ROUTES, "@app.get('/api/deriv/login')"),
]
data, bad = {}, False
for p, old, new, mark in E:
    s = data[p] if p in data else open(p, encoding='utf-8').read()
    data[p] = s
    if mark in s: print('skip (done):', mark[:40]); continue
    if s.count(old) != 1: print('STOP: need exactly once in', p, '->', old[:70].replace('\n', ' ')); bad = True; continue
    data[p] = s.replace(old, new)
if bad: print('Nothing was changed.'); sys.exit(1)
for p, s in data.items():
    if s != open(p, encoding='utf-8').read(): open(p + '.tmp', 'w', encoding='utf-8').write(s); os.replace(p + '.tmp', p); print('edited:', p)
r = subprocess.run([sys.executable, 'tests/test_ca1.py'], capture_output=True, text=True)
print((r.stdout.strip().splitlines() or ['no output'])[-1]); print(r.stderr[-300:]); sys.exit(r.returncode)
