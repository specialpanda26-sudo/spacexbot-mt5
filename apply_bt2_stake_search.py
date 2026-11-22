"""BT2 patch: (1) burst stake per entry that the person can edit (default 0.5 USD, 0 = normal sizing), used by the Deriv engine;
(2) Deriv now closes a burst group when the entries together reach entries x target per entry (before, only a 'group target' did);
(0) renames the Burst card's ids (btOn, btMsg clashed with the admin Bitcoin-weekend switch, so the switch could bind to the wrong button); (3) the Burst card moves to the TOP of the Bot tab, with the stake field and a live line (6 entries x 1 USD = closes at 6 USD);
(4) a 'Find a setting' search box at the top of the Bot tab: type what you want in plain words, it shows the matching setting cards and jumps to them.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_bt2_stake_search.py"""
import sys, re
B, D, G, F, H = 'backend/burst.py', 'backend/deriv.py', 'backend/deriv_group.py', 'static/index.html', 'docs/HANDOFF.md'
FIXED = '''

def fixed_size(entry, sl, tp, bal, stake, mult):
    """BT2: (stake, stop_loss_money, take_profit_money) or None. The person chose the stake of each burst entry (Deriv). Same multiplier maths as
    deriv._size: the loss at the stop = stake x multiplier x stop distance, and it must stay under the stake. Deriv itself decides if the stake is big enough."""
    try: entry, sl, tp, bal, stake, mult = float(entry), float(sl), float(tp), float(bal), float(stake), float(mult)
    except (TypeError, ValueError): return None
    if not entry or entry == sl or entry == tp or bal <= 0 or stake <= 0 or mult <= 0: return None
    risk = round(stake * mult * abs(entry - sl) / entry, 2)
    if stake > bal * 0.5 or risk <= 0 or risk >= stake: return None
    return round(stake, 2), risk, round(risk * abs(tp - entry) / abs(entry - sl), 2)
'''
SAVE_STAKE = '''    if 'stake_usd' in d:
        try: sv = float('nan') if isinstance(d['stake_usd'], bool) else float(d['stake_usd'])
        except (TypeError, ValueError): sv = float('nan')
        if sv != sv or not (sv == 0 or 0.1 <= sv <= USD_HI): raise ValueError('Stake per entry must be 0 (normal sizing) or from 0.1 to %g USD' % USD_HI)
        new['stake_usd'] = round(sv, 2)
'''
HELP = '''def _burst_stake(sig):
    """BT2: the stake the person chose for each entry of a burst group (0 = none, use the normal sizing)."""
    try:
        from . import burst
        g = sig['grp']; m = burst.meta(g) if g else None
        return float(m.get('stake') or 0) if m and m.get('k') in ('quick', 'big') else 0.0
    except Exception: return 0.0

'''
PY = [
 (B, "DEF = {'on': False, 'idle_min': 5, 'quick_n': 5, 'big_n': 15, 'quick_usd': 0.5, 'big_usd': 1.0, 'giveback': 40}", "DEF = {'on': False, 'idle_min': 5, 'quick_n': 5, 'big_n': 15, 'quick_usd': 0.5, 'big_usd': 1.0, 'giveback': 40, 'stake_usd': 0.5}"),
 (B, "'giveback': _clamp(j.get('giveback'), 0, 90, DEF['giveback'])}", "'giveback': _clamp(j.get('giveback'), 0, 90, DEF['giveback']),\n            'stake_usd': round(_clamp(j.get('stake_usd'), 0, USD_HI, DEF['stake_usd'], float), 2)}"),
 (B, "    cur.update(new)\n", SAVE_STAKE + "    cur.update(new)\n"),
 (B, "'giveback': p['giveback'], 'score': int(score or 0)}, 'ok'", "'giveback': p['giveback'], 'score': int(score or 0), 'stake': p['stake_usd']}, 'ok'"),
 (B, "gm = {'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now}", "gm = {'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now, 'stake': pl.get('stake', 0)}"),
 (B, "    st.put('bg:%d' % first, json.dumps(gm))", "    if not gr: gm['dtgt'] = round(float(pl['each']) * n, 2)          # BT2: the Deriv engine closes the group when the entries together reach entries x target each\n    st.put('bg:%d' % first, json.dumps(gm))"),
 (D, "def _place(sess, sig, bal, cur):", HELP + "def _place(sess, sig, bal, cur):"),
 (D, "    from . import stake as stk\n", "    from . import stake as stk\n    bs = _burst_stake(sig)          # BT2: a burst entry with a stake the person chose\n"),
 (D, "        z = (want and stk.size(sig['entry'], sig['sl'], sig['tp'], bal, want, m)) or _size(sig['entry'], sig['sl'], sig['tp'], bal, sig['risk_pct'], m)",
     "        if bs:\n            from . import burst\n            z = burst.fixed_size(sig['entry'], sig['sl'], sig['tp'], bal, bs, m)\n        else: z = (want and stk.size(sig['entry'], sig['sl'], sig['tp'], bal, want, m)) or _size(sig['entry'], sig['sl'], sig['tp'], bal, sig['risk_pct'], m)"),
 (G, "m = _meta(g); tgt = _f((m or {}).get('tgt')) or 0", "m = _meta(g); tgt = _f((m or {}).get('tgt')) or _f((m or {}).get('dtgt')) or 0"),
]
JS = [
 # the Burst card goes to the TOP of the Bot tab
 (F, "vb.appendChild(card([\"Burst mode\",", "vb.insertBefore(card([\"Burst mode\","),
 (F, "<label for=\"bswUsd\">Target per entry ($)</label>", "<label for=\"bswStake\">Stake per entry ($)</label><input class=\"inp\" id=\"bswStake\" type=\"number\" min=\"0\" step=\"0.05\" inputmode=\"decimal\" placeholder=\"0.5\"></div><div class=\"field\"><label for=\"bswUsd\">Target per entry ($)</label>"),
 (F, "<p class=\"note\" id=\"bswMsg\" role=\"status\"></p>", "<p class=\"note\" id=\"bswPrev\"></p><p class=\"note\" id=\"bswMsg\" role=\"status\"></p>"),
 (F, "Deriv refuses a stake under 1 USD. Try it on a demo account first.</p>'));", "Stake per entry is the money each entry puts in on Deriv (0 = the normal sizing); Deriv decides its own smallest stake and tells you if it refuses one. Try it on a demo account first.</p>'),vb.firstChild);"),
 (F, "$(\"#bswUsd\").value=s.quick_usd||\"\";", "$(\"#bswUsd\").value=s.quick_usd||\"\";$(\"#bswStake\").value=s.stake_usd==null?\"\":s.stake_usd;bswPrev();"),
 (F, " function bswLoad(){", " function bswPrev(){var n=parseFloat($(\"#bswN\").value)||0,u=parseFloat($(\"#bswUsd\").value)||0;$(\"#bswPrev\").textContent=n&&u?(n+\" entries x \"+u+\" USD each: the group closes at \"+(Math.round(n*u*100)/100)+\" USD in total.\"):\"\"}\n $(\"#bswN\").oninput=bswPrev;$(\"#bswUsd\").oninput=bswPrev;\n function bswLoad(){"),
 (F, "if(i)body.idle_min=i;", "var sk=$(\"#bswStake\").value.trim();if(sk!==\"\")body.stake_usd=parseFloat(sk);if(i)body.idle_min=i;"),
]
SEARCH = r'''/*BT2-start*/
 (function(){
  var st=document.createElement("style");st.textContent=".sxflash{outline:3px solid var(--accent,#7c5cff);outline-offset:3px;transition:outline-color .6s}.sxfind button.hit{display:block;width:100%;text-align:left;padding:12px 0;border:0;border-top:1px solid var(--line);background:none;color:inherit;font:inherit;cursor:pointer}.sxfind button.hit small{display:block;opacity:.7}";document.head.appendChild(st);
  var STOP="the a an i me my is am are to for of in on and or it that this with want need how do can where what which please find search searching looking look setting settings option options change set turn use bot has have show tell about way method per at be so".split(" ");
  var SYN={busy:"burst quiet signal",quiet:"burst",scalp:"burst",scalping:"burst",quick:"burst profit",fast:"burst",small:"burst profit",
   stake:"stake entry entries amount",amount:"stake",money:"stake target",entries:"entry positions group",positions:"entries group",
   profit:"target profit",target:"profit group",win:"profit target",lose:"loss limit stop",losing:"loss limit",loss:"loss limit stop",limit:"limit loss",
   repeat:"cycle",again:"cycle",auto:"cycle auto",cycle:"next group",switch:"switch",daily:"daily session limits",day:"daily session limits",
   password:"security password",security:"security",notification:"notifications",notifications:"notifications push alerts",alert:"notifications",alerts:"notifications",
   privacy:"privacy data",delete:"privacy data account",email:"account email",risk:"risk limits trade",lot:"lot size calculator",lots:"lot size calculator",
   strategy:"strategy strategies",strategies:"strategy",mode:"mode demo real",demo:"mode demo",real:"mode real",news:"safety gates news",gate:"safety gates",gates:"safety gates",
   memory:"bot memory learn",learn:"bot memory learn",backtest:"backtest test",check:"run check"};
  var FB=[["Notifications","profile","notification notifications alert alerts push sound"],["Security","profile","security password login"],["Privacy and data","profile","privacy data delete export"],["Account","profile","account plan email subscription"],["Trading profile","profile","trading profile experience"]];
  var VIEWS3=["bot","profile","connect","trades","home"];
  function words(q){var o=[],seen={};q.toLowerCase().replace(/[^a-z0-9 ]/g," ").split(/\s+/).forEach(function(w){if(w.length<2||STOP.indexOf(w)>=0||seen[w])return;seen[w]=1;o.push({w:w,o:1})});o.slice().forEach(function(a){(SYN[a.w]||"").split(" ").forEach(function(x){if(x&&!seen[x]){seen[x]=1;o.push({w:x,o:0})}})});return o}
  function scan(){var out=[];VIEWS3.forEach(function(v){var r=document.getElementById("view-"+v);if(!r)return;Array.prototype.forEach.call(r.querySelectorAll(".card"),function(c){var h=c.querySelector("h2");if(!h)return;var t=h.textContent.trim();if(!t||c.classList.contains("sxfind"))return;out.push({v:v,c:c,t:t,tl:t.toLowerCase(),x:(c.textContent||"").toLowerCase()})})});return out}
  function find(q){var w=words(q);if(!w.length)return[];var seen={},res=[];
   scan().forEach(function(k){var s=0;w.forEach(function(x){if(k.tl.indexOf(x.w)>=0)s+=x.o?6:4;else if(k.x.indexOf(x.w)>=0)s+=x.o?2:1});if(s>0){seen[k.tl]=1;res.push({s:s,v:k.v,c:k.c,t:k.t})}});
   FB.forEach(function(f){if(seen[f[0].toLowerCase()])return;var s=0;w.forEach(function(x){if(f[2].indexOf(x.w)>=0)s+=x.o?4:2});if(s>0)res.push({s:s,v:f[1],c:null,t:f[0]})});
   res.sort(function(a,b){return b.s-a.s});return res.slice(0,5)}
  function go(r){var h="#"+r.v;if(location.hash!==h)location.hash=h;else window.dispatchEvent(new Event("hashchange"));
   setTimeout(function(){var c=r.c;if(!c||!document.body.contains(c)){var f=scan().filter(function(k){return k.t===r.t&&k.v===r.v})[0];c=f&&f.c}if(!c)return;c.scrollIntoView({behavior:"smooth",block:"center"});c.classList.add("sxflash");setTimeout(function(){c.classList.remove("sxflash")},2600)},260)}
  var box=card(["Find a setting",""],'<div class="field"><label for="sxQ">What do you want to do?</label><input class="inp" id="sxQ" type="search" placeholder="e.g. burst, stake per entry, daily loss, notifications" autocomplete="off"></div><div id="sxR" role="status"></div>');
  box.classList.add("sxfind");vb.insertBefore(box,vb.firstChild);
  var q=box.querySelector("#sxQ"),R=box.querySelector("#sxR");
  q.oninput=function(){var v=q.value.trim();R.textContent="";if(v.length<2)return;var m=find(v);
   if(!m.length){R.innerHTML='<p class="note">No setting matched. Try words like burst, stake, profit target, daily loss, repeat, notifications.</p>';return}
   m.forEach(function(r){var b=document.createElement("button");b.type="button";b.className="hit";var sn=r.c?((r.c.querySelector(".note")||{}).textContent||"").slice(0,90):"";b.innerHTML="<b></b><small></small>";b.firstChild.textContent=r.t+"  ·  "+({bot:"Bot tab",profile:"Profile",connect:"Connect",trades:"Trades",home:"Home"}[r.v]||r.v);b.lastChild.textContent=sn;b.onclick=function(){go(r)};R.appendChild(b)})};
 })();
 /*BT2-end*/'''
def fix_old_test():
    T = 'tests/test_burst1.py'
    try: t = open(T, encoding='utf-8').read()
    except OSError: return
    a = "p == {'on': False, 'idle_min': 5, 'quick_n': 5, 'big_n': 15, 'quick_usd': 0.5, 'big_usd': 1.0, 'giveback': 40})"; b = a.replace("'giveback': 40}", "'giveback': 40, 'stake_usd': 0.5}")
    if t.count(a) == 1: open(T, 'w', encoding='utf-8').write(t.replace(a, b)); print('updated', T, '(defaults now include stake_usd)')

def run():
    fix_old_test()
    texts = {}
    for p in (B, D, G, F, H): texts[p] = open(p, encoding='utf-8').read()
    done = '/*BT2-start*/' in texts[F]
    if done: print('already patched'); return
    new = dict(texts)
    a0, b0 = new[F].find('/*BT1-start*/'), new[F].find('/*BT1-end*/')
    if a0 < 0 or b0 < a0: sys.exit('STOP: BT1 block not found; run apply_bt1_burst_card.py first')
    blk = new[F][a0:b0]
    for o in ('btChip', 'btOn', 'btNow', 'btIdle', 'btN', 'btUsd', 'btSave', 'btMsg', 'btShow', 'btLoad'): blk = re.sub(r'(?<![A-Za-z])' + o + r'(?![A-Za-z])', 'bsw' + o[2:], blk)          # the old ids clashed with the admin Bitcoin-weekend switch (btOn, btMsg)
    new[F] = new[F][:a0] + blk + new[F][b0:]
    for p, old, rep in PY + JS:
        if new[p].count(old) != 1: sys.exit('STOP: text not found exactly once in %s: %s' % (p, old[:70]))
        new[p] = new[p].replace(old, rep)
    if new[B].count('def fixed_size(') == 0: new[B] = new[B].rstrip('\n') + '\n' + FIXED
    e = '/*BT1-end*/'
    if new[F].count(e) != 1: sys.exit('STOP: BT1 block not found; run apply_bt1_burst_card.py first')
    new[F] = new[F].replace(e, e + '\n ' + SEARCH)
    MARK = '## Section BT2 (burst stake, Deriv group close, Find a setting)'
    if MARK not in new[H]:
        new[H] = new[H].rstrip('\n') + '\n\n\n' + MARK + """ DONE (Nov 23)
- Burst setting stake_usd (default 0.5, 0 = normal sizing, else 0.1 to 1000) in backend/burst.py, saved in the group meta. deriv._place uses burst.fixed_size for a burst entry with a stake: stake = the chosen amount, stop loss money = stake x multiplier x stop distance (must stay under the stake), take profit = that x the setup's reward ratio. The old 'under 1 USD refused' rule still applies to NORMAL Deriv sizing; for burst entries Deriv itself decides the smallest stake (its refusal text is shown). NOT tried against the real Deriv API.
- Deriv group close: burst create() now also saves dtgt = entries x target each when the person has no group target; deriv_group.check uses tgt or dtgt. MT5 is unchanged (it ignores dtgt). A burst is still never cycled.
- Bot tab: Burst card moved to the TOP with Stake per entry + a live line (6 entries x 1 USD ... closes at 6 USD). New card 'Find a setting' above it: type plain words, it scores every card in Bot, Profile, Connect, Trades, Home (title and text, plus a small word list: busy, scalp, stake, repeat...) and jumps to the card with a highlight. It is a keyword search, not an AI model. Profile cards only exist after the profile page was opened once, so a small built-in list covers Notifications, Security, Privacy and data, Account, Trading profile.
- Tests: tests/test_bt2.py.
"""
    for p in (B, D, G, F, H): open(p, 'w', encoding='utf-8').write(new[p])
    print('patched', B, D, G, F, H)
run()
