"""BT8 tests: the burst results line. No network. Run: python tests/test_bt8.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt8_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, burst, burst_results as br
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
NOW = int(time.time()); G = [100]
def reset():
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'bg:%' OR k='burst_loss_target'")
def group(pnls, status='closed', uid='', age=3600, kind='quick', meta=True):
    G[0] += 10; g = G[0]
    for i, p in enumerate(pnls):
        st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,pnl,closed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
             ('XAUUSD', 'buy', 2000, 1990, 2010, 0.1, 's', 1, status, NOW - age - 60, uid or None, g, p, NOW - age if status == 'closed' else None))
    if meta: st.put('bg:%d' % g, json.dumps({'k': kind, 'n': len(pnls)}))
    return g

reset()
T('no groups: says none closed yet', br.stats('')['n'] == 0 and 'no closed burst groups' in br.line(''))
group([0.5, 0.4]); group([-1.0, -0.2]); group([0.3, 0.3]); group([0.0, 0.0])
group([1, 1], status='open'); group([5, 5], kind='multi'); group([2, 2], age=8 * 86400); group([9, 9], uid='u1'); group([3, 3], meta=False)
s = br.stats('')
T('counts only closed burst groups of this person in the last 7 days: 4 groups', s['n'] == 4)
T('2 won, 1 lost, 1 flat', (s['won'], s['lost'], s['flat']) == (2, 1, 1))
T('percents 50 and 25, net is +0.30', s['win_pct'] == 50 and s['loss_pct'] == 25 and s['net'] == 0.3)
L = br.line('')
T('line: 4 groups, 2 won (50%), 1 lost (25%), 1 flat, net +$0.30', '4 closed groups, 2 won (50%), 1 lost (25%), 1 flat. Net +$0.30.' in L)
T('line: 25 percent loss is inside the 25 percent target', 'inside it' in L)
T('line: under 10 groups is called a rough guide', 'rough guide' in L)
st.put('burst_loss_target', '10'); T('target 10: the same 25 percent loss is above it', 'you are above it' in br.line('') and br.stats('')['target'] == 10)
st.put('burst_loss_target', 'abc'); T('a bad target falls back to 25', br.target() == 25)
st.put('burst_loss_target', '500'); T('a target of 500 is held at 99', br.target() == 99)
reset()
for _ in range(8): group([0.4])
for _ in range(2): group([-0.5])
L = br.line('')
T('10 groups: no rough guide note, 20 percent loss is inside', 'rough guide' not in L and '20%' in L and 'inside it' in L)
reset(); group([0.2, None]); group([None, None])
T('entries with no profit are ignored; a group of only those is not counted', br.stats('')['n'] == 1 and br.stats('')['won'] == 1)
reset(); group([0.4]); st.put('bg:%d' % G[0], 'not json')
T('a bad saved group value is skipped and does not crash', br.stats('')['n'] == 0)
reset(); group([0.4], uid='u1')
T('another person has their own numbers', br.stats('u1')['n'] == 1 and br.stats('')['n'] == 0)
T('burst.view carries the results line', 'results' in burst.view('') and burst.view('u1')['results'].startswith('Results (last 7 days)'))
bad = [n for n, ok in R if not ok]
print('%d passed, %d failed' % (len(R) - len(bad), len(bad)))
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
sys.exit(1 if bad else 0)
