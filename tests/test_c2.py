"""C2 checks: the learning path (backend/course.py, /api/course, static/course.js). No network. Run: python tests/test_c2.py"""
import os, sys, glob, re, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_c2_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import course, alerts
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
c.get('/api/me', headers=H('amy@x.com')); c.get('/api/me', headers=H('bob@x.com'))
A = H('amy@x.com'); B = H('bob@x.com')
def right(lid): return [q['a'] for q in next(l for l in course.LESSONS if l['id'] == lid)['quiz']]
def post(h, lid, a): r = c.post('/api/course/quiz', json={'lesson': lid, 'answers': a}, headers=h); return r.status_code, r.get_json()
T('every lesson has 3 questions with 3 options and a valid answer', all(len(l['quiz']) == 3 and all(len(q['o']) == 3 and 0 <= q['a'] < 3 and q['why'] for q in l['quiz']) for l in course.LESSONS))
T('lesson ids are unique and there are six', len({l['id'] for l in course.LESSONS}) == 6)
j = c.get('/api/course', headers=A).get_json()
T('start: first open, rest locked, nothing done', [l['status'] for l in j['lessons']] == ['open'] + ['locked'] * 5 and j['done'] == 0 and j['next'] == 'meet' and not j['complete'])
T('the answers are never sent to the app', '"a":' not in c.get('/api/course', headers=A).get_data(as_text=True) and 'why' not in str(j))
T('a locked lesson shows no questions', 'quiz' not in j['lessons'][1] and 'points' not in j['lessons'][1])
T('signed out is refused', c.get('/api/course').status_code in (401, 403))
s, e = post(A, 'risk', [0, 0, 0]); T('cannot skip ahead to a locked lesson', s == 400 and 'first' in e['error'])
s, e = post(A, 'nope', [0, 0, 0]); T('unknown lesson refused', s == 400)
s, e = post(A, 'meet', [0, 0]); T('too few answers refused', s == 400)
s, e = post(A, 'meet', [0, 9, 0]); T('out-of-range answer refused', s == 400)
s, e = post(A, 'meet', [True, 1, 1]); T('a true/false answer is refused', s == 400)
w = [(a + 1) % 3 for a in right('meet')]
s, e = post(A, 'meet', w)
T('all wrong: not passed, score 0, reasons shown, right answers NOT revealed', s == 200 and not e['passed'] and e['score'] == 0 and all('right' not in x and x['why'] for x in e['results']))
T('a failed lesson stays open and the next stays locked', e['view']['lessons'][0]['status'] == 'open' and e['view']['lessons'][1]['status'] == 'locked')
one = right('meet'); one[1] = (one[1] + 1) % 3; one[2] = (one[2] + 1) % 3
s, e = post(A, 'meet', one); T('1 of 3 right is still not a pass', e['score'] == 1 and not e['passed'])
two = right('meet'); two[2] = (two[2] + 1) % 3
s, e = post(A, 'meet', two); T('2 of 3 right passes, answers revealed, next lesson opens', e['passed'] and e['score'] == 2 and all('right' in x for x in e['results']) and e['view']['next'] == 'risk' and e['view']['done'] == 1)
s, e = post(A, 'meet', w); T('a later bad retry never takes a pass away', e['view']['lessons'][0]['status'] == 'done')
T('another person is not affected', c.get('/api/course', headers=B).get_json()['done'] == 0)
for l in course.LESSONS[1:]:
    s, e = post(A, l['id'], right(l['id']))
j = c.get('/api/course', headers=A).get_json()
T('all six passed: complete, next is none', j['complete'] and j['done'] == 6 and j['next'] is None and course.complete('dev-amy@x.com'))
T('the other person is still not complete', not course.complete('dev-bob@x.com'))
T('owner switch course_required defaults on, 0 turns it off', course.required() is True and (course.st.put('course_required', '0') or course.required() is False) and (course.st.put('course_required', '1') or course.required() is True))
js = open(os.path.join(ROOT, 'static', 'course.js'), encoding='utf-8').read(); ix = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page loads course.js', '<script src="/static/course.js"></script>' in ix)
T('the page uses the safe escape and the server route', 'function esc' in js and '/api/course/quiz' in js and 'innerHTML' in js)
T('no colours written, only site variables', not re.search(r'#[0-9a-fA-F]{3,6}\b', js))
T('wording: no profit promise', not re.search(r'guarantee|risk.free|sure profit', js + str(course.LESSONS), re.I))
if shutil.which('node'):
    r = subprocess.run(['node', '--check', os.path.join(ROOT, 'static', 'course.js')], capture_output=True, text=True); T('course.js is valid JavaScript', r.returncode == 0)
for f in glob.glob(DB + '*'): os.remove(f)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
