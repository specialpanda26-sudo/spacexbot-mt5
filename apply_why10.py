"""Section 10a: a plain "App updates" row in Settings (Android app only) that says why no update pop-up showed (the reason update.js already keeps) and has a "Check for updates now" button.
Edits static/update.js and static/index.html (one hook). Safe to run twice."""
J = "static/update.js"; H = "static/index.html"
s = open(J, encoding="utf-8").read()
if "/*W10*/" in s:
    print("update.js: already applied")
else:
    def swap(a, b):
        global s
        if s.count(a) != 1: print("STOP: expected once in update.js:", a[:60]); raise SystemExit(1)
        s = s.replace(a, b)
    swap('  var WHY = "", LAST = 0;\n  function why(t) { WHY = t; try',
         '  var WHY = "", LAST = 0, FOUND = false;\n  function why(t) { WHY = t; if (t) FOUND = false; try')
    swap('    installed().then(function (have) {\n      if (!build(have)) return;',
         '    return installed().then(function (have) {\n      if (!build(have)) return;')
    swap('why(""); show({ build:', 'why(""); FOUND = true; show({ build:')
    swap('  function again() {', r'''  /*W10*/ /* Settings row: the reason the pop-up stayed silent, in plain words, and a button that checks right now. Only inside the Android app. */
  function esc(t) { return String(t == null ? "" : t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function ago(t) { var n = Math.round((Date.now() - t) / 1000); return n < 60 ? "just now" : n < 3600 ? Math.round(n / 60) + " min ago" : Math.round(n / 3600) + " h ago"; }
  function status() {
    if (!native()) return "Update checks run inside the Android app.";
    var w = WHY; if (!w) { try { w = localStorage.getItem("sxb_upd_why") || ""; } catch (e) {} }
    if (FOUND) return "A newer app is out. Tap Check for updates now to open the update card.";
    if (!LAST) return "Not checked yet. The app checks a few seconds after it opens." + (w ? " Last time: " + w + "." : "");
    return (w ? "Last check: " + w + "." : "Last check finished.") + " Checked " + ago(LAST) + ".";
  }
  function row() {
    if (!native()) return "";
    return '<h3>App updates</h3><p class="note" id="sxbUpdWhy">' + esc(status()) + '</p><button class="btn block" type="button" data-upd="check">Check for updates now</button>';
  }
  if (document.addEventListener) document.addEventListener("click", function (e) {
    var b = e && e.target && e.target.closest ? e.target.closest("[data-upd]") : null;
    if (!b || b.getAttribute("data-upd") !== "check") return;
    try { sessionStorage.removeItem(LATER); } catch (x) {}
    LAST = 0; var n = document.getElementById("sxbUpdWhy"); if (n) n.textContent = "Checking...";
    Promise.resolve(check()).then(function () { var m = document.getElementById("sxbUpdWhy"); if (m) m.textContent = status(); });
  });
  function again() {''')
    swap('show: show, art: art,', 'show: show, art: art, row: row, status: status,')
    open(J, "w", encoding="utf-8").write(s); print("update.js done")
h = open(H, encoding="utf-8").read()
hook = "(window.SXBUpdate&&SXBUpdate.row?SXBUpdate.row():\"\")+"
if hook in h:
    print("index.html: already applied")
else:
    a = "'<h3>Data on this device</h3>"
    if h.count(a) != 1: print("STOP: Settings line not found exactly once"); raise SystemExit(1)
    open(H, "w", encoding="utf-8").write(h.replace(a, hook + a)); print("index.html done")
