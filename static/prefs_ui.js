/* P9 screens: "Strategies & entries" card (Bot tab) and "Open trades" card (Trades tab). Uses GET/POST /api/prefs and the open list from /api/journal. */
(function () {
  "use strict";
  if (!window.SXA) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function ready() { var u = me(); return !!(u && u.verified); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(t) { if (window.sxToast) window.sxToast(t); }

  /* ---------- A. Strategies & entries (Bot tab) ---------- */
  var vb = document.getElementById("view-bot");
  if (vb) (function () {
    var C = document.createElement("div"); C.className = "card"; C.id = "prefc"; C.hidden = true;
    var after = document.getElementById("posc") || document.getElementById("botstatec");
    vb.insertBefore(C, after ? after.nextSibling : vb.firstChild);
    var DATA = null, D = null, PICK = false, DIRTY = false, BUSY = false, ERR = "", SIG = "", TK = 0, LH = "";
    function copy(p) { return { strategies: (p.strategies || []).slice(), alone: !!p.alone, min_conf: p.min_conf || 0, entries: p.entries || 0, scale: !!p.scale, fast: !!p.fast }; }
    function seg(key, vals, cur, label) {
      var b = vals.map(function (v) { return '<button type="button" data-k="' + key + '" data-v="' + v[0] + '" aria-pressed="' + (cur === v[0]) + '">' + esc(v[1]) + "</button>"; }).join("");
      return '<div class="field"><label>' + esc(label) + '</label><div class="seg" role="group" aria-label="' + esc(label) + '" style="justify-self:start;max-width:100%;overflow-x:auto">' + b + "</div></div>";
    }
    function sw(key, title, sub, on) {
      return '<button type="button" class="switch" role="switch" aria-checked="' + (on ? "true" : "false") + '" data-t="' + key + '"><span><b>' + esc(title) + "</b><small>" + esc(sub) + '</small></span><span class="sw"></span></button>';
    }
    function html() {
      var h = '<div class="card-head"><h2>Strategies &amp; entries</h2>' + (DATA ? '<span class="chip info">' + (PICK && D.strategies.length ? D.strategies.length + " picked" : "All teamwork") + "</span>" : "") + "</div>";
      if (!DATA) return h + '<p class="note">' + esc(ERR || "Loading...") + "</p>";
      h += seg("mode", [["all", "All strategies"], ["pick", "Pick my own"]], PICK ? "pick" : "all", "Which strategies may trade");
      if (PICK) {
        h += '<div style="max-height:300px;overflow-y:auto;border:2px solid var(--line);border-radius:16px;padding:6px 12px;margin:8px 0">';
        h += DATA.strategies.map(function (s) { return sw("s:" + s.id, s.name, s.about, D.strategies.indexOf(s.id) >= 0); }).join("");
        h += "</div>";
        h += sw("alone", "May trade on its own", "A picked strategy can open a trade without a second one agreeing. Pick just one strategy to use only that one.", D.alone);
        h += seg("min_conf", [[0, "Default"], [1, "1"], [2, "2"], [3, "3"]], D.min_conf, "How many must agree");
      }
      var top = Math.min(10, DATA.ceiling || 1), ev = [[0, "Default"]];
      for (var i = 1; i <= top; i++) ev.push([i, String(i)]);
      h += seg("entries", ev, D.entries, "Entries per setup");
      h += '<p class="note">Several entries share the risk of ONE trade, so total risk stays the same. The owner allows up to ' + esc(DATA.ceiling) + ". Open trades at once are set in the card above.</p>";
      h += sw("scale", "Auto-scale", (DATA.scale_now && DATA.scale_now.why) || "Open more entries only while recent setups are winning.", D.scale);
      if (D.scale && D.entries <= 1) h += '<p class="note">Auto-scale needs "Entries per setup" above 1 to have any effect.</p>';
      h += sw("fast", "Also scan every 5 minutes", "Checks 5-minute candles too, so it looks for setups more often. Not tested on past data yet: use a demo account. MT5 users need the updated EA.", D.fast);
      if (ERR) h += '<p class="note">' + esc(ERR) + "</p>";
      h += '<div class="jrow"><button type="button" class="btn primary" data-save="1"' + (!DIRTY || BUSY ? " disabled" : "") + ">" + (BUSY ? "Saving..." : "Save") + "</button></div>";
      return h;
    }
    function paint() {
      var on = ready(); C.hidden = !on; C.style.display = on ? "" : "none";
      if (!on) { if (LH) { C.innerHTML = ""; LH = ""; } return; }
      var h = html(); if (h !== LH) { var sc = C.querySelector("div[style*=overflow-y]"), y = sc ? sc.scrollTop : 0; C.innerHTML = LH = h; sc = C.querySelector("div[style*=overflow-y]"); if (sc) sc.scrollTop = y; }
    }
    function load(force) {
      if (!ready() || BUSY || (DIRTY && !force)) return Promise.resolve(); BUSY = true;
      return SXA.api("/api/prefs").then(function (j) { DATA = j; if (!DIRTY) { D = copy(j.prefs); PICK = D.strategies.length > 0; } ERR = ""; }, function () { if (!DATA) ERR = "Cannot reach the server."; }).then(function () { BUSY = false; paint(); });
    }
    C.addEventListener("click", function (e) {
      if (!DATA || BUSY) return; var t = e.target.closest ? e.target : null; if (!t) return;
      var s = t.closest("[data-save]");
      if (s) {
        BUSY = true; ERR = ""; paint();
        SXA.api("/api/prefs", { method: "POST", body: { strategies: PICK ? D.strategies : [], alone: PICK ? D.alone : false, min_conf: PICK ? D.min_conf : 0, entries: D.entries, scale: D.scale, fast: D.fast } })
          .then(function () { DIRTY = false; BUSY = false; toast("Saved on the server"); return load(true); },
            function (x) { ERR = (x && x.message) || "Not saved."; BUSY = false; paint(); });
        return;
      }
      var b = t.closest("[data-k]"), w = t.closest("[data-t]");
      if (b) {
        var k = b.getAttribute("data-k"), v = b.getAttribute("data-v");
        if (k === "mode") { PICK = v === "pick"; } else D[k] = parseInt(v, 10) || 0;
      } else if (w) {
        var key = w.getAttribute("data-t");
        if (key === "alone") D.alone = !D.alone; else if (key === "scale") D.scale = !D.scale; else if (key === "fast") D.fast = !D.fast;
        else if (key.indexOf("s:") === 0) { var id = key.slice(2), i = D.strategies.indexOf(id); if (i >= 0) D.strategies.splice(i, 1); else D.strategies.push(id); }
      } else return;
      DIRTY = true; ERR = ""; paint();
    });
    setInterval(function () {
      var u = me(), sg = u ? [u.uid, !!u.verified].join("|") : ""; TK++;
      if (sg !== SIG) { SIG = sg; DATA = null; D = null; DIRTY = false; ERR = ""; paint(); if (u) load(); return; }
      if (ready() && vb.classList.contains("on") && !document.hidden && TK % 30 === 0) load();
    }, 1000);
    new MutationObserver(function () { if (ready() && vb.classList.contains("on") && !BUSY) load(); }).observe(vb, { attributes: true, attributeFilter: ["class"] });
    window.sxPrefsReload = function () { DIRTY = false; return load(true); };          /* S5: the preset card asks this card to show the new values */
    paint();
  })();

  /* ---------- A2. Small account settings (Bot tab). GET/POST /api/presets. A tap on $10 to $60 only picks; Confirm saves; Back puts the old values back. ---------- */
  if (vb) (function () {
    var C = document.createElement("div"); C.className = "card"; C.id = "presetc"; C.hidden = true;
    var pc = document.getElementById("prefc"), after = document.getElementById("posc") || document.getElementById("botstatec");
    if (pc) vb.insertBefore(C, pc); else vb.insertBefore(C, after ? after.nextSibling : vb.firstChild);
    var S = null, SEL = 0, BUSY = false, ERR = "", SIG = "", LH = "", TK = 0, SIZES = [10, 20, 30, 40, 50, 60];
    function usd(n) { return "$" + (Math.round(Number(n) * 100) / 100).toFixed(2); }
    function pct(n) { return String(+Number(n).toFixed(2)); }
    function on() { return ready() && (S ? !S.owner : !!ERR); }          /* hidden while loading and for the owner; a failed first load shows its message */
    function confirmBox(k) {
      var v = S.tiers[String(k)] || {}, m = (S.minlot || {})[String(k)] || {}, bal = Number(m.balance) || 0, blocked = !!m.blocked;
      var h = '<div style="border:2px solid var(--line);border-radius:16px;padding:10px 14px;margin:10px 0"><p class="note" style="font-weight:800;color:var(--fg)">The $' + k + " settings will set:</p>";
      h += '<p class="note">All strategies may trade (new ones too), up to ' + esc(v.entries) + " entries per setup, up to " + esc(v.max_open) + " open trades, stop after " + esc(v.streak) + " losses in a row.</p>";
      h += '<p class="note" style="font-weight:800;color:var(--fg)">Profit target for a setup: ' + esc(usd(v.target_usd)) + " for all its entries together. When it is reached they all close.</p>";
      h += '<p class="note">Risk per trade: ' + esc(pct(v.risk_pct)) + "% of your balance. Burst and every-minute scans: off.</p>";
      if (bal > 0) {
        h += '<p class="note" style="font-weight:800;color:var(--fg)">Most one trade may lose: about ' + esc(usd(m.risk_usd)) + " (" + esc(pct(m.risk_pct)) + "% of your " + esc(usd(bal)) + " balance).</p>";
      } else h += '<p class="note">Your balance is not known yet, so no dollar amount can be shown.</p>';
      if (m.message) h += '<p class="note" style="color:var(--bad);font-weight:800">' + esc(m.message) + "</p>";
      h += '<p class="note">Not set by this: ' + esc((S.not_included || []).join("; ").toLowerCase()) + ".</p>";
      h += '<div class="jrow"><button type="button" class="btn primary" data-ok="1"' + (BUSY || blocked ? " disabled" : "") + ">" + (BUSY ? "Saving..." : "Confirm $" + k + " settings") + '</button><button type="button" class="btn" data-no="1"' + (BUSY ? " disabled" : "") + ">Cancel</button></div></div>";
      return h;
    }
    function html() {
      var h = '<div class="card-head"><h2>Small account settings</h2>' + (S && S.active ? '<span class="chip info">$' + esc(S.active) + " on</span>" : "") + "</div>";
      if (!S) return h + '<p class="note">' + esc(ERR || "Loading...") + "</p>";
      h += '<p class="note">One tap sets the bot up to manage a $10 to $60 account. It only changes your own settings, and you can go back. It does not make money or keep an account safe.</p>';
      h += '<div class="seg" role="group" aria-label="Account size" style="justify-self:start;max-width:100%">' + SIZES.map(function (k) {
        return '<button type="button" data-p="' + k + '" aria-pressed="' + ((SEL || S.active) === k) + '"' + (!S.demo || BUSY ? " disabled" : "") + ">$" + k + "</button>"; }).join("") + "</div>";
      if (!S.demo) h += '<p class="note">Try these on a Demo account first. Switch to Demo above, then pick a size.</p>';
      if (SEL && S.demo) h += confirmBox(SEL);
      if (ERR) h += '<p class="note" style="color:var(--bad)">' + esc(ERR) + "</p>";
      if (S.can_undo) h += '<div class="jrow"><button type="button" class="btn" data-undo="1"' + (BUSY ? " disabled" : "") + ">Back to my old settings</button></div>";
      return h;
    }
    function paint() {
      var show = on(); C.hidden = !show; C.style.display = show ? "" : "none";
      if (!show) { if (LH) { C.innerHTML = ""; LH = ""; } return; }
      var h = html(); if (h !== LH) C.innerHTML = LH = h;
    }
    function load() {
      if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
      return SXA.api("/api/presets").then(function (j) { S = j; ERR = ""; }, function () { if (!S) ERR = "Cannot reach the server."; }).then(function () { BUSY = false; paint(); });
    }
    function send(body, done) {
      BUSY = true; ERR = ""; paint();
      SXA.api("/api/presets", { method: "POST", body: body }).then(function (j) { S = j; SEL = 0; BUSY = false; toast(done); if (window.sxPrefsReload) window.sxPrefsReload(); paint(); },
        function (x) { ERR = (x && x.message) || "Not saved."; BUSY = false; paint(); });
    }
    C.addEventListener("click", function (e) {
      if (!S || BUSY) return; var t = e.target.closest ? e.target : null; if (!t) return;
      var p = t.closest("[data-p]"), ok = t.closest("[data-ok]"), no = t.closest("[data-no]"), un = t.closest("[data-undo]");
      if (ok) { var ml = (S.minlot || {})[String(SEL)] || {}; if (SEL && S.demo && !ml.blocked) send({ tier: SEL }, "Smaller-risk settings are on"); return; }          /* a size no market can trade at is never sent */
      if (un) { send({ undo: true }, "Your old settings are back"); return; }
      if (no) { SEL = 0; ERR = ""; paint(); return; }
      if (p && S.demo) { SEL = parseInt(p.getAttribute("data-p"), 10) || 0; ERR = ""; paint(); }
    });
    setInterval(function () {
      var u = me(), sg = u ? [u.uid, !!u.verified].join("|") : ""; TK++;
      if (sg !== SIG) { SIG = sg; S = null; SEL = 0; ERR = ""; paint(); if (u) load(); return; }
      if (ready() && vb.classList.contains("on") && !document.hidden && !SEL && TK % 30 === 0) load();
    }, 1000);
    new MutationObserver(function () { if (ready() && vb.classList.contains("on") && !BUSY && !SEL) load(); }).observe(vb, { attributes: true, attributeFilter: ["class"] });
    paint();
  })();

  /* ---------- B. Open trades with their reasons (Trades tab). Filled from the same /api/journal answer the Journal already asks for. ---------- */
  var vt = document.getElementById("view-trades");
  if (vt) (function () {
    var C = document.createElement("div"); C.className = "card"; C.id = "opentc"; C.hidden = true;
    vt.insertBefore(C, document.getElementById("tStats") ? document.getElementById("tStats").nextSibling : vt.firstChild);
    var LH = "";
    function num(v) { var n = Number(v); return isFinite(n) && n > 0 ? String(+n.toFixed(5)) : "-"; }
    function one(o) {
      var st = { open: "Open", pending: "Sending", sent: "Sending" }[o.status] || o.status;
      var h = '<details style="border-top:2px solid var(--line);padding:10px 0"><summary style="font-weight:800;cursor:pointer">' + (o.side === "buy" ? "BUY " : "SELL ") + esc(o.symbol) + ' <span class="chip">' + esc(st) + "</span></summary>";
      h += '<p class="note" style="font-weight:800;color:var(--fg)">' + esc(o.strategy_name) + "</p>";
      h += '<p class="note">Entry ' + num(o.fill || o.entry) + " · Stop-loss " + num(o.sl) + " · Take-profit " + num(o.tp) + (o.lots ? " · " + esc(o.lots) + " lots" : "") + "</p>";
      if (o.why_lines && o.why_lines.length) h += '<p class="note"><b>Why the bot took it</b></p>' + o.why_lines.map(function (l) { return '<p class="note">' + esc(l) + "</p>"; }).join("");
      else h += '<p class="note">No reason was saved for this trade.</p>';
      if (o.how && o.how.length) h += '<p class="note"><b>What each strategy looks for</b></p>' + o.how.map(function (x) { return '<p class="note"><b>' + esc(x.name) + ":</b> " + esc(x.about) + "</p>"; }).join("");
      return h + "</details>";
    }
    window.sxOpenTrades = function () {
      var j = (typeof SXJ !== "undefined" && SXJ.state === "ok") ? (SXJ.open || []) : [];
      var on = ready() && j.length > 0; C.hidden = !on; C.style.display = on ? "" : "none";
      var h = on ? '<div class="card-head"><h2>Open trades</h2><span class="chip info">' + j.length + "</span></div>" + j.map(one).join("") : "";
      if (h !== LH) C.innerHTML = LH = h;
    };
    window.sxOpenTrades();
  })();
})();
