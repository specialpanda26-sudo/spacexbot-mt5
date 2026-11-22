/* C4: "How to use the bot" - a Home card and a pop-up with cartoon steps (GET /api/guide). Same pictures as the site (window.IL2). */
(function () {
  "use strict";
  if (!window.SXA) return;
  var vh = document.getElementById("view-home"); if (!vh) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function art(k) { var I = window.IL2 || {}; return I[k] || ""; }
  var C = document.createElement("div"); C.className = "card"; C.id = "guidec"; C.hidden = true;
  vh.insertBefore(C, vh.firstChild ? vh.firstChild.nextSibling : null);
  var D = null, OV = null, N = 0, LH = "";
  function drawCard() {
    var u = me(), on = !!(u && u.verified && D); C.hidden = !on; C.style.display = on ? "" : "none";
    var h = on ? '<div class="card-head"><h2>How to use the bot</h2><span class="chip info">' + D.total + ' steps</span></div>' +
      '<p class="note">Short cartoon steps: sign up, connect, demo or real, start, signals and safety.</p>' +
      '<button class="btn block" type="button" data-g="open">Show me how</button>' : "";
    if (h !== LH) C.innerHTML = LH = h;
  }
  function load() {
    var u = me(); if (!(u && u.verified)) { D = null; drawCard(); return; }
    if (D) { drawCard(); return; }
    SXA.api("/api/guide").then(function (j) { D = j; drawCard(); if (OV) draw(); }).catch(function () {});
  }
  function close() { if (OV && OV.remove) OV.remove(); OV = null; }
  function open(n) {
    if (!D) return; N = Math.max(0, Math.min(D.total - 1, n | 0));
    if (!OV) {
      OV = document.createElement("div"); OV.className = "ov"; OV.id = "guideov";
      OV.innerHTML = '<div class="bd" data-g="close"></div><div class="panel" role="dialog" aria-modal="true" id="guidep" style="max-height:88vh;overflow:auto"></div>';
      document.body.appendChild(OV); try { void OV.offsetWidth; } catch (e) {} OV.className = "ov open";
    }
    draw();
  }
  function draw() {
    var p = document.getElementById("guidep"); if (!p || !D) return; var s = D.steps[N], last = N === D.total - 1;
    p.innerHTML = art(s.art) + '<p class="muted" style="text-align:center">Step ' + (N + 1) + " of " + D.total + "</p>" +
      '<h2 style="text-align:center">' + esc(s.title) + '</h2><p class="muted" style="text-align:center">' + esc(s.intro) + "</p><ul>" +
      s.points.map(function (t) { return '<li style="margin:8px 0">' + esc(t) + "</li>"; }).join("") + "</ul>" +
      '<button class="btn primary big block" type="button" data-g="' + (last ? "close" : "next") + '">' + (last ? "Done" : "Next") + "</button>" +
      (N ? '<button class="btn block" type="button" data-g="back">Back</button>' : "") +
      '<p class="note" style="text-align:center">' + esc(D.brand) + "</p>";
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-g]"); if (!b || (!C.contains(b) && !(OV && OV.contains(b)))) return; var c = b.getAttribute("data-g");
    if (c === "open") open(0); else if (c === "close") close(); else if (c === "next") open(N + 1); else if (c === "back") open(N - 1);
  });
  window.sxGuide = { open: function () { if (D) open(0); }, state: function () { return D; } };
  load(); setInterval(load, 60000); setTimeout(load, 2500);
})();
