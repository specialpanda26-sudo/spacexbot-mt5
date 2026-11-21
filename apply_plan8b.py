"""Section 8b: two new cartoon screens in the site's own pop-up.
 - "Your plan ends soon": the plan has 3 days or less left (clock picture, Extend plan button).
 - "Your plan has ended": the plan ran out (coin picture, Choose a plan button).
Each one shows ONCE per plan end date on a phone (localStorage sxb_pe), never to an admin, never on the saved copy while the server sleeps,
never on top of another pop-up. Extending the plan gives a new end date, so the cycle starts again. Facts only. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
# 1) the page's own plan chooser is private to its script: expose it the same way 8a exposed sxLogin (same rules as the Start-bot gate)
edit(P, 'setInterval(bar,1500);bar();',
        'setInterval(bar,1500);bar();window.sxPlans=function(){if(!U)auth("login");else if(!U.verified)verify();else plans()};',
        'window.sxPlans=function(){')
BLOCK = r"""<script>
/*H8b-start*/
/* Section 8b: "Your plan ends soon" and "Your plan has ended" in the site's own pop-up (.ov, .bd, .panel, .btn). IL2 pictures, site classes only. Facts only. */
(function () {
  var KEY = "sxb_pe";
  /*H8b-pure-start*/
  function h8plan(c) {
    var u = c.u;
    if (!u || u.admin || u.offline) return "";
    var pu = Number(u.plan_until) || 0;
    if (pu <= 0) return "";
    var left = pu - c.now, k;
    if (left <= 0) k = "ended"; else if (left <= 3 * 86400) k = "soon"; else return "";
    var s = c.seen;
    if (s && s.u === u.uid && s.k === k && Number(s.t) === pu) return "";
    return k;
  }
  function h8words(k, left, date) {
    if (k === "ended") return { title: "Your plan has ended", text: "Your plan ended on " + date + ", so the bot is locked. Choose a plan to unlock it again. Your account and saved settings are still here.", go: "Choose a plan", no: "Not now" };
    var d = Math.ceil(left / 86400);
    return { title: "Your plan ends soon", text: "Your plan ends " + (left <= 86400 ? "in less than a day" : "in " + d + " days") + ", on " + date + ". Extend it to keep the bot unlocked. The days you have left are kept when you extend.", go: "Extend plan", no: "Not now" };
  }
  /*H8b-pure-end*/
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function open() { return document.getElementById("h8bov"); }
  function close() { var o = open(); if (o && o.remove) o.remove(); }
  function art(k) { var I = window.IL2 || {}; return (k === "ended" ? I.coin : I.wait) || ""; }
  function seen() { try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { return null; } }
  function mark(u, k) { try { localStorage.setItem(KEY, JSON.stringify({ u: u.uid, k: k, t: Number(u.plan_until) })); } catch (e) {} }
  function fdate(s) { return new Date(s * 1e3).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }); }
  function card(kind, w) {
    close();
    var o = el("div", "ov"); o.id = "h8bov"; o.setAttribute("data-kind", kind);
    var bd = el("div", "bd"), c = el("div", "panel");
    c.setAttribute("role", "dialog"); c.setAttribute("aria-modal", "true"); c.setAttribute("aria-labelledby", "h8bt");
    var h = el("h2", "", w.title); h.id = "h8bt"; h.setAttribute("style", "text-align:center");
    var p = el("p", "muted", w.text); p.setAttribute("style", "text-align:center");
    var b1 = el("button", "btn primary big block", w.go), b2 = el("button", "btn block", w.no);
    b1.setAttribute("type", "button"); b2.setAttribute("type", "button");
    c.appendChild(h); c.appendChild(p); c.appendChild(b1); c.appendChild(b2);
    var pic = art(kind); if (pic) c.insertAdjacentHTML("afterbegin", pic);
    o.appendChild(bd); o.appendChild(c);
    b1.onclick = function () { close(); try { if (window.sxPlans) window.sxPlans(); } catch (e) {} };
    b2.onclick = close; bd.onclick = close;
    document.body.appendChild(o);
    try { void o.offsetWidth; } catch (e) {}
    o.className = "ov open";
    try { b1.focus(); } catch (e) {}
    return o;
  }
  function check() {
    try { if (document.querySelector(".ov.open")) return; } catch (e) {}   /* any open pop-up, this card included */
    var u = null; try { u = SXA.user(); } catch (e) {}
    var now = Date.now() / 1000, k = h8plan({ u: u, now: now, seen: seen() });
    if (!k) return;
    var pu = Number(u.plan_until);
    mark(u, k);
    card(k, h8words(k, pu - now, fdate(pu)));
  }
  setTimeout(check, 3000); setInterval(check, 5000);
  window.sxH8b = { check: check, kind: h8plan, words: h8words, close: close };
})();
/*H8b-end*/
</script>
"""
edit(P, '/*H8-end*/\n</script>\n', '/*H8-end*/\n</script>\n' + BLOCK, '/*H8b-start*/')

# 3) docs/HANDOFF.md: the new section above the status board, and the status board itself
H = 'docs/HANDOFF.md'
SEC = """## Section 8b (plan ends soon / plan ended cartoon screens) DONE (Nov 21)
- apply_plan8b.py edits static/index.html only (+ tests/test_plan8b.py, 51 checks). Block /*H8b-start*/../*H8b-end*/ in its own script tag after H8. Reads SXA.user() every 5 s (first look after 3 s): plan_until within 3 days = "Your plan ends soon" (IL2.wait, Extend plan); plan_until in the past = "Your plan has ended" (IL2.coin, Choose a plan). Both are the site's .ov/.bd/.panel pop-up with .btn primary big block + quiet "Not now" (tap outside = Not now), CSS classes only.
- Rules (h8plan, between /*H8b-pure-start*/ and /*H8b-pure-end*/): never for an admin, never when plan_until is 0 (never had a plan = the locked state, not an ended plan), never on the saved copy while the server sleeps (u.offline), never on top of another open pop-up (any .ov.open; it is tried again 5 s later and was not marked as shown), each card ONCE per (person, kind, end date) on a phone (localStorage sxb_pe). Extending gives a new end date, so the cycle starts again. A plan that ended while the app was closed shows only the "ended" card.
- The soon text says "The days you have left are kept when you extend": true, payments.activate() adds the days to max(now, plan_until).
- The page's own plan chooser is private to its script, so apply_plan8b.py adds window.sxPlans (same rules as the Start-bot gate: log in / verify / plans) right after setInterval(bar,1500);bar(); the buttons call it.
- Mutation-checked (19 deliberate breaks, each went red; one redundant check was removed instead because the open-pop-up check already covers the card itself). Checked in real Chromium on the real page: dark and light, both cards, Extend plan and Choose a plan open the real "Choose your plan" screen. NOT tested: a real phone / the APK WebView, a real plan running out.
- Push alerts for the same events (kinds 42/43/44, section N3) are still parked and not built.
- OLD, UNRELATED: tests/test_burst3.py check "running apply_burst3.py again changes nothing" fails on a fresh copy (apply_burst3.py expects ea/SpaceXBridge.mq5 to still say #property version "1.00"; a later section changed it). Stale test of a historical patch, not a bug in the app.

"""
edit(H, '## STATUS BOARD (Nov 21, newest; read this first)\n', SEC + '## STATUS BOARD (Nov 21, newest; read this first)\n', '## Section 8b (plan ends soon')
edit(H, '- NEXT in order: 8b (plan about to expire / plan expired), 8c (generic', '- NEXT in order: 8c (generic', 'NEXT in order: 8c (generic')
edit(H, '8a (session ended / server waking), 8d (lock, moon, shield, plug move; closing-band rocket back in its corner), W9 (weekend rule per market). Files: apply_rel1/upd2/buddy4/upd5/upd5b/mot6/home7/sess8/pic8d/wknd9.py and their tests.',
        '8a (session ended / server waking), 8b (plan ends soon / plan ended), 8d (lock, moon, shield, plug move; closing-band rocket back in its corner), W9 (weekend rule per market). Files: apply_rel1/upd2/buddy4/upd5/upd5b/mot6/home7/sess8/plan8b/pic8d/wknd9.py and their tests.', '8b (plan ends soon / plan ended), 8d')
