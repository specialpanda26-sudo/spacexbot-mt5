"""LC1 checks: the person's biggest lot (max_lot) and fixed lot go to the MT5 bridge with every trade. No network.
Run: python tests/test_lc1.py   (last line: N checks, M failed)"""
import os, sys, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'lc1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD', BROKER_KEY='unit-test-lock-key-0123456789')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, burst
c = app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=OW)
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
st.put('bot_enabled', '1')
def poll(): return c.post('/api/ea/sync', headers={'X-EA-Key': 'k'}, json={'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'allow_live': True}).get_json()
def sig(grp=None):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES('XAUUSD','sell',3620,3624.2,3601.9,1,'s',1,'pending',?,NULL,?)", (int(time.time()), grp))

T('default: no biggest lot (0) and automatic lot (0)', burst.get('')['max_lot'] == 0 and burst.get('')['lot'] == 0)
j = c.post('/api/burst', json={'max_lot': 0.06}, headers=OW).get_json()
T('saved through the app route', j['settings']['max_lot'] == 0.06)
T('saving it leaves the other choices alone', j['settings']['lot'] == 0 and j['settings']['loss_usd'] == 0 and j['settings']['quick_n'] == 5)
T('0.01 is allowed', c.post('/api/burst', json={'max_lot': 0.01}, headers=OW).get_json()['settings']['max_lot'] == 0.01)
c.post('/api/burst', json={'max_lot': 0.06}, headers=OW)
for bad in (-1, 0.005, 'x', True, 101, None, float('nan')): T('bad value %r refused' % (bad,), c.post('/api/burst', json={'max_lot': bad}, headers=OW).status_code == 400)
T('a refused value changes nothing', burst.get('')['max_lot'] == 0.06)
c.post('/api/burst', json={'lot': 0.02}, headers=OW)
T('the fixed lot is still its own choice', burst.get('')['lot'] == 0.02 and burst.get('')['max_lot'] == 0.06)

sig(); s = (poll().get('signal') or {})
T('a single signal carries lot 0.02 and max_lot 0.06', s.get('lot') == 0.02 and s.get('max_lot') == 0.06)
T('the single signal keeps its normal fields', s.get('risk_pct') == 1 and s.get('side') == 'sell' and 'stake_pct' in s)
st.x('DELETE FROM signals')
g = sig(); st.x('UPDATE signals SET grp=? WHERE id=?', (g, g)); sig(g)
st.put('bg:%d' % g, json.dumps({'k': 'quick', 'n': 2, 'each': 0.5, 'gb': 40, 't': int(time.time()), 'dtgt': 1.0, 'lot': 0.02}))
bk = poll().get('basket') or {}
T('a burst basket carries max_lot 0.06 and its own lot 0.02', bk.get('max_lot') == 0.06 and bk.get('lot') == 0.02)
st.x('DELETE FROM signals'); c.post('/api/burst', json={'max_lot': 0, 'lot': 0}, headers=OW); sig(); s = (poll().get('signal') or {})
T('both cleared: the bridge gets 0 and 0 (automatic, no cap)', s.get('lot') == 0 and s.get('max_lot') == 0)
print('%d checks, %d failed' % (len(R), sum(1 for _, ok in R if not ok)))
