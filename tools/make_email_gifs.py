"""Draws the five animated cartoons used in the emails: static/email/signin.gif, verify.gif, reset.gif, alert.gif, receipt.gif (480x240, loops forever).
They use the SAME look as the website cartoons (Rk1-Rk3): bright flat fills, a darker shade peeking out, the fill shifted 3.5 units off a thick violet outline,
yellow sparkle ticks and the new character (blue body, white head, yellow hair). Same props (phone, envelope, lock, rocket, receipt, check badge). Needs Pillow. Run from the repo root: python tools/make_email_gifs.py"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from PIL import Image
from backend.notifart import Art

N, MS, HOLD = 16, 110, 900                      # frames, ms per frame, ms the last frame stays
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'email')
POP = {9: .45, 10: .85, 11: 1.15, 12: 1.0}      # check badge pops in from frame 9 and stays

def pop(i): return POP.get(i, 1.0 if i > 12 else 0.0)

def rgb(h): return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))
G, S, U, B, W = [(rgb(a), rgb(b)) for a, b in (('#5BE38E', '#2FB864'), ('#56B6FF', '#2F86E0'), ('#FFD43B', '#F0A800'), ('#FF6B72', '#E0444F'), ('#FFFFFF', '#DCD6FF'))]
K, OW, SH = rgb('#7F61F5'), 4, (3.5, -3.5)       # violet outline, outline width, how far the fill is shifted

def lay(a, shapes, t=(0, 0)):
    """shapes: ('p', pathdata, col) | ('r', x, y, w, h, rx, col) | ('c', cx, cy, r, col). Pass 1 shade, pass 2 shifted fill, pass 3 outline (like the website)."""
    for step in (0, 1, 2):
        for sh in shapes:
            col = sh[-1]; tt = (t[0] + SH[0], t[1] + SH[1]) if step == 1 else t
            fill = None if step == 2 else col[1 - step]; stroke = K if step == 2 else None          # ART9b
            if sh[0] == 'p': a.path(sh[1], tt, fill=fill, stroke=stroke, w=OW)
            elif sh[0] == 'r': a.rect(sh[1], sh[2], sh[3], sh[4], sh[5], tt, fill=fill, stroke=stroke, sw=OW)
            else: a.circ(sh[1], sh[2], sh[3], t=tt, fill=fill, stroke=stroke, sw=OW)

def line(a, d, t=(0, 0), col=K, w=OW): a.path(d, t, stroke=col, w=w)

def character(a, b):
    t = (112, 40 + b)
    line(a, 'M114 146c-14 4-26 2-38-4', (0, b))
    lay(a, [('p', 'M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18', S),
            ('p', 'M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z', W),
            ('p', 'M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z', U)], t)
    line(a, 'M60 47q6 5 12 0', t, w=3.5)

def spark(a, i, x, y, k):
    if (i + k * 3) % 8 < 5: line(a, 'M%d %dv10M%d %dh10' % (x, y, x - 5, y + 5), col=U[0], w=3)

def badge(a, i, cx, cy, r=14):
    k = pop(i)
    if k <= 0: return
    lay(a, [('c', 0, 0, r * k, G)], (cx, cy))
    if k >= 1: line(a, 'M-6 .5l4.2 4.2 8.2-9.6', (cx, cy), col=(255, 255, 255), w=3.5)

def scene(name, i):
    a = Art(2.62); s = math.sin(2 * math.pi * i / N); b, f = 2.4 * s, -2.4 * math.sin(2 * math.pi * i / N + .9)
    if name == 'signin':                                            # phone (the app asks for the code)
        t = (14, 22 + f); lay(a, [('r', 0, 0, 58, 96, 11, W), ('r', 9, 24, 40, 28, 7, S)], t); line(a, 'M22 10h14', t); line(a, 'm12 30 17 11 17-11', t, col=(255, 255, 255), w=3)
        badge(a, i, 66, 34 + f); spark(a, i, 92, 24, 0); spark(a, i, 12, 100, 1)
    elif name == 'verify':                                          # envelope (confirm your email)
        t = (14, 28 + f); lay(a, [('r', 0, 0, 76, 52, 8, S), ('p', 'M4 10L38 34L72 10z', W)], t)
        badge(a, i, 84, 28 + f); spark(a, i, 100, 80, 0); spark(a, i, 8, 14, 2)
    elif name == 'reset':                                           # lock: the arm lifts, then clicks shut
        up = 7 * max(0.0, math.sin(math.pi * min(1.0, i / 9.0))) if i < 10 else 0
        t = (26, 24 + f); line(a, 'M14 30v-9c0-9 7-16 16-16c9 0 16 7 16 16v9', (26, 24 + f - up), w=5)
        lay(a, [('r', 0, 30, 60, 46, 9, U)], t); lay(a, [('c', 30, 52, 4, B)], t); line(a, 'M30 56v8', t)
        badge(a, i, 74, 34 + f); spark(a, i, 92, 30, 0); spark(a, i, 6, 96, 3)
    elif name == 'alert':                                           # rocket lifts off, flame flickers
        lift = 3 * s; t = (24, 16 + f * 1.5 - lift)
        lay(a, [('p', 'M24 56q6 %d 12 0z' % (12 + 5 * (i % 3)), U)], t)
        lay(a, [('p', 'M30 0c14 10 18 30 12 52H18C12 30 16 10 30 0z', W), ('p', 'M30 0C38 5 42 10 42 16H18C18 10 22 5 30 0z', B),
                ('p', 'M18 40L8 54l12-4z', G), ('p', 'M42 40l10 14-12-4z', G), ('c', 30, 24, 8, S)], t)
        spark(a, i, 92, 24, 0); spark(a, i, 12, 100, 2); spark(a, i, 96, 90, 4)
    elif name == 'receipt':                                         # receipt fills up, then the check pops
        t = (20, 24 + f); lay(a, [('r', 0, 0, 66, 88, 9, W)], t)
        for k, d in enumerate(('M14 24h38', 'M14 40h38', 'M14 56h24')):
            if i >= 3 + k * 2: line(a, d, t, w=3.5)
        k = pop(i)
        if k > 0:
            lay(a, [('c', 48, 72, 10 * k, G)], t)
            if k >= 1: line(a, 'M43 72l3.5 3.5 6.5-7.5', t, col=(255, 255, 255), w=3)
        spark(a, i, 96, 30, 1)
    character(a, b)
    return a.done(name).resize((480, 240), Image.LANCZOS)

def main():
    os.makedirs(OUT, exist_ok=True)
    for name in ('signin', 'verify', 'reset', 'alert', 'receipt'):
        fr = [scene(name, i).quantize(colors=64, method=Image.Quantize.MEDIANCUT) for i in range(N)]
        p = os.path.join(OUT, name + '.gif')
        fr[0].save(p, save_all=True, append_images=fr[1:], duration=[MS] * (N - 1) + [HOLD], loop=0, optimize=True, disposal=1)
        print(name + '.gif', os.path.getsize(p) // 1024, 'KB')

if __name__ == '__main__': main()
