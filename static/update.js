/* spaceXBot: tells people inside the Android app when a newer app is out.
   Asks GitHub for the latest release (tag app-<build>), compares it with the installed build and shows a popup: Update now / Later.
   Later only closes it for now, it comes back the next time the app is opened. Any error = stays silent. Does nothing in a normal browser. */
(function () {
  var REPO = "specialpanda26-sudo/spacexbot-mt5";   // owner/repo, copied from the Download links in index.html. Change it here if your repo name differs.
  var APK = "https://github.com/" + REPO + "/releases/latest/download/spacexbot.apk";
  var API = "https://api.github.com/repos/" + REPO + "/releases/latest";
  var LATER = "sxb_update_later";

  function build(s) { var m = /(\d+)\s*$/.exec(String(s == null ? "" : s)); return m ? parseInt(m[1], 10) : 0; }
  function newer(latestTag, installed) { var a = build(latestTag), b = build(installed); return a > 0 && b > 0 && a > b; }
  function native() { var c = window.Capacitor; return !!(c && c.isNativePlatform && c.isNativePlatform()); }
  var WHY = "", LAST = 0;
  function why(t) { WHY = t; try { localStorage.setItem("sxb_upd_why", t); } catch (e) {} }   /*U2*/
  function appPlug() {
    var c = window.Capacitor; if (!c) return null;
    if (c.Plugins && c.Plugins.App && c.Plugins.App.getInfo) return c.Plugins.App;
    if (c.nativePromise) return { getInfo: function () { return c.nativePromise("App", "getInfo", {}); } };
    return null;
  }
  function installed() {
    var A = appPlug();
    if (!A) { why("the app version cannot be read (no App plugin)"); return Promise.resolve(""); }
    return A.getInfo().then(function (i) { return (i && (i.build || i.version)) || ""; }, function () { why("the app version cannot be read"); return ""; });
  }
  /*U5-start: the pop-up in the website look. Site pieces only: .ov/.panel, .btn primary big block, CSS variables. Colours come from the site, none are written here. */
  var NOTE_MAX = 140;
  var CH = '<path d="M30 118C26 90 36 66 62 58c26-8 46 12 50 42l4 18" fill="#1d1d20"/><path d="M42 54C38 34 54 20 72 24c18 4 22 24 10 36-10 9-32 10-40-6z" fill="#26262a"/><path d="M44 38c4-15 30-20 44-8l12 7c-2 4-10 4-14 2-12-4-30-2-42 8z" fill="#34343a"/><path d="M60 47q6 5 12 0"/>';                /* the dark-haired site character: a copy of CH2 in index.html (tests/test_update5.py fails if they ever differ) */
  function note(b) {                /* first real line of the release text: no headings, no markdown marks, no install boilerplate, short */
    var L = String(b == null ? "" : b).split(/\r?\n/);
    for (var i = 0; i < L.length; i++) {
      if (/^\s*#/.test(L[i])) continue;                 /* a heading is a title, not the note */
      var t = L[i].replace(/^[\s>#*_+`-]+/, "").replace(/[*`]+/g, "").replace(/\s+/g, " ").replace(/^\s+|\s+$/g, "");
      if (t && !/spacexbot\.apk/i.test(t)) return t.length > NOTE_MAX ? t.slice(0, NOTE_MAX - 1).replace(/\s+\S*$/, "") + "…" : t;
    }
    return "";
  }
  /* The cartoon "update": a phone with a download arrow dropping in, a flame under it, twinkling sparkles and the dark-haired site character CH. Same outline style as IL2. */
  function art() {
    return '<svg class="ill2 upd" viewBox="0 0 240 170" fill="none" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
      + '<g transform="translate(14 22)"><g class="up">'
      + '<path class="uf" d="M19 94q10 38 20 0z"/><path class="ug" d="M24 94q5 20 10 0z"/>'
      + '<rect width="58" height="96" rx="11" fill="#26262a"/><path d="M22 10h14"/><rect x="9" y="22" width="40" height="62" rx="8"/>'
      + '<g class="ua"><path d="M29 34v26"/><path d="M20 51l9 9 9-9"/><path d="M19 70h20"/></g>'
      + '</g></g>'
      + '<path class="us us1" d="M96 18v10M91 23h10"/><path class="us us2" d="M10 8v8M6 12h8"/><path class="us us3" d="M104 104v8M100 108h8"/><path class="us us4" d="M200 20v9M195.5 24.5h9"/>'
      + '<g class="ub"><path d="M114 146c-14 4-26 2-38-4"/><g transform="translate(112 40)">' + CH + '</g></g></svg>';
  }
  var CSS = [
    "#sxbUpd{z-index:100000}",
    "#sxbUpd .ucart{display:grid;place-items:center}",
    "#sxbUpd .ill2{width:210px;max-width:72%;margin:0 auto}",
    "#sxbUpd h2,#sxbUpd p{text-align:center}",
    "#sxbUpd .unote{background:var(--surface2);border:1px solid var(--line);border-radius:14px;padding:10px 14px;color:var(--fg);font-size:14px}",
    "#sxbUpd .btn.q{background:transparent;border-color:transparent;box-shadow:none;color:var(--muted)}",
    "#sxbUpd .btn.q:active{transform:none}",
    ".ill2.upd .ua{stroke:var(--green);stroke-width:3.2}",
    ".ill2.upd .uf{fill:var(--green);stroke:none}",
    ".ill2.upd .ug{fill:var(--sun);stroke:none}",
    ".ill2.upd .us{stroke:var(--green)}",
    "@media (prefers-reduced-motion:no-preference){",
    ".ill2.upd .up,.ill2.upd .ua,.ill2.upd .uf,.ill2.upd .ug,.ill2.upd .us,.ill2.upd .ub{transform-box:fill-box;animation-iteration-count:infinite!important}",
    ".ill2.upd .up{animation:sxuP 2.6s ease-in-out infinite}",
    ".ill2.upd .ua{animation:sxuA 3s ease-in-out infinite}",
    ".ill2.upd .uf{transform-origin:50% 0;animation:sxuF .5s ease-in-out infinite}",
    ".ill2.upd .ug{transform-origin:50% 0;animation:sxuG .37s ease-in-out infinite}",
    ".ill2.upd .us{transform-origin:50% 50%;animation:sxuS 1.8s ease-in-out infinite}",
    ".ill2.upd .us2{animation-delay:-.6s}.ill2.upd .us3{animation-delay:-1.2s}.ill2.upd .us4{animation-delay:-.3s}",
    ".ill2.upd .ub{animation:sxuB 3.4s ease-in-out infinite}",
    "@keyframes sxuP{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}",
    "@keyframes sxuA{0%{transform:translateY(-28px);opacity:0}20%{opacity:1}42%{transform:translateY(0)}50%{transform:translateY(4px)}58%,88%{transform:translateY(0);opacity:1}100%{transform:translateY(0);opacity:0}}",
    "@keyframes sxuF{0%{transform:scaleY(.8)}50%{transform:scaleY(1.3)}100%{transform:scaleY(.9)}}",
    "@keyframes sxuG{0%{transform:scaleY(1.2)}50%{transform:scaleY(.7)}100%{transform:scaleY(1.1)}}",
    "@keyframes sxuS{0%,100%{opacity:.2;transform:scale(.5)}50%{opacity:1;transform:scale(1.15)}}",
    "@keyframes sxuB{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}",
    "}"
  ].join("\n");
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function attr(e, k, v) { if (e.setAttribute) e.setAttribute(k, v); }

  function show(info) {
    if (document.getElementById("sxbUpd")) return;
    info = info || {};
    var o = el("div", "ov"); o.id = "sxbUpd";
    var st = el("style"); st.textContent = CSS;
    var bd = el("div", "bd");
    var c = el("div", "panel"); attr(c, "role", "dialog"); attr(c, "aria-modal", "true"); attr(c, "aria-labelledby", "sxbUpdT");
    var cart = el("div", "ucart"); cart.innerHTML = art();
    var t = el("h2", "", "Update available"); t.id = "sxbUpdT";
    var p = el("p", "muted", "A new update is available for spaceXBot. Update now to get the latest features.");
    var go = el("button", "btn primary big block", "Update now"); attr(go, "type", "button");
    var no = el("button", "btn block q", "Maybe later"); attr(no, "type", "button");
    c.appendChild(cart); c.appendChild(t); c.appendChild(p);
    if (info.build) c.appendChild(el("p", "muted num", "New build " + info.build + (info.have ? " · you have " + info.have : "")));
    if (info.note) c.appendChild(el("p", "unote", "What's new: " + info.note));      /* textContent only: release text is never read as HTML */
    c.appendChild(go); c.appendChild(no);
    o.appendChild(st); o.appendChild(bd); o.appendChild(c);
    function later() { try { sessionStorage.setItem(LATER, "1"); } catch (e) {} if (o.remove) o.remove(); }
    go.onclick = function () { var w = null; try { w = window.open(APK, "_blank"); } catch (e) {} if (!w) { try { window.location.href = APK; } catch (e) {} } if (o.remove) o.remove(); };
    no.onclick = later; bd.onclick = later;
    document.body.appendChild(o);
    try { void o.offsetWidth; } catch (e) {}
    o.className = "ov open";                                  /* added after the first paint so the panel slides in like the site's own pop-ups */
  }
  /*U5-end*/

  function check() {
    try { if (sessionStorage.getItem(LATER)) return; } catch (e) {}
    if (typeof fetch !== "function") return;
    LAST = Date.now();
    installed().then(function (have) {
      if (!build(have)) return;
      return fetch(API, { headers: { Accept: "application/vnd.github+json" } })
        .then(function (r) {
          if (r && r.ok) return r.json();
          why(r && r.status === 404 ? "no release found (the repo is private or its name is wrong)" : "GitHub answered with an error"); return null;
        })
        .then(function (j) {
          if (!j) return;
          if (newer(j.tag_name, have)) { why(""); show({ build: build(j.tag_name), have: build(have), note: note(j.body) }); } else why("up to date (" + have + ", latest " + j.tag_name + ")");
        });
    }).catch(function () { why("the update check failed (offline?)"); });
  }

  function again() { if (Date.now() - LAST >= 60000) check(); }                      /* back in the app: look again, at most once a minute */
  window.SXBUpdate = { build: build, newer: newer, show: show, art: art, note: note, check: check, again: again, why: function () { return WHY; }, APK: APK };
  if (native()) {
    var go = function () { setTimeout(check, 6500); };      // after the opening animation
    if (document.addEventListener) document.addEventListener("visibilitychange", function () { if (!document.hidden) again(); });
    if (document.readyState === "complete") go(); else window.addEventListener("load", go);
  }
})();
