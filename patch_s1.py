#!/usr/bin/env python3
"""Section 1: real accounts. Patches app.py, store.py and static/index.html. Safe to run once; refuses if an anchor is missing."""
import sys, io
def rd(p): return io.open(p, encoding='utf-8', newline='').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8', newline='').write(s)
def rep(s, old, new, name):
    n = s.count(old)
    if n != 1: sys.exit('PATCH FAILED (%s): anchor found %d times' % (name, n))
    return s.replace(old, new)
def region(s, a, b, new, name):
    i = s.find(a); j = s.find(b, i + 1) if i >= 0 else -1
    if i < 0 or j < 0 or s.count(a) != 1: sys.exit('PATCH FAILED (%s): region anchors' % name)
    return s[:i] + new + s[j:]

# ---------------- store.py ----------------
p = 'backend/store.py'; s = rd(p)
if 'exp_level' not in s:
    s = rep(s, "            except sqlite3.OperationalError: pass\n        c.commit()",
"""            except sqlite3.OperationalError: pass
        for col in ('username TEXT', 'phone TEXT', 'country TEXT', 'bio TEXT', 'exp_level TEXT', 'goal TEXT', 'risk_pref TEXT', 'av INTEGER', 'notif TEXT', 'dob TEXT', 'gender TEXT'):
            try: c.execute('ALTER TABLE users ADD COLUMN ' + col)
            except sqlite3.OperationalError: pass
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_users_username ON users(username) WHERE username IS NOT NULL')
        c.commit()""", 'store')
    wr(p, s)

# ---------------- app.py ----------------
p = 'backend/app.py'; s = rd(p)
if 'accounts' not in s:
    s = rep(s, "from . import store as st, bars, brain, risk, fb, news, stats, payments as pay", "from . import store as st, bars, brain, risk, fb, news, stats, accounts, payments as pay", 'imp')
    s = rep(s, "    u['admin'] = u['email'].lower() in ADMINS\n", "    u['admin'] = bool(u.get('verified')) and u['email'].lower() in ADMINS      # an unverified email can never be admin\n", 'admin')
    s = rep(s, "def need(admin=False, active=False):", "def need(admin=False, active=False, verified=False):", 'need1')
    s = rep(s, "            if admin and not u['admin']: return jsonify(error='admin only'), 403\n",
            "            if (verified or admin) and not u.get('verified'): return jsonify(error='verify your email first'), 403\n            if admin and not u['admin']: return jsonify(error='admin only'), 403\n", 'need2')
    s = rep(s, "    out = {'email': u['email'], 'admin': u['admin'], 'active': u['active'], 'plan_until': u['plan_until']}\n",
            "    out = {'uid': u['uid'], 'email': u['email'], 'verified': bool(u.get('verified')), 'admin': u['admin'], 'active': u['active'], 'plan_until': u['plan_until'], **accounts.view(u['uid'])}\n    out['name'] = out['name'] or u.get('name') or u['email'].split('@')[0]\n", 'me')
    s = rep(s, "@app.post('/api/me/fcm')\n",
"""@app.post('/api/me/profile')
@need()
def me_profile(u):
    try: accounts.update(u['uid'], request.get_json(silent=True) or {})
    except ValueError as e: return jsonify(error=str(e)), 400
    return jsonify(ok=True)

@app.delete('/api/me')
@need()
def me_delete(u):
    if u['admin']: return jsonify(error='Admin accounts cannot be deleted here.'), 400
    accounts.erase(u['uid']); fb.delete_user(u['uid']); return jsonify(ok=True)

@app.post('/api/me/signout-others')
@need()
def me_signout(u): return jsonify(ok=fb.revoke(u['uid']))

@app.post('/api/me/fcm')
""", 'routes')
    s = rep(s, "@app.post('/api/pay/mpesa')\n@need()\n", "@app.post('/api/pay/mpesa')\n@need(verified=True)\n", 'pay1')
    s = rep(s, "@app.post('/api/pay/paypal')\n@need()\n", "@app.post('/api/pay/paypal')\n@need(verified=True)\n", 'pay2')
    wr(p, s)

# ---------------- index.html ----------------
p = 'static/index.html'; s = rd(p)
if '/static/live.js' in s: print('index.html already patched'); sys.exit(0)

s = rep(s, '<script>window.SX_LG=', '<script src="/config.js"></script><script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script><script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js"></script><script src="/static/live.js"></script>\n<script>window.SX_LG=', 'scripts')

# boot: wait for the real session before deciding what to show
s = rep(s, 'bootT=setTimeout(function(){endBoot(true)},5000);', 'bootT=setTimeout(function(){endBoot(true)},5000);SXA.ready.then(function(){clearTimeout(bootT);bootT=setTimeout(function(){endBoot(true)},900)});', 'boot')

# session: the server is the only source of truth
s = rep(s, 'var U=LS("sxb_user")||(function(){try{return JSON.parse(sessionStorage.getItem("sxb_user"))}catch(e){return null}})();',
r'''var U=null;window.sxToast=tst;
var PROT=/^#(home|market|bot|trades|connect|profile|onboard)$/;
window.sxSetUser=function(u,first){U=u;slot();var h=location.hash;
 if(!u){if(PROT.test(h))location.hash="#welcome";return}
 if(first){if(!u.dob){setTimeout(about,500);return}if(!u.verified){setTimeout(verify,500);return}}
 if(u.verified&&(!h||h==="#"||h==="#welcome"))location.hash="#home";
 else if(!u.verified&&PROT.test(h))location.hash="#welcome";
 if(location.hash==="#profile"&&window.renderProfile)renderProfile()};
window.addEventListener("hashchange",function(){if(SXA.resolved()&&!U&&PROT.test(location.hash))location.hash="#welcome"});''', 'U')

# remove the fake reset-code engine, rebuild forgot-password on Firebase
s = region(s, 'var RESET={', 'function rsBusy', '', 'reset')
s = region(s, 'function forgot(pre){', 'var PK="sxb_prof"', r'''function forgot(pre){
 ov(BK+BR+IL2.mail+'<h2>Forgot your password?</h2><p class="muted" style="text-align:center">Enter your email. We will send you a link to choose a new password.</p><div class="field"><label for="fE">Email</label><input class="inp" id="fE" type="email" autocomplete="email" inputmode="email" placeholder="you@email.com"></div><p class="err" id="fErr" role="alert"></p><button class="btn primary big block" id="fGo">Send reset link</button><p class="note" style="text-align:center"><button class="lnk" data-auth="login">Back to log in</button></p>',1);
 $(".x",ovEl).onclick=function(){auth("login")};var i=$("#fE");i.value=pre||"";
 function sent(e){ov(BK+BR+IL2.phone+'<h2>Check your email</h2><p class="muted" style="text-align:center">If an account exists for <b>'+esc(e)+'</b>, a link to choose a new password is on its way. Check spam too.</p><button class="btn primary big block" id="fL">Back to log in</button>',1);
  $(".x",ovEl).onclick=function(){forgot(e)};$("#fL").onclick=function(){auth("login");var m=$("#aE");if(m)m.value=e}}
 function go(){var e=i.value.trim();if(!/^\S+@\S+\.\S+$/.test(e))return $("#fErr").textContent="Enter the email you signed up with.";var b=$("#fGo");rsBusy(b,"Sending");
  SXA.resetPassword(e).then(function(){sent(e)},function(x){b.disabled=false;b.textContent=b.dataset.t;$("#fErr").textContent=SXA.err(x)})}
 $("#fGo").onclick=go;i.onkeydown=function(ev){if(ev.key==="Enter")go()}}

''', 'forgot')

# profile: saved on the server
s = rep(s, 'function pfSv(){LS(PK,PF)}', 'function pfSv(){if(!U)return;U.prof=PF;SXA.save(Object.assign({name:U.name},PF)).then(function(m){U=m;PF=m.prof}).catch(function(x){tst(SXA.err(x))})}', 'pfSv')
s = rep(s, 'function pfKeep(){if(LS("sxb_user"))LS("sxb_user",U);else try{sessionStorage.setItem("sxb_user",JSON.stringify(U))}catch(x){}}', 'function pfKeep(){}', 'pfKeep')
s = rep(s, 'PF=LS(PK)||{};if(!PF.joined){PF.joined=Date.now();pfSv()}', 'PF=U.prof||(U.prof={});PF.joined=(U.created||0)*1000||Date.now();', 'renderProfile')
s = rep(s, 'pfT("tfa","Two-step verification","Ask for an email code at login. Works once the server is live.",PF.tfa)+', '', 'tfa')
s = rep(s, '>Log out others<', '>Log out everywhere<', 'others-label')
s = rep(s, 'else if(a==="others")tst("No other devices are signed in");', 'else if(a==="others"){SXA.signoutEverywhere().then(function(){pfOut();tst("Signed out on every device. Log in again.")}).catch(function(x){tst(SXA.err(x))})}', 'others')
s = rep(s, 'pe.textContent="";["pwC","pwN","pwR"].forEach(function(i){$("#"+i).value=""});$("#pwM").dataset.s=0;$("#pwT").textContent=PWH;tst("Password updated")}',
 'pe.textContent="";t.disabled=true;SXA.changePassword(c,p).then(function(){["pwC","pwN","pwR"].forEach(function(i){$("#"+i).value=""});$("#pwM").dataset.s=0;$("#pwT").textContent=PWH;t.disabled=false;tst("Password updated")}).catch(function(x){t.disabled=false;pe.textContent=SXA.err(x)})}', 'pw')
s = rep(s, 'function pfOut(){var e=U&&U.email;U=null;LS("sxb_user",null);try{sessionStorage.removeItem("sxb_user")}catch(x){}', 'function pfOut(){SXA.signOut();U=null;', 'pfOut')
s = rep(s, '$("#dGo").onclick=function(){delete VR[U.email];LS("sxb_ver",VR);LS(PK,null);PF={};pfOut();tst("Account deleted")}',
 '$("#dGo").onclick=function(){var b=this;b.disabled=true;SXA.deleteAccount().then(function(){PF={};pfOut();tst("Account deleted")}).catch(function(x){b.disabled=false;tst(SXA.err(x))})}', 'del')

# login / sign-up / google
s = rep(s, '$$("[data-soc]",ovEl).forEach(function(b){b.onclick=function(){tst(b.dataset.soc+" sign-in arrives with the back end")}});',
 '$$("[data-soc]",ovEl).forEach(function(b){b.onclick=function(){SXA.google().then(function(u){U=u;slot();if(!u.dob){about();return}if(!u.verified){verify();return}tst("Logged in");sxGo("#home")}).catch(function(x){$("#aErr").textContent=SXA.err(x)})}});', 'google')
s = region(s, 'U={name:n||e.split("@")[0],email:e};', '\n $("#aGo").onclick=go;', r"""er.textContent="";var gb=$("#aGo");dots(gb);
  (su?SXA.signUp(n,e,p):SXA.signIn(e,p,!!($("#aR")&&$("#aR").checked))).then(function(u){U=u;slot();
   if(su){window.dispatchEvent(new Event("sx-newuser"));about();return}
   if(!u.dob){about();return}if(!u.verified){verify();return}
   tst("Logged in");sxGo("#home")
  }).catch(function(x){gb.classList.remove("ld");gb.style.minWidth=gb.style.minHeight="";gb.textContent=su?"Create account":"Log in";er.textContent=SXA.err(x)})}""", 'go')

# about you: saved on the server, then email check
s = rep(s, '$(".x",ovEl).onclick=function(){U=null;LS("sxb_user",null);auth("signup")};', '$(".x",ovEl).onclick=function(){SXA.signOut();U=null;slot();auth("login")};', 'about-x')
s = rep(s, 'U.dob=YR[wy.i]+"-"+("0"+(wm.i+1)).slice(-2)+"-"+("0"+(wd.i+1)).slice(-2);U.age=a;U.gender=g;LS("sxb_user",U);slot();dots(this);setTimeout(verify,500)',
 r"""var dob=YR[wy.i]+"-"+("0"+(wm.i+1)).slice(-2)+"-"+("0"+(wd.i+1)).slice(-2),wb=this;dots(wb);
  SXA.save({dob:dob,gender:g}).then(function(m){U=m;slot();if(m.verified)welcome();else verify()}).catch(function(x){wb.classList.remove("ld");wb.style.minWidth=wb.style.minHeight="";wb.textContent="Continue";$("#wE").textContent=SXA.err(x)})""", 'about-go')

# email verification: a real link, not a code shown on screen
s = region(s, 'function verify(){var code=', 'function okPage(){', r"""function verify(){
 ov(XB+BR+IL2.phone+'<h2>Check your email</h2><p class="muted" style="text-align:center">We sent a verification link to <b>'+esc(U.email)+'</b>. Open it, then tap the button below.</p><p class="err" id="vE" role="alert"></p><button class="btn primary big block" id="vGo">I have verified</button><button class="btn block" id="vR">Resend email</button><p class="note" style="text-align:center">Nothing yet? Look in your spam folder.</p>');
 $(".x",ovEl).onclick=closeOv;
 var iv=setInterval(function(){if(!$("#vGo")){clearInterval(iv);return}chk(true)},4000);
 function chk(q){var g=$("#vGo");if(!g||g.classList.contains("ld"))return;if(!q)dots(g);
  function rst(){g.classList.remove("ld");g.style.minWidth=g.style.minHeight="";g.textContent="I have verified"}
  SXA.checkVerified().then(function(v){if(v){clearInterval(iv);U=SXA.user();okPage();return}if(!q){rst();$("#vE").textContent="Not verified yet. Open the link in your email first."}})
   .catch(function(x){if(!q){rst();$("#vE").textContent=SXA.err(x)}})}
 $("#vGo").onclick=function(){chk(false)};
 $("#vR").onclick=function(){var b=this;b.disabled=true;SXA.resendVerification().then(function(){b.textContent="Sent. Resend in 30s";setTimeout(function(){b.disabled=false;b.textContent="Resend email"},3e4)}).catch(function(x){b.disabled=false;$("#vE").textContent=SXA.err(x)})}}
""", 'verify')

# admin: only a server-confirmed admin (no PIN in the page any more)
s = region(s, 'function adm(){var PIN=', 'function panel(){', r"""function adm(){SXA.ready.then(function(){if(!(U&&U.admin)){tst("Admin only");location.hash="#welcome";return}ov(XB+BR,1);panel()})}
""", 'adm')

s = rep(s, 'setTimeout(chk,600);\n})();', 'setTimeout(chk,600);\nSXA.bind(window.sxSetUser);\n})();', 'bind')
s = s.replace('VR[U.email]', 'U.verified')
wr(p, s)
print('index.html patched')
