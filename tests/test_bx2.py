"""BX2 tests: the Journal and Stats show finished burst groups (won, lost, win rate, net, losing run). No network. Run: python tests/test_bx2.py"""
import os, sys, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bx2_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, journal
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=OW); UID = 'dev-boss@x.com'
NOW = int(time.time())
def sig(grp, pnl, status='closed', sym='XAUUSD', ago=0):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,closed,pnl,uid,grp,broker) VALUES(?,?,1,1,1,1,'x',1,?,?,?,?,?,?,'Deriv')", (sym, 'buy', status, NOW - ago - 60, NOW - ago if status == 'closed' else None, pnl if status == 'closed' else None, UID, grp))
def grp(kind, entries, status='closed', ago=0):
    first = sig(None, entries[0], status, ago=ago); st.x('UPDATE signals SET grp=id WHERE id=?', (first,))
    for p in entries[1:]: sig(first, p, status, ago=ago)
    st.put('bg:%d' % first, json.dumps({'k': kind, 'n': len(entries), 't': NOW})); return first
grp('burst', [0.5, 0.5, -0.2], ago=500)          # win +0.80
grp('burst', [-0.5, -0.5, 0.1], ago=400)         # loss -0.90
grp('burst', [-0.4, -0.4], ago=300)              # loss -0.80
grp('multi', [3.0, 3.0], ago=200)                # a normal group, NOT a burst
grp('burst', [0.5, 0.5], status='open', ago=100) # still open, not counted
grp('burst', [0.3, 0.3], ago=50)                 # win +0.60
sn = journal.snapshot(UID, True); B = sn['burst']; s = B['stats']
T('the snapshot carries a burst block', isinstance(B, dict) and 'stats' in B and 'groups' in B)
T('4 finished burst groups (normal group and open group left out)', s['groups'] == 4 and len(B['groups']) == 4)
T('2 won, 2 lost, win rate 50', (s['won'], s['lost'], s['win_rate']) == (2, 2, 50.0))
T('net is the sum of the groups (+0.80 -0.90 -0.80 +0.60 = -0.30)', s['net'] == -0.3 and s['per_group'] == -0.07 or s['per_group'] == -0.08)
T('best +0.80 and worst -0.90', s['best'] == 0.8 and s['worst'] == -0.9)
T('losing run of 2 groups in a row', s['loss_streak'] == 2)
T('newest group first and each shows its entries and result', B['groups'][0]['pnl'] == 0.6 and B['groups'][0]['entries'] == 2 and B['groups'][0]['result'] == 'win')
T('a person with no bursts gets zero groups, not an error', journal.snapshot('nobody@x', False)['burst']['stats']['groups'] == 0)
T('the ordinary numbers are unchanged', sn['stats']['trades'] >= 8 and 'pairs' in sn)
r = c.get('/api/journal', headers=OW).get_json(); T('GET /api/journal returns the burst block', r['burst']['stats']['groups'] == 4)
h = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('the page stores and draws the burst block', 'SXJ.burst = j.burst || null' in h and 'function bxs()' in h and 'BURST GROUPS' in h and "+bxs()}" in h)
f = sum(1 for _, ok in R if not ok); print('%d/%d passed' % (len(R) - f, len(R))); sys.exit(1 if f else 0)
