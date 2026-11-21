"""Draws the three animated cartoons used in the sign-in emails: static/email/signin.gif, verify.gif, reset.gif (480x270, loops forever).
Needs Pillow (already in requirements.txt). Run from the repo root: python tools/make_email_gifs.py"""
import math, os
from PIL import Image, ImageDraw

W, H, S, N, MS = 480, 270, 2, 16, 110
BG, GLOW, GREEN, SKIN, HAIR = (16, 21, 30), (26, 35, 51), (27, 154, 71), (243, 201, 160), (29, 29, 32)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'email')

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def person(d, t, i, reach):
    b = 5 * math.sin(2 * math.pi * i / N)
    P = lambda *a: [v * S for v in a]
    d.ellipse(P(88, 188 + b, 212, 330), fill=GREEN)                                     # body
    d.line(P(196, 212 + b, 196 + reach * 62, 196 + b - reach * 18), fill=SKIN, width=15 * S, joint='curve')   # arm
    d.ellipse(P(196 + reach * 62 - 9, 187 + b - reach * 18, 196 + reach * 62 + 9, 205 + b - reach * 18), fill=SKIN)
    d.rectangle(P(138, 160 + b, 162, 192 + b), fill=SKIN)                               # neck
    d.ellipse(P(108, 80 + b, 192, 168 + b), fill=SKIN)                                  # head
    d.pieslice(P(104, 74 + b, 196, 166 + b), 180, 360, fill=HAIR)                       # hair
    d.ellipse(P(100, 100 + b, 116, 124 + b), fill=HAIR); d.ellipse(P(184, 100 + b, 200, 124 + b), fill=HAIR)
    if i == N - 3: d.line(P(130, 130 + b, 142, 130 + b), fill=HAIR, width=3 * S); d.line(P(158, 130 + b, 170, 130 + b), fill=HAIR, width=3 * S)
    else: d.ellipse(P(130, 124 + b, 141, 137 + b), fill=HAIR); d.ellipse(P(159, 124 + b, 170, 137 + b), fill=HAIR)
    d.arc(P(135, 132 + b, 165, 158 + b), 25, 155, fill=HAIR, width=3 * S)               # smile

def check(d, cx, cy, r, k):
    r = r * ease(k)
    if r < 2: return
    P = lambda *a: [v * S for v in a]
    d.ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=GREEN)
    d.line(P(cx - r * .45, cy, cx - r * .1, cy + r * .35, cx + r * .5, cy - r * .35), fill=(255, 255, 255), width=max(2, int(r * .22 * S)), joint='curve')

def scene(name, i):
    t = i / (N - 1); img = Image.new('RGB', (W * S, H * S), BG); d = ImageDraw.Draw(img); P = lambda *a: [v * S for v in a]
    d.ellipse(P(250, 20, 450, 250), fill=GLOW)
    for n, (x, y) in enumerate([(40, 40), (90, 220), (455, 40), (230, 30), (440, 235), (20, 150)]):
        r = 1.5 + (1 if (i + n * 3) % 8 < 2 else 0); d.ellipse(P(x - r, y - r, x + r, y + r), fill=(120, 140, 175))
    person(d, t, i, ease(t * 3))
    if name == 'signin':
        d.rounded_rectangle(P(310, 50, 390, 230), radius=16 * S, fill=(30, 38, 56), outline=(95, 110, 145), width=3 * S)
        d.rounded_rectangle(P(318, 64, 382, 216), radius=8 * S, fill=(14, 19, 29))
        k = min(6, int(t * 9))
        for n in range(6):
            x = 327 + n * 11.2
            if n < k: d.ellipse(P(x - 4, 136, x + 4, 144), fill=GREEN)
            else: d.ellipse(P(x - 4, 136, x + 4, 144), outline=(95, 110, 145), width=S)
        check(d, 350, 100, 20, (t - .7) * 4)
    elif name == 'verify':
        o = ease(t * 2)
        d.rectangle(P(290, 112, 410, 200), fill=(205, 214, 235))
        d.rectangle(P(304, 118 - o * 46, 396, 190 - o * 46), fill=(255, 255, 255))
        for n in range(3): d.line(P(316, 134 - o * 46 + n * 14, 384 - n * 20, 134 - o * 46 + n * 14), fill=(190, 198, 220), width=3 * S)
        d.polygon(P(290, 200, 350, 150, 410, 200), fill=(232, 238, 252)); d.polygon(P(290, 112, 290, 200, 350, 156), fill=(222, 229, 247)); d.polygon(P(410, 112, 410, 200, 350, 156), fill=(222, 229, 247))
        d.polygon(P(290, 112, 350, 160 - o * 104, 410, 112), fill=(196, 206, 230) if o > .5 else (240, 244, 255))
        check(d, 404, 104, 20, (t - .55) * 3)
    else:
        up = ease((t - .15) * 2) * 30
        d.arc(P(324, 68 - up, 376, 160 - up), 180, 360, fill=(215, 222, 238), width=10 * S)
        d.line(P(325, 114 - up, 325, 134), fill=(215, 222, 238), width=10 * S)
        if up < 1: d.line(P(375, 114, 375, 134), fill=(215, 222, 238), width=10 * S)
        d.rounded_rectangle(P(308, 130, 392, 214), radius=14 * S, fill=(255, 196, 60))
        d.ellipse(P(342, 156, 358, 172), fill=(60, 45, 20)); d.polygon(P(347, 168, 353, 168, 356, 192, 344, 192), fill=(60, 45, 20))
        check(d, 398, 126, 18, (t - .6) * 3)
    return img.resize((W, H), Image.LANCZOS)

def main():
    os.makedirs(OUT, exist_ok=True)
    for name in ('signin', 'verify', 'reset'):
        fr = [scene(name, i).quantize(colors=48, method=Image.Quantize.MEDIANCUT) for i in range(N)]
        p = os.path.join(OUT, name + '.gif')
        fr[0].save(p, save_all=True, append_images=fr[1:], duration=MS, loop=0, optimize=True, disposal=1)
        print(name + '.gif', os.path.getsize(p) // 1024, 'KB')

if __name__ == '__main__': main()
