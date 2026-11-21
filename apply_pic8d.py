"""Section 8d: the last still pictures move and use the dark-haired character.
 - lock, moon (sleep) and shield cartoons get moving parts (shackle wiggle, floating Z's, shield breathing) + sparkles.
 - new IL2.plug cartoon (plug slides into a socket, check badge) replaces the old still "plug" symbol in "Connected in four steps".
 - closing-band rocket: it is already the inline IL2 rocket, but lost its corner place when fixArt renamed its class; put it back.
Motion only for people who did not ask for reduced motion. Only static/index.html changes. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
# 1 lock: shackle wiggles, two sparkles
edit(P, '<path d="M14 30v-9a16 16 0 0 1 32 0v9"/><circle cx="30" cy="52" r="4"/><path d="M30 56v8"/></g>\')};',
        '<path class="lk" d="M14 30v-9a16 16 0 0 1 32 0v9"/><circle cx="30" cy="52" r="4"/><path d="M30 56v8"/></g><path class="sp" d="M100 28v10M95 33h10"/><path class="sp" d="M14 104v8M10 108h8"/>\')};',
        'class="lk"')
# 2 moon: two Z's float up one after the other, two sparkles
edit(P, '<path d="M64 4h16L64 22h16M80 28h12L80 42h12"/></g>\');',
        '<path class="zz" d="M64 4h16L64 22h16"/><path class="zz z2" d="M80 28h12L80 42h12"/></g><path class="sp" d="M14 28v8M10 32h8"/><path class="sp" d="M104 108v8M100 112h8"/>\');',
        'class="zz"')
# 3 shield: breathes, two sparkles
edit(P, '<path d="M32 0l32 11v27c0 23-15 38-32 46C15 76 0 61 0 38V11z" fill="#26262a"/><circle cx="32" cy="36" r="8"/><path d="M32 44v13"/></g>\');',
        '<path class="sh" d="M32 0l32 11v27c0 23-15 38-32 46C15 76 0 61 0 38V11z" fill="#26262a"/><circle cx="32" cy="36" r="8"/><path d="M32 44v13"/></g><path class="sp" d="M100 30v10M95 35h10"/><path class="sp" d="M14 104v8M10 108h8"/>\');',
        'class="sh"')
# 4 plug cartoon + map it, so fixArt swaps the old still symbol
PLUG = ('IL2.plug=il2(\'<g transform="translate(8 44)"><rect x="58" y="10" width="36" height="56" rx="10" fill="#26262a"/>'
        '<path d="M70 30v12M82 30v12"/><g class="pg"><path d="M14 38c-9 0-12 22-6 42" style="stroke-width:4"/>'
        '<rect x="14" y="16" width="36" height="44" rx="10" fill="#26262a"/><path d="M50 28h8M50 48h8"/></g></g>'
        '\'+BD2(118,38,CK2)+\'<path class="sp" d="M78 30v10M73 35h10"/><path class="sp" d="M30 24v8M26 28h8"/>\');\n')
edit(P, 'var ILM={doc:', PLUG + 'var ILM={plug:"plug",doc:', 'IL2.plug=il2(')
# 5 style block (motion only when allowed)
CSS = '''</style><style id="p8">
/*P8-start*/
/* Section 8d: lock, moon, shield and plug cartoons move (only when the phone allows motion); the closing-band picture sits in its corner again */
.ctaband .ill2.sec2{position:absolute;right:10px;bottom:-6px;width:112px;max-width:none;margin:0}
@media(max-width:600px){.ctaband .ill2.sec2{width:96px}}
@media (prefers-reduced-motion:no-preference){
.ill2 .lk,.ill2 .zz,.ill2 .sh,.ill2 .pg{transform-box:fill-box;animation-iteration-count:infinite;animation-timing-function:ease-in-out}
.ill2 .lk{transform-origin:50% 100%;animation-name:sxlk;animation-duration:3.2s}
.ill2 .zz{animation-name:sxzz;animation-duration:3s}.ill2 .zz.z2{animation-delay:1s}
.ill2 .sh{transform-origin:50% 50%;animation-name:sxsd;animation-duration:2.8s}
.ill2 .pg{animation-name:sxpg;animation-duration:2.6s}
@keyframes sxlk{0%,55%,100%{transform:none}65%{transform:translateY(-3px) rotate(-7deg)}75%{transform:translateY(-3px) rotate(7deg)}85%{transform:none}}
@keyframes sxzz{0%{opacity:0;transform:translate(-3px,6px)}30%,65%{opacity:1;transform:none}100%{opacity:0;transform:translate(5px,-8px)}}
@keyframes sxsd{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
@keyframes sxpg{0%,100%{transform:translateX(-12px)}45%,75%{transform:none}}
}
/*P8-end*/
</style><style>
/* hero6:'''
edit(P, '</style><style>\n/* hero6:', CSS, '/*P8-start*/')
