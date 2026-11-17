"""Draws the cartoon pictures shown when a phone notification is expanded, on demand, as PNG bytes.
Same look as the website: dark navy, rounded outline art, the helmet mascot, green / coral / sun / sky accents."""
import io, random
from PIL import Image, ImageDraw
W, H, S = 1024, 512, 2
BG, CARD = (27, 33, 49), (35, 43, 63)
INK, MUTE = (204, 208, 207), (154, 165, 191)
GREEN, BAD, SUN, SKY = (76, 217, 123), (255, 115, 119), (255, 203, 61), (91, 176, 255)
VIS, EDGE = (11, 26, 36), (74, 92, 106)
NAMES = ('win', 'loss', 'even', 'risk', 'news', 'bill', 'off', 'hi')
_cache = {}

def mascot(d, cx, cy, r, mood, col):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INK, outline=EDGE, width=8)                       # helmet
    d.rounded_rectangle([cx - r * .78, cy - r * .5, cx + r * .78, cy + r * .55], r * .42, fill=VIS)      # visor
    ex, ey, e = r * .32, cy + 0, r * .13
    for sx in (-1, 1):
        x = cx + sx * ex
        if mood == 'happy':   d.arc([x - e * 1.3, ey - e, x + e * 1.3, ey + e * 1.4], 200, 340, fill=col, width=9)
        elif mood == 'sad':   d.arc([x - e * 1.3, ey - e * .2, x + e * 1.3, ey + e * 2], 20, 160, fill=col, width=9)
        elif mood == 'wow':   d.ellipse([x - e, ey - e, x + e, ey + e], outline=col, width=8)
        else:                 d.line([x - e, ey, x + e, ey], fill=col, width=9)
    my = cy + r * .3
    if mood == 'happy': d.arc([cx - r * .22, my - r * .12, cx + r * .22, my + r * .16], 20, 160, fill=col, width=8)
    elif mood == 'sad': d.arc([cx - r * .2, my, cx + r * .2, my + r * .3], 200, 340, fill=col, width=8)
    elif mood == 'wow': d.ellipse([cx - r * .07, my, cx + r * .07, my + r * .16], outline=col, width=7)
    else:               d.line([cx - r * .15, my + 6, cx + r * .15, my + 6], fill=col, width=8)
    d.arc([cx - r * .6, cy - r * .9, cx + r * .1, cy - r * .1], 200, 260, fill=(255, 255, 255), width=7)  # shine
    d.line([cx, cy - r, cx + r * .12, cy - r * 1.28], fill=EDGE, width=8); d.ellipse([cx + r * .06, cy - r * 1.4, cx + r * .2, cy - r * 1.26], fill=col)  # antenna
    d.rounded_rectangle([cx - r * .55, cy + r * .95, cx + r * .55, cy + r * 1.5], 26, fill=(60, 70, 92), outline=EDGE, width=6)   # suit

def plus(d, x, y, s, col, w=8): d.line([x - s, y, x + s, y], fill=col, width=w); d.line([x, y - s, x, y + s], fill=col, width=w)
def arrow(d, x, y, up, col):
    s = 1 if up else -1
    d.line([x, y + 120 * s, x, y - 100 * s], fill=col, width=22); d.polygon([(x - 62, y - 70 * s), (x + 62, y - 70 * s), (x, y - 150 * s)], fill=col)
def sparkles(d, col, n, box, seed):
    r = random.Random(seed)
    for _ in range(n):
        x, y = r.randint(box[0], box[2]), r.randint(box[1], box[3]); plus(d, x, y, r.randint(8, 18), col, 6)
def rocket(d, x, y, col, tilt=0):
    d.polygon([(x, y - 120), (x + 52, y - 20), (x + 52, y + 80), (x - 52, y + 80), (x - 52, y - 20)], fill=INK, outline=EDGE)
    d.ellipse([x - 22, y - 36, x + 22, y + 8], fill=VIS, outline=col, width=6)
    d.polygon([(x - 52, y + 20), (x - 96, y + 96), (x - 52, y + 80)], fill=col); d.polygon([(x + 52, y + 20), (x + 96, y + 96), (x + 52, y + 80)], fill=col)
    d.polygon([(x - 26, y + 84), (x + 26, y + 84), (x, y + 150)], fill=SUN)
def cloud(d, x, y, col):
    for dx, dy, r in ((-60, 10, 52), (0, -20, 66), (64, 10, 50)): d.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=col)
    d.rectangle([x - 110, y + 10, x + 114, y + 60], fill=col)

def scene(name):
    im = Image.new('RGB', (W * S, H * S), BG); d = ImageDraw.Draw(im); k = S
    def P(f): return lambda *a, **kw: f(d, *a, **kw)
    d.rounded_rectangle([40 * k, 40 * k, (W - 40) * k, (H - 40) * k], 56 * k, fill=CARD)
    sc = lambda v: [tuple(y * k for y in x) if isinstance(x, tuple) else x * k for x in v]
    if name == 'win':
        mascot(d, 330 * k, 270 * k, 150 * k, 'happy', GREEN); rocket(d, 760 * k, 250 * k, GREEN)
        for p in ((650, 110), (880, 140), (900, 330), (600, 330), (500, 120)): plus(d, p[0] * k, p[1] * k, 14 * k, GREEN, 8 * k)
        sparkles(d, SUN, 10, sc((100, 80, 940, 430)), 1)
    elif name == 'loss':
        mascot(d, 330 * k, 290 * k, 150 * k, 'sad', BAD); cloud(d, 740 * k, 150 * k, (74, 84, 110))
        r = random.Random(3)
        for i in range(9): x = (650 + i * 24) * k; y = (250 + r.randint(0, 80)) * k; d.line([x, y, x - 10 * k, y + 40 * k], fill=SKY, width=7 * k)
        d.polygon(sc([(700, 400), (780, 400), (740, 450)]), fill=BAD)
    elif name == 'even':
        mascot(d, 330 * k, 270 * k, 150 * k, 'flat', SUN)
        d.rounded_rectangle(sc([640, 190, 880, 224]), 17 * k, fill=SUN); d.rounded_rectangle(sc([640, 290, 880, 324]), 17 * k, fill=SUN)
    elif name == 'risk':
        mascot(d, 330 * k, 270 * k, 150 * k, 'wow', SUN)
        d.polygon(sc([(760, 90), (900, 190), (880, 340), (760, 420), (640, 340), (620, 190)]), fill=(60, 70, 92), outline=SUN, width=10 * k)
        d.line(sc([760, 170, 760, 290]), fill=SUN, width=22 * k); d.ellipse(sc([744, 314, 776, 346]), fill=SUN)
    elif name == 'news':
        mascot(d, 330 * k, 270 * k, 150 * k, 'wow', SKY)
        d.ellipse(sc([620, 120, 900, 400]), fill=(60, 70, 92), outline=SKY, width=12 * k); d.line(sc([760, 260, 760, 180]), fill=SKY, width=14 * k); d.line(sc([760, 260, 830, 290]), fill=SKY, width=14 * k)
        d.line(sc([600, 100, 570, 70]), fill=SUN, width=9 * k); d.line(sc([920, 100, 950, 70]), fill=SUN, width=9 * k)
    elif name == 'bill':
        mascot(d, 330 * k, 270 * k, 150 * k, 'happy', GREEN)
        d.ellipse(sc([620, 130, 880, 390]), fill=SUN, outline=(200, 150, 0), width=10 * k); d.ellipse(sc([660, 170, 840, 350]), outline=(200, 150, 0), width=8 * k)
        d.line(sc([740, 200, 740, 320]), fill=(200, 150, 0), width=14 * k); d.arc(sc([700, 205, 780, 265]), 180, 360, fill=(200, 150, 0), width=12 * k)
        sparkles(d, GREEN, 6, sc((600, 90, 940, 420)), 5)
    elif name == 'off':
        mascot(d, 330 * k, 270 * k, 150 * k, 'sad', MUTE)
        d.rounded_rectangle(sc([640, 170, 900, 350]), 30 * k, fill=(60, 70, 92), outline=BAD, width=10 * k); d.line(sc([690, 220, 850, 300]), fill=BAD, width=14 * k); d.line(sc([850, 220, 690, 300]), fill=BAD, width=14 * k)
    elif name == 'hi':
        mascot(d, 330 * k, 270 * k, 150 * k, 'happy', GREEN); rocket(d, 760 * k, 250 * k, SKY); sparkles(d, SUN, 8, sc((100, 80, 940, 430)), 7)
    return im.resize((W, H), Image.LANCZOS)

def png(name):
    if name not in NAMES: return None
    if name not in _cache:
        b = io.BytesIO(); scene(name).save(b, 'PNG', optimize=True); _cache[name] = b.getvalue()
    return _cache[name]
