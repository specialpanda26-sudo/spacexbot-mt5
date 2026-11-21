"""Checks Section 6: the cartoons move for everybody except people who asked for reduced motion, and the welcome rocket is the inline IL2 rocket
(flame + sparkles that can move) instead of a <use> of a symbol. Plain python. Run: python tests/test_motion6.py"""
import os, re, sys
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
MARK = '/* calm: no decorative motion, only for phones set to reduce motion (Section 6) */'
a = S.find(MARK)
end = S.find('</style>', a) if a > -1 else -1
blk = S[a:end] if a > -1 else ''
m = re.search(r'@media \(prefers-reduced-motion:reduce\)\{', blk)
depth = 0; j = 0
if m:
    for j in range(m.end() - 1, len(blk)):
        depth += (blk[j] == '{') - (blk[j] == '}')
        if depth == 0: break
before = blk[:m.start()] if m else blk
inside = blk[m.start():j + 1] if m else ''
after = blk[j + 1:] if m else ''
MOTION = ['animation:none!important', 'animation-iteration-count:1!important', 'stroke-dashoffset:0!important', '.ill2 .cf{display:none!important}']
T('the calm rules sit inside @media (prefers-reduced-motion:reduce)', all(x in inside for x in MOTION))
T('nothing that stops motion is left outside that media block (no animation, iteration count, confetti rule)', not any(x in before + after for x in ('animation:none', 'animation-iteration-count', 'transition:none!important;opacity', '.cf{display:none')))
T('the blanket one-iteration rule exists once and only inside the media block', S.count('*,*:before,*:after{animation-iteration-count:1!important}') == 1 and '*,*:before,*:after{animation-iteration-count:1!important}' in inside)
T('the non-motion rules of the old block still apply to everybody (.sbn, .buddy-card)', '.sbn{display:none!important}' in after and '.buddy-card{' in after)
T('the Home cartoon style (bud2) still comes before the calm block', S.find('id="bud2"') > -1 and S.find('id="bud2"') < a)
T('IL2 is shared as window.IL2 and that happens before the page script that builds the hero', 'window.IL2=IL2' in S and S.find('window.IL2=IL2') < S.find('class="ill2 hero-ill"'))
T('the welcome rocket is built from IL2.rocket (inline), the symbol is only the fallback', "IL2.rocket.replace('class=\"ill2\"','class=\"ill2 hero-ill\"')" in S and 'if(window.IL2&&IL2.rocket)' in S)
k = S.find('rocket:il2('); k2 = S.find('lock:il2(', k); rk = S[k:k2]
T('the IL2 rocket has a flame (.fl) and sparkles (.sp) that the site CSS animates', 'class="fl"' in rk and rk.count('class="sp"') >= 2 and '.ill2 .fl{' in S and '.ill2 .sp{' in S and 'animation:sxfm' in S and 'animation:sxsp' in S)
T('the hero rocket has its own size rule so it fits next to the phone', '.ill2.hero-ill{max-width:none;margin:0;' in S)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
