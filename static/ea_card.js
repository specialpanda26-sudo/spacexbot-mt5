/* EA1: "SpaceX EA for MetaTrader 5" card. Subscribers get the MQ5 code, the version, and click-by-click steps. Uses /api/ea/info and /api/ea/code. */
(function () {
  "use strict";
  var vc = document.getElementById("view-connect");
  if (!vc || !window.SXA) return;
  var S = document.createElement("style");
  S.textContent = ".steps .eaok{color:var(--ok,#1a8f4c);font-size:14px;margin-top:2px}.steps .eabad{font-size:14px;margin-top:2px}#eac textarea{resize:vertical}";
  document.head.appendChild(S);
  var A = document.createElement("div"); A.className = "card"; A.id = "eac";
  var base = document.getElementById("mt5c"); if (base && base.parentNode === vc) vc.insertBefore(A, base.nextSibling); else vc.insertBefore(A, vc.firstChild);
  var I = null, ERR = "", TAB = "first", CODE = "", SHOW = false, BUSY = false, last = 0;
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(t) { if (window.sxToast) window.sxToast(t); }
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function api(p) { return SXA.api(p); }

  function chip() {
    if (!I) return "";
    if (I.outdated) return '<span class="chip stop">Update available</span>';
    if (I.installed) return '<span class="chip ok">Up to date</span>';
    return '<span class="chip">Not reported yet</span>';
  }
  function stepsHtml(list) {
    return '<ol class="steps">' + list.map(function (s) {
      return "<li><div><b>" + esc(s.t) + "</b><span>" + esc(s.d) + "</span>" +
        (s.ok ? '<span class="eaok">You should see: ' + esc(s.ok) + "</span>" : "") +
        (s.bad ? '<span class="eabad">If not: ' + esc(s.bad) + "</span>" : "") + "</div></li>";
    }).join("") + "</ol>";
  }
  function paint() {
    var u = me(), h = '<div class="card-head"><h2>SpaceX EA for MetaTrader 5</h2>' + chip() + "</div>";
    if (!u || !u.verified || !u.active) { A.style.display = "none"; return; }
    A.style.display = "";
    if (!I) { A.innerHTML = h + (ERR ? '<p class="err" role="alert">' + esc(ERR) + "</p>" : '<p class="note">Loading the EA.</p>'); return; }
    var o = h;
    o += '<p class="note" style="font-weight:800;color:var(--fg)">Newest version: ' + esc(I.version) + " · Your MT5 runs: " + esc(I.installed || "not reported yet") + "</p>";
    if (I.outdated) o += '<p class="note" style="color:var(--bad);font-weight:800">Your EA is older. Tap Copy code, then follow the Update steps below. It takes about a minute. Your old version keeps working until you do.</p>';
    o += '<p class="note">This is the full MQ5 code of the bridge. It already has this server address filled in. Your personal key is never inside it, you type that into the EA settings.</p>';
    o += '<div class="jrow"><button class="btn primary" data-ea="copy"' + (BUSY ? " disabled" : "") + '>Copy code</button><button class="btn" data-ea="dl"' + (BUSY ? " disabled" : "") + ">Download file</button></div>";
    o += '<button class="btn block" data-ea="show">' + (SHOW ? "Hide the code" : "Show the code (to copy by hand)") + "</button>";
    if (SHOW) o += '<textarea class="inp" id="eatx" readonly spellcheck="false" style="width:100%;height:220px;font-family:monospace;font-size:12px;margin-top:8px">' + esc(CODE || "Loading...") + "</textarea>";
    o += '<div class="seg" role="group" aria-label="Steps" style="margin:14px 0 10px"><button type="button" data-ea="t1" aria-pressed="' + (TAB === "first") + '">First install</button><button type="button" data-ea="t2" aria-pressed="' + (TAB === "update") + '">Update</button></div>';
    o += stepsHtml(TAB === "first" ? I.steps.first : I.steps.update);
    if (I.changelog && I.changelog.length) {
      o += "<details><summary>What is new</summary>" + I.changelog.map(function (c) {
        return '<p class="note"><b>Version ' + esc(c.v) + (c.date ? " (" + esc(c.date) + ")" : "") + "</b></p><ul>" + c.notes.map(function (n) { return '<li class="note">' + esc(n) + "</li>"; }).join("") + "</ul>";
      }).join("") + "</details>";
    }
    o += '<p class="note">An MT5 program cannot rewrite and compile itself. So the EA tells you when a newer version exists, and the update is a copy, paste and F7.</p>';
    A.innerHTML = o + (ERR ? '<p class="err" role="alert">' + esc(ERR) + "</p>" : "");
  }
  function load(force) {
    var u = me(); if (!u || !u.verified || !u.active) { I = null; return paint(); }
    if (!force && I && Date.now() - last < 20000) return;
    last = Date.now();
    api("/api/ea/info").then(function (j) { I = j; ERR = ""; }, function (e) { ERR = (e && e.message) || "Could not load the EA."; }).then(paint);
  }
  function getCode() {
    if (CODE) return Promise.resolve(CODE);
    return api("/api/ea/code").then(function (j) { CODE = j.code || ""; return CODE; });
  }
  function fallbackCopy(t) {
    var x = document.createElement("textarea"); x.value = t; x.style.cssText = "position:fixed;opacity:0"; document.body.appendChild(x); x.select();
    var ok = false; try { ok = document.execCommand("copy"); } catch (e) {} document.body.removeChild(x); return ok;
  }
  A.addEventListener("click", function (e) {
    var b = e.target.closest("[data-ea]"); if (!b || BUSY) return; var a = b.dataset.ea;
    if (a === "t1") { TAB = "first"; return paint(); }
    if (a === "t2") { TAB = "update"; return paint(); }
    if (a === "show") { SHOW = !SHOW; paint(); if (SHOW) getCode().then(paint, function (er) { ERR = er.message || "Could not load the code."; paint(); }); return; }
    if (a === "copy" || a === "dl") {
      BUSY = true; ERR = ""; paint();
      getCode().then(function (t) {
        if (a === "copy") {
          var done = function () { toast("Code copied. Now paste it in MetaEditor."); };
          if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t).then(done, function () { if (fallbackCopy(t)) done(); else { SHOW = true; ERR = "Could not copy by itself. Press and hold in the box below, choose Select all, then Copy."; } });
          if (fallbackCopy(t)) done(); else { SHOW = true; ERR = "Could not copy by itself. Press and hold in the box below, choose Select all, then Copy."; }
        } else {
          var url = URL.createObjectURL(new Blob([t], { type: "text/plain" })), l = document.createElement("a");
          l.href = url; l.download = "SpaceXBridge.mq5"; document.body.appendChild(l); l.click(); document.body.removeChild(l); setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
          toast("SpaceXBridge.mq5 downloaded");
        }
      }).catch(function (er) { ERR = (er && er.message) || "Could not get the code."; }).then(function () { BUSY = false; paint(); });
    }
  });
  document.addEventListener("visibilitychange", function () { if (!document.hidden) load(); });
  setInterval(function () { if (!document.hidden) load(); }, 60000);
  var n = 0, t = setInterval(function () { load(); if (++n > 20 || I) clearInterval(t); }, 1500);
  load(true);
})();
