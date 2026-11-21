"""Section 8a: two new cartoon screens in the site's own pop-up.
 - "Your session ended": the sign-in was lost without the person pressing Log out (lock picture, Log in button).
 - "Waking the server up": the free server is asleep or unreachable (moon picture, tries again by itself up to 8 times).
Only the pop-up is new; the sign-in code (static/live.js) is not touched. Facts only. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
edit(P, 'window.sxSetUser=function(u,first){U=u;slot();',
        'window.sxLogin=function(){auth("login")};window.sxSetUser=function(u,first){var p8=U;U=u;slot();try{window.sxH8&&window.sxH8.user(u,first,p8)}catch(x){}', 'window.sxH8&&window.sxH8.user(')
BLOCK = r"""/*H8-start*/
/* Section 8a: two cartoon screens in the site's own pop-up (.ov, .bd, .panel, .btn). "Your session ended" = the login was lost and the person did not press Log out. "Waking the server up" = the free server sleeps when idle. IL2 pictures, site classes only. Facts only. */
(function () {
  var MINE = 0, GAVE = false, TIMER = 0, TRIES = 0, MAX = 8, BUSY = false;
  /*H8-pure-start*/
  function h8kind(c) {
    if (c.now && c.now.offline) return "wake";
    if (c.now) return "back";
    if (c.prev && !c.first && c.ago > 15000) return "expired";
    return "";
  }
  function h8toast(m) { return /cannot reach the server/i.test(String(m == null ? "" : m)); }
  /*H8-pure-end*/
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function open() { return document.getElementById("h8ov"); }
  function close() { clearTimeout(TIMER); TIMER = 0; var o = open(); if (o && o.remove) o.remove(); }
  function art(k) { var I = window.IL2 || {}; return I[k] || ""; }
  function say(m) { try { if (window.sxToast) window.sxToast(m); } catch (e) {} }
  function card(kind, pic, title, text, goTxt, go, noTxt, no) {
    close();
    var o = el("div", "ov"); o.id = "h8ov"; o.setAttribute("data-kind", kind);
    var bd = el("div", "bd"), c = el("div", "panel");
    c.setAttribute("role", "dialog"); c.setAttribute("aria-modal", "true"); c.setAttribute("aria-labelledby", "h8t");
    var h = el("h2", "", title); h.id = "h8t"; h.setAttribute("style", "text-align:center");
    var p = el("p", "muted", text); p.setAttribute("style", "text-align:center");
    var st = el("p", "muted num", ""); st.id = "h8s"; st.setAttribute("style", "text-align:center"); st.hidden = true;
    var b1 = el("button", "btn primary big block", goTxt), b2 = el("button", "btn block", noTxt);
    b1.setAttribute("type", "button"); b2.setAttribute("type", "button");
    c.appendChild(h); c.appendChild(p); c.appendChild(st); c.appendChild(b1); c.appendChild(b2);
    if (pic) c.insertAdjacentHTML("afterbegin", pic);
    o.appendChild(bd); o.appendChild(c);
    b1.onclick = go; b2.onclick = no; bd.onclick = no;
    document.body.appendChild(o);
    try { void o.offsetWidth; } catch (e) {}
    o.className = "ov open";
    try { b1.focus(); } catch (e) {}
    return o;
  }
  function expired() {
    card("expired", art("lock"), "Your session ended",
      "Your login is no longer valid on this phone, so you were signed out. Log in again to carry on. Your account and saved settings are still there.",
      "Log in", function () { close(); if (window.sxLogin) window.sxLogin(); }, "Not now", close);
  }
  function status(m) { var s = document.getElementById("h8s"); if (s) { s.textContent = m; s.hidden = false; } }
  function awake() { var u = null; try { u = SXA.user(); } catch (e) {} return !!u && !u.offline; }
  function next() { if (TRIES < MAX) TIMER = setTimeout(tick, 8000); else status("Still no answer. Check your internet, then press Try again."); }
  function tick() {
    if (!open()) return;
    TRIES++; status("Try " + TRIES + " of " + MAX);
    SXA.refresh().then(function () { if (!awake() && open()) next(); }, function (e) { if (e && e.status === 401) expired(); else if (open()) next(); });
  }
  function wake() {
    if (GAVE) return; GAVE = true; TRIES = 0;
    card("wake", art("sleep"), "Waking the server up",
      "The server sleeps when nobody has used it for a while, and it can take up to a minute to wake. We keep trying for you. If your internet is off, switch it on.",
      "Try again", function () { clearTimeout(TIMER); TRIES = 0; tick(); }, "Close", close);
    TIMER = setTimeout(tick, 3000);
  }
  function up() { return typeof fetch !== "function" ? Promise.resolve(false) : fetch("/config.js", { cache: "no-store" }).then(function (r) { return r.status < 500; }, function () { return false; }); }
  /* the page said "Cannot reach the server": ask the server itself. No answer = it is waking. It answers but the login is refused = the session ended. */
  function lost() {
    if (BUSY) return; BUSY = true;
    up().then(function (ok) {
      if (!ok) { wake(); return; }
      return SXA.refresh().then(function () {}, function (e) { if (e && e.status === 401) expired(); else wake(); });
    }).then(function () { BUSY = false; }, function () { BUSY = false; });
  }
  function user(u, first, prev) {
    var k = h8kind({ now: u, first: first, prev: prev, ago: Date.now() - MINE });
    if (k === "expired") { GAVE = false; expired(); }
    else if (k === "wake") wake();
    else if (k === "back") { var o = open(), w = o && o.getAttribute("data-kind") === "wake"; GAVE = false; if (o) close(); if (w) say("Back online"); }
  }
  try { if (window.SXA && SXA.signOut) { var so = SXA.signOut; SXA.signOut = function () { MINE = Date.now(); return so.apply(this, arguments); }; } } catch (e) {}
  try { var t0 = window.sxToast; if (typeof t0 === "function") window.sxToast = function (m) { if (h8toast(m)) { lost(); return; } return t0.apply(this, arguments); }; } catch (e) {}
  window.sxH8 = { user: user, kind: h8kind, toast: h8toast, expired: expired, wake: wake, close: close, lost: lost };
})();
/*H8-end*/
"""
edit(P, '/*H7-end*/\n</script>\n', '/*H7-end*/\n</script>\n<script>\n' + BLOCK + '</script>\n', '/*H8-start*/')
