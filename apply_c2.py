"""C2 apply: wires backend/course.py + static/course.js into backend/app.py and static/index.html.
Needs backend/course.py, static/course.js and tests/test_c2.py pasted first. Safe to run twice; changes nothing if a text does not fit exactly once."""
import os, sys, subprocess
for f in ('backend/course.py', 'static/course.js', 'tests/test_c2.py'):
    if not os.path.exists(f): print('STOP: paste', f, 'first'); sys.exit(1)
def edit(p, old, new, mark):
    s = open(p, encoding='utf-8').read()
    if mark in s: print('skip (done):', p); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', p, '->', old[:60]); sys.exit(1)
    open(p + '.tmp', 'w', encoding='utf-8').write(s.replace(old, new)); os.replace(p + '.tmp', p); print('edited:', p)
edit('backend/app.py', 'from . import btc_switch, tradeon\n', 'from . import btc_switch, tradeon, course\n', 'tradeon, course')
ROUTES = '''@app.get('/api/course')
@need(verified=True)
def course_get(u):
    """C2: the learning path. Lessons unlock one by one; the right answers stay on the server."""
    return jsonify(course.view(u['uid']))

@app.post('/api/course/quiz')
@need(verified=True)
def course_quiz(u):
    j = _j()
    try: r = course.grade(u['uid'], str(j.get('lesson') or ''), j.get('answers'))
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, 'lesson': str(j.get('lesson'))[:20], 'score': r['score']})
    return jsonify(r)

def _deriv_bot(u, on):'''
edit('backend/app.py', 'def _deriv_bot(u, on):', ROUTES, "@app.get('/api/course')")
edit('static/index.html', '<script src="/static/trade_on.js"></script>', '<script src="/static/trade_on.js"></script><script src="/static/course.js"></script>', '/static/course.js')
r = subprocess.run([sys.executable, 'tests/test_c2.py'], capture_output=True, text=True)
print((r.stdout.strip().splitlines() or ['no output'])[-1]); print(r.stderr[-300:]); sys.exit(r.returncode)
