"""PL7: app screen for the managed plan, on the Burst card (static/index.html only)."""
p = 'static/index.html'
s = open(p, encoding='utf-8').read()
if 'PL7-start' in s:
    print(p, 'already patched, skipping'); raise SystemExit

A1 = '<div class="bbox"><h3>1. When it starts</h3>'
A2 = 'function bswShow(j){var s=j.settings||{};'
A3 = ' bswLoad();\n /*BT1-end*/'
for a in (A1, A2, A3):
    assert s.count(a) == 1, 'anchor count %d != 1: %s' % (s.count(a), a[:50])

HTML = ('<div class="bbox" id="plnBox"><h3>Managed plan</h3>'
 '<p class="note">Pick a plan and every entry uses one 0.01 lot for each $10 of plan. A plan keeps burst on and ignores your account balance when it sizes the lot. A market whose smallest lot is bigger than the plan lot is skipped, not traded bigger.</p>'
 '<div id="plnChips" style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0">'
 + ''.join('<button type="button" class="btn" data-plan="%d" aria-pressed="false">$%d</button>' % (n, n) for n in (10, 20, 30, 40, 50, 60))
 + '<button type="button" class="btn" data-plan="0" aria-pressed="false">No plan</button></div>'
 '<div class="field"><label for="plnCustom">Bigger plan ($10 to $1000)</label>'
 '<input class="inp" id="plnCustom" type="number" inputmode="numeric" min="10" max="1000" step="10" placeholder="For example 100">'
 '<small class="hint">Rounded down to a whole $10. $100 is 0.10 lot per entry, $1000 is 1.00.</small></div>'
 '<p class="note" id="plnLot" role="status"></p>'
 '<div class="field"><label for="plnTiny">Risk check, % of balance (optional)</label>'
 '<input class="inp" id="plnTiny" type="number" inputmode="decimal" min="0" max="100" step="0.5" placeholder="0 = off">'
 '<small class="hint">Refuses a trade when even the smallest lot would lose more than this share of your balance at the stop. Leave 0 to switch it off. Plan accounts only.</small></div>'
 '<button class="btn primary block" id="plnSave">Save plan</button><p class="note" id="plnMsg" role="status"></p></div>')

JS = r''' /*PL7-start*/
 var plnSel=0;
 function plnWhole(v){v=Math.floor((parseFloat(v)||0)/10)*10;return v<0?0:v>1000?1000:v}
 function plnPick(n){plnSel=n;$$("#plnChips button").forEach(function(b){b.setAttribute("aria-pressed",String(+b.dataset.plan===n));b.className=+b.dataset.plan===n?"btn primary":"btn"});
  var c=$("#plnCustom");if(c&&document.activeElement!==c)c.value=(n>60?n:"");
  $("#plnLot").textContent=n>=10?"Plan $"+n+": every entry uses "+(Math.round(n/10)/100).toFixed(2)+" lot.":"No plan. Burst uses your lot setting below."}
 function plnShow(j){var s=(j&&j.settings)||{};plnPick(s.plan_usd>=10?s.plan_usd:0);var t=$("#plnTiny");if(t&&document.activeElement!==t)t.value=s.tiny_pct>0?s.tiny_pct:""}
 $$("#plnChips button").forEach(function(b){b.onclick=function(){plnPick(+b.dataset.plan)}});
 $("#plnCustom").oninput=function(){var w=plnWhole(this.value);if(w>=10){plnSel=-1;plnPick(w)}else if(this.value===""){plnPick(0)}};
 $("#plnSave").onclick=function(){var b=this;if(!window.SXA){toast("Sign in first");return}
  var tp=$("#plnTiny").value.trim(),t=tp===""?0:parseFloat(tp);
  if(!(t>=0&&t<=100)){$("#plnMsg").textContent="Risk check must be 0 to 100.";return}
  b.disabled=true;$("#plnMsg").textContent="Saving...";
  SXA.api("/api/burst",{method:"POST",body:{plan_usd:plnSel>=10?plnSel:0,tiny_pct:t}}).then(function(j){bswShow(j);$("#plnMsg").textContent="Saved on the server.";toast(plnSel>=10?"Plan $"+plnSel+" saved":"Plan removed")}).catch(function(e){$("#plnMsg").textContent=e.message||"Not saved";toast(e.message||"Not saved")}).then(function(){b.disabled=false})};
 /*PL7-end*/
'''

s = s.replace(A1, HTML + A1)
s = s.replace(A2, A2 + 'if(typeof plnShow==="function")plnShow(j);')
s = s.replace(A3, JS + A3)
open(p, 'w', encoding='utf-8').write(s)
print(p, 'patched: Managed plan box added at the top of the Burst card')
