"""Draws the cartoon pictures shown when a phone notification is expanded, on demand, as PNG bytes.
Same art as the app and website: the dark-haired character, outline style, coins, shield, rocket, clock, receipt, wifi.
Shapes are the same SVG path data the app uses, flattened and drawn with Pillow (no extra libraries)."""
import io, re
from PIL import Image, ImageDraw
W, H, SS = 1024, 512, 2
BG, CARD = (16, 21, 30), (26, 33, 48)                 # app dark theme: --bg, --surface
MUTE, SURF2 = (154, 165, 191), (35, 43, 63)           # outline colour, fill of props
GREEN, BERRY, SKY, SUN = (76, 217, 123), (255, 115, 119), (91, 176, 255), (255, 203, 61)
WHITE = (255, 255, 255)
HAIR_BODY, HAIR_MID, HAIR_TOP = (29, 29, 32), SURF2, (52, 52, 58)
NAMES = ('win', 'loss', 'even', 'risk', 'news', 'bill', 'off', 'hi')
_cache = {}
_NUM = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')

def _bez(p0, p1, p2, p3, n=22):
    return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
             (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1]) for t in [i / n for i in range(1, n + 1)]]

def parse(dstr):
    """SVG path data (M L H V C Q Z, absolute and relative) -> list of (points, closed)."""
    toks = re.findall(r'[MmLlHhVvCcQqZz]|' + _NUM.pattern, dstr)
    subs, cur, i, cmd, x, y, sx, sy = [], [], 0, None, 0.0, 0.0, 0.0, 0.0
    def num(): nonlocal i; v = float(toks[i]); i += 1; return v
    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]): cmd = toks[i]; i += 1
        if cmd in 'Zz':
            if cur: subs.append((cur, True)); cur = []
            x, y = sx, sy; continue
        rel = cmd.islower(); c = cmd.upper(); bx, by = (x, y) if rel else (0.0, 0.0)
        if c == 'M':
            if cur: subs.append((cur, False))
            x, y = bx + num(), by + num(); sx, sy = x, y; cur = [(x, y)]; cmd = 'l' if rel else 'L'
        elif c == 'L': x, y = bx + num(), by + num(); cur.append((x, y))
        elif c == 'H': x = (x if rel else 0.0) + num(); cur.append((x, y))
        elif c == 'V': y = (y if rel else 0.0) + num(); cur.append((x, y))
        elif c == 'C':
            p1 = (bx + num(), by + num()); p2 = (bx + num(), by + num()); p3 = (bx + num(), by + num())
            cur += _bez((x, y), p1, p2, p3); x, y = p3
        elif c == 'Q':
            q = (bx + num(), by + num()); p3 = (bx + num(), by + num())
            p1 = (x + 2 / 3 * (q[0] - x), y + 2 / 3 * (q[1] - y)); p2 = (p3[0] + 2 / 3 * (q[0] - p3[0]), p3[1] + 2 / 3 * (q[1] - p3[1]))
            cur += _bez((x, y), p1, p2, p3); x, y = p3
    if cur: subs.append((cur, False))
    return subs

class Art:
    def __init__(self, scale):
        self.k = scale * SS; self.ox = (W * SS - 240 * self.k) / 2; self.oy = (H * SS - 170 * self.k) / 2 + 4 * SS
        self.im = Image.new('RGB', (W * SS, H * SS), BG); self.d = ImageDraw.Draw(self.im)
        self.d.rounded_rectangle([36 * SS, 30 * SS, (W - 36) * SS, (H - 30) * SS], 56 * SS, fill=CARD)
    def X(self, x, t): return self.ox + (x + t[0]) * self.k
    def Y(self, y, t): return self.oy + (y + t[1]) * self.k
    def _line(self, pts, col, w, closed=False):
        pts = pts + ([pts[0]] if closed else [])
        if len(pts) > 1: self.d.line(pts, fill=col, width=max(1, round(w)), joint='curve')
        r = w / 2
        for (a, b) in pts: self.d.ellipse([a - r, b - r, a + r, b + r], fill=col)            # round caps and joins
    def path(self, dstr, t=(0, 0), fill=None, stroke=MUTE, w=2.3):
        for pts, closed in parse(dstr):
            P = [(self.X(a, t), self.Y(b, t)) for a, b in pts]
            if fill is not None and len(P) > 2: self.d.polygon(P, fill=fill)
            if stroke is not None: self._line(P, stroke, w * self.k, closed)
    def rect(self, x, y, w, h, rx=0, t=(0, 0), fill=None, stroke=MUTE, sw=2.3):
        box = [self.X(x, t), self.Y(y, t), self.X(x + w, t), self.Y(y + h, t)]
        self.d.rounded_rectangle(box, rx * self.k, fill=fill, outline=stroke, width=round(sw * self.k) if stroke else 0)
    def ell(self, cx, cy, rx, ry, t=(0, 0), fill=None, stroke=MUTE, sw=2.3):
        box = [self.X(cx - rx, t), self.Y(cy - ry, t), self.X(cx + rx, t), self.Y(cy + ry, t)]
        self.d.ellipse(box, fill=fill, outline=stroke, width=round(sw * self.k) if stroke else 0)
    def circ(self, cx, cy, r, **kw): self.ell(cx, cy, r, r, **kw)
    def character(self):
        t = (112, 40)
        self.path('M114 146c-14 4-26 2-38-4')
        self.path('M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18z', t, fill=HAIR_BODY)
        self.path('M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z', t, fill=HAIR_MID)
        self.path('M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z', t, fill=HAIR_TOP)
        self.path('M60 47q6 5 12 0', t)
    def sparkle(self, d, col=GREEN, t=(0, 0)): self.path(d, t, stroke=col)
    def coins(self):
        t = (18, 44)
        for cy in (48, 36, 24): self.ell(30, cy, 28, 9, t, fill=SURF2)
        self.path('M30 20v8', t)
    def badge(self, mark, col, x=80, y=46):
        self.circ(x, y, 14, fill=col, stroke=None); self.path(mark, (x, y), stroke=WHITE, w=3.2)
    def done(self, name): return self.im.resize((W, H), Image.LANCZOS)

CHECK, CROSS = 'M-6 .5l4.2 4.2 8.2-9.6', 'M-5-5l10 10M5-5l-10 10'

def scene(name):
    a = Art(2.62); T = (0, 0)
    if name in ('win', 'loss', 'even'):
        a.coins()
        if name == 'win':
            a.badge(CHECK, GREEN)
            for x, y, w_, col, rd in ((20, 6, 7, GREEN, 0), (58, 0, 6, SKY, 0), (96, 8, 3.5, SUN, 1), (128, 2, 7, BERRY, 0), (166, 10, 3.5, GREEN, 1), (196, 4, 6, SUN, 0)):
                if rd: a.circ(x, y, w_, fill=col, stroke=None)
                else: a.rect(x, y, w_, w_, 2, fill=col, stroke=None)
            a.sparkle('M184 40v10M179 45h10')
        elif name == 'loss': a.badge(CROSS, BERRY)
    elif name == 'risk':
        t = (22, 24); a.path('M32 0l32 11v27c0 23-15 38-32 46C15 76 0 61 0 38V11z', t, fill=SURF2); a.circ(32, 36, 8, t=t); a.path('M32 44v13', t)
    elif name == 'news':
        t = (22, 22); a.circ(34, 34, 30, t=t, fill=SURF2); a.path('M34 16v18l12 8', t)
    elif name == 'bill':
        t = (20, 24); a.rect(0, 0, 66, 88, 9, t, fill=SURF2); a.path('M14 24h38M14 40h38M14 56h24', t)
        a.circ(48, 72, 10, t=t, fill=GREEN, stroke=None); a.path('M43 72l3.5 3.5 6.5-7.5', t, stroke=WHITE, w=3)
    elif name == 'off':
        a.path('M16 70q36-34 72 0M30 84q22-20 44 0M44 98q8-8 16 0'); a.circ(52, 110, 3.5, fill=MUTE, stroke=None); a.path('M22 28L84 124', stroke=BERRY, w=4)
    elif name == 'hi':
        t = (24, 16); a.path('M30 0c14 10 18 30 12 52H18C12 30 16 10 30 0z', t, fill=SURF2); a.circ(30, 24, 7, t=t)
        a.path('M18 40l-10 14 12-4M42 40l10 14-12-4', t); a.path('M24 56q6 16 12 0z', t, fill=GREEN, stroke=None)
        a.sparkle('M92 24v10M87 29h10'); a.sparkle('M12 100v8M8 104h8')
    a.character()
    return a.done(name)

def png(name):
    if name not in NAMES: return None
    if name not in _cache:
        b = io.BytesIO(); scene(name).save(b, 'PNG', optimize=True); _cache[name] = b.getvalue()
    return _cache[name]
