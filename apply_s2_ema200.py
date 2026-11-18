"""Section 2 (video 3, 3C): the 200 EMA filter. Writes backend/ema200_filter.py and tests/test_e200.py, registers psar_e200 and supertrend_e200
in backend/strategies.py, updates docs/HANDOFF.md. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import sys, os

MOD = r'''"""Video 3 (Data Trader, moving average strategy) - SECTION 3C: the 200 EMA filter.
Rule from the video: price ABOVE the 200 EMA -> only buys, price BELOW it -> only sells. The video says this lifts the Parabolic SAR win rate (38% -> 46%) and
the Supertrend win rate (39% -> 48%). Those numbers are the video's claim, NOT proven here: only tools/backtest.py --solo on real data can say.
What is in this file:
  with_ema200(fn, name, skip_if)  wraps ANY strategy: a buy is dropped unless the last close is above the 200 EMA, a sell unless it is below.
  psar_raw        Parabolic SAR flip with NO trend gate of its own (the existing psar_flip already has a 50/200 trend gate, so wrapping it would change nothing).
  supertrend_flip Supertrend (ATR 10, x3) changes direction. New indicator, kept here because indicators.py must not be edited.
Registered in strategies.py as psar_e200 and supertrend_e200 (TREND group). psar_e200 is told to stay silent when psar_flip fires on the same candle,
so one SAR flip never counts as two votes in the brain's confluence. The 200 EMA is read on the main (15-minute) chart: the video gives no chart, so that is my assumption."""
from .indicators import ema, atr, psar

EMA_LEN = 200            # the filter line
MIN_BARS = 220           # history needed: 200 EMA plus warm-up
ST_N, ST_MULT = 10, 3.0  # Supertrend settings (the usual 10 / 3)
SL_MIN_ATR = 0.8         # supertrend stop is kept between these many 15-minute ATR from entry, so the brain (0.5 to 3.5 ATR) accepts it
SL_MAX_ATR = 3.0

def with_ema200(fn, name=None, skip_if=()):
    nm = name or fn.__name__ + '_e200'
    def wrapped(m, h):
        if len(m) < MIN_BARS: return None
        r = fn(m, h)
        if not r: return None
        e = ema([x['c'] for x in m], EMA_LEN)[-1]; c = m[-1]['c']
        if r['side'] == 'buy' and not c > e: return None       # below the 200 EMA: no buys
        if r['side'] == 'sell' and not c < e: return None      # above the 200 EMA: no sells
        for other in skip_if:                                  # another strategy already votes for this same signal
            if other(m, h): return None
        return dict(r, name=nm)
    wrapped.__name__ = nm
    return wrapped

def supertrend(b, n=ST_N, mult=ST_MULT):
    """-> [(line, dir)] with dir +1 (line under price, uptrend) or -1. Standard Supertrend."""
    a = atr(b, n); out = []; fu = fl = 0.0; d = 1
    for i, x in enumerate(b):
        mid = (x['h'] + x['l']) / 2; up, lo = mid + mult * a[i], mid - mult * a[i]
        if i == 0: fu, fl = up, lo
        else:
            pc = b[i - 1]['c']; pfu, pfl = fu, fl
            fu = up if (up < pfu or pc > pfu) else pfu
            fl = lo if (lo > pfl or pc < pfl) else pfl
            if d < 0 and x['c'] > pfu: d = 1
            elif d > 0 and x['c'] < pfl: d = -1
        out.append((fl if d > 0 else fu, d))
    return out

def psar_raw(m, h):
    if len(m) < MIN_BARS: return None
    s = psar(m[-120:]); a = atr(m)[-1]
    if s[-2][1] < 0 < s[-1][1]: return {'side': 'buy', 'sl': min(s[-1][0], min(x['l'] for x in m[-4:])) - 0.1 * a, 'name': 'psar_raw'}
    if s[-2][1] > 0 > s[-1][1]: return {'side': 'sell', 'sl': max(s[-1][0], max(x['h'] for x in m[-4:])) + 0.1 * a, 'name': 'psar_raw'}

def supertrend_flip(m, h):
    if len(m) < MIN_BARS: return None
    s = supertrend(m[-150:]); a = atr(m)[-1]; e = m[-1]['c']
    if not a: return None
    if s[-2][1] < 0 < s[-1][1]: return {'side': 'buy', 'sl': e - min(max(e - s[-1][0], SL_MIN_ATR * a), SL_MAX_ATR * a), 'name': 'supertrend_flip'}
    if s[-2][1] > 0 > s[-1][1]: return {'side': 'sell', 'sl': e + min(max(s[-1][0] - e, SL_MIN_ATR * a), SL_MAX_ATR * a), 'name': 'supertrend_flip'}
'''

TEST = r'''"""Tests for backend/ema200_filter.py (video 3, section 3C). Run: python tests/test_e200.py"""
import os, sys, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.ema200_filter as ef
from backend.ema200_filter import with_ema200, supertrend, psar_raw, supertrend_flip
from backend.indicators import ema, atr

def series(n, seed):
    random.seed(seed); p = 2300.0; out = []; drift = 0.0
    for i in range(n):
        if i % 200 == 0: drift = random.choice([-0.35, -0.1, 0, 0.1, 0.35])
        o = p; p += drift + random.gauss(0, 1.4) + 2.2 * math.sin(i / 17)
        out.append({'t': 1699920000 + i * 900, 'o': o, 'h': max(o, p) + abs(random.gauss(0, .6)), 'l': min(o, p) - abs(random.gauss(0, .6)), 'c': p, 'v': 100})
    return out
def line(prices):
    return [{'t': 1700000000 + i * 900, 'o': prices[i - 1] if i else p, 'h': max(prices[i - 1] if i else p, p) + .2, 'l': min(prices[i - 1] if i else p, p) - .2, 'c': p, 'v': 1} for i, p in enumerate(prices)]
def e200(m): return ema([x['c'] for x in m], 200)[-1]
def fake(side):
    f = lambda m, h: {'side': side, 'sl': m[-1]['c'] - 1 if side == 'buy' else m[-1]['c'] + 1, 'name': 'fake'}
    f.__name__ = 'fake_' + side; return f
# a long climb that ends above its 200 EMA, and a long fall that ends below it
UP = line([100 + 0.5 * i for i in range(260)]); DN = line([400 - 0.5 * i for i in range(260)])
R = []
def T(name, ok): R.append((name, bool(ok)))

assert UP[-1]['c'] > e200(UP) and DN[-1]['c'] < e200(DN)
T('buy passes above the 200 EMA', with_ema200(fake('buy'))(UP, []) is not None)
T('buy is dropped below the 200 EMA', with_ema200(fake('buy'))(DN, []) is None)
T('sell passes below the 200 EMA', with_ema200(fake('sell'))(DN, []) is not None)
T('sell is dropped above the 200 EMA', with_ema200(fake('sell'))(UP, []) is None)
r = with_ema200(fake('buy'))(UP, [])
T('result keeps the side and stop, name gets _e200', r and r['side'] == 'buy' and r['sl'] == UP[-1]['c'] - 1 and r['name'] == 'fake_buy_e200')
T('wrapped function carries the new name', with_ema200(fake('buy'), 'my_name').__name__ == 'my_name')
T('too little history gives nothing', with_ema200(fake('buy'))(UP[-(ef.MIN_BARS - 1):], []) is None)
_ema = ef.ema; ef.ema = lambda v, n: [v[-1]] * len(v)          # make the 200 EMA equal the last close exactly
T('exactly on the 200 EMA is neither above nor below', with_ema200(fake('buy'))(UP, []) is None and with_ema200(fake('sell'))(DN, []) is None)
ef.ema = _ema
T('skip_if silences a duplicate vote', with_ema200(fake('buy'), skip_if=(fake('buy'),))(UP, []) is None)
T('skip_if that stays quiet lets it through', with_ema200(fake('buy'), skip_if=(lambda m, h: None,))(UP, []) is not None)
T('a strategy that returns nothing stays nothing', with_ema200(lambda m, h: None)(UP, []) is None)

# supertrend indicator
climb = supertrend(line([100 + i for i in range(60)])); T('supertrend: steady climb is up', all(d == 1 for _, d in climb[15:]) and all(l < 100 + i for i, (l, d) in enumerate(climb) if i > 15))
fall = supertrend(line([300 - i for i in range(60)])); T('supertrend: steady fall turns down', fall[-1][1] == -1 and fall[-1][0] > 300 - 59)
turn = supertrend(line([100 + i for i in range(40)] + [140 - 4 * i for i in range(30)])); T('supertrend: a sharp drop flips it to down', turn[39][1] == 1 and turn[-1][1] == -1)
back = supertrend(line([100 + i for i in range(40)] + [140 - 4 * i for i in range(20)] + [60 + 5 * i for i in range(25)])); T('supertrend: and a sharp rise flips it back up', back[-1][1] == 1 and any(d == -1 for _, d in back))

# real-looking data: every candle, compare the raw signals with the filtered ones
from backend import strategies as S
from backend.strategies import psar_flip
pe = S.psar_e200; se = S.supertrend_e200          # the REGISTERED copies, exactly what the brain runs
st_raw = st_ok = st_cut = pe_n = overlap = bad_side = bad_sl = bad_name = 0
for seed in (3, 7, 11):
    m = series(1700, seed)
    for e in range(230, len(m) + 1):
        s = m[:e]; c = s[-1]['c']; y = e200(s)
        raw = supertrend_flip(s, []); f = se(s, [])
        if raw:
            st_raw += 1
            if f: st_ok += 1
            else: st_cut += 1
            a = atr(s)[-1]; d = abs(raw['sl'] - c)
            if not (ef.SL_MIN_ATR * a - 1e-9 <= d <= ef.SL_MAX_ATR * a + 1e-9) or (raw['side'] == 'buy') != (raw['sl'] < c): bad_sl += 1
        if f:
            if (f['side'] == 'buy' and not c > y) or (f['side'] == 'sell' and not c < y): bad_side += 1
            if f['name'] != 'supertrend_e200' or not raw or f['side'] != raw['side']: bad_name += 1
        p = pe(s, [])
        if p:
            pe_n += 1
            if psar_flip(s, []): overlap += 1
            if (p['side'] == 'buy' and not c > y) or (p['side'] == 'sell' and not c < y): bad_side += 1
T('supertrend fires on the test data', st_raw >= 20)
T('the filter drops some supertrend signals and keeps others', st_cut > 0 and st_ok > 0)
T('no filtered signal is against the 200 EMA', bad_side == 0)
T('filtered signals are the raw signal with the new name', bad_name == 0)
T('supertrend stop is on the right side, 0.8 to 3 ATR away', bad_sl == 0)
T('psar_e200 fires on the test data', pe_n > 0)
T('psar_e200 never doubles a psar_flip vote', overlap == 0)

# registration
names = [f.__name__ for f in S.ALL]
T('psar_e200 and supertrend_e200 are registered once', names.count('psar_e200') == 1 and names.count('supertrend_e200') == 1)
T('both are in the TREND group', {'psar_e200', 'supertrend_e200'} <= S.TREND)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
'''

A1 = "from .ma_bounce import ma_bounce\nALL = [pa_level, pa_bos, pa_candle, pa_pattern, pa_trendline, ma_cross, ma_bounce, jg_pullback,"
B1 = ("from .ma_bounce import ma_bounce\nfrom .ema200_filter import with_ema200, psar_raw, supertrend_flip\n"
      "psar_e200 = with_ema200(psar_raw, 'psar_e200', skip_if=(psar_flip,)); supertrend_e200 = with_ema200(supertrend_flip, 'supertrend_e200')\n"
      "ALL = [pa_level, pa_bos, pa_candle, pa_pattern, pa_trendline, ma_cross, ma_bounce, psar_e200, supertrend_e200, jg_pullback,")
EDITS = [
 ('backend/strategies.py', A1, B1, 'from .ema200_filter import'),
 ('backend/strategies.py', "'ma_cross', 'ma_bounce'}", "'ma_cross', 'ma_bounce', 'psar_e200', 'supertrend_e200'}", "'psar_e200', 'supertrend_e200'}"),
 ('docs/HANDOFF.md', '[3A, 3B done]', '[3A, 3B, 3C done]', '[3A, 3B, 3C done]'),
 ('docs/HANDOFF.md', '- 3C  backend/ema200_filter.py: the 200 EMA filter.', '- 3C  DONE (backend/ema200_filter.py + tests/test_e200.py: with_ema200 wrapper, psar_raw, supertrend_flip; registered as psar_e200 and supertrend_e200 in TREND; psar_e200 stays silent when psar_flip fires so one SAR flip is never two votes). Original spec: the 200 EMA filter.', '- 3C  DONE (backend/ema200_filter.py'),
]
if not os.path.isdir('backend') or not os.path.isdir('tests'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
if not os.path.exists('backend/ma_bounce.py'): print('STOP: section 3B (ma_bounce.py) is not in this repo yet'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: print('already applied:', path, marker[:40]); new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
open('backend/ema200_filter.py', 'w', encoding='utf-8', newline='').write(MOD)
open('tests/test_e200.py', 'w', encoding='utf-8', newline='').write(TEST)
print('patched OK')
