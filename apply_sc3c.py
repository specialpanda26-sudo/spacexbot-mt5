"""SC3c: the page finds the phone's screen plugin (SxbScreen) even when the app loads the site from Render.
Run from the repo folder: python apply_sc3c.py   (add --test to also run the tests)
Safe to run twice. If any old text is not found exactly once, NOTHING is changed.
Page change only: reaches phones after a Render deploy (no APK rebuild)."""
import os, sys, subprocess

def edit(path, old, new, done):
    s = open(path, encoding='utf-8').read()
    if done in s:
        print('skip (already done):', path, '-', done[:50]); return True
    if s.count(old) != 1:
        print('NOT FOUND exactly once:', path, '-', old[:60]); return False
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print('edited:', path); return True

OLD = """  function plug() { var c = window.Capacitor; return (c && c.isNativePlatform && c.isNativePlatform() && c.Plugins && c.Plugins.SxbScreen) || null; }   /* PH2: the Android app's own screen plugin */"""
NEW = """  var PLUG = null;
  function plug() {                          /* PH2/SC3c: the Android app's own screen plugin. A page loaded from Render may get only the native bridge, so try three ways (same as live.js) */
    var c = window.Capacitor; if (!(c && c.isNativePlatform && c.isNativePlatform())) return null;
    if (c.Plugins && c.Plugins.SxbScreen) return c.Plugins.SxbScreen;
    if (PLUG) return PLUG;
    if (c.registerPlugin) { try { var r = c.registerPlugin("SxbScreen"); if (r) return (PLUG = r); } catch (e) {} }
    if (c.nativePromise) {                   /* sxb-screen-fallback */
      var call = function (m) { return function (o) { return c.nativePromise("SxbScreen", m, o || {}); }; };
      return (PLUG = { start: call("start"), stop: call("stop"), status: call("status"), setToken: call("setToken") });
    }
    return null;
  }"""
ok = edit('static/screen.js', OLD, NEW, 'sxb-screen-fallback')
if not ok: sys.exit(1)

H = 'docs/HANDOFF.md'
SEC = """## Section SC3c (page finds the phone's screen plugin) DONE (Nov 23)
- Found: static/screen.js plug() only read Capacitor.Plugins.SxbScreen. The app loads the site from Render, which may give the page only the native bridge, so on the phone plug() could be null and Watch fell back to the browser share message.
- plug() now tries, only when Capacitor.isNativePlatform(): Capacitor.Plugins.SxbScreen, then Capacitor.registerPlugin("SxbScreen") (result kept, called once), then a nativePromise wrapper (start, stop, status, setToken -> nativePromise("SxbScreen", method, options)). Same order as the fallbacks in live.js. Marker in the source: sxb-screen-fallback.
- Page change only: reaches phones after a Render deploy (no APK rebuild). The plugin itself (ScreenPlugin.java) is still uncompiled until the next APK build.
- Tests: tests/test_sc3c.py (13 checks, fake Capacitor with ONLY nativePromise, with Plugins, with registerPlugin (returns, throws, returns null), in a plain browser, and with no bridge). 10 deliberate breaks, each went red. test_ph2, test_sc2, test_sc3, test_sc3b, test_live1-3 still pass.
- Next: SC3d (Go to the market).


"""
ok2 = edit(H, "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", SEC + "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", "## Section SC3c")
ok3 = edit(H, "- FINDING for SC3c (not built yet):", "- SC3c DONE (see Section SC3c above). Old finding, kept for the record:", "- SC3c DONE (see Section SC3c above)")
ok4 = edit(H, "Do SC3c. One section per reply", "Do SC3d (Go to the market: first find out which Deriv link opens a given market). One section per reply", "Do SC3d (Go to the market")
if not (ok2 and ok3 and ok4): sys.exit(1)
if '--test' in sys.argv:
    sys.exit(subprocess.call([sys.executable, 'tests/test_sc3c.py']))
