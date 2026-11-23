"""BT12 tests: the burst card says how long ago the MT5 bridge last talked. No network. Run: python tests/test_bt12.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt12_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, burst, burst_bridge as bb, risk
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for k, v in dict(bot_enabled='1', burst_enabled='1', burst_ceiling='15', max_trades_day='0', news_lock='0').items(): st.put(k, v)
burst.save('', {'on': True, 'idle_min': 5})
now = int(time.time()); real_acct = st.acct
def seen(sec_ago, **kw): st.acct = lambda uid='': dict({'seen': now - sec_ago if sec_ago is not None else 0, 'demo': True}, **kw)
def why(): return burst.explain('', now)['why']
BASE = 'MT5 is not talking to the server. Open MT5 on your computer and check the SpaceX bridge is running.'

seen(660); w = why()
T('silent 11 minutes: the old sentence, then Last contact: 11 min ago.', w == BASE + ' Last contact: 11 min ago.')
seen(3 * 3600 + 5); T('silent 3 hours: 3 h ago', why() == BASE + ' Last contact: 3 h ago.')
seen(None); T('never connected: says so', why() == BASE + ' The bridge has not connected yet.')
seen(30); w = why()
T('bridge talking (30 s ago): no MT5 sentence and no Last contact', 'MT5 is not talking' not in w and 'Last contact' not in w)
seen(660); st.put('bot_enabled', '0'); w = why(); st.put('bot_enabled', '1')
T('bot off: its own words, no Last contact added', 'Last contact' not in w and 'MT5 is not talking' not in w)
seen(660); burst.save('', {'on': False}); w = burst.explain('', now)['why']; burst.save('', {'on': True})
T('burst off: its own words, no Last contact added', w == 'Burst mode is off.')
seen(120); T('bridge exactly 2 minutes ago still counts as talking', 'Last contact' not in why())
seen(121); T('121 seconds ago is silent: 2 min ago', why().endswith('Last contact: 2 min ago.'))
T('bb.since is a sentence that starts with a space', bb.since('', now).startswith(' '))
j = burst.view(''); T('burst.view carries it in now.why', 'Last contact' in j['now']['why'])
st.acct = real_acct
p, f = sum(1 for _, ok in R if ok), sum(1 for _, ok in R if not ok)
print('%d passed, %d failed' % (p, f)); os.remove(os.environ['DB_PATH']); sys.exit(1 if f else 0)
