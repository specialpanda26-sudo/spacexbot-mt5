/* Losing-streak pause card (Bot tab). A person whose bot is paused by the losing streak can ask the admin to let it continue; the admin reviews here.
   Uses GET /api/streak, POST /api/streak/request (person) and GET/POST /api/admin/streak (admin). Server rules: backend/streakreq.py. */
(function () {
  "use strict";
  if (!window.SXA) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function ready() { var u = me(); return !!(u && u.verified); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(t) { if (window.sxToast) window.sxToast(t); }
  function usd(n) { var x = Math.round(Number(n) * 100) / 100; return (x < 0 ? "-$" : "$") + Math.abs(x).toFixed(2); }
  function at(sec) { try { return new Date(sec * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); } catch (e) { return ""; } }
  var vb = document.getElementById("view-bot");
  if (!vb) return;
  var C = document.createElement("div"); C.className = "card"; C.id = "streakc"; C.hidden = true;
  var after = document.getElementById("botstatec");
  vb.insertBefore(C, after ? after.nextSibling : vb.firstChild);
  var S = null, L = null, SEL = null, NOTE = "", BUSY = false, ERR = "", SIG = "", LH = "", TK = 0;
  function admin() { var u = me(); return !!(u && u.admin); }
  function losses(a) { return (a || []).map(usd).join(", "); }

  function personHtml() {
    var r = S.request, h = "";
    if (S.paused) {
      h += '<div class="card-head"><h2>Trading paused</h2><span class="chip watch">' + esc(S.k) + " losses in a row</span></div>";
      h += '<p class="note">The bot stopped new trades after ' + esc(S.k) + " losses in a row (" + esc(losses(S.losses)) + "). It starts again by itself at " + esc(at(S.until)) + ".</p>";
      if (r && r.status === "pending" && r.since === S.since) h += '<p class="note" style="font-weight:800;color:var(--fg)">Your request is with the admin. You will see the answer here.</p>';
      else if (r && r.status === "declined" && r.since === S.since) h += '<p class="note" style="font-weight:800;color:var(--bad)">The admin said not now.' + (r.note ? " " + esc(r.note) : "") + " The pause ends by itself at the time above.</p>";
      else h += '<p class="note">If you want to trade sooner, ask the admin. They look at it and decide. Nothing changes until they say yes.</p><div class="jrow"><button type="button" class="btn primary" data-ask="1"' + (BUSY ? " disabled" : "") + ">" + (BUSY ? "Sending..." : "Ask the admin to let me continue") + "</button></div>";
    } else if (r && r.status === "approved" && Date.now() / 1000 - (r.decided || 0) < 86400) {
      h += '<div class="card-head"><h2>Trading allowed again</h2><span class="chip info">Approved</span></div><p class="note">The admin said yes' + (r.note ? ": " + esc(r.note) : "") + ". The bot can open new trades again. The daily and weekly loss limits still apply.</p>";
    } else return "";
    if (ERR) h += '<p class="note" style="color:var(--bad)">' + esc(ERR) + "</p>";
    return h;
  }
  function adminHtml() {
    var w = (L && L.waiting) || [];
    if (!w.length) return "";
    var h = '<div class="card-head"><h2>Pause requests</h2><span class="chip info">' + w.length + "</span></div>";
    h += '<p class="note">These people were stopped by the losing-streak pause and ask to trade again. Yes restarts their loss count. The other limits stay.</p>';
    w.forEach(function (x) {
      h += '<div style="border-top:2px solid var(--line);padding:10px 0"><p class="note" style="font-weight:800;color:var(--fg)">' + esc(x.email || x.name || x.uid) + "</p>";
      h += '<p class="note">' + esc(x.k) + " losses in a row: " + esc(losses(x.losses)) + ". Asked at " + esc(at(x.t)) + ".</p>";
      if (SEL && SEL.uid === x.uid) {
        h += '<input class="inp" data-note="1" maxlength="200" placeholder="Note to the person (optional)" style="width:100%">';
        h += '<p class="note" style="font-weight:800;color:var(--fg)">' + (SEL.approve ? "Let this person trade again now?" : "Keep the pause on for this person?") + '</p><div class="jrow"><button type="button" class="btn primary" data-go="1"' + (BUSY ? " disabled" : "") + ">" + (BUSY ? "Saving..." : SEL.approve ? "Yes, let them continue" : "Yes, keep it paused") + '</button><button type="button" class="btn" data-no="1"' + (BUSY ? " disabled" : "") + ">Cancel</button></div>";
      } else h += '<div class="jrow"><button type="button" class="btn primary" data-a="' + esc(x.uid) + '">Approve</button><button type="button" class="btn" data-d="' + esc(x.uid) + '">Decline</button></div>';
      h += "</div>";
    });
    if (ERR) h += '<p class="note" style="color:var(--bad)">' + esc(ERR) + "</p>";
    return h;
  }
  function paint() {
    var show = ready(), h = "";
    if (show) h = admin() ? adminHtml() : (S ? personHtml() : "");
    C.hidden = !h; C.style.display = h ? "" : "none";
    if (h !== LH) C.innerHTML = LH = h;
  }
  function load() {
    if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
    var p = admin() ? SXA.api("/api/admin/streak").then(function (j) { L = j; }) : SXA.api("/api/streak").then(function (j) { S = j; });
    return p.then(function () { ERR = ""; }, function () { }).then(function () { BUSY = false; paint(); });
  }
  C.addEventListener("input", function (e) { var t = e.target; if (t && t.getAttribute && t.getAttribute("data-note") != null) NOTE = String(t.value || "").slice(0, 200); });
  C.addEventListener("click", function (e) {
    if (BUSY) return; var t = e.target.closest ? e.target : null; if (!t) return;
    var ask = t.closest("[data-ask]"), a = t.closest("[data-a]"), d = t.closest("[data-d]"), go = t.closest("[data-go]"), no = t.closest("[data-no]");
    if (ask && S && S.paused) {
      BUSY = true; ERR = ""; paint();
      SXA.api("/api/streak/request", { method: "POST", body: {} }).then(function (j) { S = j; BUSY = false; toast("Sent to the admin"); paint(); },
        function (x) { ERR = (x && x.message) || "Not sent."; BUSY = false; paint(); });
    } else if (a || d) { SEL = { uid: (a || d).getAttribute(a ? "data-a" : "data-d"), approve: !!a }; NOTE = ""; ERR = ""; paint(); }
    else if (no) { SEL = null; ERR = ""; paint(); }
    else if (go && SEL) {
      var pick = SEL; BUSY = true; ERR = ""; paint();
      SXA.api("/api/admin/streak", { method: "POST", body: { uid: pick.uid, approve: pick.approve, note: NOTE } }).then(function (j) { L = j; SEL = null; NOTE = ""; BUSY = false; toast(pick.approve ? "Approved. Trading can continue." : "Declined. The pause stays."); paint(); },
        function (x) { ERR = (x && x.message) || "Not saved."; BUSY = false; paint(); });
    }
  });
  setInterval(function () {
    var u = me(), sg = u ? [u.uid, !!u.verified, !!u.admin].join("|") : ""; TK++;
    if (sg !== SIG) { SIG = sg; S = null; L = null; SEL = null; ERR = ""; paint(); if (u) load(); return; }
    if (ready() && vb.classList.contains("on") && !document.hidden && !SEL && TK % 15 === 0) load();
  }, 1000);
  new MutationObserver(function () { if (ready() && vb.classList.contains("on") && !BUSY && !SEL) load(); }).observe(vb, { attributes: true, attributeFilter: ["class"] });
  paint();
})();
