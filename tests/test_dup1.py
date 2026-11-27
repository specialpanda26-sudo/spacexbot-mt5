"""DUP1 checks: the header gear and the 'Find a setting' card are hidden while the Search/Alerts/Settings bar shows, and come back when signed out.
Run: python tests/test_dup1.py   (exit 1 on any FAIL)"""
import os, re, sys, subprocess, json
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '..', 'static', 'topbar_ui.js')
s = open(P, encoding='utf-8').read()
ok = []
def chk(n, c): ok.append((n, bool(c)))
m = re.search(r'function dupHide\(\) \{.*?\n  \}\n', s, re.S); fn = m.group(0) if m else ''
chk('dupHide exists', fn)
chk('it is called every second with the bar', 'B.hidden = !signed(); dupHide();' in s)
chk('it targets the header gear and the Find a setting card', 'button[data-up="set"]' in fn and '.sxfind' in fn)
js = """
var on = %s; function signed(){ return on; }
var gear = {style:{display:''}}, card = {style:{display:''}};
var document = {querySelectorAll: function(q){ return q.indexOf('data-up') > -1 ? [gear] : q === '.sxfind' ? [card] : []; }};
%s
on = true; dupHide(); var a = [gear.style.display, card.style.display];
on = false; dupHide(); var b = [gear.style.display, card.style.display];
console.log(JSON.stringify([a, b]));
""" % ('true', fn)
try:
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    a, b = json.loads(r.stdout.strip()) if r.returncode == 0 else ([], [])
    chk('signed in: gear and search card hidden', a == ['none', 'none'])
    chk('signed out: both come back', b == ['', ''])
except FileNotFoundError: pass
p = os.path.join(HERE, 'dup1_check.js'); open(p, 'w').write(s)
try: chk('topbar_ui.js still parses', subprocess.run(['node', '--check', p], capture_output=True).returncode == 0)
except FileNotFoundError: pass
finally: os.remove(p)
bad = [n for n, c in ok if not c]
print('\n'.join(('ok   ' if c else 'FAIL ') + n for n, c in ok)); sys.exit(1 if bad else 0)
