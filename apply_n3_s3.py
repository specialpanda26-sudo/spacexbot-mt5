# apply_n3_s3.py - Nov 19: (1) no daily trade limit, (2) Section 3 finished: no fake numbers on Home for a signed-in person.
# Run from the repo root:  python apply_n3_s3.py   (safe to run twice: "already applied" the second time)
import os, sys
def edit(path, old, new):
    t = open(path, encoding='utf-8', newline='').read()
    if new in t: print('already applied:', path); return
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', repr(old[:70])); sys.exit(1)
    open(path, 'w', encoding='utf-8', newline='').write(t.replace(old, new)); print('edited:', path)

edit('backend/risk.py',
     '    since = int(now - now % 86400)\n    n = st.q("SELECT COUNT(*) n FROM signals WHERE created>=? AND status IN(\'pending\',\'sent\',\'open\',\'closed\') AND COALESCE(uid,\'\')=?", (since, uid), True)[\'n\']\n    if n >= int(st.fget(\'max_trades_day\')): return False, \'max trades today\'\n',
     '    since = int(now - now % 86400)\n    mt = int(st.fget(\'max_trades_day\') or 0)      # 0 = no daily trade limit (the stop loss and the loss limits protect the account)\n    if mt > 0:\n        n = st.q("SELECT COUNT(*) n FROM signals WHERE created>=? AND status IN(\'pending\',\'sent\',\'open\',\'closed\') AND COALESCE(uid,\'\')=?", (since, uid), True)[\'n\']\n        if n >= mt: return False, \'max trades today\'\n')

edit('backend/store.py',
     "DEFAULTS = {'bot_enabled': '0', 'risk_pct': os.getenv('RISK_PCT', '1.0'), 'max_open': os.getenv('MAX_OPEN', '3'),\n    'max_trades_day': os.getenv('MAX_TRADES_DAY', '6'), 'max_daily_loss_pct': os.getenv('MAX_DAILY_LOSS_PCT', '3.0'),\n",
     "DEFAULTS = {'bot_enabled': '0', 'risk_pct': os.getenv('RISK_PCT', '1.0'), 'max_open': os.getenv('MAX_OPEN', '3'),\n    'max_trades_day': os.getenv('MAX_TRADES_DAY', '0'), 'max_daily_loss_pct': os.getenv('MAX_DAILY_LOSS_PCT', '3.0'),\n")

edit('.env.example',
     'MAX_OPEN=3\nMAX_TRADES_DAY=6\n',
     'MAX_OPEN=3\nMAX_TRADES_DAY=0\n')

edit('static/index.html',
     '  var bu = vh.querySelector(".buddy-card"); vh.insertBefore(H, bu ? bu.nextSibling : vh.firstChild);\n',
     '  var bu = vh.querySelector(".buddy-card"); vh.insertBefore(H, bu ? bu.nextSibling : vh.firstChild);\n  var E = document.createElement("div"); E.className = "card"; E.id = "liveempty"; E.hidden = true; vh.insertBefore(E, H.nextSibling);\n')

edit('static/index.html',
     '    if (e && e.closest) a.push(e.closest(".card")); if (s) a.push(s); if (o && o.closest) a.push(o.closest(".card"));\n',
     '    if (e && e.closest) a.push(e.closest(".card")); if (s) a.push(s); if (o && o.closest) a.push(o.closest(".card"));\n    var g = document.getElementById("goals"); if (g && g.closest) a.push(g.closest(".grid2"));\n')

edit('static/index.html',
     '    if (!chip) return;\n',
     '    if (!chip) return;\n    var u0 = me();\n    if (k === "none" && u0 && u0.verified) {\n      var c0 = "chip watch app-only", h0 = \'<span class="dot"></span>Not connected\';\n      if (chip.className !== c0) chip.className = c0; if (chip.innerHTML !== h0) chip.innerHTML = h0; chip.title = "No broker connected yet. Connect one on the Connect tab."; return;\n    }\n')

edit('static/index.html',
     '    setChip(k);\n    if (k === "none") { H.hidden = S.hidden = true; H.style.display = S.style.display = "none"; if (LH || LB) { H.innerHTML = S.innerHTML = ""; LH = LB = ""; } showSamples(true); return; }\n',
     '    setChip(k);\n    if (k === "none") {\n      H.hidden = S.hidden = true; H.style.display = S.style.display = "none"; if (LH || LB) { H.innerHTML = S.innerHTML = ""; LH = LB = ""; }\n      if (u && u.verified) {      /* signed in: never show made-up numbers. Say what is missing instead. */\n        var eh = !D && FAIL < 3 ? \'<div class="card-head"><h2>Live account</h2></div><p class="note">Loading your account...</p>\'\n          : !D ? \'<div class="card-head"><h2>Live account</h2></div><p class="note">Cannot reach the server. Check your internet and try again.</p>\'\n          : \'<div class="card-head"><h2>No account connected yet</h2></div><p class="note">Your balance, profit today and open trades will show here as soon as a broker is connected. Nothing on this screen is invented.</p><button class="btn primary" type="button" data-go="connect">Connect a broker</button>\';\n        E.hidden = false; E.style.display = ""; if (E.innerHTML !== eh) E.innerHTML = eh; showSamples(false);\n      } else { E.hidden = true; E.style.display = "none"; showSamples(true); }\n      return;\n    }\n    E.hidden = true; E.style.display = "none";\n')

edit('tests/test_live3.py',
     "  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', 'Date', code)(document, {SXA}, SXA, f => timers.push(f), MO, {now: () => now});\n  const H = vh.inserted[0], S = vb.inserted[0];\n",
     "  new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', 'Date', code)(document, {SXA}, SXA, f => timers.push(f), MO, {now: () => now});\n  const H = vh.inserted[0], E = vh.inserted[1], S = vb.inserted[0];\n")

edit('tests/test_live3.py',
     "  const run = async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } };\n  return {H, S, chip, eq, stats, openList, vh, vb, calls, run, document, mo: () => MO.f(), setNow: v => { now = v; }, live: () => calls.filter(c => c.u === '/api/live')};\n",
     "  const run = async n => { for (let i = 0; i < n; i++) { timers[0](); await tick(); } };\n  return {H, E, S, chip, eq, stats, openList, vh, vb, calls, run, document, mo: () => MO.f(), setNow: v => { now = v; }, live: () => calls.filter(c => c.u === '/api/live')};\n")

edit('tests/test_live3.py',
     "  p = page(U, {user: U, next: ok(J({state: 'none', sources: [], balance: 0, equity: 0, today: 0, open: 0, trades: []}))}); await p.run(1);\n  OUT.push(['no broker connected: still sample data, honest chip, no Live card', p.live().length === 1 && p.H.hidden === true && p.chip.innerHTML.includes('Demo data') && p.chip.className === 'chip demo app-only' && p.eq.style.display !== 'none']);\n",
     '  p = page(U, {user: U, next: ok(J({state: \'none\', sources: [], balance: 0, equity: 0, today: 0, open: 0, trades: []}))}); await p.run(1);\n  OUT.push([\'no broker connected (signed in): NO sample numbers, chip says Not connected, a plain "No account connected yet" card with a Connect button\', p.live().length === 1 && p.H.hidden === true && p.E.hidden === false && p.E.innerHTML.includes(\'No account connected yet\') && p.E.innerHTML.includes(\'data-go="connect"\') && p.chip.innerHTML.includes(\'Not connected\') && !p.chip.innerHTML.includes(\'Demo data\') && p.eq.style.display === \'none\' && p.stats.style.display === \'none\' && p.openList.style.display === \'none\']);\n')

edit('tests/test_live3.py',
     "  st.next = ok(J({state: 'none', sources: [], balance: 0, equity: 0, today: 0, open: 0, trades: []})); await p.run(5);\n  OUT.push(['broker disconnected: the Live card goes, samples and the Demo data chip come back', p.H.hidden === true && p.chip.innerHTML.includes('Demo data') && p.chip.className === 'chip demo app-only' && p.eq.style.display === '' && p.stats.style.display === '' && p.openList.style.display === '']);\n",
     '  st.next = ok(J({state: \'none\', sources: [], balance: 0, equity: 0, today: 0, open: 0, trades: []})); await p.run(5);\n  OUT.push([\'broker disconnected: the Live card goes, the "No account connected yet" card shows, still no sample numbers\', p.H.hidden === true && p.E.hidden === false && p.E.innerHTML.includes(\'No account connected yet\') && p.chip.innerHTML.includes(\'Not connected\') && p.eq.style.display === \'none\' && p.stats.style.display === \'none\' && p.openList.style.display === \'none\']);\n')

edit('tests/test_live3.py',
     "  st3.user = {uid: 'u2', verified: true, active: true, admin: false}; st3.next = () => new Promise(() => {}); await p.run(1);\n  OUT.push(['another person signs in on this phone: the first person numbers disappear at once, before the new answer', was.includes('$1,004.70') && p.H.hidden === true && p.S.hidden === true && p.chip.innerHTML.includes('Demo data')]);\n",
     "  st3.user = {uid: 'u2', verified: true, active: true, admin: false}; st3.next = () => new Promise(() => {}); await p.run(1);\n  OUT.push(['another person signs in on this phone: the first person numbers disappear at once, before the new answer', was.includes('$1,004.70') && p.H.hidden === true && p.S.hidden === true && !p.H.innerHTML.includes('$1,004.70') && p.E.hidden === false && p.E.innerHTML.includes('Loading') && p.eq.style.display === 'none']);\n")

edit('docs/HANDOFF.md',
     '- The owner\'s MT5/EA path stays off until setting bot_enabled = 1 (default 0, risk.global_gate says "bot off"). Deriv needs DERIV_APP_ID + BROKER_KEY on Render, a verified token and the Start bot button. Render free sleeps after 15 min idle.\n- A signal needs 2 strategies to agree (min_confluence 2) unless the strategy has "may trade alone"; also max 6 trades a day, 60 min cooldown, news lock, no trades Sat/Sun or Fri after 20:00 UTC. First backtest: roughly break-even. Not proven.\n',
     '- The owner\'s MT5/EA path stays off until setting bot_enabled = 1 (default 0, risk.global_gate says "bot off"). Deriv needs DERIV_APP_ID + BROKER_KEY on Render, a verified token and the Start bot button. Render free sleeps after 15 min idle.\n- A signal needs 2 strategies to agree (min_confluence 2) unless the strategy has "may trade alone"; NO daily trade limit any more (max_trades_day default 0 = unlimited, tests/test_nolimit.py; if the Render variable MAX_TRADES_DAY or an old saved setting is above 0 it still applies), 60 min cooldown, news lock, no trades Sat/Sun or Fri after 20:00 UTC. First backtest: roughly break-even. Not proven.\n')

edit('docs/HANDOFF.md',
     '- 2 DONE  Account card on the Bot tab (/*S2-start*/ in static/index.html; tests/test_acct.py): broker balance, Demo/Real badge, switch, typing REAL, any switch stops the bot.\n- 3 TODO  Live stats: Home + header show the real balance, equity, today\'s profit in dollars, open trades, refreshed every few seconds; "Demo data" chip only when no broker is connected.\n',
     '- 2 DONE  Account card on the Bot tab (/*S2-start*/ in static/index.html; tests/test_acct.py): broker balance, Demo/Real badge, switch, typing REAL, any switch stops the bot.\n- 3 DONE (Nov 19)  Live stats: Home + header show the real balance, equity, today\'s profit in dollars, open trades, refreshed every few seconds; "Demo data" chip only when no broker is connected.\n')

edit('docs/HANDOFF.md',
     'Start now: tell me in one short line what you found in docs/HANDOFF.md, then give me the blocks for the next section.\n```\n',
     "Start now: tell me in one short line what you found in docs/HANDOFF.md, then give me the blocks for the next section.\n```\n\n## Nov 19 owner changes\n- Daily trade limit removed (risk.global_gate skips the check when max_trades_day is 0, default 0). Loss limits, max open trades, cooldown and the stop loss stay.\n- Section 3 finished: a signed-in person with no broker connected no longer sees sample equity, stats, open trades, Daily goals or Safety checks on Home; the chip says Not connected and a card says No account connected yet. Signed-out visitors still see the sample preview. Daily goals / Safety checks come back with real data in Sections 4 and 6.\n- Still fake (Section 6): Trades, Journal, Stats, Charts, Market. The Bot-tab Start/Pause button and 'Max trades a day' box only change a flag in the page (Section 4).\n")
