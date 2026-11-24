import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s: print('already done:', path, old[:40]); return
    if old not in s: sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)

R = 'backend/risk.py'
sub(R, "from . import store as st, news, links, limits, brokers as bk, roadmap", "from . import store as st, news, links, limits, brokers as bk, roadmap, userlim")
sub(R, "    if st.get('news_lock') == '1':\n        b, why = news.blocked(sym, now, st.fget('news_before_min'), st.fget('news_after_min'))\n        if b: return False, why\n",
       "    nb, na = userlim.news(uid)          # RS5: the person's own news lock (0 = off)\n    if nb > 0 or na > 0:\n        b, why = news.blocked(sym, now, nb, na)\n        if b: return False, why\n")
sub(R, "now - last['created'] < st.fget('cooldown_min') * 60", "now - last['created'] < userlim.val(uid, 'cooldown') * 60")
sub(R, "    net = exposure(uid); cap = int(st.fget('max_ccy_exposure'))\n    if cap <= 0: cap = 1000 if limits._owner(uid) else 2          # RS4: 0 = off for the owner; everyone else keeps 2\n",
       "    net = exposure(uid); cap = int(userlim.val(uid, 'same_dir'))\n    if cap <= 0: cap = 1000          # RS5: 0 = off (the person's own choice)\n")
sub(R, "    if bal and _pnl_since(day_since(uid, now), uid) <= -bal * st.fget('max_daily_loss_pct') / 100: return False, 'daily loss limit hit'\n    if bal and _pnl_since(_week_start(now), uid) <= -bal * st.fget('max_weekly_loss_pct') / 100: return False, 'weekly loss limit hit'\n",
       "    dl, wl = userlim.val(uid, 'daily_loss'), userlim.val(uid, 'weekly_loss')          # RS5: the person's own numbers (0 = off)\n    if bal and dl > 0 and _pnl_since(day_since(uid, now), uid) <= -bal * dl / 100: return False, 'daily loss limit hit'\n    if bal and wl > 0 and _pnl_since(_week_start(now), uid) <= -bal * wl / 100: return False, 'weekly loss limit hit'\n")
sub(R, "until = last[0]['closed'] + st.fget('streak_cooldown_h') * 3600 if last else 0", "until = last[0]['closed'] + userlim.val(uid, 'streak_rest') * 3600 if last else 0")

L = 'backend/limits.py'
sub(L, "    return _g('max_trades_day') if not uid else _cap(_num(_mine(uid).get('mt')), _g('max_trades_day'))", "    from . import userlim          # RS5: the person's own number; the owner's setting is for the owner's own bot\n    return int(userlim.val(uid, 'max_trades'))")
sub(L, "    return _g('max_losing_streak') if not uid else _cap(_num(_mine(uid).get('ks')), _g('max_losing_streak'))", "    from . import userlim          # RS5\n    return int(userlim.val(uid, 'streak'))")
sub(L, "    if not uid: return base\n    own = _num(_mine(uid).get('mo'))\n    return min(own, ceiling()) if own > 0 else base\n",
       "    if not uid or _owner(uid): return base\n    from . import userlim          # RS5: the person's own number (0 = off = the owner's server ceiling)\n    own = int(userlim.val(uid, 'max_open'))\n    return min(own, ceiling()) if own > 0 else ceiling()\n")

K = 'backend/risk_alerts.py'
sub(K, "from . import store as st, push, limits, risk, lag", "from . import store as st, push, limits, risk, lag, userlim")
sub(K, "limit=_num(st.fget('max_daily_loss_pct'))); return 11", "limit=_num(userlim.val(uid, 'daily_loss'))); return 11")
sub(K, "limit=_num(st.fget('max_weekly_loss_pct'))); return 12", "limit=_num(userlim.val(uid, 'weekly_loss'))); return 12")
sub(K, "until = int(last + st.fget('streak_cooldown_h') * 3600)", "until = int(last + userlim.val(uid, 'streak_rest') * 3600)")
sub(K, "lim = st.fget('max_daily_loss_pct'); loss =", "lim = userlim.val(uid, 'daily_loss'); loss =")

A = 'backend/app.py'
sub(A, "from . import risk_alerts, system_alerts,", "from . import userlim, risk_alerts, system_alerts,")
sub(A, "day_loss_limit=st.fget('max_daily_loss_pct'),", "day_loss_limit=userlim.val(sc, 'daily_loss'),")
sub(A, "news_lock=st.get('news_lock') == '1', exposure=risk.exposure(sc)", "news_lock=max(userlim.news(sc)) > 0, exposure=risk.exposure(sc)")
sub(A, "@app.get('/api/trade/<int:tid>')",
'''@app.get('/api/mylimits')
@need(verified=True)
def mylimits_api(u):
    """RS5: this person's own limits, with the plain-words guide for each."""
    return jsonify(userlim.view(_mine(u)))

@app.post('/api/mylimits')
@need(verified=True)
def mylimits_save_api(u):
    """RS5: save this person's limits ({key: number}, 0 = off) or go back to the start values ({"reset": true})."""
    j = _j(); uid = _mine(u)
    try: return jsonify(userlim.reset(uid) if j.get('reset') else userlim.save(uid, j))
    except ValueError as e: return jsonify(error=str(e)), 400

@app.get('/api/trade/<int:tid>')''')

H = 'static/index.html'
sub(H, " /*BT1-end*/\n",
''' /*BT1-end*/
 /*LM1-start*/
 vb.insertBefore(card(["My limits",'<span class="chip info" id="lmChip"></span>'],'<p class="note" id="lmIntro"></p><div id="lmRows" style="display:grid;gap:14px"></div><div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0"><button type="button" class="btn" id="lmSave">Save my limits</button><button type="button" class="btn" id="lmReset">Back to start values</button></div><p class="note" id="lmMsg" role="status"></p>'),vb.firstChild);
 function lmShow(j){$("#lmChip").textContent=j.mode==="real"?"Real account":j.mode==="owner"?"Owner":"Demo account";$("#lmIntro").textContent=j.intro||"";var h="";
  (j.fields||[]).forEach(function(f){h+='<div class="field"><label for="lm_'+f.key+'">'+esc(f.label)+' ('+f.lo+' to '+f.hi+', 0 = off)</label><input class="inp" id="lm_'+f.key+'" type="number" inputmode="decimal" min="'+f.lo+'" max="'+f.hi+'" step="'+f.step+'" value="'+f.value+'"><details><summary class="note">What this does</summary><p class="note"><b>When you set it:</b> '+esc(f.on)+'</p><p class="note"><b>Example:</b> '+esc(f.example)+'</p><p class="note"><b>When it is 0 (off):</b> '+esc(f.off)+'</p><p class="note">Start value on a real account: '+f.safe+'</p></details></div>'});$("#lmRows").innerHTML=h}
 function lmLoad(){if(!window.SXA)return;SXA.api("/api/mylimits").then(lmShow).catch(function(){})}
 $("#lmSave").onclick=function(){var b=this,body={};$$("#lmRows input").forEach(function(i){var v=parseFloat(i.value);body[i.id.slice(3)]=isNaN(v)?0:v});b.disabled=true;
  SXA.api("/api/mylimits",{method:"POST",body:body}).then(function(j){lmShow(j);$("#lmMsg").textContent="Saved. The bot uses these on its next check, about a minute."}).catch(function(e){$("#lmMsg").textContent=e.message||"Not saved"}).then(function(){b.disabled=false})};
 $("#lmReset").onclick=function(){if(!confirm("Go back to the start values?"))return;var b=this;b.disabled=true;
  SXA.api("/api/mylimits",{method:"POST",body:{reset:true}}).then(function(j){lmShow(j);$("#lmMsg").textContent="Back to the start values."}).catch(function(e){$("#lmMsg").textContent=e.message||"Not saved"}).then(function(){b.disabled=false})};
 lmLoad();
 /*LM1-end*/
''')
sub('tests/test_au1.py', "'max_ccy_exposure': 0, 'multi_entries': 11", "'max_ccy_exposure': 11, 'multi_entries': 11")
sub('tests/test_sm1.py', "'Stake per entry ($, Deriv needs 1 or more)' in html", "'Stake per entry ($) - Deriv only, needs 1 or more' in html")
sub('backend/limits.py', "return dict(mo, **{'max_trades': _cap(_num(m.get('mt')), ct) if _num(m.get('mt')) else 0, 'streak': _cap(_num(m.get('ks')), cs) if _num(m.get('ks')) else 0, 'cap_trades': ct, 'cap_streak': cs})", "return dict(mo, **{'max_trades': _num(m.get('mt')), 'streak': _num(m.get('ks')), 'cap_trades': 0, 'cap_streak': 0})          # RS5: the owner's numbers no longer cut a person's own")
sub('tests/test_limits.py', "r.json['streak'] == 0 and r.json['cap_streak'] == 3)", "r.json['streak'] == 0 and r.json['cap_streak'] == 0)")
sub('tests/test_limits.py', "T('streak: the owner 3 closes it at three losses', gate('u1')[0] is False and 'losses in a row' in gate('u1')[1])", "T('streak: a demo person with no own number has the stop off (RS5)', gate('u1') == (True, 'ok'))")
sub('tests/test_limits.py', "limits.save(JU, 20); T('own number above the owner cap is cut to the cap', limits.trades(JU) == 8 and limits.view(JU)['max_trades'] == 8)", "limits.save(JU, 20); T('own number is no longer cut by the owner cap (RS5)', limits.trades(JU) == 20 and limits.view(JU)['max_trades'] == 20)")
sub('tests/test_limits.py', "limits.save(JU, 0); T('0 means use the owner setting', limits.trades(JU) == 8 and limits.view(JU)['max_trades'] == 0)", "limits.save(JU, 0); T('0 means back to the start value, not the owner setting (RS5)', limits.trades(JU) == 0 and limits.view(JU)['max_trades'] == 0)")
sub('tests/test_limits.py', "T('the owner lowering the cap applies at once, even to a saved number', limits.trades(JU) == 3)", "T('the owner changing his own cap does not touch a saved number (RS5)', limits.trades(JU) == 5)")
sub('tests/test_limits.py', "limits.save(JU, None, 9); T('streak: own number above the owner is cut to it', limits.streak(JU) == 3)", "limits.save(JU, None, 9); T('streak: own number is no longer cut by the owner (RS5)', limits.streak(JU) == 9)")
sub('tests/test_limits.py', "T('a subscriber cannot go above the owner cap', r.json['max_trades'] == 4 and r.json['cap_trades'] == 4 and limits.trades(JU) == 4)", "T('a subscriber picks their own number, the owner cap does not cut it (RS5)', r.json['max_trades'] == 9 and r.json['cap_trades'] == 0 and limits.trades(JU) == 9)")
sub('tests/test_limits.py', "T('the owner cap closes a subscriber with no own number', gate('u2') == (False, 'max trades today') and gate('u1') == (True, 'ok'))", "T('the owner cap does not close a subscriber (RS5)', gate('u2') == (True, 'ok') and gate('u1') == (True, 'ok'))")
print('RS5 done')
