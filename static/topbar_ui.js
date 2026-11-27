/* Top banner (TB1): three buttons under the header, Search, Alerts and Settings, each opening a panel that drops from the top.
   Search   : finds any single setting and jumps to it (window.SXfind / SXgo from index.html).
   Alerts   : the in-app notification inbox (GET /api/inbox). No notifications = a cartoon that says it is all quiet.
   Settings : every setting card in the app, grouped by tab. Tap one to jump to it. Same sticker cartoons and colours as the rest of the site. */
(function () {
  "use strict";
  if (!window.SXA) return;
  var top = document.querySelector(".top"); if (!top || !top.parentNode) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(t) { if (window.sxToast) window.sxToast(t); }
  function ago(t) {
    var s = Math.max(0, Math.floor(Date.now() / 1000) - Number(t || 0)), m = Math.floor(s / 60);
    return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.floor(m / 60) + " h ago" : Math.floor(m / 1440) + " d ago";
  }
  var TABS = [["bot", "Bot"], ["connect", "Connect"], ["profile", "Profile"], ["trades", "Trades"], ["home", "Home"]];
  var TABNAME = { bot: "Bot tab", profile: "Profile", connect: "Connect", trades: "Trades", home: "Home" };
  var CATS = { trade: "Trade", risk: "Risk", news: "News", daily: "Daily", tips: "Tips", system: "System", billing: "Billing" };
  var IC = {
    search: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>',
    bell: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 17V11a6 6 0 0 1 12 0v6l2 2H4z"/><path d="M10 21h4"/></svg>',
    gear: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>',
    x: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    go: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>'
  };

  /* cartoons: same sticker style and same character as the rocket / mail / coin pictures (violet outline, darker shade offset underneath) */
  function art(kind) {
    var K = "#7F61F5", G = ["#5BE38E", "#2FB864"], B = ["#56B6FF", "#2F86E0"], Y = ["#FFD43B", "#F0A800"], W = ["#FFFFFF", "#DCD6FF"];
    function one(t, c, m) {
      var f = m === "l" ? "none" : c[m === "h" ? 1 : 0];
      var a = m === "l" ? ' stroke="' + K + '" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"' : ' stroke="none"';
      return "<" + t + ' fill="' + f + '"' + a + "/>";
    }
    function seq(a) { var o = ""; a.forEach(function (s) { o += one(s[0], s[1], "h") + '<g transform="translate(3.5 -3.5)">' + one(s[0], s[1], "f") + "</g>" + one(s[0], s[1], "l"); }); return o; }
    function ln(d, w, c) { return '<path d="' + d + '" fill="none" stroke="' + (c || K) + '" stroke-width="' + (w || 3.5) + '" stroke-linecap="round" stroke-linejoin="round"/>'; }
    var CH = [['path d="M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18"', B], ['path d="M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z"', W], ['path d="M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z"', Y]];
    var obj = "", extra = "";
    if (kind === "bell") {
      obj = '<g transform="translate(20 34)">' + seq([['path d="M40 6c-15 0-25 10-25 26v20l-9 15h68l-9-15V32C65 16 55 6 40 6z"', Y], ['circle cx="40" cy="82" r="8"', B]]) + ln("M40 -1v4", 4) + "</g>";
      extra = ln("M176 24h13l-13 14h13", 3.5) + ln("M196 8h9l-9 10h9", 3);
    } else if (kind === "search") {
      obj = '<g transform="translate(18 30)">' + ln("M62 64l26 26", 12) + ln("M62 64l26 26", 5, B[0]) + seq([['circle cx="40" cy="40" r="32"', W]]) + ln("M22 34a20 20 0 0 1 14-14", 3.5, "#C9C2F2") + "</g>";
      extra = '<path class="sp" d="M196 24v10M191 29h10" stroke-width="3"/>';
    } else {
      var t = ""; for (var i = 0; i < 8; i++) t += seq([['rect x="-7" y="-42" width="14" height="18" rx="4" transform="rotate(' + (i * 45) + ')"', G]]);
      obj = '<g transform="translate(58 84)">' + t + seq([['circle r="31"', G]]) + seq([['circle r="12"', W]]) + "</g>";
      extra = '<path class="sp" d="M196 24v10M191 29h10" stroke-width="3"/>';
    }
    return '<svg class="ill2 sm" viewBox="0 0 240 170" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ln("M114 146c-14 4-26 2-38-4", 4) + obj + '<g transform="translate(112 40)">' + seq(CH) + ln("M60 47q6 5 12 0", 3.5) + "</g>" + extra + '<path class="sp" d="M14 150v8M10 154h8" stroke-width="3"/></svg>';
  }
  function empty(kind, title, text) { return '<div class="tbe">' + art(kind) + "<b>" + esc(title) + "</b><p class=\"note\">" + esc(text) + "</p></div>"; }

  if (!document.getElementById("tbcss")) {
    var st = document.createElement("style"); st.id = "tbcss";
    st.textContent =
      ".tbn{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0 0}.tbn[hidden]{display:none}body.welcome .tbn,body.onb .tbn{display:none}" +
      ".tbb{position:relative;display:flex;align-items:center;justify-content:center;gap:7px;min-height:48px;padding:0 8px;border:2px solid var(--line);border-radius:16px;background:var(--surface);box-shadow:0 3px 0 var(--line);color:var(--fg);font:inherit;font-size:14px;font-weight:800;cursor:pointer;-webkit-tap-highlight-color:transparent}" +
      ".tbb:active{transform:translateY(3px);box-shadow:none}.tbb svg{flex:0 0 auto}" +
      ".tbd{position:absolute;top:-7px;right:-4px;min-width:20px;height:20px;padding:0 5px;border-radius:10px;background:var(--bad,#e5484d);color:#fff;font-style:normal;font-size:11px;font-weight:900;display:grid;place-items:center;border:2px solid var(--bg)}.tbd[hidden]{display:none}" +
      "#tbp{position:fixed;inset:0;z-index:97}#tbp[hidden]{display:none}" +
      ".tbbd{position:absolute;inset:0;background:rgba(10,14,28,.55);backdrop-filter:blur(6px)}" +
      ".tbpan{position:absolute;top:0;left:50%;transform:translateX(-50%);width:min(520px,100%);max-height:90vh;max-height:90dvh;overflow-y:auto;overscroll-behavior:contain;background:var(--bg);color:var(--fg);border:2px solid var(--line);border-top:0;border-radius:0 0 26px 26px;padding:calc(12px + env(safe-area-inset-top,0px)) 16px 18px;box-shadow:var(--shadow-lg,0 20px 50px rgba(0,0,0,.35));display:grid;gap:12px;align-content:start}" +
      "@media (prefers-reduced-motion:no-preference){.tbpan{animation:sxtbd .38s cubic-bezier(.22,1,.36,1)}@keyframes sxtbd{from{opacity:0;transform:translate(-50%,-26px)}to{opacity:1;transform:translate(-50%,0)}}}" +
      ".tbhd{display:flex;align-items:center;justify-content:space-between;gap:10px}.tbhd h2{margin:0;font-size:22px;font-weight:900}" +
      ".tbx{width:42px;height:42px;border-radius:14px;border:2px solid var(--line);background:var(--surface);box-shadow:0 3px 0 var(--line);display:grid;place-items:center;color:var(--fg);padding:0;cursor:pointer}.tbx:active{transform:translateY(3px);box-shadow:none}" +
      ".tbe{display:grid;justify-items:center;text-align:center;gap:4px;padding:6px 0 10px}.tbe .ill2{width:190px;max-width:70%;margin:0}.tbe b{font-size:18px;font-weight:900}.tbe .note{margin:0;max-width:32ch}" +
      ".tbhero{display:flex;align-items:center;gap:10px}.tbhero .ill2{width:96px;max-width:none;margin:0;flex:0 0 auto}.tbhero .note{margin:0}" +
      ".tbrow{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:12px 14px;border:2px solid var(--line);border-radius:16px;background:var(--surface);color:var(--fg);font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}.tbrow:active{transform:scale(.985)}" +
      ".tbrow>span{flex:1;min-width:0;display:grid;gap:2px}.tbrow b{font-size:15px;font-weight:900}.tbrow small{font-size:13px;font-weight:700;color:var(--muted);overflow-wrap:anywhere}.tbrow svg{flex:0 0 auto;color:var(--muted)}" +
      ".tblist{display:grid;gap:8px}" +
      ".tbgrp{border:2px solid var(--line);border-radius:18px;background:var(--surface2);padding:0 10px}.tbgrp>summary{list-style:none;display:flex;align-items:center;justify-content:space-between;padding:12px 4px;font-weight:900;cursor:pointer}.tbgrp>summary::-webkit-details-marker{display:none}.tbgrp[open]>summary{border-bottom:1px solid var(--line);margin-bottom:10px}.tbgrp .tblist{padding-bottom:10px}" +
      ".tbn1{display:grid;gap:3px;padding:12px 14px;border:2px solid var(--line);border-radius:16px;background:var(--surface)}.tbn1.new{border-color:var(--green,#2FB864);background:var(--green-soft,rgba(47,184,100,.12))}" +
      ".tbn1 .top1{display:flex;align-items:center;gap:8px;justify-content:space-between}.tbn1 b{font-size:15px;font-weight:900}.tbn1 p{margin:0;font-size:14px;font-weight:600;color:var(--fg)}.tbn1 small{font-size:12px;font-weight:700;color:var(--muted)}";
    document.head.appendChild(st);
  }

  /* the banner */
  var B = document.createElement("nav"); B.className = "tbn"; B.hidden = true; B.setAttribute("aria-label", "Search, alerts and settings");
  B.innerHTML = '<button type="button" class="tbb" data-p="search">' + IC.search + "<span>Search</span></button>" +
    '<button type="button" class="tbb" data-p="alerts">' + IC.bell + '<span>Alerts</span><i class="tbd" id="tbBadge" hidden></i></button>' +
    '<button type="button" class="tbb" data-p="set">' + IC.gear + "<span>Settings</span></button>";
  top.parentNode.insertBefore(B, top.nextSibling);

  /* the panel */
  var P = document.createElement("div"); P.id = "tbp"; P.hidden = true;
  P.innerHTML = '<div class="tbbd" data-x="1"></div><div class="tbpan" role="dialog" aria-modal="true" aria-labelledby="tbT"><div class="tbhd"><h2 id="tbT"></h2><button type="button" class="tbx" data-x="1" aria-label="Close">' + IC.x + '</button></div><div id="tbB" style="display:grid;gap:12px"></div></div>';
  document.body.appendChild(P);
  var PT = P.querySelector("#tbT"), PB = P.querySelector("#tbB");
  var cur = "", INBOX = null, IERR = "", RES = [], BUSY = false, TK = 0;

  function signed() { return !!me(); }
  function badge(n) { var b = document.getElementById("tbBadge"); if (!b) return; b.hidden = !(n > 0); b.textContent = n > 9 ? "9+" : String(n); }
  function loadInbox(then) {
    if (!signed() || BUSY) return; BUSY = true;
    SXA.api("/api/inbox").then(function (j) { INBOX = j; IERR = ""; badge(j.unread || 0); }, function () { if (!INBOX) IERR = "Cannot reach the server."; })
      .then(function () { BUSY = false; if (then) then(); if (cur === "alerts") renderAlerts(); });
  }

  /* ----- Search ----- */
  function renderSearch() {
    PT.textContent = "Search";
    PB.innerHTML = '<div class="field"><input class="inp" id="tbq" type="search" placeholder="e.g. daily loss, stake per entry, notifications" autocomplete="off" aria-label="Search settings"></div><div id="tbr" class="tblist"></div>';
    showRes(""); var q = PB.querySelector("#tbq");
    q.oninput = function () { showRes(q.value.trim()); }; setTimeout(function () { try { q.focus(); } catch (e) {} }, 220);
  }
  function showRes(v) {
    var R = PB.querySelector("#tbr"); if (!R) return; RES = [];
    if (v.length < 2) { R.innerHTML = empty("search", "Find any setting", "Type what you want to change, like daily loss, stake per entry, burst or notifications."); return; }
    var m = window.SXfind ? SXfind(v) : [];
    if (!m.length) { R.innerHTML = empty("search", "Nothing matched", "Try words like burst, stake, profit target, daily loss, repeat or notifications."); return; }
    RES = m; R.innerHTML = m.map(function (r, i) {
      return '<button type="button" class="tbrow" data-i="' + i + '"><span><b>' + esc(r.f || r.t) + "</b><small>" + esc((r.f ? r.t + " \u00b7 " : "") + (TABNAME[r.v] || r.v)) + "</small></span>" + IC.go + "</button>";
    }).join("");
  }

  /* ----- Settings ----- */
  function renderSettings() {
    PT.textContent = "Settings";
    var sc = window.SXscan ? SXscan() : [], by = {}; sc.forEach(function (k) { (by[k.v] = by[k.v] || []).push(k); });
    var fb = window.SXfb || [], h = '<div class="tbhero">' + art("gear") + '<p class="note">Every setting in the app. Tap one to jump straight to it.</p></div>', first = true;
    TABS.forEach(function (t) {
      var L = by[t[0]] || [], F = fb.filter(function (f) { return f[1] === t[0] && !L.some(function (k) { return k.tl === f[0].toLowerCase(); }); });
      if (!L.length && !F.length) return;
      h += '<details class="tbgrp"' + (first ? " open" : "") + "><summary><span>" + esc(t[1]) + '</span><span class="chip">' + (L.length + F.length) + '</span></summary><div class="tblist">'; first = false;
      L.forEach(function (k) {
        var sn = ((k.c.querySelector(".note") || {}).textContent || "").trim().slice(0, 90);
        h += '<button type="button" class="tbrow" data-v="' + esc(k.v) + '" data-t="' + esc(k.t) + '"><span><b>' + esc(k.t) + "</b>" + (sn ? "<small>" + esc(sn) + "</small>" : "") + "</span>" + IC.go + "</button>";
      });
      F.forEach(function (f) { h += '<button type="button" class="tbrow" data-v="' + esc(f[1]) + '" data-t="' + esc(f[0]) + '"><span><b>' + esc(f[0]) + "</b></span>" + IC.go + "</button>"; });
      h += "</div></details>";
    });
    h += '<button type="button" class="tbrow" data-dev="1"><span><b>On this device</b><small>Status banner, activity log, monitor mode, copy or clear the journal.</small></span>' + IC.go + "</button>";
    PB.innerHTML = h;
  }

  /* ----- Alerts ----- */
  function renderAlerts() {
    PT.textContent = "Alerts";
    if (!INBOX) { PB.innerHTML = '<p class="note" style="text-align:center">' + esc(IERR || "Checking...") + "</p>"; return; }
    var it = INBOX.items || [];
    if (!it.length) {
      PB.innerHTML = empty("bell", "No notifications", "It is all quiet. When the bot opens or closes a trade, reaches a limit or needs you, it shows here.") +
        '<button type="button" class="tbrow" data-v="profile" data-t="Notifications"><span><b>Choose which alerts you get</b><small>Phone alerts are set in Profile.</small></span>' + IC.go + "</button>"; return;
    }
    PB.innerHTML = '<div class="tblist">' + it.map(function (n) {
      return '<div class="tbn1' + (n.new ? " new" : "") + '"><div class="top1"><b>' + esc(n.title) + '</b><span class="chip' + (n.cat === "risk" ? " stop" : n.cat === "trade" ? " info" : "") + '">' + esc(CATS[n.cat] || "Alert") + "</span></div>" + (n.body ? "<p>" + esc(n.body) + "</p>" : "") + "<small>" + esc(ago(n.t)) + "</small></div>";
    }).join("") + '</div><button type="button" class="btn block" data-clear="1">Clear all</button>';
    if (INBOX.unread > 0) setTimeout(function () { if (cur !== "alerts" || P.hidden) return; SXA.api("/api/inbox/seen", { method: "POST", body: {} }).then(function (j) { INBOX.unread = 0; badge(0); }, function () {}); }, 900);
  }

  /* ----- open / close ----- */
  function openP(k) {
    if (cur && !P.hidden) { cur = k; render(); return; }
    cur = k; P.hidden = false; document.body.style.overflow = "hidden";
    try { history.pushState({ sxtb: 1 }, ""); } catch (e) {}
    render();
  }
  function render() { P.querySelector(".tbpan").scrollTop = 0; if (cur === "search") renderSearch(); else if (cur === "alerts") { renderAlerts(); loadInbox(); } else renderSettings(); }
  function closeP(fromPop) {
    if (P.hidden) return; P.hidden = true; cur = ""; document.body.style.overflow = ""; PB.innerHTML = "";
    if (!fromPop) { try { if (history.state && history.state.sxtb) history.back(); } catch (e) {} }
  }
  window.addEventListener("popstate", function () { if (!P.hidden) closeP(true); });
  document.addEventListener("keydown", function (e) { if (!P.hidden && e.key === "Escape") closeP(); });
  function jump(r) { closeP(); setTimeout(function () { if (window.SXgo) SXgo(r); }, 80); }

  B.addEventListener("click", function (e) { var b = e.target.closest && e.target.closest("[data-p]"); if (b) openP(b.dataset.p); });
  P.addEventListener("click", function (e) {
    var t = e.target; if (!t.closest) return;
    if (t.closest("[data-x]")) { closeP(); return; }
    var r = t.closest("[data-i]"); if (r && RES[+r.dataset.i]) { jump(RES[+r.dataset.i]); return; }
    r = t.closest("[data-v]"); if (r) { jump({ v: r.dataset.v, t: r.dataset.t, c: null }); return; }
    if (t.closest("[data-dev]")) { closeP(); setTimeout(function () { var o = document.createElement("button"); o.dataset.up = "set"; o.dataset.old = "1"; o.hidden = true; document.body.appendChild(o); o.click(); o.remove(); }, 80); return; }
    if (t.closest("[data-clear]")) { SXA.api("/api/inbox/clear", { method: "POST", body: {} }).then(function (j) { INBOX = j; badge(0); renderAlerts(); toast("Alerts cleared"); }, function () { toast("Not cleared"); }); }
  });
  /* the gear in the header opens the same Settings panel (the old device sheet stays reachable from the last row) */
  document.addEventListener("click", function (e) {
    var g = e.target.closest && e.target.closest('button[data-up="set"]');
    if (g && !g.dataset.old) { e.stopImmediatePropagation(); e.preventDefault(); openP("set"); }
  }, true);

  /* DUP1: one Settings and one Search. While the bar is showing, the header gear and the "Find a setting" card are hidden; signed out they come back. */
  function dupHide() {
    var on = signed(), g = document.querySelectorAll('.top-actions button[data-up="set"]'), f = document.querySelectorAll(".sxfind"), i;
    for (i = 0; i < g.length; i++) g[i].style.display = on ? "none" : "";
    for (i = 0; i < f.length; i++) f[i].style.display = on ? "none" : "";
  }
  setInterval(function () {
    TK++; B.hidden = !signed(); dupHide();
    if (signed() && !document.hidden && (TK === 2 || TK % 30 === 0)) loadInbox();
  }, 1000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden && signed()) loadInbox(); });
})();
