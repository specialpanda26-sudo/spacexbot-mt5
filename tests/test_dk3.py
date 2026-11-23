"""DK3: 5-minute candles reach the server. Run:  python tests/test_dk3.py"""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import bars
ok = []
def chk(name, c): ok.append((name, bool(c)))

def with_m5(fb, fail=False):
    old = fb.rates
    def rates(sym, tf, count):
        if tf != 'M5': return old(sym, tf, count)
        if fail: raise RuntimeError('no M5')
        last = int(fb.clock.now // 300) * 300 - 300
        return [[last - (count - 1 - k) * 300 + fb.off * 60, 2300.0 + k * 0.01, 2300.5 + k * 0.01, 2299.5, 2300.2, 5] for k in range(count)]
    fb.rates = rates; return fb

bars._d.clear(); clock, fb, web, e, sf = D.rig(off=180); with_m5(fb); D.go(e, clock, 4)
m5 = bars.get('XAUUSD', 'M5'); m15 = bars.get('XAUUSD', 'M15')
chk('first push: 450 five-minute candles reach the server', len(m5) >= 400)
chk('five-minute candles are 5 minutes apart and in UTC', len(m5) > 2 and m5[-1]['t'] - m5[-2]['t'] == 300 and m5[-1]['t'] <= int(clock.now))
chk('15-minute candles still go', len(m15) >= 400)
bars._d.clear(); clock, fb, web, e, sf = D.rig(off=180); with_m5(fb, fail=True); D.go(e, clock, 4)
chk('MT5 cannot give 5-minute candles: 15-minute candles still go, no crash', len(bars.get('XAUUSD', 'M15')) >= 400 and not bars.get('XAUUSD', 'M5'))
bad = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if bad else 0)
