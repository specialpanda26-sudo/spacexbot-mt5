/* Take small profits (Bot tab). GET /api/quickprofit, POST /api/quickprofit {on, usd}.
   A switch plus one number: when it is on, every entry the bot opened closes by itself as soon as ITS OWN profit reaches that many USD.
   The server hands the number to the MT5 bridge and the Deriv loop, which do the closing. Same cartoon family as the rest of the site. */
(function () {
  "use strict";
  if (!window.SXA) return;
  var vb = document.getElementById("view-bot"); if (!vb) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function ready() { var u = me(); return !!(u && u.verified); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(t) { if (window.sxToast) window.sxToast(t); }
  function fmt(x) { var n = Number(x); return isFinite(n) ? n.toFixed(2) : ""; }

  var C = document.createElement("div"); C.className = "card"; C.id = "qpc"; C.hidden = true;
  var sh = document.getElementById("sharec"), pr = document.getElementById("presetc"), pc = document.getElementById("prefc"), after = document.getElementById("posc") || document.getElementById("botstatec");
  if (sh) vb.insertBefore(C, sh); else if (pr) vb.insertBefore(C, pr.nextSibling); else if (pc) vb.insertBefore(C, pc); else vb.insertBefore(C, after ? after.nextSibling : vb.firstChild);

  if (!document.getElementById("qpcss")) {
    var st = document.createElement("style"); st.id = "qpcss";
    st.textContent = ".qprow{display:flex;align-items:center;gap:10px}.qprow .ill2{width:96px;max-width:none;margin:0;flex:0 0 auto}.qprow .note{margin:0}";
    document.head.appendChild(st);
  }

  var D = null, USD = "", BUSY = false, ERR = "", SIG = "", LH = "", TK = 0;
  function art() { var I = window.IL2 || {}; return (I.paid || "").replace('class="ill2"', 'class="ill2 sm"'); }
  function sw(title, sub, on) {
    return '<button type="button" class="switch" role="switch" aria-checked="' + (on ? "true" : "false") + '" data-t="on"' + (BUSY ? " disabled" : "") + '><span><b>' + esc(title) + "</b><small>" + esc(sub) + '</small></span><span class="sw"></span></button>';
  }
  function html() {
    var s = D && D.settings, chip = "";
    if (D) chip = '<span class="chip ' + (s.on && !D.paused ? "info" : "") + '">' + (s.on ? (D.paused ? "Paused" : "On: $" + esc(fmt(s.usd)) + " each") : "Off") + "</span>";
    var h = '<div class="card-head"><h2>Take small profits</h2>' + chip + "</div>";
    if (!D) return h + '<p class="note">' + esc(ERR || "Loading...") + "</p>";
    h += '<div class="qprow">' + art() + '<p class="note">Close each entry by itself the moment it is up a small amount. If a trade opens 6 entries, every entry closes as soon as it shows your profit, without waiting for the others.</p></div>';
    h += sw("Take small profits", s.on ? "On: each entry closes at $" + fmt(s.usd) + " profit." : "Off: entries wait for their normal take profit.", s.on);
    h += '<div class="field"><label>Profit that closes one entry (USD)</label><input class="inp" id="qpusd" type="text" inputmode="decimal" autocomplete="off" placeholder="e.g. 0.50" value="' + esc(USD) + '"></div>';
    h += '<div class="jrow"><button type="button" class="btn" data-save="1"' + (BUSY ? " disabled" : "") + ">Save amount</button></div>";
    if (D.paused) h += '<p class="note" style="color:var(--bad);font-weight:800">Paused: the owner switch "I close the profits myself" is on, so nothing closes by itself.</p>';
    if (ERR) h += '<p class="note" style="color:var(--bad)" role="alert">' + esc(ERR) + "</p>";
    h += '<p class="note">The stop loss stays on every entry. Taking small wins early leaves losing entries to run to their stop loss, and the spread and commission come out of a small profit, so this does not make money by itself. Works with MT5 (SpaceXBridge 1.22 or newer) and Deriv. Phone mode cannot close trades.</p>';
    return h;
  }
  function on() { return ready() && (D ? true : !!ERR); }
  function paint(force) {
    var show = on(); C.hidden = !show; C.style.display = show ? "" : "none";
    if (!show) { if (LH) { C.innerHTML = ""; LH = ""; } return; }
    var a = document.activeElement; if (!force && a && a.id === "qpusd" && C.contains(a)) return;          /* never redraw while the person is typing */
    var h = html(); if (h !== LH) C.innerHTML = LH = h;
  }
  function load() {
    if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
    return SXA.api("/api/quickprofit").then(function (j) { D = j; ERR = ""; if (!USD || !(document.activeElement && document.activeElement.id === "qpusd")) USD = fmt(j.settings.usd); },
      function () { if (!D) ERR = "Cannot reach the server."; }).then(function () { BUSY = false; paint(); });
  }
  function amount() {
    var el = C.querySelector("#qpusd"); if (el) USD = el.value;
    var v = parseFloat(String(USD).replace(",", ".")), lo = D ? D.min : 0.05, hi = D ? D.max : 1000;
    return v === v && v >= lo && v <= hi ? Math.round(v * 100) / 100 : null;
  }
  function post(body, ok) {
    BUSY = true; ERR = ""; paint(true);
    SXA.api("/api/quickprofit", { method: "POST", body: body }).then(function (j) { D = j; USD = fmt(j.settings.usd); BUSY = false; toast(ok(j)); paint(true); },
      function (x) { ERR = (x && x.message) || "Not saved."; BUSY = false; paint(true); });
  }
  C.addEventListener("input", function (e) { if (e.target && e.target.id === "qpusd") USD = e.target.value; });
  C.addEventListener("click", function (e) {
    if (!D || BUSY) return; var t = e.target.closest ? e.target : null; if (!t) return;
    var bad = "Enter a profit from " + fmt(D.min) + " to " + fmt(D.max) + " USD, for example 0.50.";
    if (t.closest("[data-save]")) {
      var v = amount(); if (v === null) { ERR = bad; paint(true); return; }
      post({ usd: v }, function (j) { return "Saved: $" + fmt(j.settings.usd) + " per entry"; }); return;
    }
    if (t.closest("[data-t]")) {
      var next = !D.settings.on;
      if (next) { var a = amount(); if (a === null) { ERR = bad; paint(true); return; } post({ on: true, usd: a }, function () { return "Small profits on"; }); }
      else post({ on: false }, function () { return "Small profits off"; });
    }
  });
  setInterval(function () {
    var u = me(), sg = u ? [u.uid, !!u.verified].join("|") : ""; TK++;
    if (sg !== SIG) { SIG = sg; D = null; USD = ""; ERR = ""; paint(true); if (u) load(); return; }
    if (ready() && vb.classList.contains("on") && !document.hidden && TK % 30 === 0) load();
  }, 1000);
  new MutationObserver(function () { if (ready() && vb.classList.contains("on") && !BUSY) load(); }).observe(vb, { attributes: true, attributeFilter: ["class"] });
  paint();
})();
