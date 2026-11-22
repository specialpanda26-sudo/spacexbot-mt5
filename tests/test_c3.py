"""C3 checks: the road to Real (backend/roadmap.py, risk gate, mode routes, /api/path, static/roadmap.js). No network. Run: python tests/test_c3.py"""
import os, sys, glob, re, json, shutil, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_c3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD', BROKER_KEY='unit-test-lock-key-0123456789')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import course, alerts, roadmap, risk, store as st, links, botstate, brokers as bk
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, B, BOSS = H('amy@x.com'), H('bob@x.com'), H('boss@x.com'); UA, UB, UBOSS = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'
for u in (UA, UB, UBOSS): st.x('UPDATE users SET plan_until=? WHERE uid=?', (9999999999, u))
def lessons(uid, n): st.put('course:%s' % uid, json.dumps({l['id']: 3 for l in course.LESSONS[:n]}))
def trade(uid, n=1, grp=None, pnl=-1.0):
    for _ in range(n): st.x("INSERT INTO signals(symbol,side,status,created,pnl,closed,uid,grp) VALUES('XAUUSD','buy','closed',?,?,?,?,?)", (int(time.time()) - 60, pnl, int(time.time()) - 30, uid, grp))
def pathj(h): return c.get('/api/path', headers=h).get_json()
T('default practice trades needed is 5', roadmap.needed() == 5)
for v, want in (('0', 0), ('100', 100), ('7', 7), ('101', 5), ('-1', 5), ('abc', 5), ('', 5)):
    st.put('practice_trades_needed', v); T('setting %r reads as %d' % (v, want), roadmap.needed() == want)
st.put('practice_trades_needed', '5')
T('the owner EA (uid empty) is exempt', roadmap.real_allowed('') is True)
T('an admin flag is exempt', roadmap.real_allowed(UA, admin=True) is True)
T('an ADMIN_EMAILS person is exempt without the flag', roadmap.real_allowed(UBOSS) is True)
T('an ordinary person starts locked', roadmap.real_allowed(UA) is False)
w = roadmap.why(UA); T('plain words name the lessons and the trades', '6 lessons' in w and '5 more practice trades' in w and 'Demo trading is open' in w)
lessons(UA, 6); T('all lessons but no trades: still locked, only trades named', not roadmap.real_allowed(UA) and 'lesson' not in roadmap.why(UA) and '5 more' in roadmap.why(UA))
trade(UA, 4); T('4 of 5 trades: still locked, 1 more named', not roadmap.real_allowed(UA) and '1 more practice trade.' in roadmap.why(UA))
trade(UB, 9); T('another person closed trades do not count for me', not roadmap.real_allowed(UA))
trade(UA, 1); T('lessons + 5 trades: Real opens, no reason left', roadmap.real_allowed(UA) and roadmap.why(UA) == '')
lessons(UB, 5); T('5 of 6 lessons with 9 trades: locked, one lesson named', not roadmap.real_allowed(UB) and 'finish the 1 lesson still open' in roadmap.why(UB))
st.put('practice_trades_needed', '3'); trade('dev-two@x.com', 2, grp=77); T('entries of one setup (same group) count once', roadmap.closed('dev-two@x.com') == 1)
st.put('practice_trades_needed', '5')
st.put('course_required', '0'); T('lessons switched off by the owner: only the trades count', roadmap.real_allowed(UB) and not roadmap.real_allowed('dev-two@x.com')); st.put('course_required', '1')
st.put('practice_trades_needed', '0'); lessons('dev-two@x.com', 5); T('zero practice trades: lessons alone decide (5 of 6 = locked)', not roadmap.real_allowed('dev-two@x.com')); lessons('dev-two@x.com', 6); T('zero practice trades: all lessons = open', roadmap.real_allowed('dev-two@x.com')); st.put('practice_trades_needed', '5')
# ---- the gate ----
NOW = 1700000000
class Clock:
    @staticmethod
    def time(): return NOW
real_time = risk.time; risk.time = Clock
def snap(uid, demo, real=False):
    links.new_key(uid)
    if real: links.set_mode(uid, 'real')          # a mode switch stops the bot, so the bot is switched on last
    links.set_bot(uid, True); st.set_acct({'balance': 1000, 'demo': demo, 'allow_live': True, 'open': 0}, uid)
UC = 'dev-cat@x.com'; c.get('/api/me', headers=H('cat@x.com')); snap(UC, False, True)
T('gate: a real account on Real mode with an unfinished road is refused with the road reason', risk.global_gate(NOW, uid=UC) == (False, 'learning path not finished'))
lessons(UC, 6); trade(UC, 5, pnl=1.0); T('gate: the same person after the road is allowed', risk.global_gate(NOW, uid=UC) == (True, 'ok'))
UD = 'dev-dan@x.com'; c.get('/api/me', headers=H('dan@x.com')); snap(UD, True); T('gate: a DEMO account is never blocked by the road', risk.global_gate(NOW, uid=UD) == (True, 'ok'))
snap(UBOSS, False, True); T('gate: an admin on a real account is not blocked by the road', risk.global_gate(NOW, uid=UBOSS) == (True, 'ok'))
st.set_acct({'balance': 1000, 'demo': False, 'allow_live': True}); st.put('bot_enabled', '1'); T('gate: the owner EA (uid empty) is not blocked by the road', risk.global_gate(NOW, uid='')[1] != 'learning path not finished')
risk.time = real_time
T('the status words are plain', 'learning path not finished' in botstate.PLAIN and 'Road to Real' in botstate.PLAIN['learning path not finished'] and botstate._words('learning path not finished') == botstate.PLAIN['learning path not finished'])
# ---- the two mode routes ----
def mode(h, m, conf=None): r = c.post('/api/link/mode', json={'mode': m, **({'confirm': conf} if conf else {})}, headers=h); return r.status_code, r.get_json()
UE = 'dev-eve@x.com'; EV = H('eve@x.com'); c.get('/api/me', headers=EV); st.x('UPDATE users SET plan_until=? WHERE uid=?', (9999999999, UE)); links.new_key(UE)
s, j = mode(EV, 'real', 'REAL'); T('MT5 Real with an unfinished road: 403 and plain words', s == 403 and 'Real trading is not open yet' in j['error'] and links.mode(UE) != 'real')
s, j = mode(EV, 'demo'); T('MT5 switching to Demo is always allowed', s == 200)
s, j = mode(EV, 'real'); T('the road is checked before the REAL word (still 403)', s == 403)
lessons(UE, 6); trade(UE, 5); s, j = mode(EV, 'real', 'REAL'); T('MT5 Real after the road with the word REAL: allowed', s == 200 and links.mode(UE) == 'real')
s, j = mode(EV, 'real'); T('after the road the word REAL is still needed', s == 400)
def dmode(h, m, conf=None): r = c.post('/api/brokers/Deriv/mode', json={'mode': m, **({'confirm': conf} if conf else {})}, headers=h); return r.status_code, r.get_json()
for u in (UE, UB, UBOSS): st.x("INSERT INTO broker_links(uid,broker,kind,secret_enc,mode,status,created,updated) VALUES(?,?,?,?,?,?,?,?)", (u, 'Deriv', 'token', 'x', 'demo', 'verified', 1, 1))
s, j = dmode(B, 'real', 'REAL'); T('Deriv Real with an unfinished road: 403 and plain words', s == 403 and 'Real trading is not open yet' in j['error'] and bk.mode(UB, 'Deriv') != 'real')
s, j = dmode(B, 'demo'); T('Deriv Demo is always allowed', s == 200)
s, j = dmode(EV, 'real', 'REAL'); T('Deriv Real after the road: allowed', s == 200 and bk.mode(UE, 'Deriv') == 'real')
s, j = dmode(BOSS, 'real', 'REAL'); T('an admin can switch Deriv to Real without the road', s == 200)
# ---- /api/path ----
T('signed out is refused', c.get('/api/path').status_code in (401, 403))
p = pathj(B); T('shape: eight badges, lessons, practice, why', len(p['milestones']) == 8 and p['lessons']['total'] == 6 and p['practice']['needed'] == 5 and not p['real_open'] and p['why'] and not p['exempt'])
T('badges: 5 lessons + 9 trades + a broker = first, three, broker, trade1, practice (not ten)', {m['id'] for m in p['milestones'] if m['done']} == {'first', 'three', 'broker', 'trade1', 'practice'})
UF = 'dev-fay@x.com'; FY = H('fay@x.com'); c.get('/api/me', headers=FY); p = pathj(FY)
T('a new person has no badge and every earned one starts as new', p['earned'] == 0 and not any(m['done'] or m['new'] for m in p['milestones']))
lessons(UF, 1); p = pathj(FY); T('one lesson earns exactly the first badge, flagged new', [m['id'] for m in p['milestones'] if m['done']] == ['first'] and [m['id'] for m in p['milestones'] if m['new']] == ['first'])
r = c.post('/api/path/seen', json={}, headers=FY); p = pathj(FY); T('seen clears the new flag but keeps the badge', r.status_code == 200 and p['earned'] == 1 and not any(m['new'] for m in p['milestones']))
lessons(UF, 3); p = pathj(FY); T('a later badge is new again, the old one is not', [m['id'] for m in p['milestones'] if m['new']] == ['three'])
lessons(UF, 6); trade(UF, 10); p = pathj(FY); T('all lessons + 10 trades: real, lessons, practice, ten earned and Real open', p['real_open'] and {'lessons', 'practice', 'real', 'ten', 'trade1'} <= {m['id'] for m in p['milestones'] if m['done']})
T('another person is not marked seen by my call', pathj(B)['milestones'][0]['new'] is True)
T('an admin is exempt and Real is open', pathj(BOSS)['exempt'] and pathj(BOSS)['real_open'])
# ---- the owner setting ----
r = c.post('/api/admin/settings', json={'practice_trades_needed': 101}, headers=BOSS); T('owner setting above 100 is refused', r.status_code == 400 and roadmap.needed() == 5)
r = c.post('/api/admin/settings', json={'practice_trades_needed': -1}, headers=BOSS); T('owner setting below 0 is refused', r.status_code == 400)
r = c.post('/api/admin/settings', json={'practice_trades_needed': 8}, headers=BOSS); T('owner setting 8 is saved', r.status_code == 200 and roadmap.needed() == 8)
r = c.post('/api/admin/settings', json={'practice_trades_needed': 3}, headers=A); T('a normal person cannot change it', r.status_code in (401, 403) and roadmap.needed() == 8); st.put('practice_trades_needed', '5')
# ---- the page ----
js = open(os.path.join(ROOT, 'static', 'roadmap.js'), encoding='utf-8').read(); ix = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read(); cj = open(os.path.join(ROOT, 'static', 'course.js'), encoding='utf-8').read()
T('page loads roadmap.js after course.js', '<script src="/static/course.js"></script><script src="/static/roadmap.js"></script>' in ix)
T('the page escapes text and uses the server routes', 'function esc' in js and '/api/path"' in js and '/api/path/seen' in js and 'innerHTML' in js)
T('no colours written, only site variables', not re.search(r'#[0-9a-fA-F]{3,6}\b', js))
T('wording: no profit promise', not re.search(r'guarantee|risk.free|sure profit', js + roadmap.why(UA) + str(roadmap.M), re.I) and 'promise of profit' in js)
T('the lesson screens no longer say Real is unlocked by lessons alone', 'Real trading is unlocked.' not in cj and 'unlocked for you' not in cj and 'Finishing the lessons unlocks Real' not in cj)
if shutil.which('node'):
    r = subprocess.run(['node', '--check', os.path.join(ROOT, 'static', 'roadmap.js')], capture_output=True, text=True); T('roadmap.js is valid JavaScript', r.returncode == 0)
for f in glob.glob(DB + '*'): os.remove(f)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
