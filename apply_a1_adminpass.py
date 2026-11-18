"""Admin section 1: ACCESS PASS. #admin asks for the pass (ADMIN_PASS on Render) and opens the admin panel without a normal sign-in.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
import sys, os

APP_ROUTE = r'''@app.post('/api/admin/pass')
def admin_pass():
    """Trade the admin access pass for a 12-hour signed pass (backend/adminpass.py). Wrong tries are limited."""
    ip = (request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '?')
    tok, why, wait = ap.attempt(str(_j().get('code', ''))[:200], ip)
    if why == 'ok': return jsonify(token=tok, ttl=ap.TTL)
    if why == 'off': return jsonify(error='The access pass is not set up on this server.'), 400
    if why == 'locked': return jsonify(error='Too many wrong tries. Try again in %d minutes.' % (wait // 60 + 1)), 429
    return jsonify(error='Wrong access pass.'), 401

'''

JS_OLD = 'function adm(){SXA.ready.then(function(){var me=U||SXA.user();if(!(me&&me.admin)){tst("Admin only");location.hash=me?"#home":"#welcome";return}if(!U)U=me;ov(XB+BR,1);loadPlans().then(panel)})}window.adm=adm;'
JS_NEW = r'''function apTok(){try{return sessionStorage.getItem("sxap")||""}catch(e){return ""}}
function apOpen(){ov(XB+BR,1);loadPlans().then(panel)}
function apGate(){ov(XB+BR+'<h2>Admin access</h2><p class="muted" style="text-align:center">Enter the access pass to open the admin panel.</p><div class="field"><label for="apI">Access pass</label><input class="inp" id="apI" type="password" autocomplete="off" placeholder="Access pass"></div><p class="err" id="apE" role="alert"></p><button class="btn primary big block" id="apGo">Open admin</button>');
 function go(){var b=$("#apGo"),c=$("#apI").value;if(!c)return;b.disabled=true;$("#apE").textContent="";SXA.api("/api/admin/pass",{method:"POST",body:{code:c}}).then(function(j){try{sessionStorage.setItem("sxap",j.token)}catch(e){}apOpen()}).catch(function(e){b.disabled=false;$("#apE").textContent=e.message||"Could not check the pass";$("#apI").value=""})}
 $("#apGo").onclick=go;$("#apI").onkeydown=function(e){if(e.key==="Enter")go()}}
function adm(){SXA.ready.then(function(){var me=U||SXA.user();if(me&&me.admin){if(!U)U=me;apOpen();return}
 if(apTok()){SXA.api("/api/admin/health").then(apOpen,function(){try{sessionStorage.removeItem("sxap")}catch(e){}apGate()});return}
 apGate()})}window.adm=adm;'''

EDITS = [
 ('backend/app.py', 'payments as pay\n', 'payments as pay, adminpass as ap\n', 'adminpass as ap'),
 ('backend/app.py', "def need(admin=False, active=False, verified=False):",
  "_OWNER = {'uid': '', 'email': '', 'name': 'Owner', 'verified': True, 'admin': True, 'active': True, 'plan_until': 0}     # who the admin access pass stands for\ndef need(admin=False, active=False, verified=False):", '_OWNER = {'),
 ('backend/app.py', "        def w(*a, **k):\n            u = user()\n            if not u: return jsonify(error='sign in required'), 401",
  "        def w(*a, **k):\n            if admin and ap.valid(request.headers.get('X-Admin-Pass', '')): return f(_OWNER, *a, **k)     # admin access pass: admin routes only\n            u = user()\n            if not u: return jsonify(error='sign in required'), 401", "ap.valid(request.headers"),
 ('backend/app.py', "@app.post('/api/admin/settings')", APP_ROUTE + "@app.post('/api/admin/settings')", 'def admin_pass('),
 ('static/live.js', 'var h = { "Content-Type": "application/json" }; if (t) h.Authorization = "Bearer " + t;',
  'var h = { "Content-Type": "application/json" }; if (t) h.Authorization = "Bearer " + t;\n      try { var ap = sessionStorage.getItem("sxap"); if (ap && path.indexOf("/api/admin/") === 0) h["X-Admin-Pass"] = ap; } catch (x) {}   /* admin access pass, admin routes only */', 'X-Admin-Pass'),
 ('static/index.html', JS_OLD, JS_NEW, 'function apGate('),
 ('.env.example', 'ADMIN_EMAILS=you@gmail.com\n', 'ADMIN_EMAILS=you@gmail.com\nADMIN_PASS=change-me-8-or-more-characters   # admin access pass: open #admin on the site and type it. Leave empty to turn the pass off\n', 'ADMIN_PASS='),
 ('docs/HANDOFF.md', '## REMAINING (do in this order', '- Admin section 1: access pass. backend/adminpass.py + POST /api/admin/pass + X-Admin-Pass header (static/live.js) + pass box on #admin + tests/test_adminpass.py. Set ADMIN_PASS on Render.\n\n## REMAINING (do in this order', 'Admin section 1: access pass'),
]
if not (os.path.isdir('backend') and os.path.isdir('static') and os.path.exists('backend/adminpass.py')): print('STOP: run from the repo folder, after creating backend/adminpass.py'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new[path] if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: print('already applied:', path, marker[:40]); new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:70]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
