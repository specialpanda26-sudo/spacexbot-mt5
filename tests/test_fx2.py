"""FX2-FX4 page checks (text only, no browser, no network). Run: python tests/test_fx2.py"""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
rd = lambda p: open(os.path.join(ROOT, p), encoding='utf-8').read()
g, c, ix = rd('static/guide.js'), rd('static/course.js'), rd('static/index.html')
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
card = re.search(r"<p class=\"note\">([^<]*)</p>' \+\s*\n\s*'<button class=\"btn block\" type=\"button\" data-g=\"open\"", g)
T('Home guide card: the shown sentence has no word "cartoon"', card and 'cartoon' not in card.group(1).lower() and card.group(1).startswith('Quick guide'))
T('quiz: the chosen answer has its own look and a tick', 'border-color:var(--green)' in c and 'u2713' in c and 'aria-pressed' in c)
T('quiz: a tap keeps the scroll place, a new screen starts at the top', 'draw(true)' in c and 'p.scrollTop = keep ? top : 0' in c)
T('quiz: the page says how many questions are still open', 'still to answer' in c)
T('Check connection asks the bridge and the Connection check card together', 'window.__sx2.poll' in ix and 'Promise.all([poll(), other])' in ix)
T('Check connection: every ask gives up after 20 seconds (bridge, connections, live)', ix.count('function lim(') == 3 and ix.count('lim(SXA.api(') == 3)
T('Check connection: the button comes back and the message is the truth', 'btn.textContent = "Check connection"' in ix and 'MT5 bridge is online' in ix and 'Cannot reach the server' in ix)
T('top chip says Reconnecting, not Offline, when the phone cannot reach the server', 'function stl()' in ix and 'FAIL >= 3 ? "Reconnecting" : "Offline"' in ix and ix.count('stl()') >= 3)
T('old blank-and-wait line is gone', 'D = null; paint(); poll().then(function () { if (window.sxToast && D)' not in ix)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
