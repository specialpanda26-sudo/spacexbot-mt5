"""SW2 patch (strategy switching): the bot already switches between trend and reversal strategies by market type (ADX), and the owner could switch on a
"learned switch" for everyone, but nobody could SEE it and a person had no switch of their own. Now, in plain view on the Bot tab under Burst mode:
  - a "Strategy switching" card that explains the automatic part with the real ADX limits, shows the latest market reading and each strategy's results per market type,
  - a "Learned switch" for the person: pause a strategy in a market type where THEIR OWN closed trades keep losing (off by default, owner's switch still works, Auto settings still turns it off).
Files: backend/prefs.py (new choice 'regime'), backend/app.py (3 places use it + GET /api/regimes), backend/screenread.py, static/index.html, docs/HANDOFF.md.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_sw2_switching.py"""
import sys
P, A, S, H, D = 'backend/prefs.py', 'backend/app.py', 'backend/screenread.py', 'static/index.html', 'docs/HANDOFF.md'
OLD_ORF = "st.get('regime_switch') == '1' else None"
NEW_ORF = "(st.get('regime_switch') == '1' or prefs.get(uid)['regime']) else None"
ROUTE = r'''@app.get('/api/regimes')
@need(verified=True)
def regimes_mine(u):
    """SW2: strategy switching by market type, in plain view. The automatic part (ADX limits from brain.evaluate) always runs; the learned switch is the owner's
    setting OR this person's own choice (prefs 'regime'), and Auto settings turns it off. Rows = this person's closed trades by strategy and market type."""
    import inspect
    from . import strategies as S
    sc = _mine(u); mine = bool(prefs.get(sc)['regime']); owner = st.get('regime_switch') == '1'; auto = bool(automode.on()); on = (owner or mine) and not auto
    mt = max(stats.MIN_FLOOR, int(st.fget('regime_min_trades'))); weak = stats.regime_off(sc, mt); rows = []
    for n, cells in sorted(stats.by_regime(sc).items()):
        for rg, c in sorted(cells.items()):
            w = rg in weak.get(n, ()); rows.append(dict(c, strategy=n, name=si.name(n), group=si.group(n, S.TREND, S.REVERSION), regime=rg, weak=w, paused=bool(w and on)))
    mk, age = '', None; last = botstate._last(sc)
    if last:
        m = re.search(r'Market: [^.]*\.', str(last.get('w') or ''))
        if m: mk = m.group(0); age = max(0, int(time.time()) - int(last.get('t') or 0))
    pr = inspect.signature(brain.evaluate).parameters
    return jsonify(owner=owner, mine=mine, auto=auto, active=on, min_trades=mt, adx_quiet=pr['adx_trend_min'].default, adx_strong=pr['adx_rev_max'].default, market=mk, market_age=age, rows=rows)

'''
CARD = r'''/*BT1-end*/
 /*SW2-start*/
 vb.insertBefore(card(["Strategy switching",'<span class="chip info" id="swcChip"></span>'],'<p class="note" id="swcAuto"></p><p class="note" id="swcMarket" role="status"></p><button type="button" class="switch" role="switch" aria-checked="false" id="swcOn"><span><b>Learned switch</b><small>Pause a strategy in a market type where my own closed trades keep losing. Off by default.</small></span><span class="sw"></span></button><p class="note" id="swcNow" role="status"></p><div id="swcRows" style="display:grid;gap:6px"></div><p class="note" id="swcMsg" role="status"></p>'),(function(){var b=$("#bswOn"),c=b&&b.closest?b.closest(".card"):null;return c&&c.nextSibling?c.nextSibling:vb.firstChild})());
 var swcMine=false;
 function swcAge(s){return s==null?"":s<60?"under a minute":s<5400?Math.round(s/60)+" min":Math.round(s/3600)+" h"}
 function swcShow(j){swcMine=j.mine===true;$("#swcOn").setAttribute("aria-checked",swcMine);
  $("#swcChip").textContent=j.auto?"Auto settings":j.active?"Learned switch on":"Automatic only";
  $("#swcAuto").textContent="The bot reads the market type from ADX, by itself, every time. Above "+j.adx_strong+" is a strong trend: trend strategies lead and reversal setups are skipped. Below "+j.adx_quiet+" is quiet: reversal strategies lead and trend setups are skipped. In between, both kinds are allowed. This part needs no switch.";
  $("#swcMarket").textContent=j.market?"Latest reading ("+swcAge(j.market_age)+" ago): "+j.market:"No market reading yet. It appears after the bot's next check.";
  $("#swcNow").textContent=j.auto?"Auto settings is on, so the learned switch does nothing right now.":j.owner?"The owner has the learned switch on for everyone, so it stays on whatever you choose here.":j.active?"On. A strategy is paused in a market type only after "+j.min_trades+" or more of your closed trades there, and only while it loses on average. Your own trades are used.":"Off. Turn it on and the bot pauses a strategy in a market type where it keeps losing, after "+j.min_trades+" or more of your own closed trades there.";
  var rs=j.rows||[];$("#swcRows").innerHTML=rs.length?rs.map(function(r){return'<p class="note"><b>'+esc(r.name)+'</b> ('+(r.group==="reversion"?"reversal":"trend")+') in a '+esc(r.regime)+' market: '+r.n+(r.n>1?" trades, ":" trade, ")+r.win_rate+'% wins, average '+r.avg+(r.paused?' - <b>paused here</b>':r.weak?' - losing here, not paused because the switch is off':'')+'</p>'}).join(""):'<p class="note">No results by market type yet. Every trade the bot opens saves its market type, so this fills in as you trade.</p>'}
 function swcLoad(){if(!window.SXA)return;SXA.api("/api/regimes").then(swcShow).catch(function(){})}
 $("#swcOn").onclick=function(){var b=this;if(!window.SXA){toast("Sign in first");return}
  var want=!swcMine;b.disabled=true;b.setAttribute("aria-checked",want);
  SXA.api("/api/prefs",{method:"POST",body:{regime:want}}).then(function(){toast(want?"Learned switch on":"Learned switch off");return SXA.api("/api/regimes")}).then(swcShow).catch(function(e){b.setAttribute("aria-checked",swcMine);toast(e.message||"Not saved")}).then(function(){b.disabled=false})};
 swcLoad();
 /*SW2-end*/'''
def patch(path, pairs, mark):
    s = open(path, encoding='utf-8').read()
    if mark in s: print(path, 'already patched'); return
    for o, n in pairs:
        if s.count(o) != 1: sys.exit('STOP: anchor found %d times in %s: %s' % (s.count(o), path, o[:70]))
    for o, n in pairs: s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s); print('patched', path)
patch(P, [("'scale': j.get('scale') is True, 'fast': j.get('fast') is True}", "'scale': j.get('scale') is True, 'fast': j.get('fast') is True, 'regime': j.get('regime') is True}"),
          ("for k in ('alone', 'scale', 'fast'):", "for k in ('alone', 'scale', 'fast', 'regime'):"),
          ("  fast       : True = also scan 5-minute candles", "  regime     : True = the learned switch for me: pause a strategy in a market type where my own closed trades keep losing (the owner's switch also works).\n  fast       : True = also scan 5-minute candles")],
      "'regime': j.get('regime') is True")
patch(A, [(OLD_ORF + "          # R3:", NEW_ORF + "          # R3:"),
          (OLD_ORF + "\n    off, solo, _mc = prefs.apply(", NEW_ORF + "\n    off, solo, _mc = prefs.apply("),
          ("@app.get('/api/admin/regimes')", ROUTE + "@app.get('/api/admin/regimes')")], "def regimes_mine")
patch(S, [(OLD_ORF, NEW_ORF)], "prefs.get(uid)['regime']")
patch(H, [('/*BT1-end*/', CARD)], '/*SW2-start*/')
MARK = '## Section SW2 (strategy switching, in plain view)'; h = open(D, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has SW2')
else:
    open(D, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 24)
- Finding: the bot already switches strategies by market type (brain.evaluate: ADX above 28 skips reversal setups, below 18 skips trend setups) and the owner could switch on the learned switch (setting regime_switch, per-strategy per-market-type results, stats.regime_off). Nothing showed this to a person, /api/admin/regimes had no screen, and a person had no switch of their own.
- New: prefs choice 'regime' (default off). The learned switch is on when the owner's regime_switch is on OR the person's own choice is on; Auto settings still turns it off. Used in 3 places: backend/app.py (scan and burst scan) and backend/screenread.py (dry run). Uses the person's own closed trades only, never fewer than regime_min_trades (at least 5).
- New: GET /api/regimes (verified user): owner, mine, auto, active, min_trades, the real ADX limits, the latest market reading from the last scan note, and rows per strategy per market type (weak, paused).
- Bot tab: card "Strategy switching" right under Burst mode (block /*SW2-start*/ .. /*SW2-end*/). Explains the automatic part, shows the latest reading, the learned switch, and the per-market results.
- Not built: choosing a fixed strategy per market type by hand (the Profile page lets a person pick which strategies may trade). The latest reading is the last market the bot looked at (any market), only shown when the last check left a market sentence. Not checked on a real phone. Tests: tests/test_sw2.py.
''')
    print('HANDOFF updated')
