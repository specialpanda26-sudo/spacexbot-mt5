"""Pay fix 3: show the payments log (/api/admin/payments) inside the Admin panel. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
F = 'static/index.html'
s = open(F, encoding='utf-8').read()
if 'id="aPay"' in s:
    print('already applied'); raise SystemExit
A1 = '<h3 style="margin:8px 0 0">Subscribers</h3>'
A2 = '$(".x",ovEl).onclick=function(){closeOv();ovEl.classList.remove("wide");location.hash="#home"};'
for a in (A1, A2):
    assert s.count(a) == 1, 'anchor not found exactly once: ' + a[:50]
UI = ('<h3 style="margin:8px 0 0">Payments log</h3><p class="note">Last 50 attempts with the gateway words, so you can see why a number failed. Phones are masked.</p>'
      '<div style="display:flex;gap:8px"><button class="btn" id="aPayR">Refresh</button></div><div id="aPay" style="display:grid;gap:6px"></div>')
JS = '''
 function payLog(){var box=$("#aPay");box.textContent="Loading...";SXA.api("/api/admin/payments").then(function(j){var r=j.payments||[];
  box.innerHTML=r.length?r.map(function(p){var d=new Date(p.created*1000),c=p.status==="paid"?"#16a34a":p.status==="pending"?"#ca8a04":"#dc2626";
   return'<div style="border:1px solid var(--line,#8884);border-radius:10px;padding:8px;font-size:12px"><b style="color:'+c+'">'+esc(p.status)+'</b> '+esc(p.provider)+' '+esc(p.plan)+' '+esc(String(p.amount))+' <span class="muted">'+esc(d.toLocaleString())+'</span><br>'+esc(p.phone||"")+(p.reason?' | '+esc(p.reason):"")+(p.detail?'<br><span class="muted">'+esc(p.detail)+'</span>':"")+'<br><span class="muted">'+esc(p.ref)+'</span></div>'}).join(""):"No attempts yet."},function(e){box.textContent=e.message||"Could not load"})}
 $("#aPayR").onclick=payLog;payLog();
'''
s = s.replace(A1, UI + A1).replace(A2, A2 + JS)
open(F, 'w', encoding='utf-8').write(s)
print('done')
