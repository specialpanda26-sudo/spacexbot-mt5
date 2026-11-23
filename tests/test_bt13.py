"""BT13 tests: the person's USD loss limit for a burst group. No network. Run: python tests/test_bt13.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt13_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, burst, groupcap, deriv_group as dg
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0', multi_entries='1').items(): st.put(k, v)
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=OW)
real = st.acct
def bal(b): st.acct = lambda uid='': {'balance': b, 'seen': int(time.time()), 'demo': True}
S = {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2010.0, 'strategy': 'x', 'score': 1}
def make(): st.x('DELETE FROM signals'); pl, why = burst.plan('', 1); return pl, why, (burst.create('', 'XAUUSD', S, pl) if pl else None)

T('default: no limit', burst.get('')['loss_usd'] == 0)
j = c.post('/api/burst', json={'loss_usd': 20}, headers=OW).get_json()
T('saved through the app route', j['settings']['loss_usd'] == 20)
T('0 clears it', c.post('/api/burst', json={'loss_usd': 0}, headers=OW).get_json()['settings']['loss_usd'] == 0)
for bad in (-1, 0.05, 'x', True, 5000, None, float('nan')): T('bad limit %r refused' % (bad,), c.post('/api/burst', json={'loss_usd': bad}, headers=OW).status_code == 400)
T('a refused limit changes nothing', burst.get('')['loss_usd'] == 0)

burst.save('', {'on': True, 'loss_usd': 20, 'quick_n': 5})
bal(1000.0); pl, why, ids = make(); m = burst.meta(ids[0])
T('1000 USD account, 20 USD limit: the group loss is 2 percent', m['loss'] == 2.0 and m['loss_usd'] == 20)
T('2 percent of 1000 = 20 USD (what the bridge computes)', round(1000.0 * m['loss'] / 100, 2) == 20.0)
T('the basket the bridge gets carries loss 2.0 and no group target', burst.basket(st.q("SELECT id,symbol,side,sl,tp,risk_pct FROM signals WHERE status='pending' ORDER BY id", one=True), '')['loss'] == 2.0 and not burst.meta(ids[0]).get('tgt'))
burst.save('', {'loss_usd': 4}); bal(10.0); pl, why, ids = make(); m = burst.meta(ids[0])
T('10 USD account, 4 USD limit: 40 percent', m['loss'] == 40.0 and round(10.0 * m['loss'] / 100, 2) == 4.0)
dg_m = dict(m, bal0=10.0); T('the Deriv engine reads it as 4 USD', dg.loss_limit(dg_m) == 4.0)
burst.save('', {'loss_usd': 50}); bal(10.0); pl, why, ids = make(); T('limit bigger than the account: capped at 100 percent', burst.meta(ids[0])['loss'] == 100.0)
burst.save('', {'loss_usd': 20}); bal(1000.0); groupcap.save('', {'on': True, 'loss_pct': 5, 'target_usd': 0}); pl, why, ids = make()
T('person also has a 5 percent group limit: the smaller (2 percent) wins', burst.meta(ids[0])['loss'] == 2.0)
groupcap.save('', {'on': True, 'loss_pct': 1, 'target_usd': 0}); pl, why, ids = make()
T('the group limit is smaller (1 percent): it stays', burst.meta(ids[0])['loss'] == 1.0)
groupcap.save('', {'on': False}); burst.save('', {'loss_usd': 0}); pl, why, ids = make()
T('no limit set: the group has no loss and no loss_usd', not burst.meta(ids[0]).get('loss') and 'loss_usd' not in burst.meta(ids[0]))
burst.save('', {'loss_usd': 20}); bal(0.0); pl, why, ids = make()
T('limit set but balance unknown: no burst opens and the reason says so', pl is None and 'balance is not known' in why and ids is None)
st.acct = real
page = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('the card has the loss box, fills it and sends it', page.count('id="bswLoss"') == 1 and '$("#bswLoss").value=s.loss_usd>0' in page and 'body.loss_usd=ls===""?0:parseFloat(ls)' in page)
p, f = sum(1 for _, ok in R if ok), sum(1 for _, ok in R if not ok)
print('%d passed, %d failed' % (p, f)); os.remove(os.environ['DB_PATH']); sys.exit(1 if f else 0)
