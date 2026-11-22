"""Section 4 (BTC plan): settings cleanup. Nothing is removed, nothing is renamed: important settings move to the top, the rest go under "Advanced".
 - static/index.html (admin panel): a new "Main settings" card right under the env card: Bot on, Risk per trade, Markets, Max open trades, Daily loss, Weekly loss,
   Loss streak stop (+ cooldown hours), News lock, Take profit x (RR), Widest stop (ATR), Burst on / ceiling / big-score.
   A collapsed "Advanced" block holds: Minimum agree, Multi-entry min score, Regime switch, Auto-disable losers (+ min trades), Auto markets (+ max), Markets pool,
   Max trades a day, and (moved, same ids) Big stake, Strategies, Results. Code between /*S4S-start*/ and /*S4S-end*/.
 - backend/app.py admin_set: the new numbers get range checks BEFORE anything is saved (same pattern as the Auto numbers).
Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')

APP = 'backend/app.py'
edit(APP, "('stake_max_risk_pct', 0.5, 25)):", "('stake_max_risk_pct', 0.5, 25),\n                     ('max_open', 1, 10), ('max_daily_loss_pct', 0.5, 20), ('max_weekly_loss_pct', 1, 40), ('max_losing_streak', 0, 20), ('streak_cooldown_h', 0, 72),\n                     ('burst_ceiling', 2, 30), ('burst_big_score', 2, 10), ('min_confluence', 1, 6), ('multi_min_score', 2, 10), ('auto_disable_min_trades', 5, 500),\n                     ('auto_markets_max', 0, 10), ('max_trades_day', 0, 100)):", "('max_open', 1, 10)")

H = 'static/index.html'
MAIN = '<div id="aEnv"></div><h3 style="margin:8px 0 0">Main settings</h3><p class="note">The settings you use every day. Saved for the whole bot.</p><div id="s4Main" style="display:grid;gap:8px"></div><div style="display:flex;gap:8px"><button class="btn primary" id="s4Save">Save</button></div><p class="note" id="s4Msg" role="status"></p>'
edit(H, '<div id="aEnv"></div>', MAIN, 'id="s4Main"')
ADV_OPEN = '<details id="sxAdv" style="margin:8px 0 0"><summary style="font-weight:800;cursor:pointer">Advanced</summary><p class="note">Rarely changed. Auto settings already choose most of these for you. Nothing here was removed.</p><div id="s4Adv" style="display:grid;gap:8px"></div>'
edit(H, "'+\n '<h3 style=\"margin:8px 0 0\">Big stake on strong setups</h3>", "'+\n '" + ADV_OPEN + "<h3 style=\"margin:8px 0 0\">Big stake on strong setups</h3>", 'id="sxAdv"')
edit(H, '</div><h3 style="margin:8px 0 0">Payments log</h3>', '</div></details><h3 style="margin:8px 0 0">Payments log</h3>', '</details><h3 style="margin:8px 0 0">Payments log')

JS = r'''
 /*S4S-start*/
 var S4M=[["risk_pct","Risk per trade %","n",0.1,2],["symbols","Markets (comma list, e.g. XAUUSD,BTCUSD)","s"],["max_open","Max open trades","n",1,10],["max_daily_loss_pct","Daily loss limit %","n",0.5,20],["max_weekly_loss_pct","Weekly loss limit %","n",1,40],["max_losing_streak","Stop after this many losses in a row (0 = off)","n",0,20],["streak_cooldown_h","Rest hours after that stop","n",0,72],["news_lock","News lock (no trades around big news)","c"],["rr","Take profit x (times the stop)","n",1,4],["max_stop_atr","Widest stop allowed (ATR)","n",0.8,5],["burst_enabled","Burst on","c"],["burst_ceiling","Burst: most positions at once","n",2,30],["burst_big_score","Burst: strategies that must agree for a big burst","n",2,10]],
  S4A=[["min_confluence","How many strategies must agree","n",1,6],["multi_min_score","Several entries: strategies that must agree","n",2,10],["regime_switch","Regime switch (pick strategies by market type)","c"],["auto_disable","Switch off losing strategies by themselves","c"],["auto_disable_min_trades","Losing strategies: trades needed first","n",5,500],["auto_markets","Auto markets (the bot adds markets itself)","c"],["auto_markets_max","Auto markets: most markets added","n",0,10],["symbols_pool","Markets pool for Auto markets (comma list)","s"],["max_trades_day","Max trades a day (0 = off)","n",0,100]];
 function s4Row(f){var id="s4_"+f[0];if(f[2]==="c")return'<label class="note" style="display:flex;gap:8px;align-items:center"><input type="checkbox" id="'+id+'"> '+esc(f[1])+'</label>';
  return'<div class="field"><label for="'+id+'">'+esc(f[1])+(f[2]==="n"?" ("+f[3]+" to "+f[4]+")":"")+'</label><input class="inp" id="'+id+'"'+(f[2]==="n"?' inputmode="decimal"':'')+'></div>'}
 $("#s4Main").innerHTML='<label class="note" style="display:flex;gap:8px;align-items:center"><input type="checkbox" id="s4Bot"> Bot on</label>'+S4M.map(s4Row).join("");
 $("#s4Adv").innerHTML=S4A.map(s4Row).join("")+'<div style="display:flex;gap:8px"><button class="btn primary" id="s4Save2">Save advanced</button></div>';
 function s4Fill(j){S4M.concat(S4A).forEach(function(f){var e=$("#s4_"+f[0]);if(!e)return;if(f[2]==="c")e.checked=j[f[0]]==="1";else e.value=j[f[0]]==null?"":j[f[0]]});var b=$("#s4Bot");if(b)b.checked=j.bot_enabled==="1"}
 function s4Body(list){var o={};for(var i=0;i<list.length;i++){var f=list[i],e=$("#s4_"+f[0]);if(!e)continue;
   if(f[2]==="c")o[f[0]]=e.checked?"1":"0";
   else if(f[2]==="s")o[f[0]]=String(e.value||"").toUpperCase().replace(/[^A-Z0-9.,]/g,"");
   else{var v=String(e.value).trim();if(v==="")continue;var n=+v;if(!isFinite(n)||n<f[3]||n>f[4])return{error:f[1]+" must be between "+f[3]+" and "+f[4]};o[f[0]]=String(n)}}
  return{body:o}}
 function s4Save(list,btn,withBot){var r=s4Body(list),m=$("#s4Msg");if(r.error){m.textContent=r.error;return tst(r.error)}btn.disabled=true;var on=withBot?$("#s4Bot").checked:null;
  SXA.api("/api/admin/settings",{method:"POST",body:r.body}).then(function(j){s4Fill(j);if(withBot){if((j.bot_enabled==="1")!==on)return SXA.api("/api/bot",{method:"POST",body:{on:on}}).then(function(){j.bot_enabled=on?"1":"0";s4Fill(j)})}}).then(function(){m.textContent="Saved.";tst("Saved")}).catch(function(e){m.textContent=e.message||"Not saved"}).then(function(){btn.disabled=false})}
 $("#s4Save").onclick=function(){s4Save(S4M,this,true)};$("#s4Save2").onclick=function(){s4Save(S4A,this,false)};
 SXA.api("/api/admin/settings",{method:"POST",body:{}}).then(s4Fill).catch(function(){});
 /*S4S-end*/
'''
edit(H, "\n function payLog(){", JS + " function payLog(){", '/*S4S-start*/')
print('done')
