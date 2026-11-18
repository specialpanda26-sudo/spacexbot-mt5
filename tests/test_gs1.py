"""Tests for backend/gs_zones.py (video 5, section 5A). Run: python tests/test_gs1.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import backend.gs_zones as gz
from backend.gs_zones import bias, find_zones, scan, touching, _htf_done

R = []
def T(name, ok): R.append((name, bool(ok)))
def line(prices, step=900, t0=1700000000, wick=0.3):
    return [{'t': t0 + i * step, 'o': prices[i - 1] if i else p, 'h': max(prices[i - 1] if i else p, p) + wick, 'l': min(prices[i - 1] if i else p, p) - wick, 'c': p, 'v': 1} for i, p in enumerate(prices)]
ZZ = [100, 101, 102, 101, 100, 99, 100, 101, 103, 102, 101, 100, 99, 100, 101, 102]        # base wiggle, swing high ~103.3, ATR about 1.5
def zigzag(n, up, step=900, t0=1700000000):
    p = 100.0; out = []; d = 1 if up else -1; k = 0
    while len(out) < n:
        for _ in range(8): p += d; out.append(p)
        for _ in range(4): p -= d; out.append(p)
    return line(out[:n], step, t0, 0.2)

# --- order blocks ---
bull = line(ZZ + [98.5, 103, 106, 109, 108.5, 109])            # candle 16 (98.5) is the last bearish candle, then a 3-candle impulse above the 103 swing high
from backend.indicators import atr
def obs(w, b): return gz._order_blocks(w, atr(w), b, 'm15')      # straight from the order-block finder, so the newest-zones cap cannot hide anything
z = obs(bull, True)
T('demand: order block found on the last bearish candle before the impulse', len(z) == 1 and z[0]['kind'] == 'ob' and z[0]['side'] == 'buy')
T('demand: zone edges are that candle low / high', z and abs(z[0]['lo'] - (98.5 - 0.3)) < 1e-9 and abs(z[0]['hi'] - (102 + 0.3)) < 1e-9)
T('demand: untouched while price stays away', z and z[0]['touched'] is False)
back = obs(line(ZZ + [98.5, 103, 106, 109, 108.5, 109, 106, 102]), True)
T('demand: marked touched once price comes back into it', back and back[0]['touched'] is True)
T('demand: dropped once a candle closes below the zone', obs(line(ZZ + [98.5, 103, 106, 109, 108.5, 109, 106, 103.5, 97]), True) == [])
T('demand: no impulse (slow drift) = no order block', obs(line(ZZ + [98.5, 99.5, 100.5, 101.5, 102.5, 103.5]), True) == [])
ZH = [100, 101, 102, 101, 100, 99, 100, 101, 112, 108, 105, 103, 101, 100, 101, 102]       # a swing high of 112 that the move never takes out
T('demand: impulse that does not break structure = no order block', obs(line(ZH + [98.5, 103, 106, 109, 108.5, 109]), True) == [])
two = obs(line(ZZ + [98.5, 98.3, 103, 106, 109, 108.5, 109]), True)
T('demand: only the LAST bearish candle before the move is the order block', len(two) == 1 and abs(two[0]['lo'] - 98.0) < 1e-9)
mir = [200 - p for p in ZZ + [98.5, 103, 106, 109, 108.5, 109]]
s = obs(line(mir), False)
T('supply: mirror image gives a supply zone (sell)', len(s) == 1 and s[0]['side'] == 'sell' and s[0]['kind'] == 'ob')
T('supply: dropped once a candle closes above the zone', obs(line([200 - p for p in ZZ + [98.5, 103, 106, 109, 108.5, 109, 106, 103.5, 97]]), False) == [])
T('buys never return supply zones', all(q['side'] == 'buy' for q in find_zones(bull, True)))

# --- fair value gaps ---
base = [100, 100.4, 100.1, 100.5, 100.2, 100.6, 100.3, 100.5, 100.2, 100.6, 100.3, 100.5, 100.2, 100.6, 100.3, 100.5, 100.2, 100.6, 100.3, 100.5]
def gapseries(c1, tail=None):
    b = line(base); last = b[-1]['c']
    c0 = {'t': 1, 'o': last, 'h': last + 0.2, 'l': last - 0.1, 'c': last + 0.1, 'v': 1}
    m1 = {'t': 2, 'o': last + 0.1, 'h': c1 + 0.1, 'l': last, 'c': c1, 'v': 1}
    g = {'t': 3, 'o': c1 - 0.1, 'h': c1 + 0.5, 'l': c1 - 0.2, 'c': c1 + 0.3, 'v': 1}
    for i, x in enumerate((c0, m1, g)): x['t'] = b[-1]['t'] + 900 * (i + 1)
    return b + [c0, m1, g] + (tail or [])
fv = [q for q in find_zones(gapseries(102.5), True) if q['kind'] == 'fvg']
T('fvg: bullish gap with a big middle candle is found', len(fv) == 1 and fv[0]['side'] == 'buy')
T('fvg: zone runs from the first candle high to the third candle low', fv and abs(fv[0]['lo'] - 100.7) < 0.05 and abs(fv[0]['hi'] - 102.3) < 0.05)
T('fvg: a tiny middle candle is not displacement', not [q for q in find_zones(gapseries(100.9), True) if q['kind'] == 'fvg'])
b = line(base); L = b[-1]['c']; t = b[-1]['t']
small = b + [{'t': t + 900, 'o': L, 'h': L + 0.2, 'l': L - 0.1, 'c': L + 0.1, 'v': 1}, {'t': t + 1800, 'o': L + 0.1, 'h': L + 0.5, 'l': L + 0.05, 'c': L + 0.4, 'v': 1}, {'t': t + 2700, 'o': L + 1.6, 'h': L + 2.2, 'l': L + 1.4, 'c': L + 2.0, 'v': 1}]
T('fvg: a big gap with a small middle candle is not displacement', not [q for q in find_zones(small, True) if q['kind'] == 'fvg'])
T('fvg: dropped when a later candle closes below the gap', not [q for q in find_zones(gapseries(102.5, line([99], t0=2000000000)), True) if q['kind'] == 'fvg'])

# --- touching ---
Z = {'lo': 100.0, 'hi': 101.0}
T('touching: candle inside the zone', touching({'l': 100.2, 'h': 100.8}, Z))
T('touching: wick into the zone', touching({'l': 100.9, 'h': 103}, Z))
T('touching: candle far above is not touching', not touching({'l': 101.5, 'h': 103}, Z))
T('touching: candle far below is not touching', not touching({'l': 97, 'h': 99.5}, Z))

# --- step 1: 1h and 15m must agree ---
def pair(m_up, h_up, extra=None):
    m = zigzag(120, m_up); h = zigzag(60, h_up, 3600, m[-1]['t'] + 900 - 60 * 3600)
    if extra: h = h + extra
    return m, h
m, h = pair(True, True);   T('bias: both up = up', bias(m, h) == 'up')
m, h = pair(False, False); T('bias: both down = down', bias(m, h) == 'down')
m, h = pair(False, True);  T('bias: 15m down but 1h up = no trade', bias(m, h) is None)
m, h = pair(True, False);  T('bias: 15m up but 1h down = no trade', bias(m, h) is None)
m, _ = pair(True, True);   T('bias: no 1h data = no trade', bias(m, []) is None and bias(m, None) is None)
m, h = pair(True, True)
forming = [{'t': m[-1]['t'], 'o': 500, 'h': 600, 'l': 1, 'c': 5, 'v': 1}]
T('bias: the 1h candle still forming is ignored', bias(m, h + forming) == 'up' and len(_htf_done(m, h + forming)) == len(_htf_done(m, h)))
T('bias: a 1h main chart is not used (this module is for 15m)', bias(zigzag(120, True, 3600), h) is None)
T('bias: too little data = no trade', bias(m[:30], h) is None)

# --- steps 1 + 2 together ---
m, h = pair(True, True); r = scan(m, h)
T('scan: up gives only demand zones', r and r['bias'] == 'up' and len(r['zones']) > 0 and all(q['side'] == 'buy' for q in r['zones']))
m, h = pair(False, False); r = scan(m, h)
T('scan: down gives only supply zones', r and r['bias'] == 'down' and len(r['zones']) > 0 and all(q['side'] == 'sell' for q in r['zones']))
m, h = pair(False, True)
T('scan: disagreement gives None', scan(m, h) is None)
tags = {q['tf'] for q in (scan(*pair(True, True)) or {'zones': []})['zones']}
T('scan: zones come from both the 15m and the 1h chart', tags == {'m15', 'h1'})

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
