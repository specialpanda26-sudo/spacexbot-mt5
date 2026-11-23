"""FX4: Check connection + status. Run from the repo folder: python3 apply_fx4_conn.py"""
import sys

def rep(path, old, new, count=1):
    s = open(path, encoding='utf-8').read()
    if s.count(old) != count:
        sys.exit('STOP: %s: expected %d match(es), found %d for: %s' % (path, count, s.count(old), old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new))
    print('ok', path)

H = 'static/index.html'
LIM = 'function lim(p, ms) { return new Promise(function (res, rej) { var t = setTimeout(function () { rej(new Error("slow")); }, ms || 20000); p.then(function (v) { clearTimeout(t); res(v); }, function (e) { clearTimeout(t); rej(e); }); }); }          /* FX4: a request that hangs gives up after 20 s */'

rep(H, '''  function poll() {
    if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
    return SXA.api("/api/bridge", { method: "GET" }).then(function (j) { D = j; FAIL = 0; }, function () { FAIL++; }).then(function () { BUSY = false; paint(); });
  }
  window.sxBridgeCheck = function () { if (!ready()) { paint(); if (window.sxToast) window.sxToast("Sign in to check your bridge"); return; } D = null; paint(); poll().then(function () { if (window.sxToast && D) window.sxToast(D.state === "online" ? "Bridge is online" : "Bridge is not reporting"); }); };''',
'''  ''' + LIM + '''
  var INF = null;
  function poll() {
    if (!ready()) return Promise.resolve(); if (BUSY && INF) return INF; BUSY = true;
    INF = lim(SXA.api("/api/bridge", { method: "GET" })).then(function (j) { D = j; FAIL = 0; }, function () { FAIL++; }).then(function () { BUSY = false; INF = null; paint(); });
    return INF;
  }
  window.sxBridgeCheck = function () {          /* FX4: ask the MT5 bridge AND the Connection check card together, then say what is true */
    var tt = function (m) { if (window.sxToast) window.sxToast(m); };
    if (!ready()) { paint(); tt("Sign in to check your connection"); return; }
    var btn = document.getElementById("testBtn"); if (btn) { btn.disabled = true; btn.textContent = "Checking..."; }
    var t0 = Date.now(), other = window.__sx2 && window.__sx2.poll ? window.__sx2.poll() : Promise.resolve();
    Promise.all([poll(), other]).then(function () {
      if (btn) { btn.disabled = false; btn.textContent = "Check connection"; }
      var c = window.SXCONN && window.SXCONN.t >= t0 ? window.SXCONN.j : null;
      if (D && D.state === "online") tt("MT5 bridge is online (" + (D.mode === "real" ? "real" : "demo") + " account)");
      else if (c && c.connected && c.connected.length) tt("Connected: " + c.connected.join(" + "));
      else if (FAIL || (!D && !c)) tt("Cannot reach the server. Check your internet and try again.");
      else tt(D && D.message ? D.message : "Nothing is reporting yet. See the checks below.");
    });
  };''')

rep(H, '''  window.__sx2 = { chip: over, esc: esc };''', '''  window.__sx2 = { chip: over, esc: esc, poll: function () { return poll(); } };          /* FX4: the Check connection button asks this card too */''')
rep(H, '''  function poll() {
    if (!ready() || BUSY) return Promise.resolve(); BUSY = true;
    return SXA.api("/api/connections", { method: "GET" }).then(function (j) { D = j; FAIL = 0; window.SXCONN = { u: (me() || {}).uid, j: j, t: Date.now() }; }, function () { FAIL++; }).then(function () { BUSY = false; paint(); });
  }''', '''  ''' + LIM + '''
  var INF = null;
  function poll() {
    if (!ready()) return Promise.resolve(); if (BUSY && INF) return INF; BUSY = true;
    INF = lim(SXA.api("/api/connections", { method: "GET" })).then(function (j) { D = j; FAIL = 0; window.SXCONN = { u: (me() || {}).uid, j: j, t: Date.now() }; }, function () { FAIL++; }).then(function () { BUSY = false; INF = null; paint(); });
    return INF;
  }''')

rep(H, '''    return SXA.api("/api/live", { method: "GET" }).then(function (j) { D = j; GOT = Date.now(); FAIL = 0;''', '''    return lim(SXA.api("/api/live", { method: "GET" })).then(function (j) { D = j; GOT = Date.now(); FAIL = 0;''')
rep(H, '''  function kind() { return !D || D.state === "none" ? "none" : (FAIL >= 3 || D.state === "stale") ? "stale" : "live"; }''',
       '''  ''' + LIM + '''
  function kind() { return !D || D.state === "none" ? "none" : (FAIL >= 3 || D.state === "stale") ? "stale" : "live"; }
  function stl() { return FAIL >= 3 ? "Reconnecting" : "Offline"; }          /* FX4: the phone cannot reach the server is not the broker being offline */''')
rep(H, '''    if (k === "stale") return '<span class="chip watch"><span class="dot"></span>Offline</span>';''', '''    if (k === "stale") return '<span class="chip watch"><span class="dot"></span>' + stl() + "</span>";''')
rep(H, '''txt = k === "stale" ? "Offline" : real ? "Live Real" : "Live Demo"''', '''txt = k === "stale" ? stl() : real ? "Live Real" : "Live Demo"''')
rep(H, '''chip.title = k === "stale" ? "Your broker looks offline. These are the last numbers we saw." : "Real numbers from your connected account.";''',
       '''chip.title = k === "stale" ? (FAIL >= 3 ? "Cannot reach the server right now. These are the last numbers we saw." : "Your broker looks offline. These are the last numbers we saw.") : "Real numbers from your connected account.";''')
print('FX4 done')
