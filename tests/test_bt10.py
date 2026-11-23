"""BT10 tests: candles survive a server restart (saved in kv, restored on first use). No network. Run: python tests/test_bt10.py"""
import os, sys, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt10_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, bars, brain, burst_free
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def rows(n, end, step=300, base=2000.0): return [[end - (n - 1 - i) * step, base + i, base + i + 1, base + i - 1, base + i + 0.5, 10] for i in range(n)]
def restart(): bars._d.clear(); bars._tried.clear(); bars._saved.clear()
now = int(time.time())

bars.merge('XAUUSD', 'M5', rows(120, now), uid='')
T('merge keeps the candles in memory', len(bars.get('XAUUSD', 'M5', '')) == 120)
T('first merge saved them (kv has the key)', st.get('bars::XAUUSD:M5') not in (None, ''))
restart()
g = bars.get('XAUUSD', 'M5', '')
T('after a restart the candles come back (120 of 120)', len(g) == 120 and g[-1]['t'] == now and g[-1]['c'] == 2119.5)
T('the 120-candle gate of brain.evaluate is met again', len(g) >= 120)

restart(); bars.merge('XAUUSD', 'M15', rows(500, now, 900), uid='u1'); restart()
T('at most 300 candles are saved', len(bars.get('XAUUSD', 'M15', 'u1')) == 300)
T('each person has their own saved candles', bars.get('XAUUSD', 'M15', '') == [] and bars.get('XAUUSD', 'M5', 'u1') == [])

restart(); bars.merge('XAUUSD', 'M5', [[now + 300, 1, 2, 0, 1.5, 3]], uid='')
g = bars.get('XAUUSD', 'M5', '')
T('a small push after a restart adds to the restored candles (121)', len(g) == 121 and g[-1]['t'] == now + 300)
restart(); bars.merge('XAUUSD', 'M5', [[now, 9, 9, 9, 9, 9]], uid='')
T('a live candle wins over the saved one with the same time', [x for x in bars.get('XAUUSD', 'M5', '') if x['t'] == now][0]['c'] == 9)

restart(); bars.merge('XAUUSD', 'H1', rows(10, now, 3600), uid=''); a = st.get('bars::XAUUSD:H1')
bars.merge('XAUUSD', 'H1', [[now + 3600, 1, 1, 1, 1, 1]], uid=''); T('a second merge inside 2 minutes does not write again', st.get('bars::XAUUSD:H1') == a)
bars._saved.clear(); bars.merge('XAUUSD', 'H1', [[now + 7200, 1, 1, 1, 1, 1]], uid=''); T('after the wait it writes again', st.get('bars::XAUUSD:H1') != a)

st.put('bars::EURUSD:M5', json.dumps(rows(50, now - 13 * 3600))); restart()
T('candles older than 12 hours are not restored', bars.get('EURUSD', 'M5', '') == [])
st.put('bars::GBPUSD:M5', 'not json'); st.put('bars::USDJPY:M5', json.dumps([[1, 2], 'x', None])); restart()
T('broken saved data gives no candles and no crash', bars.get('GBPUSD', 'M5', '') == [] and bars.get('USDJPY', 'M5', '') == [])
T('an unknown market gives no candles', bars.get('NOPE', 'M5', '') == [])

restart(); bars.merge('XAUUSD', 'M5', rows(200, now, 300, 2000.0), uid=''); restart()
m = bars.get('XAUUSD', 'M5', '')
T('momentum burst has its 30 candles after a restart', len(m) >= 30 and burst_free.side(m) in ('buy', 'sell'))
info = {}; brain.evaluate(m, bars.get('XAUUSD', 'M15', ''), 1, 2.0, info=info)
T('the "Not enough candle history" reason is not the answer any more', info.get('code') != 'history')
p, f = sum(1 for _, ok in R if ok), sum(1 for _, ok in R if not ok)
print('%d passed, %d failed' % (p, f)); os.remove(os.environ['DB_PATH']); sys.exit(1 if f else 0)
