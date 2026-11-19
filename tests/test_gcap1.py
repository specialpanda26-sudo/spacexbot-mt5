"""Section 3 tests: group profit target and group loss limit (server side). No network. Run: python tests/test_gcap1.py
(The closing itself is the EA's job, Section 4. These tests check what the server stores and hands to the EA.)"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_gcap1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, burst, groupcap
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); H = {'X-EA-Key': 'k'}
def sync(): return c.post('/api/ea/sync', json={'account': {'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True}}, headers=H).get_json()
def clean(): st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'bg:%' OR k LIKE 'gcap:%'")
def bad(d):
    try: groupcap.save('', d); return False
    except ValueError: return True
SET = {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 'macd_cross', 'score': 1}
def multi_group(n=3, uid=''):
    now = int(time.time()); first = None
    for i in range(n):
        rid = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES('XAUUSD','buy',2000,1990,2020,0.3,'macd_cross',1,'pending',?,?,?)", (now, uid or None, first))
        if first is None: first = rid; st.x('UPDATE signals SET grp=? WHERE id=?', (rid, rid))
    return first
st.put('bot_enabled', '1')

# ---------- the choices
clean(); T('default is off, no target, no loss limit', groupcap.get('') == {'on': False, 'target_usd': 0.0, 'loss_pct': 0.0})
g = groupcap.save('', {'on': True, 'target_usd': 50, 'loss_pct': 2}); T('saves $50 target and 2% loss limit', g == {'on': True, 'target_usd': 50.0, 'loss_pct': 2.0})
g = groupcap.save('', {'loss_pct': 0}); T('0 switches one rule off and keeps the other', g['loss_pct'] == 0 and g['target_usd'] == 50.0)
T('bad values are refused, nothing saved', bad({'target_usd': -1}) and bad({'target_usd': 'abc'}) and bad({'loss_pct': 80}) and bad({'loss_pct': True}) and bad({'on': 'yes'}) and bad({'target_usd': float('nan')}) and bad([]))
T('a refused save changed nothing', groupcap.get('')['target_usd'] == 50.0)
T('0.01 dollars is refused (too small to mean anything)', bad({'target_usd': 0.01}))

# ---------- rules() only for real groups
clean(); groupcap.save('', {'on': True, 'target_usd': 50, 'loss_pct': 2})
T('a group of 3 gets the rules', groupcap.rules('', 3) == {'tgt': 50.0, 'loss': 2.0})
T('a single trade is not a group: no rules', groupcap.rules('', 1) is None)
groupcap.save('', {'on': False}); T('switched off: no rules', groupcap.rules('', 3) is None)
groupcap.save('', {'on': True, 'target_usd': 0, 'loss_pct': 0}); T('on but both 0: no rules', groupcap.rules('', 3) is None)

# ---------- a normal multi-entry group
clean(); gid = multi_group(3); j = sync()
T('rules off: a normal group still arrives one signal at a time, no basket (unchanged)', j['signal'] is not None and 'basket' not in j)
clean(); groupcap.save('', {'on': True, 'target_usd': 50, 'loss_pct': 2}); gid = multi_group(3); groupcap.mark(gid, '', 3); j = sync()
b = j.get('basket')
T('rules on: the group comes as ONE basket, signal empty', j['signal'] is None and b is not None and b['gid'] == gid)
T('the basket carries the $50 group target and the 2 percent loss limit', b['tgt'] == 50.0 and b['loss'] == 2.0 and b['kind'] == 'multi')
T('an older EA that only reads each gets a share of the target (50/3), so it can never close at once', abs(b['each'] * 3 - 50) < 0.01)
T('all three entries are in the basket and marked sent', len(b['ids'].split(',')) == 3 and {r['status'] for r in st.q('SELECT status FROM signals')} == {'sent'})
T('a multi group does not count as a running burst', not burst.active(''))
clean(); groupcap.save('', {'on': True, 'target_usd': 0, 'loss_pct': 3}); gid = multi_group(2); groupcap.mark(gid, '', 2); b = sync()['basket']
T('loss limit only: no target, and each is a target that can never be reached (old EA cannot close it at once)', b['tgt'] == 0 and b['loss'] == 3.0 and b['each'] >= 100000)
clean(); groupcap.save('', {'on': True, 'target_usd': 50}); gid = multi_group(1); T('one entry: mark does nothing', not groupcap.mark(gid, '', 1))

# ---------- a burst group
clean(); groupcap.save('', {'on': False}); ids = burst.create('', 'XAUUSD', SET, {'kind': 'quick', 'n': 5, 'each': 0.5, 'giveback': 40}, '{}'); b = sync()['basket']
T('burst with group rules off: unchanged (each 0.5, no target, no loss)', b['each'] == 0.5 and b['tgt'] == 0 and b['loss'] == 0)
clean(); groupcap.save('', {'on': True, 'target_usd': 10, 'loss_pct': 1.5}); ids = burst.create('', 'XAUUSD', SET, {'kind': 'quick', 'n': 5, 'each': 0.5, 'giveback': 40}, '{}'); b = sync()['basket']
T('burst with a group target: $10 for the group, 1.5 percent loss limit', b['tgt'] == 10.0 and b['loss'] == 1.5 and b['kind'] == 'quick')
T('burst keeps its give-back guard', b['gb'] == 40)
T('older EA sees each = 10/5 = 2', abs(b['each'] - 2.0) < 0.001)
T('a real burst still counts as active (it holds the next burst back)', burst.active('') is True)

# ---------- people stay apart
clean(); groupcap.save('u1', {'on': True, 'target_usd': 7}); T("one person's rules never reach another", groupcap.get('u2')['target_usd'] == 0 and groupcap.get('')['target_usd'] == 0)

# ---------- the endpoints
def api(m, p, **k): return getattr(c, m)(p, **k)
r = api('get', '/api/groupcap'); T('the endpoint needs a signed-in person', r.status_code in (401, 403))

# ---------- the notification wording in the patched app
src = open(os.path.join(ROOT, 'backend', 'app.py')).read()
T("a multi group is called a 'group' not a 'burst' in alerts", "title.replace(' burst ', ' group ')" in src)

bad_ = [n for n, ok in R if not ok]
print('\n%d passed, %d failed' % (len(R) - len(bad_), len(bad_)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_ else 0)
