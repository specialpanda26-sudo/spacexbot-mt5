def ema(v, n):
    k = 2 / (n + 1); out = []; e = None
    for x in v:
        e = x if e is None else x * k + e * (1 - k)
        out.append(e)
    return out

def rsi(c, n=14):
    out = [50.0] * len(c)
    if len(c) <= n: return out
    g = l = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]; g += max(d, 0); l += max(-d, 0)
    g /= n; l /= n
    for i in range(n, len(c)):
        if i > n:
            d = c[i] - c[i - 1]
            g = (g * (n - 1) + max(d, 0)) / n; l = (l * (n - 1) + max(-d, 0)) / n
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return out

def atr(b, n=14):
    out = []; a = 0.0
    for i, x in enumerate(b):
        pc = b[i - 1]['c'] if i else x['c']
        tr = max(x['h'] - x['l'], abs(x['h'] - pc), abs(x['l'] - pc))
        if i < n: a = (a * i + tr) / (i + 1)
        else: a = (a * (n - 1) + tr) / n
        out.append(a)
    return out

def bollinger(c, n=20, k=2.0):
    mid, up, lo = [], [], []
    for i in range(len(c)):
        w = c[max(0, i - n + 1): i + 1]; m = sum(w) / len(w)
        sd = (sum((x - m) ** 2 for x in w) / len(w)) ** 0.5
        mid.append(m); up.append(m + k * sd); lo.append(m - k * sd)
    return mid, up, lo

def swings(b, left=3, right=3):
    """confirmed swing points: [(index, price, 'H'|'L')]"""
    out = []
    for i in range(left, len(b) - right):
        hi = b[i]['h']; lo = b[i]['l']
        if all(hi > b[j]['h'] for j in range(i - left, i)) and all(hi >= b[j]['h'] for j in range(i + 1, i + right + 1)):
            out.append((i, hi, 'H'))
        if all(lo < b[j]['l'] for j in range(i - left, i)) and all(lo <= b[j]['l'] for j in range(i + 1, i + right + 1)):
            out.append((i, lo, 'L'))
    return out

def macd(c, f=12, s=26, sig=9):
    line = [a - b for a, b in zip(ema(c, f), ema(c, s))]; sg = ema(line, sig)
    return line, sg, [a - b for a, b in zip(line, sg)]

def adx(b, n=14):
    """Wilder ADX. Returns 0.0 until there is enough history."""
    L = len(b); out = [0.0] * L
    if L < 2 * n + 2: return out
    tr = [0.0]; pdm = [0.0]; ndm = [0.0]
    for i in range(1, L):
        up = b[i]['h'] - b[i - 1]['h']; dn = b[i - 1]['l'] - b[i]['l']
        pdm.append(up if up > dn and up > 0 else 0.0); ndm.append(dn if dn > up and dn > 0 else 0.0)
        tr.append(max(b[i]['h'] - b[i]['l'], abs(b[i]['h'] - b[i - 1]['c']), abs(b[i]['l'] - b[i - 1]['c'])))
    def sm(v):
        o = [0.0] * L; s = sum(v[1:n + 1]); o[n] = s
        for i in range(n + 1, L): s = s - s / n + v[i]; o[i] = s
        return o
    st, sp, sn = sm(tr), sm(pdm), sm(ndm); dx = [0.0] * L
    for i in range(n, L):
        if st[i] <= 0: continue
        pi = 100 * sp[i] / st[i]; ni = 100 * sn[i] / st[i]; d = pi + ni
        dx[i] = 100 * abs(pi - ni) / d if d else 0.0
    a = sum(dx[n:2 * n]) / n; out[2 * n - 1] = a
    for i in range(2 * n, L): a = (a * (n - 1) + dx[i]) / n; out[i] = a
    return out

def psar(b, af0=0.02, step=0.02, mx=0.2):
    """Parabolic SAR. Returns [(sar, trend)] with trend +1 (SAR under price) or -1."""
    if len(b) < 3: return [(b[0]['l'], 1)] * len(b)
    up = b[1]['c'] >= b[0]['c']; sar = b[0]['l'] if up else b[0]['h']; ep = b[1]['h'] if up else b[1]['l']; af = af0
    out = [(sar, 1 if up else -1), (sar, 1 if up else -1)]
    for i in range(2, len(b)):
        sar = sar + af * (ep - sar)
        if up:
            sar = min(sar, b[i - 1]['l'], b[i - 2]['l'])
            if b[i]['l'] < sar: up = False; sar = ep; ep = b[i]['l']; af = af0
            elif b[i]['h'] > ep: ep = b[i]['h']; af = min(af + step, mx)
        else:
            sar = max(sar, b[i - 1]['h'], b[i - 2]['h'])
            if b[i]['h'] > sar: up = True; sar = ep; ep = b[i]['h']; af = af0
            elif b[i]['l'] < ep: ep = b[i]['l']; af = min(af + step, mx)
        out.append((sar, 1 if up else -1))
    return out

def heikin(b):
    out = []
    for i, x in enumerate(b):
        c = (x['o'] + x['h'] + x['l'] + x['c']) / 4
        o = (x['o'] + x['c']) / 2 if i == 0 else (out[-1]['o'] + out[-1]['c']) / 2
        out.append({'o': o, 'c': c, 'h': max(x['h'], o, c), 'l': min(x['l'], o, c)})
    return out
