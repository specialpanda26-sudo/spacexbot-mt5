"""C1: wording is "demo or real" everywhere, and the site says Powered by Ogola Tech.
Edits static/index.html only. Safe to run twice. Changes nothing if any old text does not fit exactly once.
Then writes tests/test_c1.py and runs it."""
import os, sys, subprocess
P = 'static/index.html'
MARK = 'Powered by Ogola Tech'
E = [
 ('<li><div><b>Open a demo account</b><span>FBS, Exness, HFM or Deriv, all free to practice on.</span></div></li>',
  '<li><div><b>Open an account</b><span>FBS, Exness, HFM or Deriv. Demo to practise or Real to trade, your choice.</span></div></li>'),
 ('<h2>Practice on a demo account first.</h2>', '<h2>Trade on a demo or a real account.</h2>'),
 ('<li><div><b>Open a demo account</b><span>Create an MT5 demo account with FBS, Exness or HFM and practice first.</span></div></li>',
  '<li><div><b>Open an account</b><span>Create an MT5 account (demo or real) with FBS, Exness or HFM.</span></div></li>'),
 ('<span class="chip info">Demo accounts first</span>', '<span class="chip info">Demo or Real</span>'),
 ('Start on a demo or virtual account.</p>', 'Use a demo or a real account.</p>'),
 ('show your demo balance. 4. Tap Start bot. Use a demo (virtual) account first.', 'show your balance. 4. Tap Start bot. Works with a demo (virtual) or a real account.'),
 ("You're all set. The bot is running in demo mode.", "You're all set. Pick Demo or Real on the Bot tab."),
 ('"Bot started in demo mode"', '"Bot started"'),
 ('"Practice with a demo account. Every new strategy should start here."', '"Demo uses practice money. Live uses your real account."'),
 ('"Live trading stays locked until a broker is connected and has run on demo first."', '"Live trading uses your real account and needs a connected broker."'),
 ('Try a demo account first.</p>', 'Works with a demo or a real MT5 account.</p>'),
 ('q:"Which broker will you practice on?"', 'q:"Which broker will you use?"'),
 ('["fbs","FBS","Free MT5 demo account","F"],["exness","Exness","Free MT5 demo account","E"],["hfm","HFM","Free MT5 demo account","H"]',
  '["fbs","FBS","MT5 demo or real account","F"],["exness","Exness","MT5 demo or real account","E"],["hfm","HFM","MT5 demo or real account","H"]'),
 ('<p class="gn">Practice on a demo account first.</p>', '<p class="gn">Use a demo or a real account.</p>'),
 ('</i>Practice safely in demo mode</li>', '</i>Trade on a demo or a real account</li>'),
 ('<span>© 2026 spaceXBot</span>', '<span>© 2026 spaceXBot · ' + MARK + '</span>'),
]
s = open(P, encoding='utf-8').read()
if MARK in s and all(b in s for a, b in E): print('C1 already applied'); n = s
else:
    n = s
    for a, b in E:
        if n.count(a) != 1: print('STOP: cannot find exactly once:', a[:70]); sys.exit(1)
        n = n.replace(a, b)
    open(P + '.tmp', 'w', encoding='utf-8').write(n); os.replace(P + '.tmp', P)
    print('C1 applied: %d edits' % len(E))
T = '''"""Checks C1: demo-or-real wording and the Ogola Tech credit. Plain python. Run: python tests/test_c1.py"""
import os
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
for bad in ('Open a demo account', 'Practice on a demo account first', 'Demo accounts first', 'running in demo mode', 'Bot started in demo mode', 'Try a demo account first', 'Use a demo (virtual) account first', 'Start on a demo or virtual', 'Free MT5 demo account', 'Practice safely in demo mode', 'has run on demo first'):
    T('gone: ' + bad, bad not in S)
T('landing step says Open an account (demo or real)', 'Demo to practise or Real to trade, your choice.' in S)
T('closing band says demo or real', '<h2>Trade on a demo or a real account.</h2>' in S)
T('Platforms chip says Demo or Real', '<span class="chip info">Demo or Real</span>' in S)
T('footer credit Ogola Tech (double L)', '2026 spaceXBot \\u00b7 Powered by Ogola Tech</span>' in S)
T('never the single-L spelling', 'Ogla' not in S and 'Powered by Ogola Tech' in S)
T('risk wording kept: signals do not promise profit', 'do not promise profit' in S)
print('%d/%d passed' % (sum(R), len(R)))
raise SystemExit(0 if all(R) else 1)
'''
os.makedirs('tests', exist_ok=True)
open('tests/test_c1.py', 'w', encoding='utf-8').write(T)
r = subprocess.run([sys.executable, 'tests/test_c1.py'], capture_output=True, text=True)
print(r.stdout.strip().splitlines()[-1]); sys.exit(r.returncode)
