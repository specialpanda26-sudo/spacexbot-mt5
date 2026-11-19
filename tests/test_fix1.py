"""Fix 1 checks. Run: python tests/test_fix1.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
from backend import payments as pay
R = []
def T(n, ok): R.append((n, bool(ok))); print(('PASS ' if ok else 'FAIL ') + n)
css = open('static/index.html', encoding='utf-8').read(); ea = open('ea/SpaceXBridge.mq5', encoding='utf-8').read()
T('symbol column cannot break one letter per line', '.row .t{font-weight:800;min-width:0;overflow-wrap:break-word}' in css and 'overflow-wrap:anywhere}' not in css.split('.row .t{')[1].split('}')[0] + '}')
T('strategy line spans under the symbol, not in the price column', '.row .r2{grid-column:2/4;grid-row:2' in css)
T('EA no longer drops hand-closed trades by deal magic', 'DEAL_MAGIC) != Magic) return;' not in ea.split('void OnTradeTransaction')[1])
T('EA still finds our trade by the SXB comment', 'StringFind(cm, "SXB") == 0' in ea.split('void OnTradeTransaction')[1])
T('masked phone is not compared', pay._cbphone('2547****123') == '' and pay._cbphone('254712xxx678') == '')
T('full phone still compared', pay._cbphone('254712345678') == '254712345678' and pay._cbphone('0712345678') == '0712345678')
T('too short phone is not compared', pay._cbphone('1234') == '')
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
