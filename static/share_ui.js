/* Share my settings (Bot tab). GET /api/sharecode, POST /api/sharecode/make | check | load | undo.
   The Bot tab shows one tappable card. Tap it and a full page opens (cartoon, name box, paste box, list of the settings you borrowed).
   Make a code from my settings, or paste a friend's code: see what would change first, then Load. Back puts my old settings back. */
(function () {
  "use strict";
  if (!window.SXA) return;
  var vb = document.getElementById("view-bot"); if (!vb) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function ready() { var u = me(); return !!(u && u.verified); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(t) { if (window.sxToast) window.sxToast(t); }

  /* Cartoon: same sticker style and same character as the site's rocket / mail / coin pictures
     (violet outline, darker shade offset underneath). A settings card with sliders is sent to the character as a paper plane. */
  function mkArt(extra) {
    var K = "#7F61F5", G = ["#5BE38E", "#2FB864"], B = ["#56B6FF", "#2F86E0"], Y = ["#FFD43B", "#F0A800"], W = ["#FFFFFF", "#DCD6FF"];
    function one(t, c, m) {
      var f = m === "l" ? "none" : c[m === "h" ? 1 : 0];
      var a = m === "l" ? ' stroke="' + K + '" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"' : ' stroke="none"';
      return "<" + t + ' fill="' + f + '"' + a + "/>";
    }
    function seq(a) {
      var o = "";
      a.forEach(function (s) { o += one(s[0], s[1], "h") + '<g transform="translate(3.5 -3.5)">' + one(s[0], s[1], "f") + "</g>" + one(s[0], s[1], "l"); });
      return o;
    }
    function ln(d, w, c) {
      return '<path d="' + d + '" fill="none" stroke="' + (c || K) + '" stroke-width="' + (w || 3.5) + '" stroke-linecap="round" stroke-linejoin="round"/>';
    }
    var CH = [
      ['path d="M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18"', B],
      ['path d="M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z"', W],
      ['path d="M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z"', Y]
    ];
    var card =
      '<g transform="translate(20 26) rotate(-6 36 48)">' +
        seq([['rect width="72" height="96" rx="13"', W]]) +
        ln("M14 16h22", 4) +
        ln("M14 40h44M14 62h44M14 84h44", 3, "#C9C2F2") +
        '<g class="kn k1">' + seq([['circle cx="40" cy="40" r="7"', G]]) + "</g>" +
        '<g class="kn k2">' + seq([['circle cx="24" cy="62" r="7"', B]]) + "</g>" +
        '<g class="kn k3">' + seq([['circle cx="30" cy="84" r="7"', Y]]) + "</g>" +
      "</g>";
    var badge = '<g transform="translate(98 118)">' + seq([['circle r="15"', G]]) + ln("M-5 5l9-9M-3-5h7v7", 3.5, "#fff") + "</g>";
    var plane = '<g class="pl"><g transform="translate(98 22)">' + seq([['path d="M0 10L32 0L20 26L14 14z"', B]]) + ln("M14 14L32 0", 3) + "</g></g>";
    var trail = '<g stroke="' + Y[0] + '" stroke-width="3" stroke-linecap="round"><path d="M84 40l-8 4M90 52l-9 3M100 62l-6 5"/></g>';
    return '<svg class="ill2 shart-svg ' + (extra || "") + '" viewBox="0 0 240 170" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      ln("M114 146c-14 4-26 2-38-4", 4) + card + badge + trail + plane +
      '<g transform="translate(112 40)">' + seq(CH) + ln("M60 47q6 5 12 0", 3.5) + "</g>" +
      '<path class="sp" d="M200 24v10M195 29h10" stroke-width="3"/><path class="sp" d="M14 140v8M10 144h8" stroke-width="3"/>' +
      "</svg>";
  }

  if (!document.getElementById("shartcss")) {
    var st = document.createElement("style"); st.id = "shartcss";
    st.textContent =
      ".toast{z-index:300}" +
      /* the card on the Bot tab */
      "#sharec.card{padding:10px 14px}" +
      ".shgo{display:flex;align-items:center;gap:10px;width:100%;border:0;background:none;padding:0;text-align:left;color:var(--fg);font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}" +
      ".shgo:active{transform:scale(.985)}" +
      ".shgo-art{flex:0 0 auto;width:104px}.shgo-art .ill2{width:104px;max-width:none;margin:0}" +
      ".shgo-tx{flex:1;min-width:0;display:grid;gap:3px}.shgo-tx b{font-size:17px;font-weight:900}" +
      ".shgo-tx .sub{font-size:13.5px;font-weight:700;color:var(--muted);line-height:1.35}" +
      ".shgo-tx .chip{justify-self:start;margin-top:2px}" +
      ".shgo-ch{flex:0 0 auto;color:var(--muted)}" +
      /* the full page */
      "#sharepg{position:fixed;inset:0;z-index:55;background:var(--bg);color:var(--fg);overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch}" +
      "#sharepg[hidden]{display:none}" +
      ".shbar{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:12px;padding:calc(10px + env(safe-area-inset-top,0px)) 14px 10px;background:var(--bg);border-bottom:1px solid var(--line)}" +
      ".shbar b{font-size:18px;font-weight:900}" +
      ".shback{width:42px;height:42px;border-radius:14px;border:2px solid var(--line);background:var(--surface);box-shadow:0 3px 0 var(--line);display:grid;place-items:center;color:var(--fg);padding:0;cursor:pointer}" +
      ".shback:active{transform:translateY(3px);box-shadow:none}" +
      ".shbody{max-width:520px;margin:0 auto;padding:10px 16px calc(40px + env(safe-area-inset-bottom,0px));display:grid;gap:16px}" +
      ".shhero{display:grid;justify-items:center;text-align:center;gap:6px}" +
      ".shhero .ill2{width:210px;max-width:72%;margin:0}" +
      ".shhero h1{margin:4px 0 0;font-size:26px;font-weight:900;line-height:1.15}" +
      ".shhero .note{margin:0;max-width:34ch}" +
      ".shsec{background:var(--surface);border:2px solid var(--line);border-radius:22px;padding:16px;display:grid;gap:12px;min-width:0}" +
      ".shh{margin:0;font-size:17px;font-weight:900;display:flex;align-items:center;gap:8px}" +
      ".shh i{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-style:normal;font-size:13px;font-weight:900;background:var(--green-soft);color:var(--green-d)}" +
      "#sharepg .jrow{display:flex;gap:8px;flex-wrap:wrap}#sharepg .jrow .btn{flex:1 1 auto}" +
      ".shlist{border:2px solid var(--line);border-radius:16px;background:var(--surface2);overflow:hidden}" +
      ".shrow{display:grid;gap:2px;padding:10px 14px;border-bottom:1px solid var(--line)}.shrow:last-child{border-bottom:0}" +
      ".shrow b{font-size:14px;font-weight:900}.shrow span{font-size:13.5px;font-weight:700;color:var(--muted);word-break:break-word}.shrow span em{font-style:normal;color:var(--good);font-weight:900}" +
      ".shempty{display:grid;justify-items:center;gap:6px;text-align:center;border:2px dashed var(--line);border-radius:16px;padding:18px 14px}.shempty p{margin:0}" +
      ".shok{display:flex;align-items:center;gap:8px;font-weight:900;color:var(--good)}" +
      ".shok i{width:24px;height:24px;border-radius:50%;background:var(--green);color:var(--on-green);display:grid;place-items:center;font-style:normal;font-size:13px}" +
      "@media (prefers-reduced-motion:no-preference){" +
      ".shart-svg .kn,.shart-svg .pl{transform-box:fill-box;animation-timing-function:ease-in-out;animation-iteration-count:infinite}" +
      ".shart-svg .kn{animation-name:sxshk;animation-duration:3.2s}.shart-svg .k2{animation-delay:-1.1s}.shart-svg .k3{animation-delay:-2.1s}" +
      ".shart-svg .pl{animation-name:sxspl;animation-duration:2.8s}" +
      "@keyframes sxshk{0%,100%{transform:translateX(-5px)}50%{transform:translateX(5px)}}" +
      "@keyframes sxspl{0%,100%{transform:translate(0,0) rotate(0)}50%{transform:translate(6px,-6px) rotate(-5deg)}}" +
      "#sharepg:not([hidden]){animation:sxshin .35s cubic-bezier(.22,1,.36,1)}@keyframes sxshin{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}}";
    document.head.appendChild(st);
  }

  /* the card on the Bot tab: it is a button, not a folding card, so it has no heading of its own */
  var C = document.createElement("div"); C.className = "card"; C.id = "sharec"; C.hidden = true;
  var pr = document.getElementById("presetc"), pc = document.getElementById("prefc"), after = document.getElementById("posc") || document.getElementById("botstatec");
  if (pr) vb.insertBefore(C, pr.nextSibling); else if (pc) vb.insertBefore(C, pc); else vb.insertBefore(C, after ? after.nextSibling : vb.firstChild);

  /* the full page (it sits over the whole app, with its own Back button) */
  var P = document.createElement("div"); P.id = "sharepg"; P.hidden = true; P.setAttribute("role", "dialog"); P.setAttribute("aria-modal", "true"); P.setAttribute("aria-label", "Share my settings");
  P.innerHTML = '<div class="shbar"><button type="button" class="shback" data-close="1" aria-label="Back"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg></button><b>Share my settings</b></div><div class="shbody" id="shbody"></div>';
  document.body.appendChild(P);
  var PB = P.querySelector("#shbody");

  var S = null, MADE = null, CHK = null, LOADED = null, NAME = "", PASTE = "", BUSY = false, ERR = "", SIG = "", LH = "", LP = "", TK = 0, OPEN = false;
  var AREA = "width:100%;box-sizing:border-box;border:2px solid var(--line);border-radius:14px;padding:10px 12px;background:var(--surface2);color:var(--ink);font:inherit;font-size:14px;word-break:break-all";

  function ago(t) {
    var s = Math.max(0, Math.floor(Date.now() / 1000) - Number(t || 0)), m = Math.floor(s / 60);
    return m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.floor(m / 60) + " h ago" : Math.floor(m / 1440) + " d ago";
  }
  function listHtml(rows, cols) {
    return '<div class="shlist">' + rows.map(function (r) {
      return '<div class="shrow"><b>' + esc(r.label) + "</b><span>" + (cols ? esc(r.now) + " &rarr; <em>" + esc(r.new) + "</em>" : esc(r.value)) + "</span></div>";
    }).join("") + "</div>";
  }
  function makeHtml() {
    var h = '<p class="note" style="font-weight:800;color:var(--ink);margin:4px 0 0">Your code</p>';
    h += '<textarea id="shcode" readonly rows="4" style="' + AREA + '">' + esc(MADE.code) + "</textarea>";
    h += '<div class="jrow"><button type="button" class="btn primary" data-copy="1">Copy code</button>' + (navigator.share ? '<button type="button" class="btn" data-send="1">Send</button>' : "") + '<button type="button" class="btn" data-hide="1">Close</button></div>';
    h += '<p class="note">This code holds ' + esc(MADE.count) + " settings. It has no keys, no balance, no email and no Demo/Real choice. Anyone you give it to can load these settings, so send it only to people you trust.</p>";
    h += '<details><summary class="note" style="cursor:pointer;font-weight:800">See what is inside</summary>' + listHtml(MADE.rows, false) + "</details>";
    return h;
  }
  /* the list of settings borrowed from the friend's code */
  function borrowedHtml() {
    var h = '<p class="shh"><i>3</i>Settings from your friend</p>';
    if (CHK) {
      h += '<p class="note" style="font-weight:800;color:var(--ink);margin:0">' + (CHK.name ? esc(CHK.name) + " " : "") + "settings" + (CHK.made ? " (made " + esc(ago(CHK.made)) + ")" : "") + "</p>";
      if (CHK.rows.length) h += '<p class="note" style="margin:0">' + esc(CHK.rows.length) + " will change" + (CHK.same ? ", " + esc(CHK.same) + " are already the same" : "") + ":</p>" + listHtml(CHK.rows, true);
      else h += '<p class="note" style="margin:0">Nothing would change: you already have these settings.</p>';
      (CHK.warnings || []).forEach(function (w) { h += '<p class="note" style="color:var(--bad);font-weight:800;margin:0">' + esc(w) + "</p>"; });
      (CHK.notes || []).forEach(function (w) { h += '<p class="note" style="margin:0">' + esc(w) + "</p>"; });
      h += '<p class="note" style="margin:0">Loading never starts your bot and never switches Real mode on.</p>';
      var dis = BUSY || !S.demo || !CHK.rows.length;
      h += '<div class="jrow"><button type="button" class="btn primary" data-load="1"' + (dis ? " disabled" : "") + ">" + (BUSY ? "Loading..." : "Load these settings") + '</button><button type="button" class="btn" data-no="1"' + (BUSY ? " disabled" : "") + ">Cancel</button></div>";
    } else if (LOADED && LOADED.rows && LOADED.rows.length) {
      h += '<p class="shok"><i>&#10003;</i>' + esc(LOADED.rows.length) + " settings loaded" + (LOADED.name ? " from " + esc(LOADED.name) : "") + "</p>" + listHtml(LOADED.rows.map(function (r) { return { label: r.label, value: r.new }; }), false);
      h += '<p class="note" style="margin:0">Your bot is not started. Try these on Demo first.</p>';
    } else {
      h += '<div class="shempty">' + mkArt("sm") + '<p class="note">The settings from a friend\'s code show up here. Paste a code above and tap Check code. Nothing is saved until you load it.</p></div>';
    }
    return h;
  }
  /* the card on the Bot tab */
  function cardHtml() {
    var chip = S && S.last ? '<span class="chip info">' + (S.last.name ? esc(S.last.name) + " loaded" : "Code loaded") + "</span>" : "";
    return '<button type="button" class="shgo" data-open="1" aria-haspopup="dialog"><span class="shgo-art">' + mkArt("sm") + '</span><span class="shgo-tx"><b>Share my settings</b><span class="sub">Send your settings to a friend, or use theirs.</span>' + chip + '</span><span class="shgo-ch"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg></span></button>';
  }
  /* the full page */
  function pageHtml() {
    var h = '<div class="shhero">' + mkArt("") + "<h1>Share my settings</h1>" + (S && S.last ? '<span class="chip info">' + (S.last.name ? esc(S.last.name) + " loaded" : "Code loaded") + "</span>" : "") +
      '<p class="note">Make a code from all your bot settings and send it to a friend, or paste a friend\'s code to get the same settings. You see what will change before anything is saved, and you can go back.</p></div>';
    if (!S) return h + '<p class="note" style="text-align:center">' + esc(ERR || "Loading...") + "</p>";
    h += '<div class="shsec"><p class="shh"><i>1</i>Make my code</p>' +
      '<div class="field"><label>Name for my code (optional)</label><input id="shname" type="text" maxlength="24" autocomplete="off" value="' + esc(NAME) + '" placeholder="e.g. My gold settings"></div>' +
      '<div class="jrow"><button type="button" class="btn primary" data-make="1"' + (BUSY ? " disabled" : "") + ">Make my code</button></div>" + (MADE ? makeHtml() : "") + "</div>";
    h += '<div class="shsec"><p class="shh"><i>2</i>Paste a friend\'s code</p>' +
      '<div class="field"><label>Code</label><textarea id="shpaste" rows="3" placeholder="SXB1...." style="' + AREA + '">' + esc(PASTE) + "</textarea></div>" +
      '<div class="jrow"><button type="button" class="btn" data-check="1"' + (BUSY ? " disabled" : "") + ">Check code</button></div>" +
      (!S.demo ? '<p class="note" style="margin:0">To load a code, switch to Demo first (Connect tab). Try the settings on Demo, then decide about Real.</p>' : "") +
      (ERR ? '<p class="note" style="color:var(--bad);margin:0" role="alert">' + esc(ERR) + "</p>" : "") + "</div>";
    h += '<div class="shsec" id="shlist">' + borrowedHtml() + "</div>";
    if (S.can_undo) h += '<div class="shsec"><p class="shh">Want your old settings?</p><div class="jrow"><button type="button" class="btn" data-undo="1"' + (BUSY ? " disabled" : "") + ">Back to my old settings</button></div></div>";
    return h;
  }
  function on() { return ready() && (S ? true : !!ERR); }
  function paint(force) {
    var show = on(); C.hidden = !show; C.style.display = show ? "" : "none";
    if (!show) { if (LH) { C.innerHTML = ""; LH = ""; } if (OPEN) shut(true); return; }
    var h = cardHtml(); if (h !== LH) C.innerHTML = LH = h;
    if (!OPEN) return;
    var a = document.activeElement; if (!force && a && (a.id === "shname" || a.id === "shpaste") && P.contains(a)) return;          /* never redraw while the person is typing */
    var p = pageHtml(); if (p !== LP) PB.innerHTML = LP = p;
  }
  function pop() { try { if (history.state && history.state.sxshare) history.back(); } catch (e) {} }
  function openPage() {
    if (OPEN) return; OPEN = true;
    try { history.pushState({ sxshare: 1 }, ""); } catch (e) {}
    P.hidden = false; P.scrollTop = 0; document.body.style.overflow = "hidden"; load(); paint(true);
  }
  function shut(fromPop) {
    if (!OPEN) return; OPEN = false; P.hidden = true; document.body.style.overflow = ""; LP = ""; PB.innerHTML = "";
    if (!fromPop) pop();
  }
  window.addEventListener("popstate", function () { if (OPEN) shut(true); });
  document.addEventListener("keydown", function (e) { if (OPEN && e.key === "Escape") shut(); });
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
    var n = P.querySelector("#shname"), p = P.querySelector("#shpaste");
    if (n) NAME = n.value; if (p) PASTE = p.value;
  }
  function toList() { setTimeout(function () { var l = P.querySelector("#shlist"); if (l && l.scrollIntoView) l.scrollIntoView({ behavior: "smooth", block: "start" }); }, 60); }
  function copyText(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t).then(function () { return true; }, function () { return false; });
    var a = P.querySelector("#shcode"); if (!a) return Promise.resolve(false);
    a.focus(); a.select(); try { return Promise.resolve(document.execCommand("copy")); } catch (e) { return Promise.resolve(false); }
  }
  P.addEventListener("input", function (e) {
    readInputs();
    if (CHK && e.target && e.target.id === "shpaste") {            /* new text: the old check no longer fits, so clear the list without touching the box */
      CHK = null; var l = P.querySelector("#shlist"); if (l) l.innerHTML = borrowedHtml(); LP = "";
    }
  });
  C.addEventListener("click", function (e) { if (e.target.closest && e.target.closest("[data-open]")) openPage(); });
  P.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target : null; if (!t) return;
    if (t.closest("[data-close]")) { shut(); return; }
    if (!S) return; readInputs();
    var b = function (a) { return t.closest("[data-" + a + "]"); };
    if (b("copy")) { copyText(MADE.code).then(function (ok) { toast(ok ? "Code copied" : "Press and hold the code to copy it"); }); return; }
    if (b("send")) { try { navigator.share({ text: MADE.code }); } catch (x) {} return; }
    if (b("hide")) { MADE = null; paint(true); return; }
    if (BUSY) return;
    if (b("make")) { call("/api/sharecode/make", { name: NAME }, function (j) { MADE = j; }); return; }
    if (b("check")) { CHK = null; LOADED = null; call("/api/sharecode/check", { code: PASTE }, function (j) { CHK = j; }); toList(); return; }
    if (b("no")) { CHK = null; ERR = ""; paint(true); return; }
    if (b("load")) {
      if (!CHK || !S.demo) return;
      call("/api/sharecode/load", { code: PASTE }, function (j) { LOADED = { name: CHK && CHK.name, rows: (CHK && CHK.rows) || [] }; S = j; CHK = null; PASTE = ""; toast("Settings loaded"); if (window.sxPrefsReload) window.sxPrefsReload(); toList(); });
      return;
    }
    if (b("undo")) { call("/api/sharecode/undo", {}, function (j) { S = j; CHK = null; LOADED = null; toast("Your old settings are back"); if (window.sxPrefsReload) window.sxPrefsReload(); }); return; }
  });
  setInterval(function () {
    var u = me(), sg = u ? [u.uid, !!u.verified].join("|") : ""; TK++;
    if (sg !== SIG) { SIG = sg; S = null; MADE = null; CHK = null; LOADED = null; PASTE = ""; ERR = ""; paint(true); if (u) load(); return; }
    if (ready() && vb.classList.contains("on") && !document.hidden && !CHK && !MADE && TK % 30 === 0) load();
  }, 1000);
  new MutationObserver(function () { if (ready() && vb.classList.contains("on") && !BUSY && !CHK) load(); }).observe(vb, { attributes: true, attributeFilter: ["class"] });
  paint();
})();
