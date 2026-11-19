"""R8 multi-entry tests: how many entries, shared risk, the limits that still hold, group-aware exposure and loss streak, Deriv opens every waiting entry.
No network. Run: python tests/test_multi8.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_multi8_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, multi, deriv, limits
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
SCORE = [3]
brain.evaluate = lambda *a, **k: {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 't', 'score': SCORE[0], 'adx': 20}
risk.global_gate = lambda now=None, uid='': (True, '')
real_gate = risk.symbol_gate
BAR = [int(time.time()) // 900 * 900 - 900]
def run(score, uid=''):
    """Clean slate, then one scan with a setup of this score. Returns the new rows."""
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._last_scan.clear()
    A.bars.merge('XAUUSD', 'M15', [[BAR[0] - 900 * i, 2000, 2001, 1999, 2000, 1] for i in range(130)], uid=uid)
    A.bars.merge('XAUUSD', 'H1', [[BAR[0] - 3600 * i, 2000, 2001, 1999, 2000, 1] for i in range(10)], uid=uid)
    SCORE[0] = score; A._scan('XAUUSD', uid)
    return st.q('SELECT * FROM signals ORDER BY id')
def S(**kv):
    for k, v in kv.items(): st.put(k, v)
S(risk_pct='1.2', max_open='10', max_open_ceiling='10', max_trades_day='0')

rows = run(5)
T('default (off): one entry, the normal risk, no group', len(rows) == 1 and rows[0]['risk_pct'] == 1.2 and rows[0]['grp'] is None)

S(multi_entries='6', multi_min_score='3')
rows = run(2)
T('a setup below the minimum score gets one entry', len(rows) == 1 and rows[0]['grp'] is None)
rows = run(3)
T('a strong setup gets the owner\'s number of entries', len(rows) == 6)
T('all entries share one group, same side/prices, all pending', len({r['grp'] for r in rows}) == 1 and rows[0]['grp'] == rows[0]['id'] and {r['status'] for r in rows} == {'pending'} and len({(r['side'], r['entry'], r['sl'], r['tp']) for r in rows}) == 1)
T('the entries SHARE the normal risk (total never above one trade\'s)', abs(sum(r['risk_pct'] for r in rows) - 1.2) < 0.001 and all(r['risk_pct'] == 0.2 for r in rows))

S(multi_entries='99'); rows = run(4); T('the owner cannot go past 10 entries', len(rows) == 10)
S(multi_entries='abc'); rows = run(4); T('a garbage setting means off', len(rows) == 1)
S(multi_entries='6')

S(max_open='4'); rows = run(3); T('never above the max positions at once (room 4)', len(rows) == 4)
st.x('DELETE FROM signals')
S(max_open='4')
st.x("INSERT INTO signals(symbol,side,status,created) VALUES('EURUSD','buy','open',?)", (int(time.time()),))
A._last_scan.clear(); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); SCORE[0] = 3; A._scan('XAUUSD', '')
T('positions already open use up the room (1 open, max 4 -> 3 entries)', st.q("SELECT COUNT(*) n FROM signals WHERE grp IS NOT NULL", (), True)['n'] == 3)
S(max_open='10', max_trades_day='2'); rows = run(3); T('the max trades a day counts setups, so it does not trim the entries', len(rows) == 6)
S(max_trades_day='0')

S(max_open='10', cooldown_min='0', max_ccy_exposure='2', news_lock='0')
run(3)
ok, why = real_gate('XAUUSD', 'buy', uid='')
T('six entries of one setup count once in the exposure limit', risk.exposure('') == {'XAU': 1, 'USD': -1} and ok)
st.x('DELETE FROM signals')
for i in range(3): st.x("INSERT INTO signals(symbol,side,status,created) VALUES('XAUUSD','buy','open',?)", (int(time.time()),))
ok, why = real_gate('XAUUSD', 'buy', uid='')
T('control: three separate (ungrouped) trades still hit the limit', (not ok) and 'exposure' in why)

st.x('DELETE FROM signals'); now = int(time.time())
for i in range(3): st.x("INSERT INTO signals(symbol,side,status,created,pnl,closed,grp) VALUES('XAUUSD','buy','closed',?,-2,?,77)", (now - 100, now - 10))
last = risk._setups(st.q("SELECT pnl,closed,grp FROM signals WHERE status='closed' ORDER BY closed DESC"))
T('three losing entries of one setup collapse to one result with their summed pnl', len(last) == 1 and last[0]['pnl'] == -6)
st.x('DELETE FROM signals')
for i in range(3): st.x("INSERT INTO signals(symbol,side,status,created,pnl,closed) VALUES('XAUUSD','buy','closed',?,-2,?)", (now - 100, now - 10 - i))
last = risk._setups(st.q("SELECT pnl,closed,grp FROM signals WHERE status='closed' ORDER BY closed DESC"))
T('control: three separate losses stay three results', len(last) == 3)

U = 'deriv-user'; st.x('DELETE FROM signals')
for i in range(4): st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES('XAUUSD','buy',2000,1990,2020,0.3,'t',3,'pending',?,?,1)", (int(time.time()), U))
_p, _b, _r, _s = deriv._place, deriv._bot, deriv._report, deriv._resnap
n = [0]
def place(sess, s, bal, cur): n[0] += 1; return 'open', {'contract_id': 900 + n[0], 'stake': 5.0, 'mult': 20}
deriv._place = place; deriv._bot = lambda uid: True; deriv._report = lambda *a, **k: None; deriv._resnap = lambda *a, **k: None
deriv._trade(None, U, {'demo': True, 'currency': 'USD'}, 1000.0, time.time())
T('Deriv opens all four waiting entries in one round', st.q("SELECT COUNT(*) n FROM signals WHERE uid=? AND status='open'", (U,), True)['n'] == 4)
st.x('DELETE FROM signals')
for i in range(3): st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES('XAUUSD','buy',2000,1990,2020,0.3,'t',3,'pending',?,?,1)", (int(time.time()), U))
def boom(sess, s, bal, cur): raise RuntimeError('no answer')
deriv._place = boom
deriv._trade(None, U, {'demo': True, 'currency': 'USD'}, 1000.0, time.time())
q = {r['status']: r['n'] for r in st.q("SELECT status, COUNT(*) n FROM signals WHERE uid=? GROUP BY status", (U,))}
T('an unconfirmed buy stops the round (the others stay pending)', q.get('sent') == 1 and q.get('pending') == 2)
deriv._place, deriv._bot, deriv._report, deriv._resnap = _p, _b, _r, _s

src = open(os.path.join(HERE, '..', 'backend', 'store.py')).read() + open(os.path.join(HERE, '..', 'supabase_schema.sql')).read()
T('the grp column exists in SQLite and both Postgres schemas', src.count('grp BIGINT') >= 2 and "'grp INTEGER'" in src)

bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
if bad: sys.exit(1)
