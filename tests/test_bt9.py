"""BT9 tests: the owner's burst card uses the owner's own uid when Deriv or Binance is chosen. No network. Run: python tests/test_bt9.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt9_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, burst, burst_scope as bs, brokers as bk
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0', multi_entries='1').items(): st.put(k, v)
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; AM = {'Authorization': 'Bearer dev:amy@x.com'}
c.get('/api/me', headers=OW); c.get('/api/me', headers=AM)
UID, AMY = 'dev-boss@x.com', 'dev-amy@x.com'
def on(sc): return burst.get(sc)['on']
def pick(uid, p):          # which broker's bot is running (the old 'Trade on' choice is gone)
    for b in ('Deriv', 'Binance'): bk.set_bot(uid, b, b == p)

# 1) nothing chosen: owner stays on scope '' (the owner's PC EA)
c.post('/api/burst', json={'on': True, 'minute': True, 'quick_n': 4}, headers=OW)
T('nothing chosen: the owner saves under scope "" as before', on('') is True and on(UID) is False)
# 2) MT5 chosen: still ''
pick(UID, 'MT5'); c.post('/api/burst', json={'quick_n': 3}, headers=OW)
T('MT5 chosen: still scope ""', burst.get('')['quick_n'] == 3 and burst.get(UID)['quick_n'] != 3)
T('scope(): owner on MT5 = ""', bs.scope({'uid': UID, 'admin': True}) == '')
# 3) Deriv chosen: the card uses the uid, the settings already saved are copied once
pick(UID, 'Deriv')
j = c.get('/api/burst', headers=OW).get_json()
T('Deriv chosen: scope() is the owner uid', bs.scope({'uid': UID, 'admin': True}) == UID)
T('Deriv chosen: the switches saved before are copied, not lost', j['settings']['on'] is True and j['settings']['minute'] is True and j['settings']['quick_n'] == 3 and on(UID) is True)
j = c.post('/api/burst', json={'on': False}, headers=OW).get_json()
T('Deriv chosen: switching off saves for the uid (what the Deriv scan reads)', j['settings']['on'] is False and on(UID) is False)
T('the old "" row is left alone', on('') is True)
j = c.post('/api/burst', json={'on': True, 'quick_n': 5}, headers=OW).get_json()
T('Deriv chosen: switching on saves for the uid', on(UID) is True and burst.get(UID)['quick_n'] == 5 and burst.get('')['quick_n'] == 3)
c.get('/api/burst', headers=OW); T('a second visit does not copy over the uid settings again', burst.get(UID)['quick_n'] == 5)
T('adopt() never overwrites', bs.adopt('', UID) is False and burst.get(UID)['quick_n'] == 5)
# 4) the card no longer judges the Deriv owner by the EA switch
st.put('bot_enabled', '0'); bk.set_bot(UID, 'Deriv', True)
st.set_acct({'balance': 9999.54, 'equity': 9999.54, 'open': 0, 'demo': True, 'src': 'deriv'}, UID)
from backend import risk as _rk; _ws = _rk.weekend_shut; _rk.weekend_shut = lambda now=None: False
why = c.get('/api/burst', headers=OW).get_json()['now']['why']
T('Deriv running: the card does not say "The bot is stopped" or blame MT5 (%s)' % why[:50], 'stopped' not in why and 'MT5' not in why)
# 5) end to end: the Deriv scan (scope = uid) really opens a burst group
brain.evaluate = lambda *a, **k: None
from backend import risk; risk.weekend_shut = lambda now=None: False          # the test must not depend on the day it runs (forex is shut on Sunday night)
def bars(step, n, slope):
    t0 = int(time.time()) // step * step - step
    return [[t0 - step * (n - 1 - i), 2000 + slope * i, 2000 + slope * i + 1, 2000 + slope * i - 1, 2000 + slope * i, 1] for i in range(n)]
A.bars._d.clear()
for tf, step, n in (('M15', 900, 130), ('H1', 3600, 10), ('M5', 300, 130)): A.bars.merge('XAUUSD', tf, bars(step, n, 0.05), uid=UID)
st.x('DELETE FROM signals'); A._last_scan.clear()
st.put('burst:closed:' + UID, 0); burst.save(UID, {'on': True, 'minute': True, 'minute_n': 2})
A._scan('XAUUSD', UID); rows = st.q("SELECT * FROM signals WHERE uid=?", (UID,))
T('Deriv scan under the owner uid opens a burst group of 2 (%d rows)' % len(rows), len(rows) == 2 and len({r['grp'] for r in rows}) == 1)
# 6) Binance too, everyone else unchanged, MT5 again = ""
pick(UID, 'Binance'); T('Binance chosen: the owner uid', bs.scope({'uid': UID, 'admin': True}) == UID)
pick(UID, 'MT5'); T('back to MT5: scope ""', bs.scope({'uid': UID, 'admin': True}) == '')
c.post('/api/burst', json={'on': True}, headers=AM)
T('a normal subscriber keeps their own uid', bs.scope({'uid': AMY, 'admin': False}) == AMY and on(AMY) is True)
pick(AMY, 'Deriv'); T('subscriber on Deriv: still their uid', bs.scope({'uid': AMY, 'admin': False}) == AMY)
# 7) text
S = open(os.path.join(HERE, '..', 'backend', 'app.py'), encoding='utf-8').read()
T('both burst endpoints use burst_scope', S.count('burst_scope.scope(u)') >= 2 and 'burst.save(_mine(u)' not in S and 'burst.view(_mine(u))' not in S)
f = sum(1 for _, ok in R if not ok); print('%d/%d passed' % (len(R) - f, len(R))); sys.exit(1 if f else 0)
