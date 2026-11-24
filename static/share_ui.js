/* Share my settings (Bot tab). GET /api/sharecode, POST /api/sharecode/make | check | load | undo.
   Make a code from my settings, or paste a friend's code: see what would change first, then Load. Back puts my old settings back. */
(function () {
  "use strict";
  if (!window.SXA) return;
  var vb = document.getElementById("view-bot"); if (!vb) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function ready() { var u = me(); return !!(u && u.verified); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(t) { if (window.sxToast) window.sxToast(t); }

  var C = document.createElement("div"); C.className = "card"; C.id = "sharec"; C.hidden = true;
  var pr = document.getElementById("presetc"), pc = document.getElementById("prefc"), after = document.getElementById("posc") || document.getElementById("botstatec");
  if (pr) vb.insertBefore(C, pr.nextSibling); else if (pc) vb.insertBefore(C, pc); else vb.insertBefore(C, after ? after.nextSibling : vb.firstChild);

  var S = null, MADE = null, CHK = null, NAME = "", PASTE = "", BUSY = false, ERR = "", SIG = "", LH = "", TK = 0;
  var AREA = "width:100%;box-sizing:border-box;border:2px solid var(--line);border-radius:14px;padding:10px 12px;background:var(--surface);color:var(--ink);font:inherit;font-size:14px;word-break:break-all";

  function ago(t) {
    var s = Math.max(0, Math.floor(Date.now() / 1000) - Number(t || 0)), m = Math.floor(s / 60);
    return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.floor(m / 60) + " h ago" : Math.floor(m / 1440) + " d ago";
  }
  function rowsHtml(rows, cols) {
    return '<div style="max-height:260px;overflow-y:auto;border:2px solid var(--line);border-radius:16px;padding:4px 12px;margin:8px 0">' + rows.map(function (r) {
      return '<p class="note" style="margin:6px 0"><b>' + esc(r.label) + ":</b> " + (cols ? esc(r.now) + " &rarr; <b>" + esc(r.new) + "</b>" : esc(r.value)) + "</p>";
    }).join("") + "</div>";
  }
  function makeHtml() {
    var h = '<p class="note" style="font-weight:800;color:var(--ink)">Your code</p>';
    h += '<textarea id="shcode" readonly rows="4" style="' + AREA + '">' + esc(MADE.code) + "</textarea>";
    h += '<div class="jrow"><button type="button" class="btn primary" data-copy="1">Copy code</button>' + (navigator.share ? '<button type="button" class="btn" data-send="1">Send</button>' : "") + '<button type="button" class="btn" data-hide="1">Close</button></div>';
    h += '<p class="note">This code holds ' + esc(MADE.count) + " settings. It has no keys, no balance, no email and no Demo/Real choice. Anyone you give it to can load these settings, so send it only to people you trust.</p>";
    h += '<details><summary class="note" style="cursor:pointer;font-weight:800">See what is inside</summary>' + rowsHtml(MADE.rows, false) + "</details>";
    return h;
  }
  function checkHtml() {
    var h = '<div style="border:2px solid var(--line);border-radius:16px;padding:10px 14px;margin:10px 0"><p class="note" style="font-weight:800;color:var(--ink)">' + (CHK.name ? esc(CHK.name) + " " : "") + "settings" + (CHK.made ? " (made " + esc(ago(CHK.made)) + ")" : "") + "</p>";
    if (CHK.rows.length) h += '<p class="note">' + esc(CHK.rows.length) + " will change" + (CHK.same ? ", " + esc(CHK.same) + " are already the same" : "") + ":</p>" + rowsHtml(CHK.rows, true);
    else h += '<p class="note">Nothing would change: you already have these settings.</p>';
    (CHK.warnings || []).forEach(function (w) { h += '<p class="note" style="color:var(--bad);font-weight:800">' + esc(w) + "</p>"; });
    (CHK.notes || []).forEach(function (w) { h += '<p class="note">' + esc(w) + "</p>"; });
    h += '<p class="note">Loading never starts your bot and never switches Real mode on.</p>';
    var dis = BUSY || !S.demo || !CHK.rows.length;
    h += '<div class="jrow"><button type="button" class="btn primary" data-load="1"' + (dis ? " disabled" : "") + ">" + (BUSY ? "Loading..." : "Load these settings") + '</button><button type="button" class="btn" data-no="1"' + (BUSY ? " disabled" : "") + ">Cancel</button></div></div>";
    return h;
  }
  function html() {
    var h = '<div class="card-head"><h2>Share my settings</h2>' + (S && S.last ? '<span class="chip info">' + (S.last.name ? esc(S.last.name) + " loaded" : "Code loaded") + "</span>" : "") + "</div>";
    if (!S) return h + '<p class="note">' + esc(ERR || "Loading...") + "</p>";
    h += '<p class="note">Make a code from all your bot settings and send it to a friend, or paste a friend\'s code to get the same settings. You see what will change before anything is saved, and you can go back.</p>';
    h += '<div class="field"><label>Name for my code (optional)</label><input id="shname" type="text" maxlength="24" autocomplete="off" value="' + esc(NAME) + '" placeholder="e.g. My gold settings"></div>';
    h += '<div class="jrow"><button type="button" class="btn primary" data-make="1"' + (BUSY ? " disabled" : "") + ">Make my code</button></div>";
    if (MADE) h += makeHtml();
    h += '<div class="field" style="margin-top:14px"><label>Paste a friend\'s code</label><textarea id="shpaste" rows="3" placeholder="SXB1...." style="' + AREA + '">' + esc(PASTE) + "</textarea></div>";
    h += '<div class="jrow"><button type="button" class="btn" data-check="1"' + (BUSY ? " disabled" : "") + ">Check code</button></div>";
    if (!S.demo) h += '<p class="note">To load a code, switch to Demo first (Connect tab). Try the settings on Demo, then decide about Real.</p>';
    if (CHK) h += checkHtml();
    if (ERR) h += '<p class="note" style="color:var(--bad)">' + esc(ERR) + "</p>";
    if (S.can_undo) h += '<div class="jrow"><button type="button" class="btn" data-undo="1"' + (BUSY ? " disabled" : "") + ">Back to my old settings</button></div>";
    return h;
  }
  function on() { return ready() && (S ? true : !!ERR); }
  function paint(force) {
    var show = on(); C.hidden = !show; C.style.display = show ? "" : "none";
    if (!show) { if (LH) { C.innerHTML = ""; LH = ""; } return; }
    var a = document.activeElement; if (!force && a && (a.id === "shname" || a.id === "shpaste") && C.contains(a)) return;          /* never redraw while the person is typing */
    var h = html(); if (h !== LH) C.innerHTML = LH = h;
  }
  function load() {
    if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
    return SXA.api("/api/sharecode").then(function (j) { S = j; ERR = ""; }, function () { if (!S) ERR = "Cannot reach the server."; }).then(function () { BUSY = false; paint(); });
  }
  function call(path, body, ok) {
    BUSY = true; ERR = ""; paint(true);
    SXA.api(path, { method: "POST", body: body }).then(function (j) { BUSY = false; ok(j); paint(true); },
      function (x) { BUSY = false; ERR = (x && x.message) || "Something went wrong."; paint(true); });
  }
  function readInputs() {
    var n = C.querySelector("#shname"), p = C.querySelector("#shpaste");
    if (n) NAME = n.value; if (p) PASTE = p.value;
  }
  function copyText(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t).then(function () { return true; }, function () { return false; });
    var a = C.querySelector("#shcode"); if (!a) return Promise.resolve(false);
    a.focus(); a.select(); try { return Promise.resolve(document.execCommand("copy")); } catch (e) { return Promise.resolve(false); }
  }
  C.addEventListener("input", function () { readInputs(); if (CHK && C.querySelector("#shpaste") === document.activeElement) { CHK = null; } });
  C.addEventListener("click", function (e) {
    if (!S) return; var t = e.target.closest ? e.target : null; if (!t) return; readInputs();
    var b = function (a) { return t.closest("[data-" + a + "]"); };
    if (b("copy")) { copyText(MADE.code).then(function (ok) { toast(ok ? "Code copied" : "Press and hold the code to copy it"); }); return; }
    if (b("send")) { try { navigator.share({ text: MADE.code }); } catch (x) {} return; }
    if (b("hide")) { MADE = null; paint(true); return; }
    if (BUSY) return;
    if (b("make")) { call("/api/sharecode/make", { name: NAME }, function (j) { MADE = j; }); return; }
    if (b("check")) { CHK = null; call("/api/sharecode/check", { code: PASTE }, function (j) { CHK = j; }); return; }
    if (b("no")) { CHK = null; ERR = ""; paint(true); return; }
    if (b("load")) {
      if (!CHK || !S.demo) return;
      call("/api/sharecode/load", { code: PASTE }, function (j) { S = j; CHK = null; PASTE = ""; toast("Settings loaded"); if (window.sxPrefsReload) window.sxPrefsReload(); });
      return;
    }
    if (b("undo")) { call("/api/sharecode/undo", {}, function (j) { S = j; CHK = null; toast("Your old settings are back"); if (window.sxPrefsReload) window.sxPrefsReload(); }); return; }
  });
  setInterval(function () {
    var u = me(), sg = u ? [u.uid, !!u.verified].join("|") : ""; TK++;
    if (sg !== SIG) { SIG = sg; S = null; MADE = null; CHK = null; PASTE = ""; ERR = ""; paint(true); if (u) load(); return; }
    if (ready() && vb.classList.contains("on") && !document.hidden && !CHK && !MADE && TK % 30 === 0) load();
  }, 1000);
  new MutationObserver(function () { if (ready() && vb.classList.contains("on") && !BUSY && !CHK) load(); }).observe(vb, { attributes: true, attributeFilter: ["class"] });
  paint();
})();
