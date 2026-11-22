import sys, os
P = 'backend/notifart.py'
if not os.path.isfile(P): print('STOP: run this from the repo folder'); sys.exit(1)
t = open(P, encoding='utf-8', newline='').read()
if 'ART9' in t: print('already applied'); sys.exit(0)
a = t.find("CHECK, CROSS = "); b = t.find("def png(name):")
if a < 0 or b < a or t.count("def scene(name):") != 1 or t.count("def png(name):") != 1: print('STOP: cannot find the scene block exactly once'); sys.exit(1)
NEW = '''# ART9: new look. Palette = (fill, shade) pairs, same colours as the emails.
def _rgb(h): return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))
PG, PS, PU, PB, PW = [(_rgb(a), _rgb(b)) for a, b in (('#5BE38E', '#2FB864'), ('#56B6FF', '#2F86E0'), ('#FFD43B', '#F0A800'), ('#FF6B72', '#E0444F'), ('#FFFFFF', '#DCD6FF'))]
PK, OW, SH = _rgb('#7F61F5'), 4, (3.5, -3.5)
CHECK, CROSS = 'M-6 .5l4.2 4.2 8.2-9.6', 'M-5-5l10 10M5-5l-10 10'

def lay(a, shapes, t=(0, 0)):
    for step in (0, 1, 2):
        for sh in shapes:
            col = sh[-1]; tt = (t[0] + SH[0], t[1] + SH[1]) if step == 1 else t
            fill = None if step == 2 else col[1 - step]; stroke = PK if step == 2 else None
            if sh[0] == 'p': a.path(sh[1], tt, fill=fill, stroke=stroke, w=OW)
            elif sh[0] == 'r': a.rect(sh[1], sh[2], sh[3], sh[4], sh[5], tt, fill=fill, stroke=stroke, sw=OW)
            elif sh[0] == 'e': a.ell(sh[1], sh[2], sh[3], sh[4], t=tt, fill=fill, stroke=stroke, sw=OW)
            else: a.circ(sh[1], sh[2], sh[3], t=tt, fill=fill, stroke=stroke, sw=OW)

def line(a, d, t=(0, 0), col=PK, w=OW): a.path(d, t, stroke=col, w=w)
def spark(a, x, y): line(a, 'M%d %dv10M%d %dh10' % (x, y, x - 5, y + 5), col=PU[0], w=3)

def person(a):
    t = (112, 40)
    line(a, 'M114 146c-14 4-26 2-38-4')
    lay(a, [('p', 'M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18', PS), ('p', 'M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z', PW),
            ('p', 'M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z', PU)], t)
    line(a, 'M60 47q6 5 12 0', t, w=3.5)

def badge(a, mark, col, x=80, y=46):
    lay(a, [('c', 0, 0, 14, col)], (x, y)); line(a, mark, (x, y), col=(255, 255, 255), w=3.5)

def scene(name):
    a = Art(2.62)
    if name in ('win', 'loss', 'even'):
        t = (18, 44); lay(a, [('e', 30, cy, 28, 9, PU) for cy in (48, 36, 24)], t); line(a, 'M30 20v8', t, w=3.5)
        if name == 'win':
            badge(a, CHECK, PG)
            for x, y, w_, col, rd in ((20, 6, 7, PG, 0), (58, 0, 6, PS, 0), (96, 8, 4, PU, 1), (128, 2, 7, PB, 0), (166, 10, 4, PG, 1), (196, 4, 6, PU, 0)):
                lay(a, [('c', x, y, w_, col) if rd else ('r', x, y, w_, w_, 2, col)])
            spark(a, 184, 40)
        elif name == 'loss': badge(a, CROSS, PB)
        else: badge(a, 'M-6 0h12', PS)
    elif name == 'risk':
        t = (22, 24); lay(a, [('p', 'M32 0l32 11v27c0 23-15 38-32 46C15 76 0 61 0 38V11z', PU)], t); lay(a, [('c', 32, 36, 8, PW)], t); line(a, 'M32 44v13', t, w=3.5)
    elif name == 'news':
        t = (22, 22); lay(a, [('c', 34, 34, 30, PW)], t); line(a, 'M34 16v18l12 8', t, w=3.5)
    elif name == 'bill':
        t = (20, 24); lay(a, [('r', 0, 0, 66, 88, 9, PW)], t)
        for d in ('M14 24h38', 'M14 40h38', 'M14 56h24'): line(a, d, t, w=3.5)
        lay(a, [('c', 48, 72, 10, PG)], t); line(a, 'M43 72l3.5 3.5 6.5-7.5', t, col=(255, 255, 255), w=3)
    elif name == 'off':
        line(a, 'M16 70q36-34 72 0M30 84q22-20 44 0M44 98q8-8 16 0'); lay(a, [('c', 52, 110, 4, PW)]); line(a, 'M22 28L84 124', col=PB[0], w=5)
    elif name == 'hi':
        t = (24, 16); lay(a, [('p', 'M24 56q6 14 12 0z', PU)], t)
        lay(a, [('p', 'M30 0c14 10 18 30 12 52H18C12 30 16 10 30 0z', PW), ('p', 'M30 0C38 5 42 10 42 16H18C18 10 22 5 30 0z', PB),
                ('p', 'M18 40L8 54l12-4z', PG), ('p', 'M42 40l10 14-12-4z', PG), ('c', 30, 24, 8, PS)], t)
        spark(a, 92, 24); spark(a, 12, 100)
    person(a)
    return a.done(name)

'''
t = t[:a] + NEW + t[b:]
open(P, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
