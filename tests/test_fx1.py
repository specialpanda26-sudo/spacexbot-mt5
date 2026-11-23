"""FX1 checks: candles survive a restart (database copy) and 'trade every minute' works with 18 candles. No network. Run: python tests/test_fx1.py"""
import os, sys, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'fx1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, bars, burst_free as bf, burst_look as bl
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

now = int(time.time()); step = 300
rows = [(now - (200 - i) * step, 2000 + i * 0.3, 2001 + i * 0.3, 1999 + i * 0.3, 2000.5 + i * 0.3, 10) for i in range(200)]
bars.merge('XAUUSD', 'M5', rows, uid='u1')
T('200 candles are in memory', len(bars.get('XAUUSD', 'M5', 'u1')) == 200)
T('the first merge saved a copy in the database', len(st.get('bars:u1:XAUUSD:M5') or '') > 1000)
bars._d.clear(); bars._tried.clear(); bars._saved.clear()          # what a restart does
T('after a restart the memory is empty before the first use', bars._d == {})
back = bars.get('XAUUSD', 'M5', 'u1')
T('the first use after a restart brings all 200 candles back, oldest first', len(back) == 200 and back[0]['t'] < back[-1]['t'] and back[-1]['c'] == rows[-1][4])
bars._d.clear(); bars._tried.clear(); bars._saved.clear()
bars.merge('XAUUSD', 'M5', [(now + step, 1, 2, 0.5, 1.5, 1)], uid='u1')
got = bars.get('XAUUSD', 'M5', 'u1')
T('a new candle after a restart is added to the saved history, not instead of it', len(got) == 201 and got[-1]['t'] == now + step)
T('another person has their own candles', bars.get('XAUUSD', 'M5', 'u2') == [])
st.put('bars:u3:XAUUSD:M5', '{not json'); T('a damaged saved copy is ignored, no crash', bars.get('XAUUSD', 'M5', 'u3') == [])
old = [[now - 40 * 86400, 1, 2, 0.5, 1.5, 1]]; import json; st.put('bars:u4:XAUUSD:M5', json.dumps(old)); T('candles older than 14 days are not loaded back', bars.get('XAUUSD', 'M5', 'u4') == [])
bars.merge('XAUUSD', 'M5', rows[:5], uid='u5', keep=3); T('keep still trims the memory', len(bars.get('XAUUSD', 'M5', 'u5')) == 3)

short = [{'t': now - (18 - i) * step, 'o': 2000 + i, 'h': 2001.5 + i, 'l': 1999.5 + i, 'c': 2001 + i, 'v': 1} for i in range(18)]
T('18 candles: the normal no-signal burst still waits (needs 30)', bf.setup('u1', short) is None)
s = bf.setup('u1', short, minute=True)
T('18 candles: "trade every minute" can open a chance (buy: price rising)', s and s['side'] == 'buy' and s['sl'] < s['entry'] < s['tp'])
T('9 candles: still too few, no guess', bf.setup('u1', short[:9], minute=True) is None)
down = [dict(x, c=4000 - x['c']) for x in short]; s2 = bf.setup('u9', down, minute=True)
T('18 candles falling: sell', s2 and s2['side'] == 'sell')
T('the burst card says plainly why when there are too few candles', 'Only 18 candles' in bl.free_words('u1', short, False) and bl.free_words('u1', short[:9], True).startswith('Only 9 candles'))
T('with enough candles the old wording stays', bl.free_words('u1', [dict(x, c=2000.0, h=2000.0, l=2000.0, o=2000.0) for x in short * 2], False) == 'No clear price move either.')
bad = [x for x, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
