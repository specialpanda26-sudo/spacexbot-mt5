/* Section SC2: "Screen assistant" card (Bot tab) with the talking panel.
   The person presses Watch, shares one browser tab or window, and every ~20 s (or on "Read now") ONE picture goes to POST /api/screen/read.
   The server's AI only READS the chart; the bot answers in words. The page shows the site's cartoon for each situation.
   SC2 places nothing and saves nothing: Explain level only (Suggest = SC4, Auto = SC5, both shown as "soon").
   The picture lives in one local variable, is sent, and is dropped. It is never put in storage, a log or the page. */
(function () {
  "use strict";
  var EVERY = 20000, MAXSIDE = 1280, MAXB64 = 780000;
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---- pure helpers (the test runs these in node) ---- */
  function fit(w, h) {                       /* size to send: long side at most MAXSIDE, never bigger than the source */
    w = +w || 0; h = +h || 0; if (w < 1 || h < 1) return null;
    var k = Math.min(1, MAXSIDE / Math.max(w, h));
    return { w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k)) };
  }
  function nums(a) { return (Array.isArray(a) ? a : []).filter(function (x) { return typeof x === "number" && isFinite(x); }).slice(0, 4).join(", "); }
  function pick(r) {                         /* r = {kind: idle|scan|read|err, read, bot, status, text} -> {pic, head, say, tone} */
    r = r || { kind: "idle" };
    if (r.kind === "scan") return { pic: "eye", head: "Looking at your chart...", say: "Hold on. I am reading the chart and asking the bot what it thinks.", tone: "info" };
    if (r.kind === "err") {
      var s = r.status, t = r.text || "Something went wrong. Try again in a moment.";
      if (s === 429) return { pic: "wait", head: "One moment", say: t, tone: "watch" };
      if (s === 402) return { pic: "coin", head: "You need an active plan", say: t, tone: "watch" };
      if (s === 403) return { pic: "off", head: "The screen assistant is off", say: t, tone: "stop" };
      return { pic: "cx", head: "I could not read it this time", say: t, tone: "stop" };
    }
    if (r.kind === "read") {
      var rd = r.read || {}, b = r.bot;
      if (!rd.readable) return { pic: "off", head: "I could not read this chart", say: (rd.note || "Show one market with its name and price on the screen, then try again."), tone: "stop" };
      if (!b) return { pic: "wait", head: "I read the chart", say: rd.note || "", tone: "info" };
      var c = b.code, say = b.text || "";
      if (c === "agree") return { pic: "ok", head: "I see a possible trade.", say: say, tone: "ok" };
      if (c === "blocked") return { pic: /weekend|Friday|rests/i.test(say) ? "sleep" : "shield", head: "I see a setup, but I cannot trade right now.", say: say, tone: "watch" };
      if (c === "disagree") return { pic: "wait", head: "We do not agree, so I stay out.", say: say, tone: "watch" };
      if (c === "no_setup") return { pic: "wait", head: "Nothing to trade here yet.", say: say, tone: "info" };
      if (c === "bot_only") return { pic: "wait", head: "The bot sees a setup.", say: say, tone: "watch" };
      return { pic: "wait", head: "I can only give you the AI read.", say: say, tone: "info" };      /* no_data and anything new */
    }
    return { pic: "eye", head: "Show me a chart.", say: "Press Watch and share the tab with your chart. I will read it and tell you what the bot thinks.", tone: "info" };
  }
  function lines(read, bot) {                /* plain-word facts under the bubble */
    var o = [];
    if (!read || !read.readable) return o;
    var m = [];
    if (read.symbol) m.push("Market: " + read.symbol);
    if (read.timeframe && read.timeframe !== "unknown") m.push("Timeframe: " + read.timeframe);
    if (read.trend && read.trend !== "unclear") m.push("Trend: " + read.trend);
    if (m.length) o.push(m.join(" · "));
    var sp = nums(read.support), rs = nums(read.resistance);
    if (sp || rs) o.push((sp ? "Support near " + sp + ". " : "") + (rs ? "Resistance near " + rs + "." : ""));
    if (Array.isArray(read.patterns) && read.patterns.length) o.push("Patterns: " + read.patterns.slice(0, 5).join(", "));
    if (read.bias === "buy" || read.bias === "sell") o.push("The AI leans " + read.bias + ".");
    var g = bot && bot.signal;
    if (g) o.push("The bot's own plan: " + g.side + " near " + g.entry + ", stop loss " + g.sl + ", target " + g.tp + (g.strategy_name ? " (" + g.strategy_name + ")" : "") + ".");
    return o;
  }
  window.SXSC = { pick: pick, lines: lines, fit: fit, MAXB64: MAXB64, EVERY: EVERY };

  if (!window.SXA) return;
  var vb = document.getElementById("view-bot"); if (!vb) return;
  function me() { try { return SXA.user(); } catch (e) { return null; } }

  /* ---- look: the site's classes and variables only ---- */
  var st = document.createElement("style"); st.id = "sc2";
  st.textContent =
    ".sc2p{display:grid;grid-template-columns:104px 1fr;gap:12px;align-items:center}" +
    ".sc2p .ill2{width:104px;height:auto;display:block}" +
    ".sc2say{position:relative;background:var(--surface2);border:1px solid var(--line);border-radius:14px;padding:10px 12px;min-width:0}" +
    ".sc2say:before{content:\"\";position:absolute;left:-7px;top:24px;width:12px;height:12px;background:var(--surface2);border-left:1px solid var(--line);border-bottom:1px solid var(--line);transform:rotate(45deg)}" +
    ".sc2say b{display:block;color:var(--fg)}.sc2say p{margin:4px 0 0;color:var(--muted);overflow-wrap:anywhere}" +
    ".sc2l{margin:10px 0 0;padding:0;list-style:none;display:grid;gap:4px;color:var(--fg);font-size:.9em;overflow-wrap:anywhere}" +
    ".sc2r{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}" +
    "@media (prefers-reduced-motion:no-preference){.sc2dot{animation:sc2pu 1.8s ease-in-out infinite}.ill2 .mg{animation:sc2mg 3.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}" +
    "@keyframes sc2pu{50%{opacity:.45}}@keyframes sc2mg{0%,100%{transform:translate(0,0)}50%{transform:translate(-14px,6px)}}}";
  document.head.appendChild(st);

  var C = document.createElement("div"); C.className = "card"; C.id = "screenc"; C.hidden = true;
  vb.insertBefore(C, vb.firstChild ? vb.firstChild.nextSibling : null);

  var D = null, R = { kind: "idle" }, WATCH = false, BUSY = false, ERR = "", LH = "", USED = null, CAP = null;
  var STREAM = null, VID = null, TIMER = 0, UID = null;

  function canShare() { return !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia); }
  function draw() {
    var u = me(), admin = !!(u && u.admin);
    var show = !!(u && u.verified && D && (D.on || admin)); C.hidden = !show; C.style.display = show ? "" : "none";
    var h = "";
    if (show) {
      var plan = !!(D.trade && D.trade.allowed), can = !!D.on && plan;
      var chip = !D.on ? ["stop", "Off"] : !plan ? ["watch", "Plan needed"] : WATCH ? ["ok sc2dot", "Watching"] : ["info", "Ready"];
      var v = pick(R), pic = (window.IL2 && (window.IL2[v.pic] || window.IL2.wait)) || "";
      var ls = lines(R.read, R.bot);
      h = '<div class="card-head"><h2>Screen assistant</h2><span class="chip ' + chip[0] + '">' + chip[1] + "</span></div>" +
        '<div class="sc2p"><div>' + pic + '</div><div class="sc2say"><b>' + esc(v.head) + "</b><p>" + esc(v.say) + "</p></div></div>" +
        (ls.length ? '<ul class="sc2l">' + ls.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" : "") +
        '<div class="sc2r">' +
        (WATCH ? '<button type="button" class="btn" data-a="stop">Stop watching</button><button type="button" class="btn primary" data-a="now"' + (BUSY ? " disabled" : "") + ">Read now</button>"
               : '<button type="button" class="btn primary" data-a="watch"' + (can ? "" : " disabled") + ">Watch my screen</button>") + "</div>" +
        '<div class="seg" role="group" aria-label="What the screen assistant may do" style="justify-self:start;max-width:100%;overflow-x:auto;margin-top:10px">' +
        '<button type="button" aria-pressed="true">Explain</button><button type="button" aria-pressed="false" disabled>Suggest · soon</button><button type="button" aria-pressed="false" disabled>Auto · soon</button></div>' +
        (ERR ? '<p class="err">' + esc(ERR) + "</p>" : "") +
        '<p class="note">This is a read of your screen, not advice. It is the bot, not the AI, that decides whether it could trade, and it places nothing here. ' +
        "Everything you can see on the shared screen goes to the AI service, so close private screens first. The picture is dropped right after the answer.</p>" +
        (USED != null ? '<p class="note">' + esc(USED + " of " + CAP + " reads used today.") + "</p>" : "") +
        (!D.on ? '<p class="note">It is switched off for now.' + (admin ? ' <button type="button" class="btn" data-a="admin1">Switch it on</button>' : "") + "</p>"
               : (admin ? '<p class="note"><button type="button" class="btn" data-a="admin0">Switch it off for everyone</button></p>' : "")) +
        (!plan && D.on ? '<p class="note">Choose a plan to use it. Your plan also unlocks the bot.</p>' : "");
    }
    if (h !== LH) C.innerHTML = LH = h;
  }

  function stop(quiet) {
    clearTimeout(TIMER); TIMER = 0;
    try { if (STREAM) STREAM.getTracks().forEach(function (t) { try { t.onended = null; t.stop(); } catch (e) {} }); } catch (e) {}
    STREAM = null; if (VID) { try { VID.srcObject = null; } catch (e) {} } VID = null; WATCH = false; BUSY = false;
    if (!quiet) draw();
  }
  function grab() {                          /* one JPEG as base64, or null. The picture exists only inside this call and the request. */
    if (!VID || !VID.videoWidth) return null;
    var s = fit(VID.videoWidth, VID.videoHeight); if (!s) return null;
    var cv = document.createElement("canvas"); cv.width = s.w; cv.height = s.h;
    var g = cv.getContext("2d"); if (!g) return null; g.drawImage(VID, 0, 0, s.w, s.h);
    var q = [0.7, 0.55, 0.4];
    for (var i = 0; i < q.length; i++) { var d = cv.toDataURL("image/jpeg", q[i]), b = String(d).split(",")[1] || ""; if (b && b.length <= MAXB64) return b; }
    return null;
  }
  function later() { clearTimeout(TIMER); if (WATCH) TIMER = setTimeout(readNow, Math.max(EVERY, ((D && D.gap) || 10) * 1000 + 1000)); }
  function readNow() {
    if (!WATCH || BUSY) return;
    var img = grab();
    if (!img) { ERR = "The shared screen is not ready yet or the picture is too big. Trying again soon."; draw(); later(); return; }
    ERR = ""; BUSY = true; R = { kind: "scan" }; draw();
    SXA.api("/api/screen/read", { method: "POST", body: { context: "trade", image: img } }).then(function (j) {
      img = null; BUSY = false; R = { kind: "read", read: j.read, bot: j.bot }; USED = j.used; CAP = j.cap; draw(); later();
    }).catch(function (x) {
      img = null; BUSY = false; var s = x && x.status;
      R = { kind: "err", status: s, text: (x && x.message) || "" };
      if (s === 402 || s === 403 || s === 401) stop(true);
      draw(); later();
    });
  }
  function start() {
    if (WATCH) return;
    if (!canShare()) { ERR = "This browser cannot share the screen. Use Chrome, Edge or Firefox on a computer. The phone app version comes later."; draw(); return; }
    ERR = "";
    navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 1 }, audio: false }).then(function (s) {
      STREAM = s; VID = document.createElement("video"); VID.muted = true; VID.setAttribute("playsinline", ""); VID.srcObject = s;
      try { var p = VID.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {}
      s.getTracks().forEach(function (t) { t.onended = function () { R = { kind: "idle" }; stop(); }; });
      WATCH = true; R = { kind: "idle" }; draw(); TIMER = setTimeout(readNow, 900);
    }).catch(function (e) {
      ERR = (e && e.name === "NotAllowedError") ? "Sharing was cancelled. Nothing was sent." : "Could not start screen sharing.";
      draw();
    });
  }
  function load() {
    var u = me(); if (!(u && u.verified)) { D = null; if (WATCH) stop(true); draw(); return; }
    if (UID && u.uid !== UID && WATCH) { stop(true); R = { kind: "idle" }; }
    UID = u.uid;
    SXA.api("/api/screen/status").then(function (j) { D = j; draw(); }).catch(function () {});
  }
  function admin(v) {
    SXA.api("/api/admin/settings", { method: "POST", body: { screen_on: v } }).then(function () { if (!+v && WATCH) stop(true); load(); if (window.sxToast) window.sxToast(+v ? "Screen assistant is on" : "Screen assistant is off"); })
      .catch(function (x) { ERR = (x && x.message) || "Could not change the setting."; draw(); });
  }
  C.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("button[data-a]"); if (!b || b.disabled) return;
    var a = b.getAttribute("data-a");
    if (a === "watch") start(); else if (a === "stop") { R = { kind: "idle" }; stop(); } else if (a === "now") { clearTimeout(TIMER); readNow(); }
    else if (a === "admin1") admin("1"); else if (a === "admin0") admin("0");
  });
  window.addEventListener("pagehide", function () { stop(true); });
  load(); setInterval(load, 60000); setTimeout(load, 2500);
  window.SXSC.state = function () { return { watching: WATCH, busy: BUSY, hidden: C.hidden, html: LH }; };
})();
