"""D3a tests: running() lists taken trades with no result yet. Run: python tests/test_d3.py"""
import os, sys
D = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(D, '_d3_test.db')
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
a = sig('EURUSD', 'buy', NOW); b = sig('XAUUSD', 'sell', NOW + 10); c = sig('GBPUSD', 'buy', NOW + 20)
T('nothing taken: empty list', assist.running('u1', NOW) == [])
assist.take('u1', a, now=NOW + 60); assist.take('u1', b, now=NOW + 120); assist.skip('u1', c, now=NOW + 130)
r = assist.running('u1', NOW + 720)
T('two taken trades are listed, the skipped one is not', len(r) == 2 and {x['symbol'] for x in r} == {'EURUSD', 'XAUUSD'})
T('newest taken first', r[0]['symbol'] == 'XAUUSD')
T('row has side, entry, sl, tp, lots, since', all(k in r[0] for k in ('side', 'entry', 'sl', 'tp', 'lots', 'since')) and r[0]['side'] == 'sell' and r[0]['tp'] == 102.0)
T('minutes running', r[0]['minutes'] == 10 and r[1]['minutes'] == 11)
T('still listed a day later (no silent drop)', len(assist.running('u1', NOW + 86400)) == 2)
T('another person sees none of it', assist.running('u2', NOW) == [])
assist.result('u1', a, 'win', 5.0, now=NOW + 800)
r = assist.running('u1', NOW + 900)
T('logging a result removes it from running', len(r) == 1 and r[0]['symbol'] == 'XAUUSD')
T('GET /api/assist carries running', "running=assist.running(u['uid'])" in open(os.path.join(D, '..', 'backend', 'app.py'), encoding='utf-8').read())
if os.path.exists(P): os.remove(P)
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
