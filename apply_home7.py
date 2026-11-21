"""Section 7: the Home cartoon changes with the bot's real situation.
locked -> lock, loss limit reached -> shield, stopped -> clock, profit target reached -> party, market closed -> moon, otherwise the usual candles.
It only swaps the picture (and adds one small line for loss limit / market closed / target). Facts only, no promise of profit.
Inputs: the plan check the page already has, /api/botstate (S4) and /api/live (S3), which now publish window.SXBOT / window.SXLIVE."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
edit(P, 'D = j; FAIL = 0; ERR = ""; paint(); }, function () { FAIL++; if (!D) ERR',
        'D = j; FAIL = 0; ERR = ""; window.SXBOT = { u: (me() || {}).uid, j: j, t: Date.now() }; paint(); }, function () { FAIL++; if (!D) ERR', 'window.SXBOT =')
edit(P, 'D = j; GOT = Date.now(); FAIL = 0; }, function () { FAIL++; }).then(',
        'D = j; GOT = Date.now(); FAIL = 0; window.SXLIVE = { u: (me() || {}).uid, j: j, t: Date.now() }; }, function () { FAIL++; }).then(', 'window.SXLIVE =')
BLOCK = r"""/*S4-end*/
</script>
<script>
/*H7-start*/
/* Section 7: the Home cartoon follows the bot's real situation. It swaps the picture only (IL2 props, character bobs with the bud2 hook). */
(function () {
  var card = document.querySelector("#view-home .buddy-card"), sv = card && card.querySelector("svg.buddy.cart"), act = card && card.querySelector(".buddy-actions");
  if (!sv || !act) return;
  var HOME = sv.innerHTML, note = document.createElement("p"), cur = "", NOW = "";
  note.id = "h7note"; note.className = "muted"; note.hidden = true; note.setAttribute("style", "margin:8px 0 0;font-size:14px;line-height:1.4");
  act.insertAdjacentElement("afterend", note);
  /*H7-pure-start*/
  function h7pick(c) {
    if (c.locked) return { k: "lock" };
    var b = c.bot || null, code = b && b.code ? String(b.code) : "";
    if (code === "daily loss limit hit" || code === "weekly loss limit hit") return { k: "loss", say: b.why || "" };
    if (b && b.state === "stopped") return { k: "stopped" };
    var l = c.live, tp = Number(c.tp);
    if (l && l.state === "live" && tp > 0 && Number(l.today) >= tp) return { k: "target", say: "Today's profit is $" + Number(l.today).toFixed(2) + ", at or above your daily target of $" + tp + "." };
    if (code === "weekend/Friday-night risk") return { k: "closed", say: b.why || "" };
    return { k: "run" };
  }
  /*H7-pure-end*/
  function me() { try { return SXA.user(); } catch (e) { return null; } }
  function locked() { try { var u = me(); if (!u) return !(SXA.resolved && !SXA.resolved()); return !(u.admin || u.active || (u.plan_until || 0) > Date.now() / 1e3); } catch (e) { return true; } }
  function fresh(o) { var u = me(); return o && u && o.u === u.uid && Date.now() - o.t < 120000 ? o.j : null; }
  function tpv() { var v = 3; try { var x = JSON.parse(localStorage.getItem("sxb_up") || "null"); if (x && x.tp != null && x.tp !== "" && isFinite(Number(x.tp))) v = Number(x.tp); } catch (e) {} return v; }
  function art(k) {
    var I = window.IL2; if (!I) return null;
    var m = { lock: I.lock, loss: I.shield, stopped: I.wait, target: I.yay, closed: I.sleep }[k]; if (!m) return null;
    var t = m.replace(/^<svg[^>]*>/, "").replace(/<\/svg>$/, ""), a = '<path d="M114 146c-14 4-26 2-38-4"/>', i = t.indexOf(a);
    return i < 0 ? t : t.slice(0, i) + '<g class="bd">' + t.slice(i) + "</g>";
  }
  function paint() {
    var r = h7pick({ locked: locked(), bot: fresh(window.SXBOT), live: fresh(window.SXLIVE), tp: tpv() }), k = r.k, inner = k === "run" ? HOME : art(k);
    if (inner == null) { k = "run"; r = { k: k }; inner = HOME; }
    if (k !== cur) { cur = k; sv.innerHTML = inner; sv.setAttribute("data-h7", k); }
    var say = r.say || ""; if (say !== NOW) { NOW = say; note.textContent = say; note.hidden = !say; }
  }
  setInterval(paint, 1500); paint();
})();
/*H7-end*/
</script>"""
edit(P, '/*S4-end*/\n</script>', BLOCK, '/*H7-start*/')
NOTE = """
## Section 7 (Home cartoon states) DONE (Nov 21)
- apply_home7.py edits static/index.html only (+ tests/test_home7.py). The Home cartoon (svg.ill2.buddy.cart) now follows the bot's real situation; only the picture changes (plus one small grey line for three states). Order of checks: locked (no plan / signed out, same rule as the Locked chip) = IL2.lock; /api/botstate code 'daily loss limit hit' or 'weekly loss limit hit' = IL2.shield + the server's own sentence; botstate state 'stopped' = IL2.wait; today's profit from /api/live (state live) at or above the Daily profit target = IL2.yay + "Today's profit is $X, at or above your daily target of $Y."; code 'weekend/Friday-night risk' = IL2.sleep + the server sentence; anything else = the usual candles. The new pictures get the character wrapped in class bd, so the Section 4 bob (bud2) moves them; flames/sparkles/confetti come from the IL2 props.
- Plumbing: S4 now publishes window.SXBOT {u, j, t} and S3 window.SXLIVE {u, j, t} (one extra assignment each; no new requests). The H7 block (/*H7-start*/../*H7-end*/, its own script tag after S4) reads them, ignores another person's or older than 2 minutes, and repaints every 1.5 s. h7pick() (between /*H7-pure-start*/ and /*H7-pure-end*/) is the only decision code; the test runs it in node.
- IMPORTANT: the Daily profit target is a page setting on this phone (localStorage sxb_up, default $3, the Bot tab box). The server has NO profit-target stop for one person, so the cartoon only celebrates; it does not claim the bot stopped. Group target (groupcap) has no status the app can read, so it is not a state. Market closed is only the weekend / Friday-night rule the server already has (no holiday calendar exists, none invented).
- tests/test_home7.py (42 checks), mutation-checked. Checked in real Chromium on the real page: dark, light, reduced motion. NOT tested: a real phone / the APK WebView.
- FOUND, NOT FIXED: the Home speech bubble (#bubble) is still written by older code (the sample 'I'm watching 8 pairs...' for the owner and unlinked people; statusText for linked people), so next to the loss-limit / stopped picture it can say the old thing. The grey line under the buttons says the true thing. Fix in Section 8: let H7 own the bubble text for those states.
- Next: Section 8 (more in-app cartoon screens).
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if 'Section 7 (Home cartoon states) DONE' in h: print('docs/HANDOFF.md : already ok')
else: open('docs/HANDOFF.md', 'a', encoding='utf-8').write(NOTE); print('docs/HANDOFF.md : note added')
