"""C3 apply: wires backend/roadmap.py + static/roadmap.js into the app. Needs those two files and tests/test_c3.py pasted first (and C2 applied).
Every old text must appear exactly once or NOTHING is changed. Safe to run twice (marker check). Each file is written to .tmp then os.replace."""
import os, sys, subprocess
for f in ('backend/roadmap.py', 'static/roadmap.js', 'tests/test_c3.py', 'backend/course.py'):
    if not os.path.exists(f): print('STOP: missing', f); sys.exit(1)
APP, RISK, BOT, STO, IDX, CJS = 'backend/app.py', 'backend/risk.py', 'backend/botstate.py', 'backend/store.py', 'static/index.html', 'static/course.js'
ROUTES = '''@app.get('/api/path')
@need(verified=True)
def path_get(u):
    """C3: the road to Real (lessons + practice trades), badges, and which ones are new."""
    return jsonify(roadmap.view(u['uid'], bool(u['admin'])))

@app.post('/api/path/seen')
@need(verified=True)
def path_seen(u):
    return jsonify(ok=True, seen=roadmap.seen(u['uid']))

def _deriv_bot(u, on):'''
CONF = "        if j.get('confirm') != 'REAL': return jsonify(error='Type REAL to confirm. Real mode trades real money.'), 400\n"
NO = "        if not roadmap.real_allowed(u['uid'], bool(u['admin'])): return jsonify(error=roadmap.why(u['uid'], bool(u['admin']))), 403          # C3: the road to Real\n"
GL = "    was = links.view(u['uid']).get('mode'); r = _link_edit"
GB = "    was = bk.mode(u['uid'], n); bk.set_mode"
OPEN = "st.put('course_required', '0'); st.put('practice_trades_needed', '0')          # C3: this test is about something else, so the road to Real is open for its people\n"
E = [
 (APP, 'from . import btc_switch, tradeon, course\n', 'from . import btc_switch, tradeon, course, roadmap\n', 'course, roadmap'),
 (APP, 'def _deriv_bot(u, on):', ROUTES, "@app.get('/api/path')"),
 (APP, CONF + GL, NO + CONF + GL, NO + CONF + GL),          # the road is checked BEFORE the word REAL is asked for
 (APP, CONF + GB, NO + CONF + GB, NO + CONF + GB),
 (APP, "('auto_target_usd', 0, 1000)):", "('auto_target_usd', 0, 1000), ('practice_trades_needed', 0, 100)):", "('practice_trades_needed', 0, 100)"),
 (STO, "'orb_session': '0', 'plans': ''}", "'orb_session': '0', 'practice_trades_needed': '5', 'plans': ''}", "'practice_trades_needed': '5'"),
 (RISK, 'from . import store as st, news, links, limits, brokers as bk\n', 'from . import store as st, news, links, limits, brokers as bk, roadmap\n', 'brokers as bk, roadmap'),
 (RISK, "return False, 'real account needs Real mode and live trading allowed'\n", "return False, 'real account needs Real mode and live trading allowed'\n        if a.get('demo') is not True and not roadmap.real_allowed(uid): return False, 'learning path not finished'          # C3: lessons + practice trades first\n", "'learning path not finished'"),
 (BOT, "    'plan ended': 'Your plan has ended. Renew it to trade.',\n", "    'plan ended': 'Your plan has ended. Renew it to trade.',\n    'learning path not finished': 'Real trading is locked until you finish the lessons and the practice trades. See Road to Real on Home. Demo trading is open.',\n", "'learning path not finished'"),
 (IDX, '<script src="/static/course.js"></script>', '<script src="/static/course.js"></script><script src="/static/roadmap.js"></script>', '/static/roadmap.js'),
 (CJS, 'All lessons done. Real trading is unlocked for you.', 'All lessons done. See Road to Real below for what is left.', 'See Road to Real below'),
 (CJS, 'All lessons done. Real trading is unlocked.', 'All lessons done. See Road to Real on Home for what is left.', 'See Road to Real on Home'),
 (CJS, 'Finishing the lessons unlocks Real.', 'The lessons are the first part of the road to Real.', 'first part of the road to Real.'),
 ('tests/test_all.py', "st.x('DELETE FROM kv'); bars._d.clear()\ndef uacct", "st.x('DELETE FROM kv'); bars._d.clear(); " + OPEN.replace('          #', '  #') + "def uacct", "# C3: this test is about"),
]
for f, imp in (('test_acct', 'from backend import store as st, brokers as bk, deriv, links\n'), ('test_deriv7', 'from backend import store as st, brokers as bk, deriv, links, risk, botstate, bars\n'), ('test_deriv_e2e', 'from backend import store as st, brokers as bk, deriv, links, bars\n'),
               ('test_n6b', 'from backend import store as st, push, alerts\n')):
    E.append(('tests/%s.py' % f, imp, imp + OPEN, '# C3: this test is about'))
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
r = subprocess.run([sys.executable, 'tests/test_c3.py'], capture_output=True, text=True)
print((r.stdout.strip().splitlines() or ['no output'])[-1]); print(r.stderr[-300:]); sys.exit(r.returncode)
