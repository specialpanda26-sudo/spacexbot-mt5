"""Checks Rk2: the other site cartoons are repainted like the rocket and keep their animation classes. Plain python. Run: python tests/test_rk2.py"""
import os, re, sys
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
a = S.find('/* rk2: the other cartoons, repainted like the rocket */'); b = S.find('var ILM={plug', a) if a > -1 else -1
blk = S[a:b] if b > -1 else ''
KEYS = ['mail', 'wait', 'coin', 'paid', 'phone', 'ok', 'push', 'yay', 'lock', 'off', 'cx', 'doc', 'shield', 'cookie', 'sleep', 'plug']
def body(k):
    m = re.search(r'IL2\.' + k + r'=il\((.*)\);\n', blk)
    return m.group(1) if m else ''
T('the rk2 block exists once and sits before the ILM list', S.count('/* rk2: the other cartoons, repainted like the rocket */') == 1 and 0 < a < b)
T('it comes after every old cartoon is defined (so it replaces them)', S.find('IL2.plug=il2(') < a and S.find('IL2.cx=il2(') < a)
T('all 16 cartoons are redefined with the new il() wrapper', all(('IL2.' + k + '=il(') in blk for k in KEYS) and len(KEYS) == 16)
T('same palette and violet outline as the rocket', all(x in blk for x in ('#5BE38E', '#2FB864', '#56B6FF', '#FFD43B', '#FF6B72', '#7F61F5')) and 'translate(3.5 -3.5)' in blk)
T('the check keeps class ckd, the lock shackle keeps lk', "'ckd'" in body('ok') and "'lk'" in body('lock'))
T('push keeps its banner, 4 pins and 3 waves', 'class="bn"' in body('push') and 'class="pin"' in body('push') and body('push').count('class="wv"') == 3)
T('yay keeps its confetti (4 squares from the list plus 2 dots = 6 pieces)', body('yay').count('class="cf"') == 3 and body('yay').count('],[') == 3)
T('shield keeps .sh, sleep keeps both .zz, plug keeps .pg, off keeps .wf and .sl', 'class="sh"' in body('shield') and body('sleep').count("'zz") == 2 and 'class="pg"' in body('plug') and 'class="wf"' in body('off') and "'sl'" in body('off'))
T('no old black or dark fill is used (the site CSS would recolor it)', '#000' not in blk and '#26262a' not in blk and '#1d1d20' not in blk)
T('the old cartoon definitions and the rocket from Rk1 are untouched', S.count("mail:il2(") == 1 and S.count('IL2.doc=il2(') == 1 and S.count('/* rk1: repainted welcome rocket') == 1)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
