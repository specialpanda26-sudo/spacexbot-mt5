"""Draws the spaceXBot logo (the planet-helmet with its ring and rocket) as a transparent 1024 PNG. Same shapes as the website's logo."""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.notifart import parse
from PIL import Image, ImageDraw

BODY, EDGE, VIS = (204, 208, 207), (74, 92, 106), (11, 26, 36)

def render(out_path, N=1024, SS=2):
    Z = N * SS; K = .76 * Z / 412
    def T(x, y): return (((x - 315) * .76 + 256 - 50) * Z / 412, ((y - 287) * .76 + 262 - 50) * Z / 412)
    base = Image.new('RGBA', (Z, Z), (0, 0, 0, 0))
    def put(fn, op=1.0):
        L = Image.new('RGBA', (Z, Z), (0, 0, 0, 0)); fn(ImageDraw.Draw(L))
        if op < 1: L.putalpha(L.getchannel('A').point(lambda v: int(v * op)))
        base.alpha_composite(L)
    def rot(px, py, ang, cx, cy):
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang)); return (cx + px * c - py * s, cy + px * s + py * c)
    def ring(t0, t1, n=240):
        return [T(*rot(273 * math.cos(t0 + (t1 - t0) * i / n), 90 * math.sin(t0 + (t1 - t0) * i / n), -34.6, 315, 370)) for i in range(n + 1)]
    def stroke(d, pts, col, w):
        d.line(pts, fill=col, width=round(w * K), joint='curve'); r = w * K / 2
        for a, b in (pts[0], pts[-1]): d.ellipse([a - r, b - r, a + r, b + r], fill=col)
    def poly(d, dstr, col):
        for pts, _ in parse(dstr): d.polygon([T(a, b) for a, b in pts], fill=col)
    def ell(d, cx, cy, rx, ry, col, ang=0):
        d.polygon([T(*rot(rx * math.cos(2 * math.pi * i / 90), ry * math.sin(2 * math.pi * i / 90), ang, cx, cy)) for i in range(90)], fill=col)
    full, front = ring(0, 2 * math.pi), ring(math.pi, 0)
    put(lambda d: (stroke(d, full, EDGE, 13), stroke(d, full, BODY, 7)))
    put(lambda d: poly(d, 'M333 168L346 150L413 30L360 152Z', BODY), .6)
    put(lambda d: poly(d, 'M346 150L413 30L372 158Z', BODY))
    put(lambda d: poly(d, 'M318 160Q335 148 358 152L362 170Q335 180 320 172Z', VIS))
    put(lambda d: ell(d, 295, 345, 186, 178, BODY))
    put(lambda d: ell(d, 478, 338, 22, 34, VIS), .75)
    put(lambda d: poly(d, 'M138 268C205 300 380 298 448 252C474 330 456 424 402 470C332 522 195 520 152 440C124 390 124 322 138 268Z', VIS))
    put(lambda d: stroke(d, [T(*p) for p in parse('M148 330C150 300 156 282 168 270')[0][0]], BODY, 5), .5)
    put(lambda d: ell(d, 178, 384, 31, 14, BODY, 24))
    put(lambda d: ell(d, 329, 380, 51, 17, BODY, -11))
    put(lambda d: (stroke(d, front, EDGE, 13), stroke(d, front, BODY, 7)))
    base.resize((N, N), Image.LANCZOS).save(out_path)

if __name__ == '__main__':
    render(sys.argv[1] if len(sys.argv) > 1 else 'branding/logo.png'); print('logo written')
