"""R5 auto-markets tests: the rules (pool, steady + profitable, one at a time, drop when losing, off removes), group-aware counting, owner-only route.
No network. Run: python tests/test_markets5.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_markets5_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, automarkets as am
c = A.app.test_client()
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
NOW = 1800000000; D = 86400
def clear(): st.x('DELETE FROM signals')
def closed(sym, pnl, ago, grp=None): st.x("INSERT INTO signals(symbol,side,status,created,pnl,closed,grp) VALUES(?,'buy','closed',?,?,?,?)", (sym, NOW - ago, pnl, NOW - ago, grp))
def good(n=22, sym='XAUUSD'):
    for i in range(n): closed(sym, 3.0 if i % 3 else -1.0, 20 * D - i * 3600)
def S(**kv):
    for k, v in kv.items(): st.put(k, v)
def syms(): return [x for x in st.get('symbols').split(',') if x]
S(symbols='XAUUSD,EURUSD', symbols_pool='GBPJPY,AUDUSD,bad symbol!', auto_markets='0', auto_markets_max='2', max_losing_streak='3')

clear(); good()
T('off by default: nothing is added, the list is untouched', am.tick(NOW) == 'off' and syms() == ['XAUUSD', 'EURUSD'])

S(auto_markets='1'); clear()
for i in range(5): closed('XAUUSD', 2.0, D * (i + 1))
T('too few trades: not added, and it says how many', am.tick(NOW).startswith('only 5 of 20') and syms() == ['XAUUSD', 'EURUSD'])

clear(); good(20, 'XAUUSD')
for i in range(20): closed('XAUUSD', 1.0, 2 * D + i, grp=500)
rows = am.setups(NOW - 30 * D, {'XAUUSD'}); T('twenty entries of one setup count as one result', len(rows) == 21 and any(abs(r['pnl'] - 20.0) < 1e-9 for r in rows))
clear()
for i in range(25): closed('XAUUSD', 1.0, 2 * D + i, grp=500)
T('...so a big group does not fake "enough trades"', am.tick(NOW).startswith('only 1 of 20') and syms() == ['XAUUSD', 'EURUSD'])

clear(); good(22)
T('steady and profitable: adds the first market of the pool', am.tick(NOW) == 'added GBPJPY' and syms() == ['XAUUSD', 'EURUSD', 'GBPJPY'])
T('the bad pool entry is ignored', 'BAD SYMBOL!' not in am.pool() and am.pool() == ['GBPJPY', 'AUDUSD'])
T('the bot remembers what it added', [a['s'] for a in am.added()] == ['GBPJPY'])
r = am.tick(NOW + D); T('one market at a time: a second add waits 7 days', r.startswith('waiting') and syms() == ['XAUUSD', 'EURUSD', 'GBPJPY'])
for i in range(22): closed('XAUUSD', 3.0 if i % 3 else -1.0, -8 * D + 20 * D - i * 3600 - 8 * D)
T('after the wait it adds the next one', am.tick(NOW + 8 * D) == 'added AUDUSD' and syms()[-1] == 'AUDUSD')
T('never more than the cap', am.tick(NOW + 20 * D).startswith('already added the most') and len(am.added()) == 2)

S(symbols='XAUUSD,EURUSD', symbols_pool='GBPJPY'); st.put('am:added', '[]'); st.put('am:last', 0)
clear()
for i in range(22): closed('XAUUSD', -1.0 if i % 2 else 0.5, 20 * D - i * 3600)
T('markets not in profit: not added', 'not in profit' in am.tick(NOW) and syms() == ['XAUUSD', 'EURUSD'])
clear(); good(22)
for i in range(3): closed('XAUUSD', -1.0, 2 * D - i * 60)
T('a run of 3 losses in the last 7 days blocks it, even when the month is in profit', 'run of 3 losses' in am.tick(NOW) and syms() == ['XAUUSD', 'EURUSD'])
clear(); good(22); S(symbols_pool='XAUUSD,EURUSD')
T('nothing outside the pool is ever added, and pool markets already traded are skipped', 'no new market' in am.tick(NOW) and syms() == ['XAUUSD', 'EURUSD'])

S(symbols_pool='GBPJPY,AUDUSD'); st.put('am:last', 0); st.put('am:added', '[]'); clear(); good(22)
am.tick(NOW); T('(setup) GBPJPY added', 'GBPJPY' in syms())
for i in range(10): closed('GBPJPY', -2.0, -D // 2 + 0 - i)
for i in range(22): closed('XAUUSD', 3.0 if i % 3 else -1.0, -D + 20 * D - i * 3600 - D)
r = am.tick(NOW + D)
T('a market that loses over its first 10 trades is dropped again', 'GBPJPY' not in syms() and am.added() == [])
T('...and the owner\'s own markets are untouched', syms()[:2] == ['XAUUSD', 'EURUSD'])
st.put('am:last', 0); r = am.tick(NOW + 2 * D)
T('a dropped market is not tried again for 30 days (the next pool market is)', 'GBPJPY' not in syms() and 'AUDUSD' in syms())

S(auto_markets='0'); am.tick(NOW + 3 * D)
T('switching off removes every market the bot added', syms() == ['XAUUSD', 'EURUSD'] and am.added() == [])

S(auto_markets='1', symbols='XAUUSD,EURUSD,AUDUSD'); st.put('am:added', json.dumps([{'s': 'AUDUSD', 'at': NOW}])); S(symbols='XAUUSD,EURUSD'); am.tick(NOW + 4 * D)
T('a market the owner took out by hand is forgotten, not re-added as "ours"', all(a['s'] != 'AUDUSD' for a in am.added()))

T('owner can read the status', c.get('/api/admin/markets', headers={'Authorization': 'Bearer dev:boss@x.com'}).get_json().get('max_added') == 2)
T('a normal user cannot', c.get('/api/admin/markets', headers={'Authorization': 'Bearer dev:joe@x.com'}).status_code in (401, 403))
S(auto_markets_max='abc'); T('a garbage cap falls back to 2', am.cap() == 2)

bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
if bad: sys.exit(1)
