"""D4a tests: the account tag on Take. Run: python tests/test_d4.py"""
import os, sys
D = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(D, '_d4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=P)
if os.path.exists(P): os.remove(P)
sys.path.insert(0, os.path.join(D, '..'))
from backend.app import app
from backend import store as st, assist
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
NOW = 1700000000
def sig(sym, side, created):
    st.x('INSERT INTO signals(symbol,side,entry,sl,tp,status,created) VALUES(?,?,?,?,?,?,?)', (sym, side, 100.0, 99.0, 102.0, 'new', created))
    return st.q('SELECT MAX(id) AS m FROM signals', (), True)['m']
a = sig('EURUSD', 'buy', NOW); b = sig('XAUUSD', 'sell', NOW + 10); c = sig('GBPUSD', 'buy', NOW + 20); d = sig('USDJPY', 'sell', NOW + 30); e = sig('AUDUSD', 'buy', NOW + 40)
tag = lambda u, s: {x['id']: x['acct'] for x in assist.running(u, NOW + 900)}.get(s, 'MISSING')
assist.take('u1', a, now=NOW + 60, acct='Deriv MT5')
T('tag is saved and shown in running', tag('u1', a) == 'Deriv MT5')
assist.take('u1', b, now=NOW + 70)
T('no tag gives None', tag('u1', b) is None)
assist.take('u1', c, now=NOW + 80, acct='fbs')
T('lower case is accepted', tag('u1', c) == 'FBS')
assist.take('u1', d, now=NOW + 90, acct='Binance')
T('an unknown name is ignored, the take still works', tag('u1', d) is None)
assist.skip('u2', e, now=NOW + 100); assist.take('u2', e, now=NOW + 110, acct='FBS')
T('skip then take keeps the tag', tag('u2', e) == 'FBS')
assist.take('u1', a, now=NOW + 120, acct='FBS')
T('a second tap does not change the tag', tag('u1', a) == 'Deriv MT5')
T('the Take route passes the tag', "acct=_j().get('acct')" in open(os.path.join(D, '..', 'backend', 'app.py'), encoding='utf-8').read())
st.x('DROP TABLE assist_log')
st.x('CREATE TABLE assist_log(uid TEXT,sid BIGINT,action TEXT,ts BIGINT,lots DOUBLE PRECISION,outcome TEXT,pnl DOUBLE PRECISION,done BIGINT,PRIMARY KEY(uid,sid))')
st.x("INSERT INTO assist_log(uid,sid,action,ts,lots) VALUES(?,?,'taken',?,?)", ('old', a, NOW, 0.1))
assist.init()
T('an old table gets the column and keeps its row', tag('old', a) is None)
assist.init(); assist.take('new', b, now=NOW + 60, acct='FBS')
T('init twice is safe, and take works after it', tag('new', b) == 'FBS')
if os.path.exists(P): os.remove(P)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
