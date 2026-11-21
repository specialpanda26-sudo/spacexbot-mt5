"""Section 8c: two more cartoon screens in the site's own pop-up.
 - "Something went wrong": the page was about to show a "Something went wrong" toast; a card (IL2.cx) with Reload the app / Close shows instead.
 - "<Deriv / MT5> is connected": the Connect-tab check (GET /api/connections) moved a way of connecting from not set up / not connected to connected (IL2.plug, Go to Bot tab).
Facts only. Never on top of another pop-up. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
# 1) the Connect-tab check shares its last answer (same idea as SXBOT / SXLIVE), so a block after it can see a state change
edit(P, 'SXA.api("/api/connections", { method: "GET" }).then(function (j) { D = j; FAIL = 0; }, function () { FAIL++; })',
        'SXA.api("/api/connections", { method: "GET" }).then(function (j) { D = j; FAIL = 0; window.SXCONN = { u: (me() || {}).uid, j: j, t: Date.now() }; }, function () { FAIL++; })',
        'window.SXCONN = {')
BLOCK = r"""<script>
/*H8c-start*/
/* Section 8c: "Something went wrong" and "<broker> is connected" in the site's own pop-up (.ov, .bd, .panel, .btn). IL2 pictures, site classes only. Facts only. */
(function () {
  var KEY = "sxb_bc", LASTERR = 0, UID = null, PREV = null, LAST = 0;
  /*H8c-pure-start*/
  function h8err(m) { return /something went wrong/i.test(String(m == null ? "" : m)); }
  function h8errok(c) { return !c.open && (!c.last || c.now - c.last >= 30000); }
  function h8map(rows) { var m = {}; (rows || []).forEach(function (r) { if (r && r.id) m[r.id] = r.state; }); return m; }
  function h8conn(c) {
    if (!c.prev) return [];
    var out = [];
    (c.rows || []).forEach(function (r) {
      if (!r || r.state !== "ok") return;
      var p = c.prev[r.id];
      if ((p === "none" || p === "problem") && (c.seen || []).indexOf(r.id) < 0) out.push(r.id);
    });
    return out;
  }
  function h8words(k, id) {
    if (k === "error") return { title: "Something went wrong", text: "Something did not work as expected. Reload the app and try again. Your account and saved settings are still here.", go: "Reload the app", no: "Close" };
    return { title: id + " is connected", text: "spaceXBot can now see your account, so your balance and trades show in the app. The bot does not trade until you start it on the Bot tab.", go: "Go to Bot tab", no: "Not now" };
  }
  /*H8c-pure-end*/
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function open() { return document.getElementById("h8cov"); }
  function close() { var o = open(); if (o && o.remove) o.remove(); }
  function busy() { try { return !!document.querySelector(".ov.open"); } catch (e) { return false; } }
  function art(k) { var I = window.IL2 || {}; return (k === "error" ? I.cx : I.plug) || ""; }
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function seen(uid) { try { var s = JSON.parse(localStorage.getItem(KEY) || "null"); return s && s.u === uid && s.ids instanceof Array ? s.ids : []; } catch (e) { return []; } }
  function mark(uid, ids) { try { localStorage.setItem(KEY, JSON.stringify({ u: uid, ids: seen(uid).concat(ids) })); } catch (e) {} }
  function card(kind, w, go) {
    close();
    var o = el("div", "ov"); o.id = "h8cov"; o.setAttribute("data-kind", kind);
    var bd = el("div", "bd"), c = el("div", "panel");
    c.setAttribute("role", "dialog"); c.setAttribute("aria-modal", "true"); c.setAttribute("aria-labelledby", "h8ct");
    var h = el("h2", "", w.title); h.id = "h8ct"; h.setAttribute("style", "text-align:center");
    var p = el("p", "muted", w.text); p.setAttribute("style", "text-align:center");
    var b1 = el("button", "btn primary big block", w.go), b2 = el("button", "btn block", w.no);
    b1.setAttribute("type", "button"); b2.setAttribute("type", "button");
    c.appendChild(h); c.appendChild(p); c.appendChild(b1); c.appendChild(b2);
    var pic = art(kind); if (pic) c.insertAdjacentHTML("afterbegin", pic);
    o.appendChild(bd); o.appendChild(c);
    b1.onclick = function () { close(); try { go(); } catch (e) {} };
    b2.onclick = close; bd.onclick = close;
    document.body.appendChild(o);
    try { void o.offsetWidth; } catch (e) {}
    o.className = "ov open";
    try { b1.focus(); } catch (e) {}
    return o;
  }
  function reload() { window.location.reload(); }
  function botTab() { var n = document.querySelector('[data-go="bot"]'); if (n) n.click(); }
  /* a "Something went wrong" toast becomes a card; true = the card took it, false = show the toast as before */
  function showErr() {
    var now = Date.now();
    if (!h8errok({ open: busy(), last: LASTERR, now: now })) return false;
    LASTERR = now; card("error", h8words("error"), reload); return true;
  }
  function check() {
    var u = me(), S = window.SXCONN;
    if (!u || u.offline || !S || S.u !== u.uid || !S.j || Date.now() - S.t > 120000) return;
    if (UID !== u.uid) { UID = u.uid; PREV = null; LAST = 0; }
    if (S.t === LAST) return;
    var rows = S.j.rows || [], hit = h8conn({ rows: rows, prev: PREV, seen: seen(u.uid) });
    if (hit.length && busy()) return;          /* tried again at the next look; nothing was marked */
    PREV = h8map(rows); LAST = S.t;
    if (hit.length) { mark(u.uid, hit); card("connected", h8words("connected", hit[0]), botTab); }
  }
  try { var t1 = window.sxToast; if (typeof t1 === "function") window.sxToast = function (m) { if (h8err(m) && showErr()) return; return t1.apply(this, arguments); }; } catch (e) {}
  setInterval(check, 1500);
  window.sxH8c = { check: check, err: h8err, errok: h8errok, conn: h8conn, words: h8words, close: close };
})();
/*H8c-end*/
</script>
"""
edit(P, '/*H8b-end*/\n</script>\n', '/*H8b-end*/\n</script>\n' + BLOCK, '/*H8c-start*/')

# 2) docs/HANDOFF.md
H = 'docs/HANDOFF.md'
SEC = """## Section 8c (something went wrong / broker connected cartoon screens) DONE (Nov 21)
- apply_pop8c.py edits static/index.html only (+ tests/test_pop8c.py). Block /*H8c-start*/../*H8c-end*/ in its own script tag after H8b. Same pop-up as 8a/8b (.ov/.bd/.panel, .btn primary big block + quiet button, tap outside = quiet button, CSS classes only, IL2 pictures).
- \"Something went wrong\" (IL2.cx): window.sxToast is wrapped; a toast whose text contains \"something went wrong\" opens the card instead (Reload the app / Close). At most one every 30 s and never on top of another open pop-up: in both cases the plain toast shows as before. Only toasts are caught: the inline ERR lines inside cards (\"Something went wrong.\") are unchanged, and window errors / unhandled promise rejections are NOT caught on purpose (too noisy).
- \"<Deriv or MT5> is connected\" (IL2.plug, Go to Bot tab / Not now): R2's poll now publishes window.SXCONN {u, j, t} (one extra assignment, like SXBOT / SXLIVE). The block compares the rows of GET /api/connections with the previous answer: a row that was none (not set up) or problem (not connected) and is now ok = the card. Offline (stale) to ok does NOT count, so an EA restart never pops it. No card on the first look after the page loads, for another person's answer, or one older than 2 minutes. Once per (person, broker id) on a phone (localStorage sxb_bc). If another pop-up is open it waits and tries again 1.5 s later. The text says the bot does not trade until it is started on the Bot tab (true: bot_enabled / the Start bot switch).
- R2 only polls while the Connect tab is open, so the card shows when the person connects while looking at that tab.
- NOT done: the Home speech bubble (#bubble) bug is still open. NOT tested: a real phone / the APK WebView, a real broker connecting.

"""
edit(H, '## STATUS BOARD (Nov 21, newest; read this first)\n', SEC + '## STATUS BOARD (Nov 21, newest; read this first)\n', '## Section 8c (something went wrong')
edit(H, '8c (generic "something went wrong", broker connected cartoons), 9 (more', '9 (more', '- NEXT in order: 9 (more')
edit(H, '8b (plan ends soon / plan ended), 8d (lock', '8b (plan ends soon / plan ended), 8c (something went wrong / broker connected), 8d (lock', '8c (something went wrong / broker connected), 8d (lock')
edit(H, 'plan8b/pic8d/wknd9.py', 'plan8b/pop8c/pic8d/wknd9.py', 'plan8b/pop8c/pic8d/wknd9.py')
