"""No daily trade limit (owner's request Nov 19). max_trades_day = 0 means unlimited; a number above 0 still works if someone sets it. Run: python tests/test_nolimit.py"""
import os, sys, glob, time, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'nolimit_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t')
os.environ.pop('MAX_TRADES_DAY', None)
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app   # creates the tables
from backend import store as st, risk, links
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
now = dt.datetime(2026, 11, 18, 12, 0, tzinfo=dt.timezone.utc).timestamp()      # a Wednesday, midday
st.acct = lambda uid='': {'seen': now - 5, 'balance': 1000, 'open': 0, 'demo': True}
links.bot_on = lambda uid='': True
for i in range(40):
    st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
         ('XAUUSD', 'buy', 1, 1, 1, 1, 's', 1, 'closed', int(now - 60 * i), ''))
T('the default setting is 0 (no daily limit)', st.fget('max_trades_day') == 0)
T('40 trades already today: the gate is still open', risk.global_gate(now) == (True, 'ok'))
st.put('max_trades_day', 6)
T('if someone sets a limit of 6 it still works', risk.global_gate(now) == (False, 'max trades today'))
st.put('max_trades_day', 0)
T('set back to 0: open again', risk.global_gate(now) == (True, 'ok'))
for f in glob.glob(DB + '*'): os.remove(f)
print('\n%d/%d passed' % (sum(1 for _, o in R if o), len(R))); sys.exit(0 if all(o for _, o in R) else 1)
