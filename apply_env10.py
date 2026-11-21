"""Section 10b: the admin 'Setup check'. Needs backend/envcheck.py (new file) in place first.
Edits backend/app.py (GET /api/admin/health also returns env + env_count) and static/index.html (a Setup check card at the top of the Admin panel). Safe to run twice."""
import os
if not os.path.exists("backend/envcheck.py"): print("STOP: backend/envcheck.py is missing. Paste that file first."); raise SystemExit(1)
A = "backend/app.py"; H = "static/index.html"
a = open(A, encoding="utf-8").read()
if "envcheck" in a:
    print("app.py: already applied")
else:
    o1 = "from . import lag, multi, automarkets, prefs, scale, burst, groupcap, authmail, binance, stake"
    o2 = "    return jsonify(dict(h, ok=not bad, problems=bad, deriv_loop_last=beat or None, deriv_loop_ago=int(time.time()) - beat if beat else None))"
    if a.count(o1) != 1 or a.count(o2) != 1: print("STOP: app.py lines not found exactly once"); raise SystemExit(1)
    a = a.replace(o1, o1 + ", envcheck")
    a = a.replace(o2, "    rows = envcheck.report()\n    return jsonify(dict(h, ok=not bad, problems=bad, deriv_loop_last=beat or None, deriv_loop_ago=int(time.time()) - beat if beat else None, env=rows, env_count=envcheck.summary(rows)))")
    open(A, "w", encoding="utf-8").write(a); print("app.py done")
h = open(H, encoding="utf-8").read()
if "function envCard(" in h:
    print("index.html: already applied")
else:
    p1 = "'<h2>Admin panel</h2><h3 style=\"margin:8px 0 0\">Test price</h3>"
    p2 = "function panel(){ovEl.classList.add(\"wide\");"
    p3 = "$(\".x\",ovEl).onclick=function(){closeOv();ovEl.classList.remove(\"wide\");location.hash=\"#home\"};"
    if h.count(p1) != 1 or h.count(p2) != 1 or h.count(p3) != 1: print("STOP: admin panel lines not found exactly once"); raise SystemExit(1)
    card = r'''function envCard(){var box=$("#aEnv");if(!box)return;
 var T='<h3 style="margin:8px 0 0">Setup check</h3>';
 function draw(j){var rows=j.env||[],n=j.env_count||{bad:0,warn:0,ok:0},lv={bad:["stop","Fix"],warn:["watch","Check"],ok:["ok","OK"]},all=box.dataset.all==="1",
  h=T+'<p class="note"><span class="chip '+(n.bad?"stop":n.warn?"watch":"ok")+'">'+(n.bad?n.bad+" to fix":n.warn?n.warn+" to check":"All good")+'</span> '+n.ok+' fine. Only names are shown, never a secret. Change them in Render > Environment, then press Check again.</p>';
  rows.filter(function(r){return all||r.level!=="ok"}).forEach(function(r){var c=lv[r.level]||lv.warn;h+='<div style="border:1px solid var(--line,#8884);border-radius:10px;padding:8px;font-size:12px;margin-bottom:6px"><span class="chip '+c[0]+'">'+c[1]+'</span> <b>'+esc(r.key)+'</b> <span class="muted">'+esc(r.group)+'</span><br>'+esc(r.msg)+'</div>'});
  h+='<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="aEnvR">Check again</button><button class="btn" id="aEnvA">'+(all?"Show problems only":"Show everything")+'</button></div>';
  box.innerHTML=h;$("#aEnvR").onclick=load;$("#aEnvA").onclick=function(){box.dataset.all=all?"0":"1";draw(j)}}
 function load(){box.innerHTML=T+'<p class="note">Loading...</p>';SXA.api("/api/admin/health").then(draw,function(){box.innerHTML=T+'<p class="note">Could not load the setup check.</p>'})}
 load()}
'''
    h = h.replace(p1, "'<h2>Admin panel</h2><div id=\"aEnv\"></div><h3 style=\"margin:8px 0 0\">Test price</h3>")
    h = h.replace(p2, card + p2)
    h = h.replace(p3, p3 + " envCard();")
    open(H, "w", encoding="utf-8").write(h); print("index.html done")
