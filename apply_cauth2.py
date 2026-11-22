"""C-AUTH 2: the Log in with Deriv button + Deriv logo in the Deriv connect card. Adds static/deriv_login.js (already written) and edits static/index.html. Idempotent. Run: python apply_cauth2.py"""
import os
R = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(R, 'static', 'index.html'); s = open(p, encoding='utf-8').read()
pairs = [
 ('\'<div class="field"><label for="pF">\'+f1+',
  '(n==="Deriv"&&window.sxDerivLogin?window.sxDerivLogin.html():"")+\'<div class="field"><label for="pF">\'+f1+'),
 ('var go=$("#pG"),bb=$("#pB"),pw=$("#pW");',
  'var go=$("#pG"),bb=$("#pB"),pw=$("#pW");if(window.sxDerivLogin)window.sxDerivLogin.wire($("#pL"),$("#pE"));'),
 ('<script src="/static/trade_on.js"></script>',
  '<script src="/static/trade_on.js"></script><script src="/static/deriv_login.js"></script>'),
]
for old, new in pairs:
    if new in s: continue
    assert s.count(old) == 1, (old[:60], s.count(old))
    s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print('C-AUTH 2 applied')
