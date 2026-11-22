"""Checks Nav1: gradient-filled active tab icon (no square) and the in-app banner. Plain python. Run: python tests/test_nav1.py"""
import os, re, sys
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
a = S.find('<style id="nav1">'); b = S.find('</style>', a) if a > -1 else -1; css = S[a:b] if a > -1 else ''
j = S.find('window.sxBanner=', b); js = S[j:S.find('</script>', j)] if j > -1 else ''
T('the nav1 block exists once', S.count('<style id="nav1">') == 1 and S.count('window.sxBanner=') == 1)
T('gradient uses userSpaceOnUse (line icons have no width or height)', 'id="sxNavG" gradientUnits="userSpaceOnUse"' in S and S.count('<stop ') >= 3 and S.find('id="sxNavG"') < a)
T('active tab icon keeps its lines: no fill, line stroked with the gradient, Bot logo left alone', 'svg:not(.mk){fill:none;stroke:url(#sxNavG);stroke-width:2.6}' in css and 'fill:url(#sxNavG)' not in css)
T('phone: the square highlight is gone', '@media (max-width:899px){.nav button[aria-current="page"]{background:none}}' in css)
T('the lines draw themselves in when a tab is tapped (and not for reduce-motion phones)', '@keyframes sxNavDraw{from{stroke-dashoffset:80}to{stroke-dashoffset:0}}' in css and 'stroke-dasharray:80;animation:sxNavDraw' in css and 'reduce){.nav button[aria-current="page"] svg:not(.mk) *{animation:none}' in css)
T('nav1 comes after the old nav rules so it wins', a > S.find('.nav button[aria-current="page"]{color:var(--green);background:var(--green-soft)}') > -1)
T('banner has the site look (dark card, rainbow strip, chunky shadow, Nunito font)', all(x in css for x in ('#0C1B33', '#E5484D', '0 4px 0 rgba(0,0,0,.35)', 'var(--font)')))
T('banner sits under the phone notch and above the toast', 'env(safe-area-inset-top' in css and 'z-index:60' in css)
T('banner text is set with textContent (no HTML injection)', 'querySelector("b").textContent=t' in js and 'innerHTML=t' not in js and 'innerHTML=x' not in js)
T('banner can be dismissed (x button, swipe up, auto after 6s) and can open a tab', 'clientY-y0<-30' in js and 'tm=setTimeout(hide,o.ms>0?o.ms:6000)' in js and '.nav [data-go=' in js)
T('banner respects reduced motion', 'prefers-reduced-motion:reduce){.sxbn{transition:none}}' in css)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
