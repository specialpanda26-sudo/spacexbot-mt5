"""BX4 tests: the banner lists each open trade with its stop loss and take profit. No network. Run: python tests/test_bx4.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bx4_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, livestats, live, brokers as bk, tradeon
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=OW); UID = 'dev-boss@x.com'
NOW = time.time()
st.x("INSERT OR REPLACE INTO broker_links(uid,broker,kind,label,mode,status,created,updated) VALUES(?,'Deriv','oauth','x','demo','verified',1,1)", (UID,))
st.set_acct({'balance': 500, 'equity': 500, 'open': 2, 'demo': True, 'src': 'deriv'}, UID); bk.set_bal(UID, 'Deriv', 500, 'USD', True); tradeon.set_(UID, True, 'Deriv')
def op(side, fill, sl, tp): return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,ticket,broker,fill) VALUES('XAUUSD',?,?,?,?,1,'macd_cross',1,'open',?,?,'7','Deriv',?)", (side, fill, sl, tp, int(NOW), UID, fill))
a = op('buy', 2650.12, 2640.5, 2670.25); b = op('sell', 2651.0, None, None)
sn = livestats.snapshot(UID, True, NOW); tr = {t['id']: t for t in sn['trades']}
T('each open trade carries its stop loss and take profit', tr[a]['sl'] == 2640.5 and tr[a]['tp'] == 2670.25 and tr[b]['sl'] is None)
big = live.build(True, live.snapshot(NOW, UID))['big']
T('the banner shows SL and TP for a trade that has them', 'BUY XAUUSD at 2650.12  SL 2640.5  TP 2670.25' in big)
T('a trade without levels shows no empty SL/TP', 'SELL XAUUSD at 2651.0' in big and 'SELL XAUUSD at 2651.0  SL' not in big)
T('the balance shows in the title and the expanded text for the owner', 'Bot running' in live.build(True, live.snapshot(NOW, UID))['title'] and 'Balance $500.00' in big and 'Equity $500.00' in big)
f = sum(1 for _, ok in R if not ok); print('%d/%d passed' % (len(R) - f, len(R))); sys.exit(1 if f else 0)
