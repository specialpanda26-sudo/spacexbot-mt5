"""Checks Rk1: the welcome rocket cartoon is repainted. Plain python. Run: python tests/test_rk1.py"""
import os, re, sys
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
a = S.find('/* rk1: repainted welcome rocket'); b = S.find("IL2.rs=IL2.rocket.replace('class=\"ill2\"','class=\"ill2 sm\"');", a) if a > -1 else -1
blk = S[a:b] if b > -1 else ''
T('the rk1 block exists once', S.count('/* rk1: repainted welcome rocket') == 1)
T('it sits after the old IL2 list and before IL2.rs is made (so the small rocket is repainted too)', S.find('rocket:il2(') < a < b)
T('palette: bright fills with a darker shade each, violet outline', all(x in blk for x in ('#5BE38E', '#2FB864', '#56B6FF', '#FFD43B', '#FF6B72', '#7F61F5')))
T('colors are shifted off the outline (offset layer) and the shade sits under it', 'translate(3.5 -3.5)' in blk and "c[m==='h'?1:0]" in blk)
T('flame keeps class fl (animated) and both sparkles keep class sp', 'class="fl"' in blk and blk.count('class="sp"') == 2)
T('the character is drawn too (body, head, cap) and smiles', blk.count("'M30 118C26") == 1 and 'M60 47q6 5 12 0' in blk)
T('old rocket and the other cartoons are untouched in the file', "rocket:il2('<g transform=\"translate(24 16)\">" in S and 'mail:il2(' in S and 'lock:il2(' in S)
T('output is a closed svg with the ill2 class and the same size as the old one', "return '<svg class=\"ill2\" viewBox=\"0 0 240 170\"" in blk and "</svg>'})();" in blk)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
