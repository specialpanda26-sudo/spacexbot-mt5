"""BT5 tests: the burst card's 'last look' line. No network. Run: python tests/test_bt5.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt5_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, burst, burst_look as bl
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
brain.evaluate = lambda *a, **k: None
risk.global_gate = lambda now=None, uid='', burst=False: (True, 'ok')
def bars(step, n, slope):
    t0 = int(time.time()) // step * step - step
    return [[t0 - step * (n - 1 - i), 2000 + slope * i, 2000 + slope * i + 1, 2000 + slope * i - 1, 2000 + slope * i, 1] for i in range(n)]
def run(slope, feed=True):
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%' OR k LIKE 'bg:%' OR k LIKE 'burst:closed:%' OR k LIKE 'blook:%'")
    A._last_scan.clear(); A.bars._d.clear()
    if feed:
        for tf, step, n in (('M15', 900, 130), ('H1', 3600, 10), ('M5', 300, 130)): A.bars.merge('XAUUSD', tf, bars(step, n, slope), uid='')
    A._scan('XAUUSD', ''); return st.q('SELECT * FROM signals ORDER BY id')
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0', multi_entries='1').items(): st.put(k, v)
burst.save('', {'on': True, 'idle_min': 5})

T('nothing looked yet: no last look', burst.view('')['look'] is None)
run(0.0); L = burst.view('')['look']
T('flat market: the look says no clear price move, with "just now"', L and 'No clear price move' in L['why'] and L['ago'] == 'just now' and L['why'].startswith('XAUUSD'))
rows = run(1.0); L = burst.view('')['look']
T('rising market: the look says it opened a quick burst of 5 buy entries, momentum only', len(rows) == 5 and 'opened a quick burst of 5 buy entries' in L['why'] and 'momentum only' in L['why'])
A._last_scan.clear(); st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%' OR k LIKE 'burst:closed:%'"); st.put('burst_free_per_hour', '1')
A._scan('XAUUSD', ''); L = burst.view('')['look']
T('hourly cap reached: the look says so (1 of 1)', 'Hourly cap reached (1 of 1' in L['why'])
st.put('burst_free_per_hour', '0'); A._last_scan.clear(); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._scan('XAUUSD', '')
T('cap 0: the look says burst without a strategy signal is off', 'is off' in burst.view('')['look']['why'])
run(1.0, feed=False); T('no candles: the look says none received', 'no candles received' in burst.view('')['look']['why'])
bl.note('', 'old news', now=time.time() - 7 * 3600); T('a look older than 6 hours is hidden', bl.last('') is None)
bl.note('', 'x', now=time.time() - 300); T('five minutes old reads "5 min ago"', bl.last('')['ago'] == '5 min ago')
bl.note('', 'y' * 500); T('text is cut to 240 characters', len(bl.last('')['why']) == 240)
st.put('blook:', 'not json'); T('a bad saved value shows nothing and does not crash', bl.last('') is None)
T('one person never sees another person look', (bl.note('u2', 'mine'), bl.last('u3'))[1] is None)
s = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('the card shows the last look once', s.count('j.look.ago') == 1)
src = open(os.path.join(HERE, '..', 'backend', 'app.py'), encoding='utf-8').read()
T('five notes in the scanner', src.count('burst_look.note(uid') == 5)
n = sum(1 for _, ok in R if ok); print('%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
