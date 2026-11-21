"""Section 6 (motion for the site cartoons): static/index.html.
1) The blanket "calm" block (it froze every cartoon for everybody and forced animation-iteration-count:1 everywhere) now sits inside
   @media (prefers-reduced-motion:reduce): only people who asked for less motion get the still pictures. Everybody else gets the site's own
   motion back (flames, sparkles, floating cartoons, confetti, ticks). The non-motion rules in the same block stay for everyone.
2) The welcome rocket is no longer a <use> of a symbol (its parts could not move): it is the inline IL2 rocket with its flame and sparkles.
   IL2 is shared as window.IL2 for this. The closing-band rocket and the other symbol pictures are not touched (next sections)."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
edit(P, r'''IL2.rs=IL2.rocket.replace('class="ill2"','class="ill2 sm"');''',
 r'''IL2.rs=IL2.rocket.replace('class="ill2"','class="ill2 sm"');window.IL2=IL2;''', 'window.IL2=IL2')
edit(P, r'''add(".hero .stage","rocket","hero-ill");''',
 r'''(function(){var h=$(".hero .stage");if(!h||h.querySelector(".hero-ill"))return;if(window.IL2&&IL2.rocket)h.insertAdjacentHTML("beforeend",IL2.rocket.replace('class="ill2"','class="ill2 hero-ill"'));else add(".hero .stage","rocket","hero-ill")})();''', 'class="ill2 hero-ill"')
edit(P, '''/* calm: no decorative motion */
.buddy,.buddy .eye,.hero-ill,''', '''/* hero6: the welcome rocket is the inline IL2 rocket (flame and sparkles move whenever motion is allowed) */
.ill2.hero-ill{max-width:none;margin:0;width:176px;left:-14px;bottom:-50px}
@media(max-width:600px){.ill2.hero-ill{width:136px;left:-8px;bottom:-40px}}
/* calm: no decorative motion, only for phones set to reduce motion (Section 6) */
@media (prefers-reduced-motion:reduce){
.buddy,.buddy .eye,.hero-ill,''', 'calm: no decorative motion, only for phones')
edit(P, '''.ill2 .wv{animation:none!important;opacity:.6!important}.ill2 .cf{display:none!important}
.sbn{display:none!important}''', '''.ill2 .wv{animation:none!important;opacity:.6!important}.ill2 .cf{display:none!important}
}
.sbn{display:none!important}''', '''.ill2 .cf{display:none!important}
}
.sbn''')
edit('tests/test_buddy4.py', r"""T('the calm block is still there (only the Home cartoon was brought back)', '/* calm: no decorative motion */' in s and s.index('id="bud2"') < s.index('/* calm: no decorative motion */'))""",
 r"""T('the calm block is still there for reduce-motion phones (Section 6 made it narrow)', '/* calm: no decorative motion, only for phones' in s and s.index('id="bud2"') < s.index('/* calm: no decorative motion, only for phones'))""", 'Section 6 made it narrow')
