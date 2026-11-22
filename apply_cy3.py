"""CY3 patch: the Auto-cycle card on the Bot tab (static/index.html) and two extra facts in GET /api/cycle (today, last) from backend/cycle.py.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_cy3.py"""
import sys
C, F, H = 'backend/cycle.py', 'static/index.html', 'docs/HANDOFF.md'
OLDV = "'limits': {'max_per_day': [MAX_LO, MAX_HI]}}"
NEWV = "'limits': {'max_per_day': [MAX_LO, MAX_HI]}, **_facts(uid)}"
FACTS = '''

def _facts(uid):
    """CY3: how many new groups the Deriv engine opened today, and its last plain-words reason for not opening one (empty when nothing to say)."""
    try:
        from . import deriv_group as dg
        w = dg.why(uid or '')
        return {'today': dg.used_today(uid or ''), 'last': '' if w == 'cycle off' else w}
    except Exception: return {'today': 0, 'last': ''}
'''
BLOCK = r'''/*CY3-start*/
 vb.appendChild(card(["Auto-cycle",'<span class="chip info" id="cyChip"></span>'],'<button type="button" class="switch" role="switch" aria-checked="false" id="cyOn"><span><b>Open the next group</b><small>When a group closes at its profit target, start a new one straight away.</small></span><span class="sw"></span></button><div class="inp-row"><div class="field"><label for="cyN">New groups a day</label><input class="inp" id="cyN" type="number" min="1" max="100" step="1" inputmode="numeric" placeholder="10"></div></div><button class="btn primary block" id="cySave">Save</button><p class="note" id="cyMsg" role="status"></p><p class="note" id="cyNote"></p><p class="note">Needs the group target above (on, more than 0) and 2 or more positions. Only a group that closed at its profit target starts the next one: a stop loss, a loss limit or a manual close never does. Works on Deriv for now. Repeating trades also repeats losses, so try it on a demo account first.</p>'));
 var cyOn=false;
 function cyShow(j){var s=j.settings||{};cyOn=s.on===true;$("#cyOn").setAttribute("aria-checked",cyOn);$("#cyN").value=s.max_per_day||"";$("#cyChip").textContent=!cyOn?"Off":j.note?"Needs setup":"On";
  var t=[];if(cyOn&&j.note)t.push(j.note);if(cyOn&&typeof j.today==="number")t.push("New groups opened today: "+j.today+" of "+(s.max_per_day||10)+".");if(cyOn&&j.last)t.push("Last time it did not open one: "+j.last+".");$("#cyNote").textContent=t.join(" ")}
 function cyLoad(){if(!window.SXA)return;SXA.api("/api/cycle").then(cyShow).catch(function(){})}
 $("#cyOn").onclick=function(){cyOn=!cyOn;this.setAttribute("aria-checked",cyOn);$("#cyChip").textContent=cyOn?"On":"Off"};
 $("#cySave").onclick=function(){var b=this;if(!window.SXA){toast("Sign in first");return}
  var n=Math.round(parseFloat($("#cyN").value)||0),body={on:cyOn};if(n)body.max_per_day=n;
  b.disabled=true;$("#cyMsg").textContent="Saving...";
  SXA.api("/api/cycle",{method:"POST",body:body}).then(function(j){cyShow(j);$("#cyMsg").textContent="Saved on the server.";toast("Auto-cycle saved")}).catch(function(e){$("#cyMsg").textContent=e.message||"Not saved";toast(e.message||"Not saved")}).then(function(){b.disabled=false})};
 cyLoad();
 /*CY3-end*/
 '''
ANCHOR = 'vb.appendChild(card(["Run check",""],'
c = open(C, encoding='utf-8').read(); s = open(F, encoding='utf-8').read()
do_c = '_facts(uid)' not in c; do_s = '/*CY3-start*/' not in s
if do_c and c.count(OLDV) != 1: sys.exit('STOP: view line found %d times in %s' % (c.count(OLDV), C))
if do_s and s.count(ANCHOR) != 1: sys.exit('STOP: Run check anchor found %d times in %s' % (s.count(ANCHOR), F))
if do_c: open(C, 'w', encoding='utf-8').write(c.replace(OLDV, NEWV).rstrip('\n') + '\n' + FACTS); print('patched', C)
else: print(C, 'already patched')
if do_s: open(F, 'w', encoding='utf-8').write(s.replace(ANCHOR, BLOCK + ANCHOR)); print('patched', F)
else: print(F, 'already patched')
MARK = '## Section CY3 (Auto-cycle card on the Bot tab)'; h = open(H, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has CY3')
else:
    open(H, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 22)
- static/index.html: card "Auto-cycle" on the Bot tab, right under "Group target and loss" (block /*CY3-start*/ .. /*CY3-end*/): switch, New groups a day (blank = keep the saved number), Save -> POST /api/cycle, chip Off / Needs setup / On, plain-words note (cycle.why_not), "New groups opened today: x of y" and "Last time it did not open one: <reason>".
- backend/cycle.py: GET/POST /api/cycle now also return today (deriv_group.used_today) and last (deriv_group.why, '' when the reason is just 'cycle off').
- Not checked on a real phone. Tests: tests/test_cy3.py (server facts + the card code run in node against a fake page).
- Still open: CY4 (MT5 EA + Binance engines), group LOSS limit on Deriv, run tools/deriv_probe.py to confirm the sell message.
''')
    print('HANDOFF updated')
