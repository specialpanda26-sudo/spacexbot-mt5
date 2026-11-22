"""Nav3: static/index.html + tests/test_nav1.py. The active tab icon uses the normal site green (var(--green)) instead of the mint-to-dark-green gradient."""
import re
def rw(p, f):
    s = open(p, encoding='utf-8').read(); n = f(s)
    assert n != s, 'nothing changed in ' + p
    open(p, 'w', encoding='utf-8').write(n)
GRAD = re.compile(r'<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><linearGradient id="sxNavG".*?</svg>\n', re.S)
def page(s):
    assert len(GRAD.findall(s)) == 1
    s = GRAD.sub('', s)
    a = 'svg:not(.mk){fill:none;stroke:url(#sxNavG);stroke-width:2.6}'
    assert s.count(a) == 1
    s = s.replace(a, 'svg:not(.mk){fill:none;stroke:var(--green);stroke-width:2.6}')
    return s.replace('/* nav1: active tab icon is filled with a green gradient, no square behind it */', '/* nav1: active tab icon is the normal site green (var(--green)), no square behind it */')
rw('static/index.html', page)
def test(x):
    x = x.replace("""T('gradient uses userSpaceOnUse (line icons have no width or height)', 'id="sxNavG" gradientUnits="userSpaceOnUse"' in S and S.count('<stop ') >= 3 and S.find('id="sxNavG"') < a)""", """T('no gradient left: the active tab uses the normal site green', 'sxNavG' not in S)""")
    return x.replace("""line stroked with the gradient, Bot logo left alone', 'svg:not(.mk){fill:none;stroke:url(#sxNavG);stroke-width:2.6}' in css and 'fill:url(#sxNavG)' not in css)""", """line stroked with var(--green), Bot logo left alone', 'svg:not(.mk){fill:none;stroke:var(--green);stroke-width:2.6}' in css and 'url(#sxNavG)' not in css)""")
rw('tests/test_nav1.py', test)
print('Nav3 applied')
