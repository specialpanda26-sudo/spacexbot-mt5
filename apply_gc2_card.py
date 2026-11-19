"""Group card in the app (Bot tab): positions at once, group profit target (USD), group loss limit (% of account), one Save button.
Uses GET/POST /api/groupcap (target, loss, on) and POST /api/prefs {entries} (positions). Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
F = 'static/index.html'
s = open(F, encoding='utf-8').read()
if 'id="gcSave"' in s:
    print('already applied'); raise SystemExit
A = 'vb.appendChild(card(["Run check",""],'
assert s.count(A) == 1, 'anchor not found exactly once'
NEW = r'''vb.appendChild(card(["Group target and loss",'<span class="chip info" id="gcChip"></span>'],'<div class="inp-row"><div class="field"><label for="gcN">Positions at once</label><input class="inp" id="gcN" type="number" min="1" max="10" step="1" inputmode="numeric"></div><div class="field"><label for="gcT">Group profit target ($)</label><input class="inp" id="gcT" type="number" min="0" step="0.5" inputmode="decimal" placeholder="0 = off"></div><div class="field"><label for="gcL">Group loss limit (% of account)</label><input class="inp" id="gcL" type="number" min="0" max="50" step="0.1" inputmode="decimal" placeholder="0 = off"></div></div><button type="button" class="switch" role="switch" aria-checked="false" id="gcOn"><span><b>Use group rules</b><small>Close the whole group together at the target or the loss limit.</small></span><span class="sw"></span></button><button class="btn primary block" id="gcSave">Save</button><p class="note" id="gcMsg" role="status"></p><p class="note">Works with 2 or more positions. The MT5 bridge closes the group; phone-only mode only sends signals. A loss limit caps what a bad group can lose. It does not create profit. Try it on a demo account first.</p>'));
 var gcOn=false;
 function gcShow(j){var g=j.settings||{};gcOn=g.on===true;$("#gcOn").setAttribute("aria-checked",gcOn);$("#gcN").value=j.positions||"";$("#gcN").placeholder="Owner default";$("#gcT").value=g.target_usd||"";$("#gcL").value=g.loss_pct||"";$("#gcChip").textContent=gcOn?"On":"Off"}
 function gcLoad(){if(!window.SXA)return;SXA.api("/api/groupcap").then(gcShow).catch(function(){})}
 $("#gcOn").onclick=function(){gcOn=!gcOn;this.setAttribute("aria-checked",gcOn);$("#gcChip").textContent=gcOn?"On":"Off"};
 $("#gcSave").onclick=function(){var b=this;if(!window.SXA){toast("Sign in first");return}
  var n=Math.round(parseFloat($("#gcN").value)||0),t=parseFloat($("#gcT").value)||0,l=parseFloat($("#gcL").value)||0;
  b.disabled=true;$("#gcMsg").textContent="Saving...";
  SXA.api("/api/prefs",{method:"POST",body:{entries:n}}).then(function(){return SXA.api("/api/groupcap",{method:"POST",body:{on:gcOn,target_usd:t,loss_pct:l}})}).then(function(j){gcShow(j);$("#gcMsg").textContent=gcOn&&(j.positions||0)<2?"Saved, but group rules need 2 or more positions at once.":"Saved on the server.";toast("Group rules saved")}).catch(function(e){$("#gcMsg").textContent=e.message||"Not saved";toast(e.message||"Not saved")}).then(function(){b.disabled=false})};
 gcLoad();
 '''
s = s.replace(A, NEW + A)
open(F, 'w', encoding='utf-8').write(s)
print('done')
