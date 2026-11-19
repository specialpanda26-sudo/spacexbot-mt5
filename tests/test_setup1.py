"""Section 1 checks: the daily trade limit counts SETUPS, not entries, so 6 entries opened together are ONE trade. Run: python tests/test_setup1.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'setup1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import store as st, risk, multi, prefs
WED = 1735732800          # Wednesday 2025-01-01 12:00 UTC
R = []
def T(name, ok): R.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name)
def fresh(**kv):
    st.x('DELETE FROM signals'); st.x('DELETE FROM kv'); st.put('bot_enabled', 1)
    st.put('acct', json.dumps({'balance': 1000, 'open': 0, 'demo': True, 'allow_live': False, 'seen': WED}))
    for k, v in kv.items(): st.put(k, v)
def setup(n, status='closed', t=WED - 100):
    """n entries opened together: the first row names the group, the others join it (the same way the bot writes them)."""
    q = "INSERT INTO signals(symbol,side,status,created,uid) VALUES('EURUSD','buy',?,?,'')"
    first = st.x(q, (status, t)); st.x('UPDATE signals SET grp=? WHERE id=?', (first, first))
    for _ in range(n - 1): st.x("INSERT INTO signals(symbol,side,status,created,uid,grp) VALUES('EURUSD','buy',?,?,'',?)", (status, t, first))
fresh(max_trades_day=3); setup(6)
T('6 entries of one setup count as one trade', risk.global_gate(WED) == (True, 'ok'))
setup(1); setup(1)
ok, why = risk.global_gate(WED)
T('three setups reach a limit of three', (ok, why) == (False, 'max trades today'))
st.put('max_trades_day', 4)
T('a limit of four allows one more', risk.global_gate(WED) == (True, 'ok'))
fresh(max_trades_day=6, max_open=8, max_open_ceiling=8); prefs.save('', {'entries': 6}); setup(6, t=st.day_start() + 1)
T('after one setup of 6, the next setup may still open 6', multi.entries('', 3) == 6)
fresh(max_open=8, max_open_ceiling=8); prefs.save('', {'entries': 6}); setup(3, 'open', st.day_start() + 1)
T('entries are cut only by the room left under positions at once', multi.entries('', 3) == 5)
fresh(max_open=3); prefs.save('', {'entries': 6})
T('positions at once of 3 keeps a setup to 3 entries (raise it to 8)', multi.entries('', 3) == 3)
if os.path.exists(DB): os.remove(DB)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
