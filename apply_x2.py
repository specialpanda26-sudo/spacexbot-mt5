"""X2: the X on every pop-up card needs ONE tap (the heading after it was painted on top of the X, so a tap in the middle hit the heading). Also the Test Lab button Payment: Cancelled now works first, with no screen open. Edits static/index.html. Idempotent. Run: python apply_x2.py"""
import os
R = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(R, 'static', 'index.html'); s = open(p, encoding='utf-8').read()
old, new = '.ov .x{position:absolute;right:14px;top:14px}', '.ov .x{position:absolute;right:14px;top:14px;z-index:5}'
if new not in s:
    assert s.count(old) == 1, s.count(old)
    s = s.replace(old, new)
a = 'else if(w==="cancel")cancelled(false)}finally{if(sp)payPend(sp);PAYW=sw}},stop'
b = 'else if(w==="cancel"){ov(XB+BR,1);cancelled(false)}}finally{if(sp)payPend(sp);PAYW=sw}},stop'
if b not in s and a in s: s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)
print('X2 applied')
