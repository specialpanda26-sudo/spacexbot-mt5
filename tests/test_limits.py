"""Tests for backend/limits.py: the server now enforces Max trades a day and the loss-streak stop per person. Run: python tests/test_limits.py"""
import os, sys, json, re, time, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'limits_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend import app as appmod, store as st, limits, risk, links
C = appmod.app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; J = {'Authorization': 'Bearer dev:joe@x.com'}; K = {'Authorization': 'Bearer dev:kim@x.com'}
JU, KU = 'dev-joe@x.com', 'dev-kim@x.com'
R = []
def T(name, ok): R.append((name, bool(ok)))
NOW = int(dt.datetime(2026, 11, 18, 12, 0, tzinfo=dt.timezone.utc).timestamp())          # a Wednesday, midday UTC, so no weekend gate
def reset():
    st.x('DELETE FROM signals'); st.x('DELETE FROM links'); st.x("DELETE FROM kv WHERE k LIKE 'lim:%'")
    st.put('max_trades_day', '0'); st.put('max_losing_streak', '3'); st.put('bot_enabled', '1')
def setup(uid):
    links.new_key(uid); links.set_bot(uid, True)
    st.x('UPDATE links SET acct=?,seen=? WHERE uid=?', (json.dumps({'demo': True, 'balance': 1000, 'open': 0, 'seen': NOW}), NOW, uid))
def sig(uid, n=1, status='closed', pnl=None, closed=None):
    for i in range(n): st.x('INSERT INTO signals(symbol,side,entry,sl,tp,status,created,uid,pnl,closed) VALUES(?,?,?,?,?,?,?,?,?,?)', ('XAUUSD', 'buy', 1, .5, 2, status, NOW - 600 - i, uid or None, pnl, closed))
def gate(uid): return risk.global_gate(NOW, uid)
def fails(f):
    try: f(); return False
    except ValueError: return True

# ---- the rule (module) ----
reset()
T('defaults: no trade limit, streak stop 3 (the owner defaults)', limits.trades('') == 0 and limits.streak('') == 3 and limits.trades(JU) == 0 and limits.streak(JU) == 3)
st.put('max_trades_day', '8'); limits.save(JU, 5)
T('own number below the owner cap wins', limits.trades(JU) == 5)
limits.save(JU, 20); T('own number above the owner cap is cut to the cap', limits.trades(JU) == 8 and limits.view(JU)['max_trades'] == 8)
limits.save(JU, 0); T('0 means use the owner setting', limits.trades(JU) == 8 and limits.view(JU)['max_trades'] == 0)
st.put('max_trades_day', '0'); limits.save(JU, 5); T('owner has no cap: the own number applies', limits.trades(JU) == 5)
st.put('max_trades_day', '3'); T('the owner lowering the cap applies at once, even to a saved number', limits.trades(JU) == 3)
st.put('max_trades_day', '0'); limits.save(JU, None, 2)
T('streak: own number below the owner (3) wins', limits.streak(JU) == 2)
limits.save(JU, None, 9); T('streak: own number above the owner is cut to it', limits.streak(JU) == 3)
st.put('max_losing_streak', '0'); T('owner switched the streak stop off: the own number applies alone', limits.streak(JU) == 9 and limits.streak('') == 0)
st.put('max_losing_streak', '3'); limits.save(JU, 4, 2); limits.save(KU, 6, 1)
T('two people keep separate numbers', limits.trades(JU) == 4 and limits.streak(JU) == 2 and limits.trades(KU) == 6 and limits.streak(KU) == 1)
T('a subscriber saving does not touch the owner settings', st.get('max_trades_day') == '0' and st.get('max_losing_streak') == '3')
limits.save('', 7, 2); T('the owner saving writes the global settings', st.get('max_trades_day') == '7' and st.get('max_losing_streak') == '2' and limits.trades('') == 7)
st.put('max_trades_day', '0'); st.put('max_losing_streak', '3')
before = (limits.trades(JU), limits.streak(JU))
for bad in ((-1, None), (101, None), (2.5, None), ('abc', None), (True, None), ([], None), (None, 11), (None, -2), (None, None), (None, 'x'), (1, 99)):
    T('refuses bad input %r' % (bad,), fails(lambda: limits.save(JU, *bad)))
T('refused input changed nothing', (limits.trades(JU), limits.streak(JU)) == before)
T('a number sent as text is accepted', limits.save(JU, '5', '2')['max_trades'] == 5)

# ---- the routes ----
reset(); C.get('/api/me', headers=J); C.get('/api/me', headers=K)
T('signed out: refused', C.get('/api/limits').status_code == 401 and C.post('/api/limits', json={'max_trades': 3}).status_code == 401)
r = C.get('/api/limits', headers=J); T('a new subscriber starts with no own limits', r.status_code == 200 and r.json['max_trades'] == 0 and r.json['streak'] == 0 and r.json['cap_streak'] == 3)
r = C.post('/api/limits', json={'max_trades': 5}, headers=J); T('saving max trades returns the saved value', r.status_code == 200 and r.json['max_trades'] == 5)
T('it is still there on the next read', C.get('/api/limits', headers=J).json['max_trades'] == 5)
r = C.post('/api/limits', json={'streak': 2}, headers=J); T('saving the streak keeps max trades', r.json['streak'] == 2 and r.json['max_trades'] == 5)
T('the server rule really changed', limits.trades(JU) == 5 and limits.streak(JU) == 2)
T('another subscriber is not affected', C.get('/api/limits', headers=K).json['max_trades'] == 0 and limits.trades(KU) == 0)
for body in ({'max_trades': -1}, {'max_trades': 500}, {'max_trades': 'abc'}, {'max_trades': 1.5}, {'streak': 50}, {}, {'foo': 1}):
    r = C.post('/api/limits', json=body, headers=J); T('route refuses %s' % body, r.status_code == 400 and 'error' in r.json)
T('refused requests changed nothing', limits.trades(JU) == 5 and limits.streak(JU) == 2)
r = C.post('/api/limits', json={'max_trades': 0}, headers=J); T('0 clears it back to the default', r.json['max_trades'] == 0 and limits.trades(JU) == 0)
r = C.post('/api/limits', json={'max_trades': 4}, headers=A); T('the owner saves the global setting through the same route', r.status_code == 200 and st.get('max_trades_day') == '4' and r.json['max_trades'] == 4)
r = C.post('/api/limits', json={'max_trades': 9}, headers=J); T('a subscriber cannot go above the owner cap', r.json['max_trades'] == 4 and r.json['cap_trades'] == 4 and limits.trades(JU) == 4)
st.put('max_trades_day', '0')

# ---- the real gate ----
reset(); setup('u1'); setup('u2')
T('gate baseline is open', gate('u1') == (True, 'ok'))
sig('u1', 3); limits.save('u1', 3)
T('own limit reached: the gate says max trades today', gate('u1') == (False, 'max trades today'))
limits.save('u1', 4); T('own limit raised: the gate opens', gate('u1') == (True, 'ok'))
limits.save('u1', 0); T('limit cleared and no owner limit: the gate opens', gate('u1') == (True, 'ok'))
sig('u2', 3); T("one person's trades and limit do not close another person's gate", gate('u2') == (True, 'ok'))
limits.save('u1', 3); T('u1 still closed after u2 moves', gate('u1') == (False, 'max trades today'))
reset(); st.put('acct', json.dumps({'demo': True, 'balance': 1000, 'open': 0, 'seen': NOW})); st.put('bot_enabled', '1')
T('owner gate baseline is open', gate('') == (True, 'ok'))
sig('', 2); st.put('max_trades_day', '2'); T('owner global limit closes the owner gate', gate('') == (False, 'max trades today'))
st.put('max_trades_day', '0'); T('and no limit opens it again', gate('') == (True, 'ok'))
reset(); setup('u1'); setup('u2'); st.put('max_trades_day', '2'); sig('u2', 2)
T('the owner cap closes a subscriber with no own number', gate('u2') == (False, 'max trades today') and gate('u1') == (True, 'ok'))
reset(); setup('u1')
sig('u1', 2, pnl=-1.0, closed=NOW - 60); limits.save('u1', None, 2)
T('streak: own stop of 2 closes the gate after 2 losses', gate('u1')[0] is False and 'losses in a row' in gate('u1')[1])
limits.save('u1', None, 0); T('streak: cleared, the owner 3 needs a third loss', gate('u1') == (True, 'ok'))
sig('u1', 1, pnl=-1.0, closed=NOW - 30); T('streak: the owner 3 closes it at three losses', gate('u1')[0] is False and 'losses in a row' in gate('u1')[1])

# ---- the page ----
h = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page loads the limits from the server', 'function limLoad()' in h and 'SXA.api("/api/limits")' in h and 'limLoad();' in h)
T('page saves the two boxes to the server', 'function limSave(' in h and 'limSave(a[1],n,this,a[2])' in h and h.count('/api/limits') >= 2)
T('page text no longer shows a made-up default of 10 trades', '" · Max "+X.maxT+" trades · Stop after "' not in h and 'No trade limit' in h and 'X.maxT?"Max "' in h)
try:
    js = '\n;\n'.join(re.findall(r'<script>(.*?)</script>', h, re.S)); p = os.path.join(HERE, 'limits_page.js'); open(p, 'w', encoding='utf-8').write(js)
    rr = subprocess.run(['node', '--check', p], capture_output=True, text=True); os.remove(p)
    T('the page script still parses (node --check)', rr.returncode == 0)
except FileNotFoundError: print('(node not found: page script check skipped)')
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
