"""BTN1 checks: the stat buttons are always drawn (Journal and Stats), not hidden behind the sign-in. No network. Run: python tests/test_btn1.py"""
import os, re, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
ok = []
def chk(n, c): ok.append((n, bool(c)))
jb = re.search(r'function jbtns\(s\)\{(.*?)\}\nfunction ', s, re.S); jb = jb.group(1) if jb else ''
jsum = re.search(r'function jsum\(\)\{(.*?)\n return h\}', s, re.S); jsum = jsum.group(1) if jsum else ''
sr = re.search(r'function sr\(\)\{(.*?)\nfunction bxs', s, re.S); sr = sr.group(1) if sr else ''
for i in ('jDay', 'jReset', 'jWipe', 'jFrom', 'jUndo'): chk('button %s is in jbtns' % i, 'id="%s"' % i.replace('"', '') in jb.replace('\\"', '"'))
chk('jbtns is not gated by sign-in', 'if(u)' not in jb and 'if(u)h' not in jsum)
chk('owner still gets Clear all trades, others Reset my stats', '(u&&u.admin)' in jb)
chk('Journal draws the buttons', 'jbtns(s)' in jsum)
chk('Stats draws the buttons at the top, also when there are no trades yet', sr.count('jbtns(s)') == 2 and "b.innerHTML=jbtns(s)+'<div class=\"stats\">'" in sr and sr.rstrip().endswith('+bxs()}'))
chk('buttons repaint when sign-in finishes', 'SXA.ready().then(function(){try{jr();sr()}' in s)
js = '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)); p = os.path.join(HERE, 'btn1_check.js'); open(p, 'w').write(js)
try: r = subprocess.run(['node', '--check', p], capture_output=True, text=True); chk('page script still parses', r.returncode == 0)
except FileNotFoundError: pass
finally: os.remove(p)
bad = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if bad else 0)
