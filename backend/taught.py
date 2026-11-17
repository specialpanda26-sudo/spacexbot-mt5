"""Strategies you teach the bot: JSON files in the taught/ folder (no code). The brain loads them next to the built-in ones.
Rule: "<value> <op> <value>"  ops: > < >= <= cross_above cross_below.  Values: a number, open high low close, ema(n) sma(n) rsi(n)
atr(n) adx(n) macd macd_signal macd_hist bb_upper(n,k) bb_mid(n) bb_lower(n,k) hh(n) ll(n). Add [k] for k candles back."""
import os, re, json, glob, datetime as dt
from .indicators import ema, rsi, atr, adx, bollinger, macd

OPS = r'\s*(>=|<=|cross_above|cross_below|>|<)\s*'
VAL = re.compile(r'^([a-z_]+)(?:\(([\d.,\s]*)\))?(?:\[(\d+)\])?$')
def _num(x):
    try: return float(x)
    except ValueError: return None

def _series(name, a, m):
    c = [x['c'] for x in m]; n = int(a[0]) if a else 0
    if name in ('open', 'high', 'low', 'close'): return [x[name[0]] for x in m]
    if name == 'ema': return ema(c, n)
    if name == 'sma': return [sum(c[max(0, i - n + 1):i + 1]) / len(c[max(0, i - n + 1):i + 1]) for i in range(len(c))]
    if name == 'rsi': return rsi(c, n or 14)
    if name == 'atr': return atr(m, n or 14)
    if name == 'adx': return adx(m, n or 14)
    if name in ('macd', 'macd_signal', 'macd_hist'): return macd(c, *[int(x) for x in a[:3]])[('macd', 'macd_signal', 'macd_hist').index(name)]
    if name in ('bb_upper', 'bb_mid', 'bb_lower'): return bollinger(c, n or 20, a[1] if len(a) > 1 else 2.0)[('bb_mid', 'bb_upper', 'bb_lower').index(name)]
    if name == 'hh': return [max([x['h'] for x in m[max(0, i - n):i]] or [m[i]['h']]) for i in range(len(m))]
    if name == 'll': return [min([x['l'] for x in m[max(0, i - n):i]] or [m[i]['l']]) for i in range(len(m))]
    raise ValueError('unknown value: ' + name)

def _val(t):
    t = t.strip()
    if _num(t) is not None: return ('n', _num(t))
    g = VAL.match(t)
    if not g: raise ValueError('cannot read: ' + t)
    a = [_num(x) for x in (g.group(2) or '').split(',') if x.strip()]
    _series(g.group(1), a, [{'o': 1, 'h': 1, 'l': 1, 'c': 1}] * 3)
    return ('s', g.group(1), tuple(a), int(g.group(3) or 0))

def _rule(text):
    p = re.split(OPS, text.strip()); assert len(p) == 3, 'rule needs one operator: ' + text
    return _val(p[0]), p[1], _val(p[2])

def _get(v, m, cache, back):
    if v[0] == 'n': return v[1]
    k = v[:3]
    if k not in cache: cache[k] = _series(v[1], list(v[2]), m)
    return cache[k][-1 - v[3] - back]

def _ok(r, m, cache):
    a, op, b = r; x, y = _get(a, m, cache, 0), _get(b, m, cache, 0)
    if op == '>': return x > y
    if op == '<': return x < y
    if op == '>=': return x >= y
    if op == '<=': return x <= y
    px, py = _get(a, m, cache, 1), _get(b, m, cache, 1)
    return (x > y and px <= py) if op == 'cross_above' else (x < y and px >= py)

def make(sp):
    name = str(sp['name'])
    assert re.fullmatch(r'[a-z0-9_]{3,30}', name), 'name: 3-30 letters/digits/underscore, lowercase'
    sides = {s: [_rule(t) for t in sp[s]] for s in ('buy', 'sell') if sp.get(s)}
    assert sides, 'needs "buy" and/or "sell" rules'
    k = float(sp.get('sl_atr', 1.5)); nb = int(sp.get('sl_bars', 0)); hrs = sp.get('hours'); solo = sp.get('solo') is True
    def fn(m, h):
        if len(m) < 250: return None
        if hrs and not (hrs[0] <= dt.datetime.utcfromtimestamp(m[-1]['t']).hour < hrs[1]): return None
        cache = {}
        for side, rules in sides.items():
            if all(_ok(r, m, cache) for r in rules):
                a = atr(m)[-1]; e = m[-1]['c']
                if nb: sl = (min(x['l'] for x in m[-nb:]) - 0.2 * a) if side == 'buy' else (max(x['h'] for x in m[-nb:]) + 0.2 * a)
                else: sl = e - k * a if side == 'buy' else e + k * a
                out = {'side': side, 'sl': sl, 'name': name}
                if solo: out['solo'] = True
                return out
    fn.__name__ = name; return fn

def load(ALL, REVERSION, TREND, folder=None):
    folder = folder or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'taught'); n = 0
    for p in sorted(glob.glob(os.path.join(folder, '*.json'))):
        try:
            j = json.load(open(p, encoding='utf-8')); j = j.get('strategies', [j]) if isinstance(j, dict) else j
        except Exception as e: print('taught: cannot read', p, e); continue
        for sp in j:
            try:
                if sp.get('enabled') is False: continue
                f = make(sp)
                if f.__name__ in {x.__name__ for x in ALL}: raise ValueError('name already used')
                ALL.append(f); (REVERSION if sp.get('kind') == 'reversion' else TREND).add(f.__name__); n += 1
            except Exception as e: print('taught: skipped', sp.get('name') if isinstance(sp, dict) else sp, '-', e)
    return n
