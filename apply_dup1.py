"""DUP1: one Settings and one Search. While the bar (Search, Alerts, Settings) is showing, the header gear and the 'Find a setting' card are hidden.
Signed out (no bar), they come back, so nothing becomes unreachable. Safe to run twice."""
import sys
P = 'static/topbar_ui.js'
s = open(P, encoding='utf-8').read()
if 'DUP1' in s: print('already done'); sys.exit(0)
old = "  setInterval(function () {\n    TK++; B.hidden = !signed();"
if s.count(old) != 1: print('NOT FOUND: the banner timer'); sys.exit(1)
new = '''  /* DUP1: one Settings and one Search. While the bar is showing, the header gear and the "Find a setting" card are hidden; signed out they come back. */
  function dupHide() {
    var on = signed(), g = document.querySelectorAll('.top-actions button[data-up="set"]'), f = document.querySelectorAll(".sxfind"), i;
    for (i = 0; i < g.length; i++) g[i].style.display = on ? "none" : "";
    for (i = 0; i < f.length; i++) f[i].style.display = on ? "none" : "";
  }
  setInterval(function () {
    TK++; B.hidden = !signed(); dupHide();'''
open(P, 'w', encoding='utf-8').write(s.replace(old, new, 1))
print('DUP1 applied')
