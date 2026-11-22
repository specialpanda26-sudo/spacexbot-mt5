"""Nav1: static/index.html. 1) Active tab: no square highlight, the icon itself is filled with a green gradient.
2) In-app notification banner window.sxBanner({title,text,kind,go,ms}): site look (dark card, rainbow top strip, chunky shadow, rocket tile)."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
BLOCK = r'''<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><linearGradient id="sxNavG" gradientUnits="userSpaceOnUse" x1="3" y1="2" x2="21" y2="22"><stop offset="0" stop-color="#A6F5BC"/><stop offset=".5" stop-color="#3CCB68"/><stop offset="1" stop-color="#13803B"/></linearGradient></defs></svg>
<style id="nav1">
/* nav1: active tab icon is filled with a green gradient, no square behind it */
.nav button[aria-current="page"]{color:var(--green)}
@media (max-width:899px){.nav button[aria-current="page"]{background:none}}
.nav button[aria-current="page"] svg:not(.mk){fill:url(#sxNavG);stroke:url(#sxNavG)}
.nav button[data-go="market"][aria-current="page"] svg,.nav button[data-go="trades"][aria-current="page"] svg{fill:none;stroke-width:2.9}
/* nav1: in-app notification banner, same look as the Home card */
.sxbn{position:fixed;left:50%;top:calc(10px + env(safe-area-inset-top,0px));width:min(520px,calc(100% - 24px));z-index:60;display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;padding:14px 10px 14px 14px;border-radius:20px;border:2px solid #303A52;color:#EAF1FF;font-family:var(--font);background:linear-gradient(90deg,#E5484D,#F5B400 50%,#3CCB68) top/100% 3px no-repeat,linear-gradient(135deg,#0C1B33,#0E1422);box-shadow:0 4px 0 rgba(0,0,0,.35),0 18px 40px rgba(0,0,0,.35);transform:translate(-50%,-150%);opacity:0;pointer-events:none;transition:transform .45s var(--spring),opacity .25s;touch-action:pan-x}
.sxbn.on{transform:translate(-50%,0);opacity:1;pointer-events:auto}
.sxbn .ic{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;background:#16304D}
.sxbn.k-good .ic{background:#143824}.sxbn.k-warn .ic{background:#3E3210}.sxbn.k-bad .ic{background:#43202A}
.sxbn .ic svg{width:28px;height:28px}
.sxbn b{display:block;font-size:15px;font-weight:900;letter-spacing:-.01em}
.sxbn p{margin:2px 0 0;font-size:13px;font-weight:700;color:#9AA5BF;line-height:1.3}
.sxbn .x{border:0;background:none;color:#9AA5BF;font:900 22px/1 var(--font);width:34px;height:34px;border-radius:10px}
@media (prefers-reduced-motion:reduce){.sxbn{transition:none}}
</style>
<script>
/* nav1: window.sxBanner({title,text,kind:"info|good|warn|bad",go:"home|market|bot|trades|connect",ms}) */
(function(){var el,tm,y0=0;
function hide(){clearTimeout(tm);if(el)el.classList.remove("on")}
window.sxBanner=function(o){o=o||{};var t=String(o.title||""),x=String(o.text||"");if(!t&&!x)return;
 if(!el){el=document.createElement("div");el.setAttribute("role","status");el.setAttribute("aria-live","polite");
  el.innerHTML='<span class="ic"><svg class="mk" aria-hidden="true"><use href="#mk"/></svg></span><div><b></b><p></p></div><button class="x" type="button" aria-label="Dismiss">\u00d7</button>';
  document.body.appendChild(el);
  el.addEventListener("click",function(e){var g=el.dataset.go;hide();if(e.target.closest(".x")||!g)return;var n=document.querySelector('.nav [data-go="'+g+'"]');if(n)n.click()});
  el.addEventListener("touchstart",function(e){y0=e.touches[0].clientY},{passive:true});
  el.addEventListener("touchend",function(e){if(e.changedTouches[0].clientY-y0<-30)hide()},{passive:true})}
 el.className="sxbn k-"+(/^(good|warn|bad)$/.test(o.kind)?o.kind:"info");el.dataset.go=o.go||"";
 el.querySelector("b").textContent=t;el.querySelector("p").textContent=x;el.querySelector("p").hidden=!x;
 void el.offsetWidth;el.classList.add("on");clearTimeout(tm);tm=setTimeout(hide,o.ms>0?o.ms:6000)};
window.sxBannerHide=hide})();
</script>
'''
edit(P, '<script src="/static/prefs_ui.js"></script>', BLOCK + '<script src="/static/prefs_ui.js"></script>', 'id="nav1"')
