"""Rk3: static/index.html + docs/HANDOFF.md. (1) The Home buddy card cartoon (candles, sparkle, character) is repainted like the rocket: bright flat fills, darker shade, fills shifted off a thick violet outline, same new character. Its motion hooks (bk k1-k3, bs, bd) are kept. (2) Bug from Rk2: the Home state pictures (lock, shield, waiting, yay, sleep) lost their bob because the code looked for the tail path by its exact text; it now finds it with a pattern. (3) HANDOFF gets an entry for Rk1-Rk3. Safe to run twice."""
import re, sys
P = 'static/index.html'
G = ('#5BE38E', '#2FB864'); S = ('#56B6FF', '#2F86E0'); U = ('#FFD43B', '#F0A800'); B = ('#FF6B72', '#E0444F'); W = ('#FFFFFF', '#DCD6FF'); K = '#7F61F5'
def sh(s, m):
    c = s[-1]
    a = 'fill="none" stroke="%s" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"' % K if m == 'l' else 'fill="%s" stroke="none"' % c[1 if m == 'h' else 0]
    if s[0] == 'r': return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>' % (s[1], s[2], s[3], s[4], s[5], a)
    return '<path d="%s" %s/>' % (s[0], a)
def lay(a):
    return ''.join(sh(s, 'h') for s in a) + '<g transform="translate(3.5 -3.5)">' + ''.join(sh(s, 'f') for s in a) + '</g>' + ''.join(sh(s, 'l') for s in a)
C = [('M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18', S), ('M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z', W), ('M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z', U)]
NEW = ('<svg class="ill2 buddy cart" data-rk3="1" viewBox="0 0 240 170" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
 '<g transform="translate(8 10)"><path d="M20 40v70M50 20v80M80 50v70" stroke="%s" stroke-width="3.5"/>' % K
 + '<g class="bk k1">' + lay([('r', 10, 60, 20, 36, 4, G)]) + '</g>'
 + '<g class="bk k2">' + lay([('r', 40, 36, 20, 40, 4, B)]) + '</g>'
 + '<g class="bk k3">' + lay([('r', 70, 68, 20, 36, 4, G)]) + '</g></g>'
 + '<path class="bs" d="M200 20v12M194 26h12" stroke="%s" stroke-width="3"/>' % U[0]
 + '<g class="bd"><path d="M114 146c-14 4-26 2-38-4" stroke="%s" stroke-width="4"/>' % K
 + '<g transform="translate(112 40)">' + lay(C) + '<path d="M60 47q6 5 12 0" stroke="%s" stroke-width="3.5"/></g></g></svg>' % K)
s = open(P, encoding='utf-8').read()
rx = re.compile(r'<svg class="ill2 buddy cart".*?</svg>', re.S)
if len(rx.findall(s)) != 1: sys.exit('STOP: the Home cartoon is not in index.html exactly once')
if 'data-rk3="1"' in s: print(P, ': cartoon already ok')
else: s = rx.sub(lambda m: NEW, s, count=1); print(P, ': cartoon repainted')
OLD = ''', a = '<path d="M114 146c-14 4-26 2-38-4"/>', i = t.indexOf(a);'''
FIX = ''', i = t.search(/<path d="M114 146c-14 4-26 2-38-4"[^>]*>/);'''
if FIX in s: print(P, ': bob fix already ok')
elif s.count(OLD) != 1: sys.exit('STOP: the state picture line is not in index.html exactly once')
else: s = s.replace(OLD, FIX); print(P, ': bob fix edited')
open(P, 'w', encoding='utf-8').write(s)
H = 'docs/HANDOFF.md'; h = open(H, encoding='utf-8').read()
if '## Section Rk1-Rk3' in h: print(H, ': already ok')
else:
    h = h.rstrip('\n') + '''

## Section Rk1-Rk3 (cartoons repainted like the rocket) DONE (Nov 22)
- static/index.html only. Rk1 (apply_rk1.py): the welcome rocket IL2.rocket is repainted: bright flat fills, a darker shade peeking out, fills shifted 3.5 px off a thick violet (#7F61F5) outline, yellow ticks, new little character (blue body, white head, yellow hair). Rk2 (apply_rk2.py): the 16 other site cartoons (mail, wait, coin, paid, cx, phone, ok, push, yay, lock, off, doc, shield, cookie, sleep, plug) got the same look; their class names (ckd, lk, bn, pin, wv, cf, sh, zz, pg, wf, sl) and animations are kept. Rk3 (apply_rk3.py): the Home buddy card cartoon (candles, sparkle, character) in the same look, hooks bk k1-k3, bs, bd kept.
- Bug fixed in Rk3: after Rk2 the five Home state pictures no longer bobbed, because H7 art() looked for the tail path by its exact text; it now uses a pattern.
- tests: test_rk1.py, test_rk2.py, test_rk3.py, test_motion6.py.
- NOT done yet (next, Rk4): the notification large icon (round badge with the character's face; needs a Java change in LiveMessagingService.java and the test stub in test_push2.py, and works only where the app draws the notification, not for system-drawn pushes while the app is closed). The small status-bar icon stays a white logo silhouette (Android flattens it). Also not touched: the logo-style symbol cartoons on the legal pages and the 5 email GIFs.
'''
    open(H, 'w', encoding='utf-8').write(h); print(H, ': entry added')
