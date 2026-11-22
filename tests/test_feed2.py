"""Tests for Section 2 (BTC feed lines + resting). No network. Run: python tests/test_feed2.py"""
import os, sys, time, calendar
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'feed2_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
os.environ.pop('FEED_MAP', None); os.environ.pop('FEED_ON', None)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend import app as appmod, feed, store as st, bars, btc_switch
appmod.alerts.stop()
R = []
def T(name, ok): R.append((name, bool(ok)))
def utc(y, m, d, h=12): return calendar.timegm((y, m, d, h, 0, 0))
WED = utc(2023, 11, 15); SAT = utc(2023, 11, 18); FRI_LATE = utc(2023, 11, 17, 21)       # a Wednesday, a Saturday, Friday 21:00 UTC
sys.path.insert(0, HERE)
CALLS = []
def rows(now, tf):
    step = feed.STEP[tf]; end = now - now % step - step; n = 400 if tf == 'M15' else 300
    ts = [end - step * (n - 1 - i) for i in range(n)]
    return {'chart': {'result': [{'timestamp': ts, 'indicators': {'quote': [{'open': [60000.0] * n, 'high': [60050.0] * n, 'low': [59950.0] * n, 'close': [60010.0] * n, 'volume': [1] * n}]}}], 'error': None}}
class Resp:
    def __init__(s, js): s.js, s.status_code = js, 200
    def json(s): return s.js
CUR = {'now': WED}
def fake_get(url, params=None, headers=None, timeout=None):
    CALLS.append(url); return Resp(rows(CUR['now'], 'M15' if params['interval'] == '15m' else 'H1'))
feed.requests.get = fake_get
scanned = []; scan = lambda s, u='': scanned.append(s)
def fresh(symbols, btc=False, mode='always'):
    CALLS.clear(); scanned.clear(); feed._h1.clear(); feed.STATUS['sym'].clear()
    for k in [k for k in list(bars._d) if k[0] == '']: bars._d.pop(k)
    st.put('acct', '{}'); st.put('feed_on', '1'); st.put('symbols', symbols); st.put('crypto_weekend', '1' if btc else '0'); st.put('btc_mode', mode)
def tick(now): CUR['now'] = now; return feed.tick(scan, now=now)

m = feed.parse_map()
T('default map: gold, three forex pairs and BTC', set(m) == {'XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD'} and m['BTCUSD'] == 'BTC-USD')
T('FEED_MAP still overrides the default', feed.parse_map('XAUUSD:GC=F') == {'XAUUSD': 'GC=F'})
fresh('XAUUSD,EURUSD,GBPUSD,USDJPY'); T('BTC not in Symbols: it is not a feed symbol', 'BTCUSD' not in feed.symbols())
fresh('XAUUSD,BTCUSD'); T('BTC in Symbols: it is a feed symbol', 'BTCUSD' in feed.symbols())

fresh('BTCUSD', btc=True); tick(WED)
T('BTC candles are stored (15m and 1h) and scanned', len(bars.get('BTCUSD', 'M15')) > 300 and len(bars.get('BTCUSD', 'H1')) > 200 and scanned == ['BTCUSD'])
T('BTC asks Yahoo for BTC-USD', all('BTC-USD' in c for c in CALLS) and CALLS)
fresh('XAUUSD,EURUSD,GBPUSD,USDJPY,BTCUSD', btc=True); tick(WED)
T('a weekday, mode always: all five markets are downloaded and scanned', sorted(scanned) == sorted(['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD']))

fresh('XAUUSD,EURUSD,BTCUSD', btc=True); s = tick(SAT)
T('Saturday with BTC listed: gold and forex are not downloaded, BTC is', scanned == ['BTCUSD'] and all('BTC-USD' in c for c in CALLS))
T('Saturday: the resting market shows a reason, not a red error', s['sym']['XAUUSD'].get('rest') == 'weekend' and s['sym']['XAUUSD']['err'] == '' and not s['err'])
fresh('XAUUSD,BTCUSD', btc=True); tick(FRI_LATE); T('Friday 21:00 UTC counts as the weekend', scanned == ['BTCUSD'])
fresh('XAUUSD,BTCUSD', btc=True, mode='weekend'); s = tick(WED)
T('weekends-only mode on a weekday: BTC rests, gold is downloaded', scanned == ['XAUUSD'] and s['sym']['BTCUSD'].get('rest') == 'weekdays')
fresh('XAUUSD,BTCUSD', btc=True, mode='weekend'); tick(SAT); T('weekends-only mode on Saturday: BTC is downloaded', scanned == ['BTCUSD'])
fresh('XAUUSD,BTCUSD', btc=False); tick(SAT)
T('weekend exemption off (crypto_weekend 0): old behaviour, everything is downloaded', sorted(scanned) == ['BTCUSD', 'XAUUSD'])
fresh('XAUUSD,EURUSD'); tick(SAT); T('no BTC listed on a Saturday: nothing changes (gold still downloaded)', sorted(scanned) == ['EURUSD', 'XAUUSD'])
fresh('XAUUSD,BTCUSD', btc=True); tick(SAT); tick(WED + 7 * 86400 * 0)
T('after a rest the market comes back with a normal entry (rest cleared)', 'rest' not in feed.status()['sym']['XAUUSD'] and 'XAUUSD' in scanned)
# the real switch from Section B1 works with the feed
fresh('XAUUSD,EURUSD,GBPUSD,USDJPY'); btc_switch.set_on(True, weekend_only=True); st.put('feed_on', '1'); tick(SAT)
T('B1 switch on + Saturday: only BTC is downloaded', scanned == ['BTCUSD'])
btc_switch.set_on(False)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
