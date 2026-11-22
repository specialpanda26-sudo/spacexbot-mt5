"""BT1 patch: the Burst switch on the Bot tab (static/index.html). The server side (/api/burst, backend/burst.py) already exists, only the card was missing.
A real switch: tap it and it saves at once (no Save button needed). Under it: quiet minutes, entries and USD per entry (Save).
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_bt1_burst_card.py"""
import sys
F, H = 'static/index.html', 'docs/HANDOFF.md'
ANCHOR = 'vb.appendChild(card([\"Session limits\",'
BLOCK = r'''/*BT1-start*/
 vb.appendChild(card(["Burst mode",'<span class="chip info" id="btChip"></span>'],'<button type="button" class="switch" role="switch" aria-checked="false" id="btOn"><span><b>Burst switch</b><small>Turn on when the market is quiet and no strategy is giving signals. The bot then takes small, quick profits in a group and closes them together.</small></span><span class="sw"></span></button><p class="note" id="btNow" role="status"></p><div class="inp-row"><div class="field"><label for="btIdle">Quiet minutes first</label><input class="inp" id="btIdle" type="number" min="1" max="60" step="1" inputmode="numeric"></div><div class="field"><label for="btN">Entries</label><input class="inp" id="btN" type="number" min="1" max="15" step="1" inputmode="numeric"></div><div class="field"><label for="btUsd">Target per entry ($)</label><input class="inp" id="btUsd" type="number" min="0.05" step="0.05" inputmode="decimal"></div></div><button class="btn primary block" id="btSave">Save numbers</button><p class="note" id="btMsg" role="status"></p><p class="note">The switch saves the moment you tap it. After the quiet minutes with no signal, the bot opens this many entries on one idea and closes them at the target, or when the profit starts to go away. It still obeys your daily limits and loss stops. Auto settings turns burst off. The MT5 bridge does the closing; phone-only mode cannot close for you. Deriv refuses a stake under 1 USD. Try it on a demo account first.</p>'));
 var btOn=false;
 function btShow(j){var s=j.settings||{};btOn=s.on===true;$("#btOn").setAttribute("aria-checked",btOn);$("#btIdle").value=s.idle_min||"";$("#btN").value=s.quick_n||"";$("#btUsd").value=s.quick_usd||"";
  var o=j.now||{},off=j.enabled===false;$("#btChip").textContent=off?"Off (owner)":!btOn?"Off":o.state==="running"?"Running":o.state==="ready"?"Ready":"On";$("#btNow").textContent=btOn||off?(o.why||""):""}
 function btLoad(){if(!window.SXA)return;SXA.api("/api/burst").then(btShow).catch(function(){})}
 $("#btOn").onclick=function(){var b=this;if(!window.SXA){toast("Sign in first");return}
  var want=!btOn;b.disabled=true;b.setAttribute("aria-checked",want);
  SXA.api("/api/burst",{method:"POST",body:{on:want}}).then(function(j){btShow(j);toast(want?"Burst on":"Burst off")}).catch(function(e){b.setAttribute("aria-checked",btOn);toast(e.message||"Not saved")}).then(function(){b.disabled=false})};
 $("#btSave").onclick=function(){var b=this;if(!window.SXA){toast("Sign in first");return}
  var body={},i=Math.round(parseFloat($("#btIdle").value)||0),n=Math.round(parseFloat($("#btN").value)||0),u=parseFloat($("#btUsd").value)||0;
  if(i)body.idle_min=i;if(n)body.quick_n=n;if(u)body.quick_usd=u;
  if(!Object.keys(body).length){$("#btMsg").textContent="Type a number first.";return}
  b.disabled=true;$("#btMsg").textContent="Saving...";
  SXA.api("/api/burst",{method:"POST",body:body}).then(function(j){btShow(j);$("#btMsg").textContent="Saved on the server.";toast("Burst numbers saved")}).catch(function(e){$("#btMsg").textContent=e.message||"Not saved";toast(e.message||"Not saved")}).then(function(){b.disabled=false})};
 btLoad();
 /*BT1-end*/
 '''
s = open(F, encoding='utf-8').read()
if '/*BT1-start*/' in s: print(F, 'already patched')
else:
    if s.count(ANCHOR) != 1: sys.exit('STOP: Session limits anchor found %d times in %s' % (s.count(ANCHOR), F))
    open(F, 'w', encoding='utf-8').write(s.replace(ANCHOR, BLOCK + ANCHOR)); print('patched', F)
MARK = '## Section BT1 (Burst switch on the Bot tab)'; h = open(H, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has BT1')
else:
    open(H, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 23)
- Owner wish (dictated): burst should be a simple switch users flip when the market is too busy / no strategy is firing. The server (backend/burst.py, GET/POST /api/burst) existed but had NO user card.
- static/index.html: card "Burst mode" at the top of the Bot tab (block /*BT1-start*/ .. /*BT1-end*/). The switch saves at once (POST /api/burst {on}) and goes back if the save fails. Fields: Quiet minutes first, Entries, Target per entry ($) with Save numbers (blank = keep). Chip: Off / Off (owner) / On / Ready / Running, plus the plain-words line from burst.explain.
- Notes on the card: Auto settings turns burst off, phone-only mode cannot close, Deriv refuses stakes under 1 USD (0.5 USD entries are rejected on Deriv).
- Not built: big-burst numbers on the card; Deriv sub-1-USD stakes. Not checked on a real phone. Test: tests/test_bt1.py.
''')
    print('HANDOFF updated')
