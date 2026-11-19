"""Section 6 page patch: no sample trades; Closed trades, Journal and Stats read GET /api/journal. Safe to run twice."""
import sys
P = 'static/index.html'
S = open(P, encoding='utf-8').read()
if '/*S6-start*/' in S: print('skip: the Section 6 page patch is already in'); sys.exit(0)
def edit(old, new, marker=''):
    """Replace `old` (must appear exactly once). Nothing is written to disk until every edit has worked."""
    global S
    if S.count(old) != 1: print('STOP: cannot find exactly once:', old[:70].replace('\n', ' '), S.count(old)); sys.exit(1)
    S = S.replace(old, new); print('ok  ', marker[:50] or old[:50].replace('\n', ' '))
def cut(start, end, new, marker=''):
    """Replace everything from `start` (must appear once) through the first `end` after it."""
    global S
    if S.count(start) != 1: print('STOP: start not exactly once:', start[:70], S.count(start)); sys.exit(1)
    a = S.index(start); b = S.find(end, a)
    if b < 0: print('STOP: end not found after', start[:50]); sys.exit(1)
    S = S[:a] + new + S[b + len(end):]; print('ok  ', marker[:50] or start[:50])

# 1. the sample data goes (trades, open trades, equity curve)
cut('var OPEN=[{s:"EURUSD",side:"Buy",lots:0.04', 'dd:ddOf(EQ)*100}}\n',
'''var SXJ={rows:[],total:0,stats:null,pairs:[],brokers:[],broker:"",state:"idle"};/* the person's REAL closed trades, filled by the S6 block from GET /api/journal. state: idle | out (signed out) | load | ok | err. There is no sample data any more. */
function jmsg(){return SXJ.state==="out"?"Sign in to see your trades.":SXJ.state==="err"?"Cannot load your trades right now. Check your internet and try again.":SXJ.state==="ok"?"No trades yet. Your closed trades show up here after your broker closes some. Nothing on this screen is invented.":"Loading your trades..."}
function jtime(t){return new Date(t*1000).toLocaleString("en-US",{month:"short",day:"numeric",hour:"numeric",minute:"2-digit"})}
''', 'var SXJ={rows:[]')
# 2. Home: the sample equity / stats / open-trades cards go (the Live card shows the real numbers; Section 9 adds the real P&L card)
edit('''    <div class="card">
      <div class="card-head"><h2>Account equity</h2><div class="seg" id="rangeSeg" role="group" aria-label="Range"></div></div>
      <div><div class="equity num" id="eq">$0.00</div><div id="eqChange" class="num"></div></div>
      <div class="chart" id="eqChart" role="img" aria-label="Equity curve"></div>
    </div>

    <div class="stats" id="stats"></div>

''', '', 'S6: no sample equity card')
edit('''    <div class="card">
      <div class="card-head"><h2>Open trades</h2><span class="chip info" id="openCount"></span></div>
      <ul class="list" id="openList"></ul>
    </div>
''', '', 'S6: no sample open-trades card')
cut('function rangeVals(){return EQ', '.join("")}\n', '', 'S6: no rangeVals')
cut('function renderHome(anim){', '"eq");\n}\n', 'function renderHome(anim){renderBot();renderGoals()}/* S6: the real numbers are the Live card (S3) */\n', 'function renderHome(anim){renderBot();renderGoals()}')
edit('dd=stats().dd,tripped', 'dd=0,tripped', 'dd=0,tripped')
edit('''  gates.push({n:"Open trades",pct:OPEN.length/S.maxOpen,t:OPEN.length+" of "+S.maxOpen+" slots used",st:OPEN.length>=S.maxOpen?"watch":"ok"});\n''', '', 'S6: no sample open gate')
edit('renderRange();renderBot();renderCats();', 'renderBot();renderCats();', 'S6: no renderRange call')
edit('  if(t.dataset.r){S.range=+t.dataset.r;save();renderRange();renderHome(true);return}\n', '', 'S6: no range click')
# 3. Trades tab: real rows, All / Wins / Losses, broker picker, honest empty states
edit('''<ul class="list" id="tList"></ul>
    </div>''', '''<div class="seg" id="tBroker" role="group" aria-label="Broker" style="display:none;justify-self:start"></div>
      <ul class="list" id="tList"></ul>
      <p class="note" id="tNote"></p>
    </div>''', 'id="tBroker"')
cut('function renderTrades(){', "No trades match.</span></li>';\n}\n",
'''function renderTrades(){
  var s=SXJ.stats,ok=SXJ.state==="ok"&&s,n=ok?s.trades:0,B=SXJ.brokers||[],pick=B.length>1||!!SXJ.broker;
  $("#tStats").innerHTML=n?[["Net result",m2(s.net)],["Win rate",s.win_rate+"%"],["Profit factor",s.profit_factor===null?"-":s.profit_factor.toFixed(2)],["Trades",n]].map(function(x){return '<div class="stat"><span>'+x[0]+'</span><b class="num">'+x[1]+'</b></div>'}).join(""):"";
  $("#tFilter").innerHTML=[["all","All"],["win","Wins"],["loss","Losses"]].map(function(f){return '<button type="button" data-f="'+f[0]+'" aria-pressed="'+(S.filter===f[0])+'">'+f[1]+'</button>'}).join("");
  var pk=$("#tBroker");if(pk){pk.style.display=pick?"":"none";pk.innerHTML=pick?[["","All brokers"]].concat(B.map(function(b){return[b,b]})).map(function(b){return '<button type="button" data-b="'+esc(b[0])+'" aria-pressed="'+(SXJ.broker===b[0])+'">'+esc(b[1])+'</button>'}).join(""):""}
  var list=ok?SXJ.rows.filter(function(t){return S.filter==="all"||t.result===S.filter}):[];
  $("#tList").innerHTML=list.map(function(t){var up=t.result==="win";return '<li class="row"><span class="ic '+(up?"up":"dn")+'">'+(up?ICON_UP:ICON_DN)+'</span><span class="t">'+esc(t.symbol)+' '+(t.side==="buy"?"Buy":"Sell")+'</span><span class="r num '+(up?"good":"bad")+'">'+m2(t.pnl)+'</span><span class="s">'+jtime(t.t)+' · '+esc(t.broker)+(t.strategy_name?' · '+esc(t.strategy_name):"")+'</span></li>'}).join("")||'<li class="row"><span class="s">'+(ok&&n?"No trades match.":jmsg())+'</span></li>';
  var nt=$("#tNote");if(nt)nt.textContent=ok&&SXJ.total>SXJ.rows.length?"Showing the newest "+SXJ.rows.length+" of "+SXJ.total+" trades. The numbers above count all of them.":""
}
''', 'function renderTrades(){\n  var s=SXJ.stats')
# 4. Journal + Stats tabs
cut('/* ---------- sample trade history', "return b.n-a.n})}\n",
'/* ---------- (no sample trades any more: the real ones come from GET /api/journal, see the S6 block) ---------- */\nvar NOW=Date.now();\n', 'var NOW=Date.now();\n/* ---------- journal')
edit('if(!X.j.length){H.slice(0,3).forEach(function(t){X.j.push({t:+t.d,k:"trade",m:t.s+" "+t.side+" closed "+m2(t.pl)})});',
     'var n0=X.j.length;X.j=X.j.filter(function(e){return e.k!=="trade"});if(X.j.length!==n0)sv();/* older builds saved 3 made-up trade lines here: drop them */\nif(!X.j.length){', 'older builds saved 3 made-up')
cut('function jr(){var f=X.jf,L=X.j.filter', "'<p class=\"note\">Nothing here yet.</p>'}\n",
'''function jall(){var T=SXJ.state==="ok"?SXJ.rows.map(function(r){return{t:r.t*1000,k:"trade",m:r.symbol+" "+(r.side==="buy"?"Buy":"Sell")+" closed "+m2(r.pnl)+" ("+r.broker+")"}}):[];return X.j.concat(T).sort(function(a,b){return b.t-a.t})}
function jr(){var f=X.jf,A=jall(),L=A.filter(function(e){return f==="all"||e.k===f});
 $$("#jF button").forEach(function(b){b.setAttribute("aria-pressed",b.dataset.f===f)});
 $("#jCount").textContent=A.length+" entries";
 $("#jList").innerHTML=L.slice(0,60).map(function(e){return'<div class="al"><time style="min-width:78px">'+tf(e.t)+'</time><span><b class="jt '+e.k+'">'+KL[e.k]+'</b>'+esc(e.m)+'</span></div>'}).join("")||'<p class="note">'+(f==="trade"||f==="all"&&SXJ.state!=="ok"?jmsg():"Nothing here yet.")+'</p>'}
''', 'function jall(){')
edit('toast("Journal cleared")', 'toast("Notes cleared. Your real trades stay.")', 'Notes cleared. Your real trades stay.')
edit('function copyJ(){var t=X.j.map(', 'function copyJ(){var t=jall().map(', 'function copyJ(){var t=jall()')
cut('function sr(){var s=stx(H),v;', '.join("")+\'</ul>\'}\n',
'''function sr(){var s=SXJ.stats,v,b=$("#sBody");
 if(SXJ.state!=="ok"||!s||!s.trades){b.innerHTML='<p class="note">'+jmsg()+'</p>';return}
 if(s.trades<30)v="Too few trades to say much yet. You need 30 or more before a win rate means something.";
 else if(s.win_rate<s.break_even-s.band)v="Your win rate is below break-even by more than luck explains. At this rate you lose money.";
 else if(s.win_rate>s.break_even+s.band)v="Your win rate is above break-even beyond normal luck. Keep risk small and keep checking.";
 else v="Your win rate is inside the luck range, so it cannot be told apart from chance.";
 b.innerHTML='<div class="stats">'+kp("Win rate",s.win_rate.toFixed(1)+"%")+kp("Break-even",s.break_even.toFixed(1)+"%")+kp("Per trade",m2(s.per_trade))+kp("Loss streak",s.loss_streak)+'</div>'+
 '<div class="note">Luck range '+(s.break_even-s.band).toFixed(1)+'% to '+(s.break_even+s.band).toFixed(1)+'% · Best '+m2(s.best)+' · Worst '+m2(s.worst)+' · Deepest dip '+m2(-s.max_drawdown)+'</div><div class="callout">'+v+'</div>'+
 '<b style="font-size:13px" class="muted">BY PAIR</b><ul class="list">'+SXJ.pairs.map(function(o){return'<li class="row"><span class="ic '+(o.pnl>=0?"up":"dn")+'">'+(o.pnl>=0?ICK:ICX)+'</span><span class="t">'+esc(o.symbol)+'</span><span class="r num '+(o.pnl>=0?"good":"bad")+'">'+m2(o.pnl)+'</span><span class="s">'+o.n+' trade'+(o.n>1?"s":"")+' · '+o.win_rate+'% won</span></li>'}).join("")+'</ul>'}
''', 'function sr(){var s=SXJ.stats')
# 5. Section 3's Home card: signed-out visitors no longer get sample cards either
edit('''if (k === "none") { if (chip.className !== CH.c) chip.className = CH.c; if (chip.innerHTML !== CH.h) chip.innerHTML = CH.h; chip.title = CH.t; return; }''',
     '''if (k === "none") { var c1 = "chip watch app-only", h1 = '<span class="dot"></span>Signed out'; if (chip.className !== c1) chip.className = c1; if (chip.innerHTML !== h1) chip.innerHTML = h1; chip.title = "Sign in to see your account."; return; }''', 'h1 = \'<span class="dot"></span>Signed out')
edit('''} else { E.hidden = true; E.style.display = "none"; showSamples(true); }''',
     '''} else {      /* signed out: no sample numbers either */
        var sh = '<div class="card-head"><h2>Sign in to see your account</h2></div><p class="note">Your balance, profit today and trades show here once you sign in with a verified email and connect a broker. Nothing on this screen is invented.</p>';
        E.hidden = false; E.style.display = ""; if (E.innerHTML !== sh) E.innerHTML = sh; showSamples(false);
      }''', 'Sign in to see your account</h2>')
# 6. the loader
edit('/*S4-end*/\n</script>\n', '''/*S4-end*/
</script>
<script>
/*S6-start*/
/* ---- Real Journal + Stats. Asks GET /api/journal for the signed-in person's closed trades and hands them to the Closed trades, Journal and Stats tabs (SXJ, renderTrades, jr, sr). No sample data anywhere. ---- */
(function () {
  "use strict";
  var vt = document.getElementById("view-trades");
  if (!vt || !window.SXA || typeof SXJ === "undefined") return;
  var WANT = "", BUSY = false, AGAIN = false, SIG = "", TK = 0;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function paint() { try { renderTrades(); jr(); sr(); } catch (e) {} }
  function reset(state) { SXJ.rows = []; SXJ.total = 0; SXJ.stats = null; SXJ.pairs = []; SXJ.brokers = []; SXJ.broker = ""; SXJ.state = state; }
  function poll() {
    var u = me(); if (!u || !u.verified) return;
    if (BUSY) { AGAIN = true; return; }
    BUSY = true; var asked = WANT;
    if (SXJ.state === "idle" || SXJ.state === "out") { SXJ.state = "load"; paint(); }
    SXA.api("/api/journal" + (asked ? "?broker=" + encodeURIComponent(asked) : ""), { method: "GET" }).then(function (j) {
      if (asked !== WANT) return;      /* the person picked another broker while this was loading */
      SXJ.rows = j.rows || []; SXJ.total = j.total || 0; SXJ.stats = j.stats || null; SXJ.pairs = j.pairs || []; SXJ.brokers = j.brokers || []; SXJ.broker = j.broker || ""; SXJ.state = "ok";
    }, function () { if (SXJ.state !== "ok") SXJ.state = "err"; }).then(function () {
      BUSY = false; paint(); if (AGAIN) { AGAIN = false; poll(); }
    });
  }
  setInterval(function () {      /* every second: notice sign-in / sign-out; every 15 s while the Trades screen is open: ask the server again */
    var u = me(), done = !SXA.resolved || SXA.resolved(), sg = u ? [u.uid, !!u.verified].join("|") : done ? "out" : ""; TK++;
    if (sg !== SIG) {
      SIG = sg; WANT = "";
      if (u && u.verified) { reset("idle"); poll(); } else reset(done ? "out" : "idle");
      paint(); return;
    }
    if (u && u.verified && !document.hidden && vt.classList.contains("on") && TK % 15 === 0) poll();
  }, 1000);
  var mo = new MutationObserver(function () { if (vt.classList.contains("on") && !document.hidden) poll(); });
  mo.observe(vt, { attributes: true, attributeFilter: ["class"] });
  document.addEventListener("visibilitychange", function () { if (!document.hidden && vt.classList.contains("on")) poll(); });
  document.addEventListener("click", function (e) {
    var b = e.target && e.target.closest ? e.target.closest("#tBroker button") : null; if (!b) return;
    WANT = b.getAttribute("data-b") || ""; SXJ.broker = WANT; paint(); poll();
  });
  paint();
})();
/*S6-end*/
</script>
''', '/*S6-start*/')

open(P, 'w', encoding='utf-8').write(S); print('done: static/index.html patched')
