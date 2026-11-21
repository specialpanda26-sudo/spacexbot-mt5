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
  function box(tag, css, text) { var e = document.createElement(tag); e.style.cssText = css; if (text) e.textContent = text; return e; }

  function show() {
    if (document.getElementById("sxbUpd")) return;
    var o = box("div", "position:fixed;left:0;top:0;right:0;bottom:0;z-index:100000;background:rgba(0,0,0,.62);display:flex;align-items:center;justify-content:center;padding:20px;");
    o.id = "sxbUpd";
    var c = box("div", "max-width:360px;width:100%;background:#10151E;color:#fff;border-radius:22px;padding:24px 22px;text-align:center;font-family:Arial,Helvetica,sans-serif;box-shadow:0 20px 60px rgba(0,0,0,.5);");
    var t = box("div", "font-size:20px;font-weight:800;margin:0 0 8px;", "Update available");
    var p = box("div", "font-size:15px;line-height:1.5;color:rgba(255,255,255,.78);margin:0 0 20px;", "A new version of spaceXBot is ready. Update now to get the latest fixes and features.");
    var go = box("button", "display:block;width:100%;border:0;border-radius:14px;padding:14px;font-size:16px;font-weight:800;background:#1B9A47;color:#fff;margin:0 0 10px;", "Update now");
    var no = box("button", "display:block;width:100%;border:1px solid rgba(255,255,255,.25);border-radius:14px;padding:13px;font-size:15px;font-weight:700;background:transparent;color:#fff;", "Later");
    go.onclick = function () { var w = null; try { w = window.open(APK, "_blank"); } catch (e) {} if (!w) { try { window.location.href = APK; } catch (e) {} } if (o.remove) o.remove(); };
    no.onclick = function () { try { sessionStorage.setItem(LATER, "1"); } catch (e) {} if (o.remove) o.remove(); };
    c.appendChild(t); c.appendChild(p); c.appendChild(go); c.appendChild(no); o.appendChild(c);
    document.body.appendChild(o);
  }

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
          if (newer(j.tag_name, have)) { why(""); show(); } else why("up to date (" + have + ", latest " + j.tag_name + ")");
        });
    }).catch(function () { why("the update check failed (offline?)"); });
  }

  function again() { if (Date.now() - LAST >= 60000) check(); }                      /* back in the app: look again, at most once a minute */
  window.SXBUpdate = { build: build, newer: newer, show: show, check: check, again: again, why: function () { return WHY; }, APK: APK };
  if (native()) {
    var go = function () { setTimeout(check, 6500); };      // after the opening animation
    if (document.addEventListener) document.addEventListener("visibilitychange", function () { if (!document.hidden) again(); });
    if (document.readyState === "complete") go(); else window.addEventListener("load", go);
  }
})();
