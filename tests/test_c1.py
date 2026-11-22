"""Checks C1: demo-or-real wording and the Ogolla Tech credit. Plain python. Run: python tests/test_c1.py"""
import os
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
for bad in ('Open a demo account', 'Practice on a demo account first', 'Demo accounts first', 'running in demo mode', 'Bot started in demo mode', 'Try a demo account first', 'Use a demo (virtual) account first', 'Start on a demo or virtual', 'Free MT5 demo account', 'Practice safely in demo mode', 'has run on demo first'):
    T('gone: ' + bad, bad not in S)
T('landing step says Open an account (demo or real)', 'Demo to practise or Real to trade, your choice.' in S)
T('closing band says demo or real', '<h2>Trade on a demo or a real account.</h2>' in S)
T('Platforms chip says Demo or Real', '<span class="chip info">Demo or Real</span>' in S)
T('footer credit Ogolla Tech (double L)', '2026 spaceXBot \u00b7 Powered by Ogolla Tech</span>' in S)
T('never the single-L spelling', 'Ogola' not in S and 'Powered by Ogolla Tech' in S)
T('risk wording kept: signals do not promise profit', 'do not promise profit' in S)
print('%d/%d passed' % (sum(R), len(R)))
raise SystemExit(0 if all(R) else 1)
