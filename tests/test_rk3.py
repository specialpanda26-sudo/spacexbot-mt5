"""Checks Rk3: the Home buddy card cartoon is repainted like the rocket (same colours, shade, offset, violet outline, new character), keeps its motion hooks, and the Home state pictures can be wrapped for the bob again. No temp files. Run: python tests/test_rk3.py"""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
s = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
m = re.findall(r'<svg class="ill2 buddy cart".*?</svg>', s, re.S); svg = m[0] if m else ''
T('there is one Home cartoon and it is the Rk3 one', len(m) == 1 and 'data-rk3="1"' in svg)
T('it uses the rocket colours (green, red, blue, white, yellow, violet outline)', all(c in svg for c in ('#5BE38E', '#2FB864', '#FF6B72', '#E0444F', '#56B6FF', '#FFFFFF', '#FFD43B', '#7F61F5')))
T('each candle has shade, offset fill and outline (3 candles x 3 layers)', len(re.findall(r'<rect ', svg)) == 9 and svg.count('translate(3.5 -3.5)') == 4)
T('the old dark character and the old theme colours are gone', not re.search(r'#1d1d20|#26262a|#34343a|var\(--green\)|var\(--berry\)', svg))
T('motion hooks kept: bk k1 k2 k3, bs, bd', all(('class="bk k%d"' % i) in svg for i in (1, 2, 3)) and 'class="bs"' in svg and '<g class="bd">' in svg)
T('the svg is well formed (as many </g> as <g)', svg.count('<g') == svg.count('</g>'))
T('the tail path that the Home states look for is still in the picture', '<path d="M114 146c-14 4-26 2-38-4" stroke="#7F61F5" stroke-width="4"/>' in svg)
rx = re.search(r"i = t\.search\(/(.+?)/\);", s)
pat = re.compile(rx.group(1)) if rx else None
T('the state picture code finds the tail with a pattern, not the exact text', bool(pat) and 't.indexOf(a)' not in s)
T('the pattern finds the plain tail and a tail with attributes (the Rk2 pictures)', bool(pat) and bool(pat.search('<g/><path d="M114 146c-14 4-26 2-38-4"/><g/>')) and bool(pat.search('<path d="M114 146c-14 4-26 2-38-4" fill="none" stroke="#7F61F5" stroke-width="4"/>')))
T('the pattern does not match another path', bool(pat) and not pat.search('<path d="M10 10c-14 4-26 2-38-4" fill="none"/>'))
T('the Home motion style (bud2) is still there', 'id="bud2"' in s and '@keyframes sxbb' in s)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
