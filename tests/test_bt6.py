"""BT6 tests: live profit of open Deriv groups on the burst card and in Deriv's floating figure. Fake Deriv session, no network. Run: python tests/test_bt6.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt6_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, burst, burst_live as bl, deriv_group as dg, livestats as ls, brokers as bk
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
NOW = int(time.time())
class Fake:
    def __init__(s, prof): s.prof, s.log = dict(prof), []
    def ask(s, m):
        s.log.append(m)
        if 'proposal_open_contract' in m: return {'proposal_open_contract': {'is_sold': 0, 'profit': s.prof.get(m['contract_id'], 0), 'current_spot': 2000.0}}
        return {'error': {'message': 'x'}}
def wipe(): st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'bg:%' OR k LIKE 'glive:%'")
def group(uid='', n=3, kind='quick', dtgt=10.0, status='open'):
    ids = []; sql = "INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason,ticket,broker,lots) VALUES('XAUUSD','buy',2000,1990,2020,0.33,'s',1,?,?,?,?,'why',?,'Deriv',1.0)"
    for i in range(n): ids.append(st.x(sql, (status, NOW - 60, uid or None, ids[0] if ids else None, str(101 + i))))
    st.x('UPDATE signals SET grp=? WHERE id=?', (ids[0], ids[0]))
    st.put('bg:%d' % ids[0], json.dumps({'k': kind, 'n': n, 'each': 1, 'gb': 0, 'dtgt': dtgt, 't': NOW - 60})); return ids

wipe(); T('no group open: no sentence and floating 0', bl.group('', NOW) is None and bl.floating(('',), NOW) == 0.0)
ids = group()
T('burst group open but no live figure yet: says so', bl.group('', NOW) == '3 open, live profit not read yet.')
f = Fake({101: 0.2, 102: 0.15, 103: -0.05}); out = dg.check(f, '', {}, now=NOW)
T('check does not close a group under its target', out == [] and not [m for m in f.log if 'sell' in m])
T('check saved the live total 0.30', json.loads(st.get('glive:%d' % ids[0]))['live'] == 0.3)
T('the card sentence: 3 open, +$0.30 of +$10.00 target, just now', bl.group('', NOW) == '3 open, profit now +$0.30 of +$10.00 target (updated just now).')
T('burst.view carries it as group', burst.view('')['group'] == bl.group('', time.time()) or 'profit now +$0.30' in (burst.view('')['group'] or ''))
T('floating for the person is +0.30', bl.floating(('',), NOW) == 0.3)
T('a figure older than 150 seconds is ignored', bl.floating(('',), NOW + 151) == 0.0 and bl.group('', NOW + 151) == '3 open, live profit not read yet.')
T('another person sees nothing of it', bl.floating(('u9',), NOW) == 0.0 and bl.group('u9', NOW) is None)
T('a negative total reads -$0.40', (bl.save(ids[0], -0.4, -0.4, 3, 10, 0, NOW), bl.group('', NOW))[1] == '3 open, profit now -$0.40 of +$10.00 target (updated just now).')
bl.save(ids[0], 0.3, 0.3, 3, 10, 0, NOW - 300); T('five minutes old shown only when still fresh: not shown (150 s)', bl.group('', NOW) == '3 open, live profit not read yet.')
bl.save(ids[0], 0.3, 0.3, 3, 10, 0, NOW - 100); T('100 seconds old reads "1 min ago"', bl.group('', NOW).endswith('(updated 1 min ago).'))
st.x("UPDATE signals SET status='closed' WHERE grp=?", (ids[0],)); T('a closed group no longer counts', bl.group('', NOW) is None and bl.floating(('',), NOW) == 0.0)
wipe(); m = group(kind='multi'); bl.save(m[0], 0.5, 0.5, 3, 5, 0, NOW)
T('a normal multi group has no burst sentence but its profit counts as floating', bl.group('', NOW) is None and bl.floating(('',), NOW) == 0.5)
orig = bk.view; bk.view = lambda uid: [{'name': 'Deriv', 'balance': 100.0, 'bal_t': NOW, 'acct_demo': True}]
src = ls.sources('', True, NOW); T('Deriv equity = balance + floating (100.5)', src[0]['equity'] == 100.5 and src[0]['balance'] == 100.0)
wipe(); src = ls.sources('', True, NOW); T('no open group: equity equals balance', src[0]['equity'] == 100.0); bk.view = orig
page = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the card shows the group sentence once', page.count('j.group?') == 1)
n = sum(1 for _, ok in R if ok); print('%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
