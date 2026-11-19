"""Section 7: the Connect tab shows the REAL bridge status (GET /api/bridge) instead of the made-up "No signal from ... next build step" message.
Safe to run twice: every old text must appear exactly once, otherwise nothing is written."""
import sys
FILES = {}
def rd(p):
    if p not in FILES: FILES[p] = open(p, encoding='utf-8', newline='').read()
    return FILES[p]
def edit(p, old, new, marker):
    t = rd(p)
    if marker in t: print('skip (already in):', p, marker[:40]); return
    if t.count(old) != 1: print('STOP: cannot find exactly once in', p, '->', old[:70].replace('\n', ' '), t.count(old)); sys.exit(1)
    FILES[p] = t.replace(old, new); print('ok  ', p, marker[:40])

edit('backend/app.py', 'livestats, limits, journal\n', 'livestats, limits, journal, bridge\n', ', journal, bridge')
edit('backend/app.py', "@app.get('/api/botstate')\n", '''@app.get('/api/bridge')
@need(verified=True)
def bridge_api(u):
    """Section 7: is the MT5 bridge reporting, which account, demo or real, and plain setup help (nothing made up)."""
    site = (os.getenv('BASE_URL') or '').strip().rstrip('/')
    if not site.startswith('http'): site = request.host_url.rstrip('/'); site = site.replace('http://', 'https://') if 'localhost' not in site and '127.0.0.1' not in site else site
    return jsonify(bridge.describe(u['uid'], bool(u['admin']), _paid(u['uid']), site))

@app.get('/api/botstate')
''', "def bridge_api(u)")

edit('static/index.html',
 '''  if(t.id==="testBtn"){var sv2=$("#server").value.trim();S.server=sv2;save();
    $("#connMsg").textContent=sv2?"No signal from "+sv2+" yet. The bridge and the analysis server are not installed, so there is nothing to connect to. That is the next build step.":"Enter your MT5 server name first. You can find it on the MT5 login screen.";return}''',
 '''  if(t.id==="testBtn"){var sv2=$("#server").value.trim();S.server=sv2;save();
    if(window.sxBridgeCheck){window.sxBridgeCheck();return}
    $("#connMsg").textContent="Sign in to see your real bridge status.";return}''', 'window.sxBridgeCheck){')
edit('static/index.html',
 '<p class="note">This is the front end. The analysis server and MT5 bridge are the next build steps, so every figure is sample data. The same page becomes the Android app later.</p>',
 '<p class="note">The analysis runs on this site. MT5 stays on your PC with the small bridge file, and the card at the top of this page shows what the bridge reports.</p>', 'The analysis runs on this site.')

S7 = r'''
<script>
/* ---- Section 7: the Connect tab shows the REAL bridge (GET /api/bridge): online or not, which account, demo or real, last report, and plain setup help.
   The old made-up connection message is gone. The chip on the Your broker card tells the truth too. ---- */
/*S7-start*/
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function ago(s) { s = Math.max(0, Math.round(s)); return s < 10 ? "just now" : s < 90 ? s + " s ago" : s < 5400 ? Math.round(s / 60) + " min ago" : s < 129600 ? Math.round(s / 3600) + " h ago" : Math.round(s / 86400) + " days ago"; }
  function stat(l, v) { return '<div class="stat"><span>' + l + '</span><b class="num">' + esc(v) + "</b></div>"; }
  function chip(d) {
    if (!d) return ["stop", "Not connected"];
    return d.state === "online" ? ["ok", d.mode === "real" ? "Bridge online - Real" : d.mode === "demo" ? "Bridge online - Demo" : "Bridge online"] : d.state === "offline" ? ["watch", "Bridge offline"] : d.state === "expired" ? ["watch", "Plan ended"] : ["stop", "Not connected"];
  }
  function html(d) {
    var h = '<p class="note"><b>' + esc(d.message) + "</b></p>";
    if (d.state === "online" || d.state === "offline") {
      h += '<div class="stats">' + stat("Account", d.login ? "#" + d.login : "-") + stat("Mode", d.mode === "real" ? "Real" : d.mode === "demo" ? "Demo" : "Unknown") +
        stat("Balance", d.balance == null ? "-" : "$" + Number(d.balance).toFixed(2)) + stat("Last report", d.age == null ? "-" : ago(d.age)) + "</div>";
      h += '<p class="note">' + (d.bot ? "Bot is on." : "Bot is off.") + (d.can_trade ? " Ready to trade." : d.why ? " Not trading: " + esc(d.why) + "." : "") + "</p>";
    }
    if (d.warn) h += '<p class="note">' + esc(d.warn) + "</p>";
    if (d.help && d.help.length) h += '<ol class="steps">' + d.help.map(function (x) { return "<li><div><b>" + esc(x.t) + "</b><span>" + esc(x.d) + "</span></div></li>"; }).join("") + "</ol>";
    return h;
  }
  window.__sx7 = { esc: esc, ago: ago, chip: chip, html: html };
  var vc = document.getElementById("view-connect"), msg = document.getElementById("connMsg"); if (!vc || !msg) return;
  var box = document.createElement("div"); box.id = "bridgeBox"; box.hidden = true; msg.parentNode.insertBefore(box, msg.nextSibling);
  var head = vc.querySelector(".card-head .chip"), TXT = msg.textContent, D = null, BUSY = false, FAIL = 0, SIG = "", TK = 0, HEAD0 = head ? head.className : "", HT0 = head ? head.innerHTML : "";
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function ready() { var u = me(); return !!(u && u.verified); }
  function setChip(c) { if (!head) return; head.className = "chip " + c[0]; head.innerHTML = '<span class="dot"></span>' + esc(c[1]); }
  function paint() {
    if (!ready()) { box.hidden = true; msg.hidden = false; msg.textContent = me() ? "Verify your email to see your bridge status." : "Sign in to see your real bridge status."; if (head) { head.className = HEAD0; head.innerHTML = HT0; } return; }
    if (!D) { box.hidden = true; msg.hidden = false; msg.textContent = FAIL ? "Cannot reach the server right now. Check your internet and try again." : "Checking your bridge..."; return; }
    msg.hidden = true; box.hidden = false; var h = html(D); if (h !== box.getAttribute("data-h")) { box.innerHTML = h; box.setAttribute("data-h", h); } setChip(chip(D));
  }
  function poll() {
    if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
    return SXA.api("/api/bridge", { method: "GET" }).then(function (j) { D = j; FAIL = 0; }, function () { FAIL++; }).then(function () { BUSY = false; paint(); });
  }
  window.sxBridgeCheck = function () { if (!ready()) { paint(); if (window.sxToast) window.sxToast("Sign in to check your bridge"); return; } D = null; paint(); poll().then(function () { if (window.sxToast && D) window.sxToast(D.state === "online" ? "Bridge is online" : "Bridge is not reporting"); }); };
  setInterval(function () {
    var u = me(), sg = u ? [u.uid, !!u.verified].join("|") : ""; TK++;
    if (sg !== SIG) { SIG = sg; D = null; FAIL = 0; paint(); if (ready()) poll(); return; }
    var on = vc.classList.contains("on");
    if (ready() && on && !document.hidden && TK % 5 === 0) poll(); else if (ready() && !on) { /* not looking: do nothing */ } else paint();
  }, 1000);
  new MutationObserver(function () { if (ready() && vc.classList.contains("on") && !document.hidden) poll(); }).observe(vc, { attributes: true, attributeFilter: ["class"] });
  paint();
})();
/*S7-end*/
</script>
'''
edit('static/index.html', '/*S3-end*/\n</script>\n', '/*S3-end*/\n</script>\n' + S7, '/*S7-start*/')

edit('docs/HANDOFF.md', '- 7 TODO  Connect screen shows the REAL bridge', '- 7 DONE (Nov 19: backend/bridge.py + GET /api/bridge + the S7 block in static/index.html + tests/test_bridge7.py + tests/test_bridge7ui.py; the fake "No signal ... next build step" message is gone)  Connect screen shows the REAL bridge', '- 7 DONE (Nov 19')
for p, t in FILES.items(): open(p, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
