"""Checks Section 4: the Home cartoon has its motion hooks (candles, sparkle, character) and the style that animates them, only for phones that did not ask to reduce motion,
and that style beats the 'calm' block (which forces every animation to play once). Run: python tests/test_buddy4.py"""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
s = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
svg = re.search(r'<svg class="ill2 buddy cart".*?</svg>', s, re.S).group(0)
m = re.search(r'<style id="bud2">(.*?)</style>', s, re.S); css = m.group(1) if m else ''
T('the three candles have the bk class', len(re.findall(r'class="bk k[123]"', svg)) == 3)
T('the sparkle and the character have the bs and bd classes', 'class="bs"' in svg and '<g class="bd">' in svg)
T('the cartoon svg is still well formed (as many </g> as <g)', svg.count('<g') == svg.count('</g>'))
T('the motion style exists and has the 3 keyframes', bool(m) and all('@keyframes ' + k in css for k in ('sxbc', 'sxbt', 'sxbb')))
T('it only plays when the phone did not ask to reduce motion', css.count('prefers-reduced-motion:no-preference') == 1 and css.index('prefers-reduced-motion') < css.index('.buddy .bk'))
T('it loops forever and beats the calm block (iteration count is !important)', 'animation-iteration-count:infinite!important' in css)
T('each part has its own animation name', all(('animation-name:' + k + '!important') in css for k in ('sxbc', 'sxbt', 'sxbb')))
T('the calm block is still there (only the Home cartoon was brought back)', '/* calm: no decorative motion */' in s and s.index('id="bud2"') < s.index('/* calm: no decorative motion */'))
T('index.html has one Home cartoon', s.count('class="ill2 buddy cart"') == 1)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
