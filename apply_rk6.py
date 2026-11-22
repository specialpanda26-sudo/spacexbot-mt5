import sys, os, re
P, Q, H = 'backend/notifart.py', 'backend/pushcopy.py', 'docs/HANDOFF.md'
if not (os.path.isfile(P) and os.path.isfile(Q)): print('STOP: run this from the repo folder'); sys.exit(1)
t = open(P, encoding='utf-8', newline='').read()
if 'RK6' in t: print('already applied'); sys.exit(0)
a1 = "NAMES = ('win', 'loss', 'even', 'risk', 'news', 'bill', 'off', 'hi')"
a2 = "    elif name == 'hi':\n"
if t.count(a1) != 1 or t.count(a2) != 1: print('STOP: cannot find the anchors exactly once'); sys.exit(1)
t = t.replace(a1, "NAMES = ('win', 'loss', 'even', 'risk', 'news', 'bill', 'off', 'hi', 'update', 'soon', 'ended', 'linked')   # RK6: 4 new pictures")
NEW = '''    elif name == 'update':                                          # RK6: phone, download arrow, flame, sparkles (like the in-app update cartoon)
        t = (14, 22); lay(a, [('p', 'M17 98q12 18 24 0z', PU)], t)
        lay(a, [('r', 0, 0, 58, 96, 11, PW), ('r', 9, 24, 40, 28, 7, PS)], t); line(a, 'M22 10h14', t); line(a, 'M29 30v14M21 37l8 8 8-8', t, col=(255, 255, 255), w=3.5)
        spark(a, 92, 24); spark(a, 12, 100); spark(a, 96, 90)
    elif name in ('soon', 'ended'):                                 # RK6: calendar; a clock badge = plan ends soon, a cross badge = plan ended
        t = (20, 30); lay(a, [('r', 0, 6, 70, 66, 9, PW), ('r', 0, 6, 70, 20, 9, PU)], t)
        for d in ('M18 0v12', 'M52 0v12'): line(a, d, t, w=5)
        for x, y in ((16, 40), (35, 40), (54, 40), (16, 56), (35, 56)): lay(a, [('c', x, y, 3, PS)], t)
        if name == 'soon': badge(a, 'M0-6v6l5 3', PU, 70, 66)
        else: badge(a, CROSS, PB, 70, 66)
    elif name == 'linked':                                          # RK6: two chain links and a check badge (connected)
        t = (20, 36); lay(a, [('r', 0, 18, 44, 28, 14, PS), ('r', 30, 18, 44, 28, 14, PW)], t); line(a, 'M30 32h14', t, w=5)
        badge(a, CHECK, PG, 74, 18); spark(a, 96, 70); spark(a, 8, 20)
'''
t = t.replace(a2, NEW + a2)
open(P, 'w', encoding='utf-8', newline='').write(t)
M = {26: 'linked', 28: 'linked', 29: 'update', 42: 'soon', 43: 'soon', 44: 'ended'}
L = open(Q, encoding='utf-8', newline='').read().split('\n'); n = 0
for i, ln in enumerate(L):
    m = re.match(r'^ (\d+): ', ln)
    if m and int(m.group(1)) in M:
        new = re.sub(r"'(hi|bill|off)'\),?$", "'%s')," % M[int(m.group(1))], ln)
        if new != ln: L[i] = new; n += 1
if n != len(M): print('STOP: expected %d picture changes in pushcopy.py, made %d (nothing written there)' % (len(M), n)); sys.exit(1)
open(Q, 'w', encoding='utf-8', newline='').write('\n'.join(L))
if os.path.isfile(H):
    h = open(H, encoding='utf-8', newline='').read()
    h += ('\n\n## Section Rk6 (notification pictures) DONE (Nov 22)\n- backend/notifart.py already had the new look (ART9: violet outline, blue/white/yellow character); the old note "still in the old dark style" was stale. '
          'Rk6 adds 4 pictures: update, soon (plan ends), ended (plan ended), linked (connected) and maps them in backend/pushcopy.py: kind 29 update; 42 and 43 soon; 44 ended; 26 and 28 linked.\n'
          '- apply_rk6.py (idempotent), tests/test_rk6.py. The card behind the picture is still the dark navy. NOT seen on a real phone. Kinds with no picture of their own yet: session ended, server waking, something went wrong (no push kind for them).\n')
    open(H, 'w', encoding='utf-8', newline='').write(h)
print('Rk6 applied: 4 new notification pictures + 6 kinds remapped')
