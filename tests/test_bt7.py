"""BT7 tests: 'trade every minute' switch. No network. Run: python tests/test_bt7.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt7_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, burst, burst_free as bf, burst_look as bl
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
brain.evaluate = lambda *a, **k: None
risk.global_gate = lambda now=None, uid='', burst=False: (True, 'ok')
def bars(step, n, slope):
    t0 = int(time.time()) // step * step - step
    return [[t0 - step * (n - 1 - i), 2000 + slope * i, 2000 + slope * i + 1, 2000 + slope * i - 1, 2000 + slope * i, 1] for i in range(n)]
def feed(slope):
    A.bars._d.clear()
    for tf, step, n in (('M15', 900, 130), ('H1', 3600, 10), ('M5', 300, 130)): A.bars.merge('XAUUSD', tf, bars(step, n, slope), uid='')
def fresh(slope):
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%' OR k LIKE 'bg:%' OR k LIKE 'burst:closed:%' OR k LIKE 'blook:%' OR k LIKE 'bmin:%' OR k LIKE 'bfree:%'")
    A._last_scan.clear(); feed(slope)
def scan(): A._last_scan.clear(); A._scan('XAUUSD', ''); return st.q('SELECT * FROM signals ORDER BY id')
def later(sec): st.x('UPDATE signals SET created=created-?', (sec,)); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._last_scan.clear()          # a minute passes: the minute stamp changes
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0', multi_entries='1').items(): st.put(k, v)
burst.save('', {'on': True, 'idle_min': 5})

g = burst.get('')
T('off by default, 2 entries a minute', g['minute'] is False and g['minute_n'] == 2)
j = burst.save('', {'minute': True, 'minute_n': 3}); T('saved: on, 3 entries', j['minute'] is True and j['minute_n'] == 3)
for bad in ({'minute': 'yes'}, {'minute': 1}, {'minute_n': 1}, {'minute_n': 4}, {'minute_n': 2.5}, {'minute_n': 'x'}):
    try: burst.save('', bad); ok = False
    except ValueError: ok = True
    T('bad %r refused' % (bad,), ok)
T('side_any: tiny rise = buy, tiny fall = sell, none = None', bf.side_any([{'c': 2000 + 0.01 * i} for i in range(40)]) == 'buy' and bf.side_any([{'c': 2000 - 0.01 * i} for i in range(40)]) == 'sell' and bf.side_any([{'c': 2000} for i in range(40)]) is None)

fresh(0.05); rows = scan()
T('every minute ON, tiny drift, no strategy: opens a group of 3 entries at once (quiet only 1 minute needed)', len(rows) == 3 and {r['side'] for r in rows} == {'buy'} and len({r['grp'] for r in rows}) == 1)
T('it counts in the every-minute cap, not the other cap', bf.used('', minute=True) == 1 and bf.used('') == 0)
n0 = len(scan()); T('a second look in the same minute opens nothing', n0 == 3)
later(61); rows = scan()
T('a minute later: a second group opens while the first is still waiting (6 entries, 2 groups)', len(rows) == 6 and len({r['grp'] for r in rows}) == 2)
st.put('burst_minute_per_hour', '2'); later(61); rows = scan()
T('owner cap 2 an hour reached: no third group and the card says so', len(rows) == 6 and 'every-minute cap reached (2 of 2' in burst.view('')['look']['why'])
st.put('burst_minute_per_hour', '30')
burst.save('', {'minute_n': 2}); fresh(0.05); rows = scan(); T('2 entries a minute when set to 2', len(rows) == 2)
burst.save('', {'minute': False}); fresh(0.05); rows = scan()
T('switch OFF: tiny drift gives no group (old rules: needs a clear move)', rows == [])
burst.save('', {'minute': True, 'minute_n': 2}); fresh(0.0); rows = scan()
T('price not moving at all: no direction, no group', rows == [] and 'No clear price move' in burst.view('')['look']['why'])
fresh(0.05); risk.global_gate = lambda now=None, uid='', burst=False: (False, 'daily loss limit reached'); rows = scan()
T('a loss limit still stops every-minute mode', rows == []); risk.global_gate = lambda now=None, uid='', burst=False: (True, 'ok')
burst.save('', {'minute': False}); fresh(1.0); rows = scan(); T('switch off + clear rise: the normal 5-entry burst as before', len(rows) == 5)
burst.save('', {'minute': True}); pl, why = burst.plan('', 3, n=2); T('plan with entries given is never big', pl and pl['kind'] == 'quick' and pl['n'] == 2)
page = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('card has the switch and the entries field once each, and sends them', page.count('id="bswMin"') == 1 and page.count('id="bswMinN"') == 1 and 'body:{minute:want}' in page and 'body.minute_n=mn' in page)
T('owner cap is on the admin page and checked 1 to 60', '"burst_minute_per_hour"' in page and "('burst_minute_per_hour', 1, 60)" in open(os.path.join(HERE, '..', 'backend', 'app.py'), encoding='utf-8').read())
n = sum(1 for _, ok in R if ok); print('%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
