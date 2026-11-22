/* D3: "Your running trades (phone)": a read-only list from GET /api/assist (running). Sits under the Phone mode card. */
(function () {
  "use strict";
  var vc = document.getElementById("view-connect");
  if (!vc || !window.SXA) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function num(v) { var n = Number(v); return isFinite(n) ? String(n) : "-"; }
  function span(m) { return m < 1 ? "just now" : m < 60 ? m + " min" : m < 1440 ? Math.round(m / 60) + " h" : Math.round(m / 1440) + " d"; }
  var C = document.createElement("div"); C.className = "card"; C.id = "runningc"; C.hidden = true;
  var pc = document.getElementById("phonec"); vc.insertBefore(C, pc ? pc.nextSibling : vc.firstChild);
  var R = null, ERR = false, LH = "";
  function row(t) {
    return '<div style="border:2px solid var(--surface2);border-radius:16px;padding:10px 14px;margin-top:10px">' +
      '<div class="card-head" style="margin:0"><h2 style="font-size:16px">' + (t.side === "buy" ? "BUY " : "SELL ") + esc(t.symbol) + '</h2><span class="chip info">' + (t.acct ? esc(t.acct) + " \u00b7 " : "") + esc(span(t.minutes)) + '</span></div>' +
      '<p class="note">Entry ' + num(t.entry) + " · SL " + num(t.sl) + " · TP " + num(t.tp) + " · " + (t.lots == null ? "lots not set" : num(t.lots) + " lots") + "</p></div>";
  }
  function draw() {
    var u = me(), ok = !!(u && !u.admin && u.verified && u.active), show = ok && (ERR || (R && R.length > 0)), h = "";
    C.hidden = !show; C.style.display = show ? "" : "none";
    if (show && ERR) h = '<div class="card-head"><h2>Your running trades (phone)</h2></div><p class="note">Could not load your running trades.</p><button class="btn block" type="button" data-rn="retry">Try again</button>';
    else if (show) h = '<div class="card-head"><h2>Your running trades (phone)</h2><span class="chip info">' + R.length + '</span></div>' + R.map(row).join("") + '<p class="note">This list comes from the trades you tapped Take on. It cannot see your MT5 app. Check MT5, then log the result in Phone mode.</p>';
    if (h !== LH) C.innerHTML = LH = h;
  }
  function load() {
    var u = me();
    if (!u || u.admin || !u.verified || !u.active) { R = null; ERR = false; draw(); return; }
    SXA.api("/api/assist", { method: "GET" }).then(function (j) { R = (j && j.running) || []; ERR = false; })
      .catch(function () { ERR = true; }).then(draw);
  }
  C.addEventListener("click", function (e) { if (e.target.closest('[data-rn="retry"]')) load(); });
  if (pc) pc.addEventListener("click", function () { setTimeout(load, 1500); });
  if (SXA.ready && SXA.ready.then) SXA.ready.then(load);
  load(); setInterval(load, 60000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) load(); });
})();
