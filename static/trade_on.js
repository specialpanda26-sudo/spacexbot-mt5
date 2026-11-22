/* Section 5A screen: "Trade on" card (Bot tab). Pick the ONE platform that trades (MT5, Deriv or Binance). Uses GET/POST /api/trade-on. */
(function () {
  "use strict";
  if (!window.SXA) return;
  var vb = document.getElementById("view-bot"); if (!vb) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var C = document.createElement("div"); C.className = "card"; C.id = "tradeonc"; C.hidden = true;
  vb.insertBefore(C, vb.firstChild ? vb.firstChild.nextSibling : null);
  var D = null, BUSY = false, ERR = "", LH = "";
  function draw() {
    var u = me(), on = !!(u && u.verified && D); C.hidden = !on; C.style.display = on ? "" : "none";
    var h = "";
    if (on) {
      h = '<div class="card-head"><h2>Trade on</h2><span class="chip info">' + (D.trade_on ? esc(D.trade_on) : "Not chosen") + "</span></div>" +
        '<div class="seg" role="group" aria-label="Trading platform" style="justify-self:start;max-width:100%;overflow-x:auto">' +
        D.platforms.map(function (p) { return '<button type="button" data-p="' + esc(p.name) + '" aria-pressed="' + (D.trade_on === p.name) + '"' + (BUSY ? " disabled" : "") + ">" + esc(p.name) + "</button>"; }).join("") + "</div>" +
        '<p class="note">' + esc(D.note) + " Picking one stops the bots on the other platforms.</p>" + (ERR ? '<p class="err">' + esc(ERR) + "</p>" : "");
    }
    if (h !== LH) C.innerHTML = LH = h;
  }
  function load() {
    var u = me(); if (!(u && u.verified)) { D = null; draw(); return; }
    SXA.api("/api/trade-on").then(function (j) { D = j; draw(); }).catch(function () {});
  }
  C.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-p]"); if (!b || BUSY) return;
    BUSY = true; ERR = ""; draw();
    SXA.api("/api/trade-on", { method: "POST", body: { platform: b.getAttribute("data-p") } })
      .then(function (j) { D = j; BUSY = false; draw(); if (window.sxToast) window.sxToast(j.trade_on + " is now your trading platform"); })
      .catch(function (x) { BUSY = false; ERR = (x && x.message) || "Could not change the platform."; draw(); });
  });
  load(); setInterval(load, 30000); setTimeout(load, 2500);
})();
