"""Tests for backend/trail_exit.py + the --trail flag in tools/backtest.py (video 3, section 3D). Run: python tests/test_trail.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools')); os.chdir(ROOT)
from backend.trail_exit import trail_exit
import backtest as bt

def bar(o, h, l, c): return {'t': 0, 'o': o, 'h': h, 'l': l, 'c': c, 'v': 0}
R = []
def T(name, ok): R.append((name, bool(ok)))
def close(x, y): return x is not None and abs(x - y) < 1e-9

# buy: entry 100, stop 98 (risk 2), ATR 1, trail 2 ATR. Price runs to 110 -> stop 108; then a bar dips to 107 -> out at 108 = +4R
up = [bar(100, 104, 100, 104), bar(104, 110, 104, 109), bar(109, 109, 107, 107.5)]
r = trail_exit('buy', 100, 98, up, 1.0, 2.0)
T('buy: trailing stop locks in profit (+4R)', r and close(r[0], 4.0) and r[1] == 3)
T('buy: result is above the old fixed 2R target', r and r[0] > 2.0)
# the stop never moves down: ATR so big that high-minus-trail is under the original stop
r = trail_exit('buy', 100, 98, [bar(100, 101, 99, 100), bar(100, 100.5, 97.5, 100)], 3.0, 2.0)
T('buy: stop never moves below the original stop (-1R)', r and close(r[0], -1.0))
# gap: bar opens below the stop -> filled at the open, worse than -1R
r = trail_exit('buy', 100, 98, [bar(96, 97, 95, 96)], 1.0, 2.0)
T('buy: a gap through the stop fills at the open (-2R)', r and close(r[0], -2.0))
# pessimistic: one bar that reaches both a huge high and the stop -> stop first
r = trail_exit('buy', 100, 98, [bar(100, 110, 90, 95)], 1.0, 2.0)
T('buy: stop is checked before the same bar can raise it (-1R)', r and close(r[0], -1.0))
# sell mirror: entry 100, stop 102, falls to 90 -> stop 92; bar high 93 -> out at 92 = +4R
dn = [bar(100, 100, 96, 96), bar(96, 96, 90, 91), bar(91, 93, 91, 92.5)]
r = trail_exit('sell', 100, 102, dn, 1.0, 2.0)
T('sell: trailing stop locks in profit (+4R)', r and close(r[0], 4.0) and r[1] == 3)
r = trail_exit('sell', 100, 102, [bar(100, 101, 99, 100), bar(100, 102.5, 99.5, 100)], 3.0, 2.0)
T('sell: stop never moves above the original stop (-1R)', r and close(r[0], -1.0))
r = trail_exit('sell', 100, 102, [bar(104, 105, 103, 104)], 1.0, 2.0)
T('sell: a gap through the stop fills at the open (-2R)', r and close(r[0], -2.0))
# out of time: closes at the last bar's close
r = trail_exit('buy', 100, 98, [bar(100, 101, 99.5, 100.5)] * 5, 1.0, 2.0, max_bars=3)
T('out of time: closes at market after max_bars', r and close(r[0], 0.25) and r[1] == 3)
# bad input
T('no bars -> None', trail_exit('buy', 100, 98, [], 1.0) is None)
T('zero risk -> None', trail_exit('buy', 100, 100, up, 1.0) is None)
T('zero ATR -> None', trail_exit('buy', 100, 98, up, 0.0) is None)

# --trail flag parsing
T('flag: absent = fixed target', bt.trail_arg(['x.csv']) == 0.0)
T('flag: --trail = 2.0', bt.trail_arg(['--trail']) == 2.0)
T('flag: --trail=3 = 3.0', bt.trail_arg(['--trail=3']) == 3.0)
for bad in ('--trail=abc', '--trail=0', '--trail=-1'):
    try: bt.trail_arg([bad]); ok = False
    except SystemExit: ok = True
    T('flag: refuses ' + bad, ok)

# backtest.run: a steady climb. Fixed target gives exactly +2R each; the trailing exit rides the trend, so it must differ and beat it.
m15 = [bar(1000 + i, 1000 + i + 1.2, 1000 + i - 0.2, 1000 + i + 1) for i in range(700)]
for x in m15: x['t'] = 1700000000 + 900 * m15.index(x)
def fake_eval(w, h, mc, rr, off):
    e = w[-1]['c']; return {'side': 'buy', 'entry': e, 'sl': e - 3, 'tp': e + 3 * rr, 'strategy': 'fake', 'score': 2}
real = bt.evaluate; bt.evaluate = fake_eval
fixed = bt.run(m15); trailed = bt.run(m15, trail=2.0); bt.evaluate = real
T('run: default (no trail) is the old fixed 2R behaviour', fixed and all(abs(x - 2.0) < 1e-9 for x in fixed))
T('run: trail=2 gives different, larger results in a clean trend', trailed and all(x > 2.0 for x in trailed))
T('run: trail trades do not overlap (cooldown after the exit)', len(trailed) < len(fixed))

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
