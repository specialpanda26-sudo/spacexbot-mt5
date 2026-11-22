"""Nav2: static/index.html + tests/test_nav1.py. Active tab icons keep their lines (no fill): the lines turn green (gradient) and draw themselves in when the tab is tapped."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
edit(P, '''.nav button[aria-current="page"] svg:not(.mk){fill:url(#sxNavG);stroke:url(#sxNavG)}
.nav button[data-go="market"][aria-current="page"] svg,.nav button[data-go="trades"][aria-current="page"] svg{fill:none;stroke-width:2.9}
''', '''.nav button[aria-current="page"] svg:not(.mk){fill:none;stroke:url(#sxNavG);stroke-width:2.6}
.nav button[aria-current="page"] svg:not(.mk) *{stroke-dasharray:80;animation:sxNavDraw .7s var(--ease) both}
@keyframes sxNavDraw{from{stroke-dashoffset:80}to{stroke-dashoffset:0}}
@media (prefers-reduced-motion:reduce){.nav button[aria-current="page"] svg:not(.mk) *{animation:none}}
''', 'sxNavDraw')
T = 'tests/test_nav1.py'
edit(T, """T('active tab icon is filled and stroked with the gradient, Bot logo left alone', 'svg:not(.mk){fill:url(#sxNavG);stroke:url(#sxNavG)}' in css)""",
 """T('active tab icon keeps its lines: no fill, line stroked with the gradient, Bot logo left alone', 'svg:not(.mk){fill:none;stroke:url(#sxNavG);stroke-width:2.6}' in css and 'fill:url(#sxNavG)' not in css)""", 'keeps its lines: no fill')
edit(T, """T('open-line icons (Market, Trades) stay lines, not filled shapes', '[data-go="market"][aria-current="page"] svg' in css and '[data-go="trades"][aria-current="page"] svg' in css and 'fill:none;stroke-width:2.9' in css)""",
 """T('the lines draw themselves in when a tab is tapped (and not for reduce-motion phones)', '@keyframes sxNavDraw{from{stroke-dashoffset:80}to{stroke-dashoffset:0}}' in css and 'stroke-dasharray:80;animation:sxNavDraw' in css and 'reduce){.nav button[aria-current="page"] svg:not(.mk) *{animation:none}' in css)""", 'the lines draw themselves')
