"""BT4 tests: burst with no strategy signal, capped per hour. No network. Run: python tests/test_bt4.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt4_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, burst, burst_free as bf
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
brain.evaluate = lambda *a, **k: None          # no strategy ever sees a setup
risk.global_gate = lambda now=None, uid='', burst=False: (True, 'ok')
def bars(step, n, slope):
    t0 = int(time.time()) // step * step - step
    return [[t0 - step * (n - 1 - i), 2000 + slope * i, 2000 + slope * i + 1, 2000 + slope * i - 1, 2000 + slope * i, 1] for i in range(n)]
def feed(slope, uid=''):
    A.bars._d.clear()
    for tf, step, n in (('M15', 900, 130), ('H1', 3600, 10), ('M5', 300, 130)): A.bars.merge('XAUUSD', tf, bars(step, n, slope), uid=uid)
def run(slope, uid=''):
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%' OR k LIKE 'bg:%' OR k LIKE 'burst:closed:%'")
    A._last_scan.clear(); feed(slope, uid); A._scan('XAUUSD', uid); return st.q('SELECT * FROM signals ORDER BY id')
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0', multi_entries='1').items(): st.put(k, v)
burst.save('', {'on': True, 'idle_min': 5})

T('default cap is 2 groups an hour', bf.per_hour() == 2)
m = [{'t': i, 'o': 2000 + i, 'h': 2001 + i, 'l': 1999 + i, 'c': 2000 + i} for i in range(60)]
T('rising prices = buy', bf.side(m) == 'buy')
T('falling prices = sell', bf.side([dict(x, c=4000 - x['c'], h=4001 - x['c'], l=3999 - x['c']) for x in m]) == 'sell')
T('flat prices = no side', bf.side([{'t': i, 'o': 2000, 'h': 2001, 'l': 1999, 'c': 2000} for i in range(60)]) is None)
T('too few candles = no side', bf.side(m[:20]) is None)
s = bf.setup('', m)
T('setup: buy, stop below, target above, 1 ATR each, named burst_free', s and s['side'] == 'buy' and s['sl'] < s['entry'] < s['tp'] and abs(s['entry'] - s['sl']) == abs(s['tp'] - s['entry']) and s['strategy'] == 'burst_free' and s['score'] == 1)

rows = run(1.0)
T('rising market, no strategy: one quick burst of 5 pending buys in one group', len(rows) == 5 and {r['side'] for r in rows} == {'buy'} and len({r['grp'] for r in rows}) == 1 and {r['status'] for r in rows} == {'pending'})
T('the group is a quick burst, 5 x 0.5 USD', burst.meta(rows[0]['grp'])['k'] == 'quick' and burst.meta(rows[0]['grp'])['n'] == 5)
T('it counted 1 toward the hourly cap', bf.used('') == 1)
rows = run(-1.0)
T('falling market: sell burst', len(rows) == 5 and {r['side'] for r in rows} == {'sell'} and bf.used('') == 2)
rows = run(1.0)
T('cap of 2 an hour reached: no third burst', rows == [] and bf.used('') == 2)
st.put('burst_free_per_hour', '3'); rows = run(1.0)
T('owner raises the cap to 3: a third burst opens', len(rows) == 5 and bf.used('') == 3)
st.put('burst_free_per_hour', '0'); st.put('bfree:', '[]'); rows = run(1.0)
T('owner sets 0: switched off, nothing opens', rows == [])
st.put('burst_free_per_hour', '2'); rows = run(0.0)
T('flat market: nothing opens', rows == [])
burst.save('', {'on': False}); rows = run(1.0)
T('burst switch off: nothing opens', rows == [])
burst.save('', {'on': True}); st.put('burst_enabled', '0'); rows = run(1.0)
T('owner master switch off: nothing opens', rows == []); st.put('burst_enabled', '1')
risk.global_gate = lambda now=None, uid='', burst=False: (False, 'daily loss limit reached'); rows = run(1.0)
T('a loss limit still stops it', rows == [])
src = open(os.path.join(HERE, '..', 'backend', 'app.py'), encoding='utf-8').read()
T('hooks are in app.py once each', src.count('burst_free.setup(uid, m)') == 1 and src.count('burst_free.mark(uid)') == 1)
T('owner setting is on the admin page and checked 0 to 12', '"burst_free_per_hour"' in open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read() and "('burst_free_per_hour', 0, 12)" in src)
n = sum(1 for _, ok in R if ok); print('%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
