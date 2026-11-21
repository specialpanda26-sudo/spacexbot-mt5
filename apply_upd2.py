"""Section 2 (update pop-up): finds the app version even when Capacitor.Plugins.App is missing, checks again when you come back to the app (at most once a minute),
says WHY it stayed silent (SXBUpdate.why(), also saved in localStorage sxb_upd_why), and Update now falls back to opening the link in the same window."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/update.js'
edit(P, '''  function installed() {
    var c = window.Capacitor, A = c && c.Plugins && c.Plugins.App;
    if (!A || !A.getInfo) return Promise.resolve("");
    return A.getInfo().then(function (i) { return (i && (i.build || i.version)) || ""; }, function () { return ""; });
  }''', '''  var WHY = "", LAST = 0;
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
  }''', '/*U2*/')
edit(P, '''go.onclick = function () { try { window.open(APK, "_blank"); } catch (e) {} if (o.remove) o.remove(); };''',
 '''go.onclick = function () { var w = null; try { w = window.open(APK, "_blank"); } catch (e) {} if (!w) { try { window.location.href = APK; } catch (e) {} } if (o.remove) o.remove(); };''', 'var w = null; try { w = window.open')
edit(P, '''    installed().then(function (have) {
      if (!build(have)) return;
      return fetch(API, { headers: { Accept: "application/vnd.github+json" } })
        .then(function (r) { return r && r.ok ? r.json() : null; })
        .then(function (j) { if (j && newer(j.tag_name, have)) show(); });
    }).catch(function () {});''', '''    LAST = Date.now();
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
    }).catch(function () { why("the update check failed (offline?)"); });''', 'LAST = Date.now();')
edit(P, '''window.SXBUpdate = { build: build, newer: newer, show: show, check: check, APK: APK };''',
 '''function again() { if (Date.now() - LAST >= 60000) check(); }                      /* back in the app: look again, at most once a minute */
  window.SXBUpdate = { build: build, newer: newer, show: show, check: check, again: again, why: function () { return WHY; }, APK: APK };''', 'function again()')
edit(P, '''    var go = function () { setTimeout(check, 6500); };      // after the opening animation''',
 '''    var go = function () { setTimeout(check, 6500); };      // after the opening animation
    if (document.addEventListener) document.addEventListener("visibilitychange", function () { if (!document.hidden) again(); });''', 'visibilitychange')
