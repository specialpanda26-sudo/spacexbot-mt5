/* C3: the road to Real. A Home card (lessons + practice trades), eight badges and a celebration pop-up (GET /api/path, POST /api/path/seen). The server decides; this only shows. */
(function () {
  "use strict";
  if (!window.SXA) return;
  var vh = document.getElementById("view-home"); if (!vh) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function art(k) { var I = window.IL2 || {}; return I[k] || ""; }
  var C = document.createElement("div"); C.className = "card"; C.id = "roadc"; C.hidden = true;
  var cc = document.getElementById("coursec"); if (cc && cc.parentNode === vh) vh.insertBefore(C, cc.nextSibling); else vh.insertBefore(C, vh.firstChild ? vh.firstChild.nextSibling : null);
  var D = null, LH = "", OV = null, BUSY = false;
  function bar(p) { return '<div style="height:8px;border-radius:8px;background:var(--surface2);overflow:hidden"><div style="height:100%;width:' + Math.max(0, Math.min(100, p)) + '%;background:var(--green)"></div></div>'; }
  function pct(a, b) { return b > 0 ? Math.round(100 * a / b) : 100; }
  function drawCard() {
    var u = me(), on = !!(u && u.verified && D && !D.exempt); C.hidden = !on; C.style.display = on ? "" : "none";
    var h = "";
    if (on) {
      var L = D.lessons, P = D.practice;
      h = '<div class="card-head"><h2>Road to Real</h2><span class="chip ' + (D.real_open ? "ok" : "info") + '">' + (D.real_open ? "Real is open" : D.earned + " of " + D.total + " badges") + "</span></div>" +
        (L.required ? '<p class="muted">Lessons: ' + L.done + " of " + L.total + "</p>" + bar(pct(L.done, L.total)) : "") +
        (P.needed ? '<p class="muted">Practice trades closed: ' + Math.min(P.closed, P.needed) + " of " + P.needed + "</p>" + bar(pct(P.closed, P.needed)) : "") +
        '<p class="note">' + (D.real_open ? "The road is finished. Real mode is open. Demo works any time, and you type the word REAL to switch." : esc(D.why)) + "</p>" +
        '<button class="btn block" type="button" data-r="open">See my badges</button>';
    }
    if (h !== LH) C.innerHTML = LH = h;
  }
  function close() { if (OV && OV.remove) OV.remove(); OV = null; }
  function shell(html) {
    close(); OV = document.createElement("div"); OV.className = "ov"; OV.id = "roadov";
    OV.innerHTML = '<div class="bd" data-r="close"></div><div class="panel" role="dialog" aria-modal="true" style="max-height:88vh;overflow:auto">' + html + "</div>";
    document.body.appendChild(OV); try { void OV.offsetWidth; } catch (e) {} OV.className = "ov open";
  }
  function badges() {
    shell(art("rocket") + '<h2 style="text-align:center">Your badges</h2><p class="muted" style="text-align:center">' + D.earned + " of " + D.total + ' earned. No badge is a promise of profit, they only show your steps.</p>' +
      D.milestones.map(function (m) {
        return '<div class="note" style="display:flex;gap:10px;align-items:center;margin:6px 0;' + (m.done ? "" : "opacity:.55") + '"><span style="width:44px;flex:none">' + art(m.art) + "</span><span><b>" + esc(m.title) + "</b> " +
          '<span class="chip ' + (m.done ? "ok" : "") + '">' + (m.done ? "Earned" : "Not yet") + "</span><br><small>" + esc(m.text) + "</small></span></div>";
      }).join("") + '<button class="btn block" type="button" data-r="close">Close</button>');
  }
  function party(m) {
    shell(art(m.art === "rocket" ? "yay" : m.art) + '<h2 style="text-align:center">New badge: ' + esc(m.title) + '</h2><p class="muted" style="text-align:center">' + esc(m.text) + "</p>" +
      '<button class="btn primary big block" type="button" data-r="close">Great</button><button class="btn block" type="button" data-r="open">See all badges</button>');
  }
  function seen() { SXA.api("/api/path/seen", { method: "POST", body: {} }).catch(function () {}); }
  function celebrate() {
    if (!D || D.exempt || OV || document.querySelector(".ov.open")) return;
    var n = D.milestones.filter(function (m) { return m.new; }); if (!n.length) return;
    party(n[n.length - 1]); seen(); D.milestones.forEach(function (m) { m.new = false; });
  }
  function load() {
    var u = me(); if (!(u && u.verified)) { D = null; drawCard(); return; } if (BUSY) return; BUSY = true;
    SXA.api("/api/path").then(function (j) { BUSY = false; D = j; drawCard(); celebrate(); }).catch(function () { BUSY = false; });
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-r]"); if (!b || (!C.contains(b) && !(OV && OV.contains(b)))) return; var c = b.getAttribute("data-r");
    if (c === "open" && D) badges(); else if (c === "close") close();
  });
  window.sxRoad = { state: function () { return D; }, reload: load };
  load(); setInterval(load, 60000); setTimeout(load, 3000);
})();
