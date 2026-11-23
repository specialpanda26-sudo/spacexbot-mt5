"""BT11 tests: burst uses the timeframe that has enough candles (5-minute only when it has 120 or more). No network. Run: python tests/test_bt11.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt11_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
seen = []
brain.evaluate = lambda m, *a, **k: seen.append(len(m))          # records how many candles the strategies were given; never a setup
risk.global_gate = lambda now=None, uid='', burst=False: (True, 'ok')
def bars(step, n):
    t0 = int(time.time()) // step * step - step
    return [[t0 - step * (n - 1 - i), 2000 + i, 2001 + i, 1999 + i, 2000 + i, 1] for i in range(n)]
def run(n5, n15):
    seen.clear(); st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%' OR k LIKE 'bg:%' OR k LIKE 'burst:closed:%' OR k LIKE 'bfree:%' OR k LIKE 'blook:%' OR k LIKE 'bars:%'"); A._last_scan.clear(); A.bars._d.clear(); A.bars._tried.clear(); A.bars._saved.clear()
    for tf, step, n in (('M15', 900, n15), ('H1', 3600, 10), ('M5', 300, n5)):
        if n: A.bars.merge('XAUUSD', tf, bars(step, n), uid='')
    A._burst_scan('XAUUSD', ''); return list(seen)
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0', multi_entries='1').items(): st.put(k, v)
burst.save('', {'on': True, 'idle_min': 5})
T('5-minute 140, 15-minute 130: the 5-minute candles are used', run(140, 130) == [140])
T('5-minute only 25, 15-minute 130: the 15-minute candles are used', run(25, 130) == [130])
T('5-minute 119, 15-minute 130: the 15-minute candles are used', run(119, 130) == [130])
T('5-minute 120, 15-minute 130: the 5-minute candles are used', run(120, 130) == [120])
T('no 5-minute candles: the 15-minute candles are used (as before)', run(0, 130) == [130])
T('both short (25 and 20): the 5-minute ones stay, nothing better', run(25, 20) == [25])
p, f = sum(1 for _, ok in R if ok), sum(1 for _, ok in R if not ok)
print('%d passed, %d failed' % (p, f)); os.remove(os.environ['DB_PATH']); sys.exit(1 if f else 0)
