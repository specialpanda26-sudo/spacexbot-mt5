"""U7: static/update.js, android-wrapper/prepare.py, android-wrapper/native/MainActivity.java. In-app update: Update now downloads inside the app (progress bar), opens Android's installer, and after the restart shows an 'Update successful' cartoon. Without the native plugin (older app) the old behaviour stays."""
def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    if pairs[0][1] in s: print(p, ': already ok'); return
    for old, new in pairs:
        assert s.count(old) == 1, 'STOP: not found exactly once in %s: %s' % (p, old[:60])
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s); print(p, ': edited')
FLOW = r'''  /*U7-start: in-page update. Inside the new app the APK is downloaded by the app itself (plugin SxbUpdate), with a progress bar on this card,
     then Android's installer opens. After the restart the next check shows a "Update successful" cartoon. Without the plugin (an older app) nothing here runs
     and "Update now" opens the download link as before. Pictures come from the site (window.IL2), no colour is written here. */
  var PENDING = "sxb_upd_pending";
  function plug() {
    var c = window.Capacitor; if (!c) return null;
    if (c.Plugins && c.Plugins.SxbUpdate) return c.Plugins.SxbUpdate;
    if (c.registerPlugin) { try { return c.registerPlugin("SxbUpdate"); } catch (e) {} }
    return null;
  }
  function pic(k) { var I = window.IL2; return (I && I[k]) || art(); }
  function stage(c, o) {           /* o: {pic, title, text, bar, btns:[[label, fn, quiet]]}; returns {bar, text} so progress can move */
    while (c.firstChild) c.removeChild(c.firstChild);
    var cart = el("div", "ucart"); cart.innerHTML = pic(o.pic); c.appendChild(cart);
    var t = el("h2", "", o.title); t.id = "sxbUpdT"; c.appendChild(t);
    var p = el("p", "muted", o.text || ""); c.appendChild(p);
    var bar = null;
    if (o.bar) { var b = el("div", "bar"); bar = el("i"); bar.style.width = "0%"; b.appendChild(bar); c.appendChild(b); }
    (o.btns || []).forEach(function (d) { var x = el("button", "btn block " + (d[2] ? "q" : "primary big"), d[0]); attr(x, "type", "button"); x.onclick = d[1]; c.appendChild(x); });
    return { bar: bar, text: p };
  }
  function whyText(e) { var m = String((e && (e.message || e.errorMessage)) || e || ""); return m.replace(/^download failed:\s*/i, "").slice(0, 120); }
  function inPage(o, c, P, info) {
    function close() { if (o.remove) o.remove(); }
    function fallback() { var w = null; try { w = window.open(APK, "_blank"); } catch (e) {} if (!w) { try { window.location.href = APK; } catch (e) {} } close(); }
    function ready() {
      try { localStorage.setItem(PENDING, String((info && info.build) || 1)); } catch (e) {}
      var ui = stage(c, { pic: "ok", title: "Download complete", text: "Tap Install on the next screen to finish the update.", btns: [["Install now", function () { ready(); }], ["Close", close, 1]] });
      Promise.resolve(P.install()).then(function (r) {
        if (r && r.needPermission) stage(c, { pic: "shield", title: "One more step", text: "Allow spaceXBot to install updates in the settings that just opened, then come back here and tap Install now.", btns: [["Install now", ready], ["Close", close, 1]] });
      }, function (e) { start("Could not open the installer: " + whyText(e)); });
    }
    function start(err) {
      var ui = stage(c, err ? { pic: "off", title: "Update stopped", text: err, btns: [["Try again", function () { start(""); }], ["Open in browser", fallback, 1], ["Close", close, 1]] }
                            : { pic: "phone", title: "Downloading update", text: "0%. Keep the app open.", bar: true });
      if (err) return;
      var h = null; try { h = P.addListener && P.addListener("progress", function (e) { var n = Math.max(0, Math.min(100, Math.round((e && e.pct) || 0))); if (ui.bar) ui.bar.style.width = n + "%"; ui.text.textContent = n + "%. Keep the app open."; }); } catch (e) {}
      function off() { try { if (h && h.then) h.then(function (x) { if (x && x.remove) x.remove(); }); else if (h && h.remove) h.remove(); } catch (e) {} }
      Promise.resolve(P.download({ url: APK })).then(function () { off(); ready(); }, function (e) { off(); start("Download failed: " + whyText(e)); });
    }
    start("");
  }
  /* the card shown once after the restart, when the installed build is the one that was downloaded */
  function celebrate(have) {
    var want = 0; try { want = parseInt(localStorage.getItem(PENDING) || "0", 10) || 0; } catch (e) {}
    if (!want || !(build(have) >= want)) return false;
    try { localStorage.removeItem(PENDING); } catch (e) {}
    var P = plug(); try { if (P && P.cleanup) P.cleanup(); } catch (e) {}
    if (document.getElementById("sxbUpd")) return true;
    var o = el("div", "ov"); o.id = "sxbUpd"; var st = el("style"); st.textContent = CSS; var bd = el("div", "bd");
    var c = el("div", "panel"); attr(c, "role", "dialog"); attr(c, "aria-modal", "true"); attr(c, "aria-labelledby", "sxbUpdT");
    function close() { if (o.remove) o.remove(); }
    stage(c, { pic: "yay", title: "Update successful", text: "spaceXBot is now on build " + build(have) + ". Thanks for updating!", btns: [["Done", close]] });
    bd.onclick = close; o.appendChild(st); o.appendChild(bd); o.appendChild(c); document.body.appendChild(o);
    try { void o.offsetWidth; } catch (e) {} o.className = "ov open"; return true;
  }
  /*U7-end*/
'''
edit('static/update.js', [
    ("  function show(info) {\n", FLOW + "\n  function show(info) {\n"),
    ("go.onclick = function () { var w = null;", "go.onclick = function () { var P = plug(); if (P && P.download && P.install) { inPage(o, c, P, info); return; } var w = null;"),
    ("      if (!build(have)) return;\n      return fetch(API", "      if (!build(have)) return;\n      if (celebrate(have)) return;\n      return fetch(API"),
    ("window.SXBUpdate = { build: build,", "window.SXBUpdate = { celebrate: celebrate, build: build,")])
edit('android-wrapper/prepare.py', [("import launch_patch; launch_patch.run(MAIN, HERE)", "import launch_patch; launch_patch.run(MAIN, HERE)\nimport update_patch; update_patch.run(MAIN, HERE, PKG)")])
edit('android-wrapper/native/MainActivity.java', [("registerPlugin(GoogleSignInPlugin.class);   // must come BEFORE super.onCreate", "registerPlugin(GoogleSignInPlugin.class);   // must come BEFORE super.onCreate\n        registerPlugin(AppUpdatePlugin.class);")])
