"""Draws the five animated cartoons used in the emails: static/email/signin.gif, verify.gif, reset.gif, alert.gif, receipt.gif (480x240, loops forever).
They use the SAME art as the website and the phone notifications: backend/notifart.py (dark card, thin outlines, the dark-haired character) and the same props
(phone, envelope, lock, rocket, receipt, check badge). Needs Pillow. Run from the repo root: python tools/make_email_gifs.py"""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from PIL import Image
from backend.notifart import Art, SURF2, GREEN, WHITE, HAIR_BODY, HAIR_MID, HAIR_TOP

N, MS, HOLD = 16, 110, 900                      # frames, ms per frame, ms the last frame stays
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'email')
POP = {9: .45, 10: .85, 11: 1.15, 12: 1.0}      # check badge pops in from frame 9 and stays

def pop(i): return POP.get(i, 1.0 if i > 12 else 0.0)

def character(a, b):
    t = (112, 40 + b)
    a.path('M114 146c-14 4-26 2-38-4', (0, b))
    a.path('M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18z', t, fill=HAIR_BODY)
    a.path('M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z', t, fill=HAIR_MID)
    a.path('M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z', t, fill=HAIR_TOP)
    a.path('M60 47q6 5 12 0', t)

def spark(a, i, x, y, k):
    if (i + k * 3) % 8 < 5: a.path('M%d %dv10M%d %dh10' % (x, y, x - 5, y + 5), stroke=GREEN)

def badge(a, i, cx, cy, r=14):
    k = pop(i)
    if k <= 0: return
    a.circ(cx, cy, r * k, fill=GREEN, stroke=None)
    if k >= 1: a.path('M-6 .5l4.2 4.2 8.2-9.6', (cx, cy), stroke=WHITE, w=3.2)

def scene(name, i):
    a = Art(2.62); s = math.sin(2 * math.pi * i / N); b, f = 2.4 * s, -2.4 * math.sin(2 * math.pi * i / N + .9)
    if name == 'signin':                                            # phone (the app asks for the code)
        t = (14, 22 + f); a.rect(0, 0, 58, 96, 11, t, fill=SURF2); a.path('M22 10h14', t); a.rect(9, 24, 40, 28, 7, t); a.path('m12 30 17 11 17-11', t)
        badge(a, i, 66, 34 + f); spark(a, i, 92, 24, 0); spark(a, i, 12, 100, 1)
    elif name == 'verify':                                          # envelope (confirm your email)
        t = (14, 28 + f); a.rect(0, 0, 76, 52, 8, t, fill=SURF2); a.path('m4 10 34 24 34-24', t)
        badge(a, i, 84, 28 + f); spark(a, i, 100, 80, 0); spark(a, i, 8, 14, 2)
    elif name == 'reset':                                           # lock: the arm lifts, then clicks shut
        up = 7 * max(0.0, math.sin(math.pi * min(1.0, i / 9.0))) if i < 10 else 0
        t = (26, 24 + f); a.rect(0, 30, 60, 46, 9, t, fill=SURF2); a.path('M14 30v-9c0-9 7-16 16-16c9 0 16 7 16 16v9', (26, 24 + f - up))
        a.circ(30, 52, 4, t=t); a.path('M30 56v8', t)
        badge(a, i, 74, 34 + f); spark(a, i, 92, 30, 0); spark(a, i, 6, 96, 3)
    elif name == 'alert':                                           # rocket lifts off, flame flickers
        lift = 3 * s; t = (24, 16 + f * 1.5 - lift)
        a.path('M30 0c14 10 18 30 12 52H18C12 30 16 10 30 0z', t, fill=SURF2); a.circ(30, 24, 7, t=t); a.path('M18 40l-10 14 12-4M42 40l10 14-12-4', t)
        a.path('M24 56q6 %d 12 0z' % (12 + 5 * (i % 3)), t, fill=GREEN, stroke=None)
        spark(a, i, 92, 24, 0); spark(a, i, 12, 100, 2); spark(a, i, 96, 90, 4)
    elif name == 'receipt':                                         # receipt fills up, then the check pops
        t = (20, 24 + f); a.rect(0, 0, 66, 88, 9, t, fill=SURF2)
        for k, d in enumerate(('M14 24h38', 'M14 40h38', 'M14 56h24')):
            if i >= 3 + k * 2: a.path(d, t)
        k = pop(i)
        if k > 0:
            a.circ(48, 72, 10 * k, t=t, fill=GREEN, stroke=None)
            if k >= 1: a.path('M43 72l3.5 3.5 6.5-7.5', t, stroke=WHITE, w=3)
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
