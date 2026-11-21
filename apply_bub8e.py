"""Section 8e: the Home speech bubble follows the same situation as the Home cartoon.
Bug found in Section 7 and left open: three older pieces of code keep writing #bubble (the sample 'I'm watching 8 pairs...', the locked line, statusText for linked people), so next to the loss-limit / stopped / target / market-closed picture the bubble could still say the old thing.
Fix without touching the old writers: H7 publishes its decision (window.SXH7), and a small block holds the bubble text for the five non-running states.
Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'static/index.html'
# 1) H7 publishes what it decided (one extra assignment, like SXBOT / SXLIVE)
edit(P, '    var say = r.say || ""; if (say !== NOW)',
        '    window.SXH7 = { k: r.k, say: r.say || "", why: (fresh(window.SXBOT) || {}).why || "" };\n    var say = r.say || ""; if (say !== NOW)', 'window.SXH7 =')
# 2) the bubble block, own script tag after H8c
BLOCK = r"""<script>
/*B8e-start*/
/* Section 8e: the Home speech bubble says the same thing as the Home picture. Older code keeps writing #bubble (sample text, the locked line, statusText), so for the five non-running states this block holds the text and gives the last older text back when the bot runs again. Facts only. */
(function () {
  /*B8e-pure-start*/
  function b8eText(h) {
    if (!h) return "";
    if (h.k === "lock") return "The bot is locked. Choose a plan to switch it on.";
    if (h.k === "loss") return h.say || "A loss limit was reached, so the bot is not opening new trades.";
    if (h.k === "stopped") return h.why || "The bot is stopped. Tap Start bot.";
    if (h.k === "target" || h.k === "closed") return h.say || "";
    return "";
  }
  /*B8e-pure-end*/
  var bu = document.getElementById("bubble"); if (!bu) return;
  var d = Object.getOwnPropertyDescriptor(Node.prototype, "textContent"); if (!d || !d.get || !d.set) return;
  var HOLD = "", LAST = null;
  Object.defineProperty(bu, "textContent", { configurable: true,
    get: function () { return d.get.call(bu); },
    set: function (v) { LAST = v; d.set.call(bu, HOLD || v); } });
  function tick() {
    var t = b8eText(window.SXH7);
    if (t) { HOLD = t; if (d.get.call(bu) !== t) d.set.call(bu, t); }
    else if (HOLD) { HOLD = ""; if (LAST !== null) d.set.call(bu, LAST); }
  }
  setInterval(tick, 700); tick();
})();
/*B8e-end*/
</script>
"""
edit(P, '/*H8c-end*/\n</script>\n', '/*H8c-end*/\n</script>\n' + BLOCK, '/*B8e-start*/')

# 3) docs/HANDOFF.md
H = 'docs/HANDOFF.md'
SEC = """## Section 8e (Home speech bubble follows the Home picture) DONE (Nov 21)
- apply_bub8e.py edits static/index.html only (+ tests/test_bub8e.py). Fixes the bug left open since Section 7: older code (render(), the locked sync(), S4 home() / statusText) keeps writing #bubble, so next to the loss-limit / stopped / target / market-closed picture it could say the old sample text.
- H7's paint() now also publishes window.SXH7 {k, say, why} (k = lock / loss / stopped / target / closed / run; why = the server sentence from /api/botstate). The new block /*B8e-start*/../*B8e-end*/ (own script tag after H8c) puts an own textContent property on #bubble: in the five non-running states it HOLDS the text (writes from the older code are remembered but not shown); when the bot is running again it gives the last older text back. The older writers were NOT edited.
- Texts (b8eText, between /*B8e-pure-start*/ and /*B8e-pure-end*/): lock = 'The bot is locked. Choose a plan to switch it on.' (same as before); loss limit = the server sentence; stopped = the server sentence ('The bot is stopped. Tap Start bot.' or the plan-ended one); profit target and market closed = the same line the grey note shows under the buttons. Running = nothing held, so the older text shows as before.
- tests/test_bub8e.py, mutation-checked. NOT tested: a real phone / the APK WebView. The bubble can lag the picture by up to ~2 s (700 ms and 1.5 s timers).

"""
edit(H, '## STATUS BOARD (Nov 21, newest; read this first)\n', SEC + '## STATUS BOARD (Nov 21, newest; read this first)\n', '## Section 8e (Home speech bubble')
edit(H, 'W9 (weekend rule per market). Files:', 'W9 (weekend rule per market), 8e (Home speech bubble follows the picture). Files:', '8e (Home speech bubble follows the picture). Files:')
edit(H, 'plan8b/pop8c/pic8d/wknd9.py', 'plan8b/pop8c/pic8d/wknd9/bub8e.py', 'pic8d/wknd9/bub8e.py')
edit(H, '- OPEN BUGS / NOTES: the Home speech bubble (#bubble) is still written by older code and can contradict the Section 7 picture (fix in 8b or 8c). Motion is on',
        '- OPEN BUGS / NOTES: (the Home speech bubble bug is fixed in 8e). Motion is on', '(the Home speech bubble bug is fixed in 8e)')
