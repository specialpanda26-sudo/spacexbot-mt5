"""Section 4 (home cartoon): the Home screen cartoon (candles + sparkle + the dark-haired character) moves again.
The 'calm' style block at the end of static/index.html switched its animation off for everyone and forces other animations to play once.
This adds a small style block (id bud2) and three class names in the cartoon's markup: candles breathe, the sparkle twinkles, the character bobs.
It plays only on phones that did NOT ask to reduce motion. The calm block is left as it is."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
edit(P, '<rect x="10" y="60" width="20" height="36" rx="4" style="fill:var(--green);stroke:none"/>', '<rect class="bk k1" x="10" y="60" width="20" height="36" rx="4" style="fill:var(--green);stroke:none"/>', 'class="bk k1"')
edit(P, '<rect x="40" y="36" width="20" height="40" rx="4" style="fill:var(--berry);stroke:none"/>', '<rect class="bk k2" x="40" y="36" width="20" height="40" rx="4" style="fill:var(--berry);stroke:none"/>', 'class="bk k2"')
edit(P, '<rect x="70" y="68" width="20" height="36" rx="4" style="fill:var(--green);stroke:none"/>', '<rect class="bk k3" x="70" y="68" width="20" height="36" rx="4" style="fill:var(--green);stroke:none"/>', 'class="bk k3"')
edit(P, '<path d="M200 20v12M194 26h12" style="stroke:var(--green)"/><path d="M114 146c-14 4-26 2-38-4"/><g transform="translate(112 40)">',
        '<path class="bs" d="M200 20v12M194 26h12" style="stroke:var(--green)"/><g class="bd"><path d="M114 146c-14 4-26 2-38-4"/><g transform="translate(112 40)">', '<g class="bd"><path d="M114 146')
edit(P, '<path d="M60 47q6 5 12 0"/></g></svg></div>', '<path d="M60 47q6 5 12 0"/></g></g></svg></div>', '<path d="M60 47q6 5 12 0"/></g></g></svg></div>')
edit(P, '</script><style>\n/* calm: no decorative motion */', '''</script><style id="bud2">
/* bud2: the Home cartoon moves (candles breathe, sparkle twinkles, character bobs). Not on phones set to reduce motion. */
@media (prefers-reduced-motion:no-preference){
.buddy .bk,.buddy .bs,.buddy .bd{transform-box:fill-box;animation-iteration-count:infinite!important;animation-timing-function:ease-in-out!important}
.buddy .bk{transform-origin:50% 100%;animation-name:sxbc!important;animation-duration:2.6s!important}
.buddy .k2{animation-delay:-.9s!important}.buddy .k3{animation-delay:-1.7s!important}
.buddy .bs{transform-origin:50% 50%;animation-name:sxbt!important;animation-duration:1.8s!important}
.buddy .bd{animation-name:sxbb!important;animation-duration:3.4s!important}
@keyframes sxbc{0%,100%{transform:scaleY(.8)}50%{transform:scaleY(1.18)}}
@keyframes sxbt{0%,100%{opacity:.25;transform:scale(.6)}50%{opacity:1;transform:scale(1.2)}}
@keyframes sxbb{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
}
</style><style>
/* calm: no decorative motion */''', 'id="bud2"')
