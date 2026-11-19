"""Burst mode Section 2 tests: the scanner hook. When it fires, what it needs, what it never skips, and that normal scanning is untouched. No network.
Run: python tests/test_burst2.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_burst2_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
SCORE = [1]; CALLS = []; NORMAL = [False]
def fake(m, h, mc, *a, **k):
    CALLS.append((mc, m[-1]['t'] - m[-2]['t']))          # the candle length in seconds: 300 = 5-minute, 900 = 15-minute
    if mc == 1 or NORMAL[0]: return {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 'macd_cross', 'score': SCORE[0], 'adx': 20}
    return None
brain.evaluate = fake
GATE = [(True, 'ok')]
risk.global_gate = lambda now=None, uid='', burst=False: GATE[0]
BAR = [int(time.time()) // 300 * 300 - 300]
def run(score=1, uid='', m5=True, seed_quiet=True, keep=False):
    """Clean slate (a long quiet), then one scan."""
    if not keep:
        st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%' OR k LIKE 'bg:%' OR k LIKE 'burst:closed:%'")
    A._last_scan.clear(); CALLS.clear(); BAR[0] += 300; A.bars._d.clear()
    for tf, step, n in (('M15', 900, 130), ('H1', 3600, 10)) + ((('M5', 300, 130),) if m5 else ()):
        A.bars.merge('XAUUSD', tf, [[BAR[0] - step * i, 2000, 2001, 1999, 2000, 1] for i in range(n)], uid=uid)
    SCORE[0] = score; A._scan('XAUUSD', uid)
    return st.q('SELECT * FROM signals ORDER BY id')
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0', multi_entries='1').items(): st.put(k, v)

burst.save('', {'on': False}); rows = run()
T('burst off: nothing happens, and the normal scan is untouched (it saw no setup)', rows == [] and all(c[0] == 2 for c in CALLS) and len(CALLS) >= 1)

burst.save('', {'on': True, 'idle_min': 5})
rows = run(1)
T('quiet long enough + one strategy = a quick burst of 5 entries, one group, all pending', len(rows) == 5 and len({r['grp'] for r in rows}) == 1 and {r['status'] for r in rows} == {'pending'})
m = burst.meta(rows[0]['grp']); T('the group remembers: quick, 5 entries, 0.5 USD each, 40 percent give-back', m and m['k'] == 'quick' and m['n'] == 5 and m['each'] == 0.5 and m['gb'] == 40)
T('the entries share the normal risk (total = 1.0 percent)', abs(sum(r['risk_pct'] for r in rows) - 1.0) < 0.001)
T('the burst looked at the 5-minute candles with ONE strategy enough (min_conf 1)', any(c == (1, 300) for c in CALLS))
T('the reason text says it was a burst', json.loads(rows[0]['reason']).get('burst', {}).get('kind') == 'quick')

rows = run(3); T('three strategies agreeing = a big burst of 15 entries', len(rows) == 15 and burst.meta(rows[0]['grp'])['k'] == 'big' and burst.meta(rows[0]['grp'])['each'] == 1.0)

rows = run(1, m5=False)
T('no 5-minute candles: it falls back to the 15-minute ones', len(rows) == 5 and json.loads(rows[0]['reason'])['burst']['tf'] == 'M15' and any(c == (1, 900) for c in CALLS))

rows = run(1); first = len(rows); A._last_scan.clear(); A._scan('XAUUSD', '')
T('one burst at a time: a second scan makes no new group', len(st.q('SELECT * FROM signals')) == first)

st.x('DELETE FROM signals'); burst.closed('', time.time()); A._last_scan.clear(); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); CALLS.clear(); A._scan('XAUUSD', '')
T('not quiet long enough (just restarted): no burst, and it did not even evaluate', st.q('SELECT COUNT(*) n FROM signals', (), True)['n'] == 0 and not any(c[0] == 1 for c in CALLS))

st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'burst:closed:%'")
st.x("INSERT INTO signals(symbol,side,status,created) VALUES('XAUUSD','buy','closed',?)", (int(time.time()) - 600,))
rows = run(1, keep=True); T('the 60-minute symbol cooldown does NOT stop a burst (last trade was 10 minutes ago)', len([r for r in rows if r['grp']]) == 5)

NORMAL[0] = True; rows = run(2)
T('when the normal scan finds a setup it trades normally and no burst is added', len(rows) == 1 and rows[0]['grp'] is None); NORMAL[0] = False

GATE[0] = (False, 'bot off'); st.x("DELETE FROM kv WHERE k LIKE 'burst:closed:%'"); rows = run(1)
T('a closed gate stops the burst and restarts the quiet timer', rows == [] and int(float(st.get('burst:closed:') or 0)) >= int(time.time()) - 5); GATE[0] = (True, 'ok')

st.put('news_lock', '1'); st.put('max_ccy_exposure', '0'); rows = run(1)
T('the other gates still apply (currency exposure at 0 blocks it)', rows == []); st.put('news_lock', '0'); st.put('max_ccy_exposure', '2')

st.put('max_trades_day', '1'); rows = run(1)
T('max trades a day = 1 leaves no room for a burst', rows == []); st.put('max_trades_day', '0')

st.put('bot_enabled', '1'); burst.save('u7', {'on': True}); rows = run(1, uid='u7')
T('a subscriber gets their own burst, kept under their own id', len(rows) == 5 and {r['uid'] for r in rows} == {'u7'})

bad_n = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad_n), len(R)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_n else 0)
