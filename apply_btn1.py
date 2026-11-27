"""BTN1: the three stat buttons (Restart daily loss count, Reset my stats / Clear all trades, Start stats from now) never vanish.
They were drawn only if the sign-in had already loaded; now they are always drawn, in the Journal AND at the top of Stats, and repainted when sign-in finishes. Safe to run twice."""
import sys, re
P = 'static/index.html'
s = open(P, encoding='utf-8').read()
if 'function jbtns(' in s: print('already done'); sys.exit(0)
m = re.search(r"\n if\(u\)h\+=('<div style=\"margin:8px 0\">.*?);\n return h\}", s, re.S)
if not m: print('journal buttons not found'); sys.exit(1)
expr = m.group(1).replace('u.admin', '(u&&u.admin)')
s = s[:m.start()] + '\n h+=jbtns(s);          /* BTN1: always drawn */\n return h}\nfunction jbtns(s){var u=null;try{u=SXA.user()}catch(e){}return ' + expr + '}' + s[m.end():]
def rep(old, new):
    global s
    if s.count(old) != 1: print('NOT FOUND:', old[:70]); sys.exit(1)
    s = s.replace(old, new, 1)
rep("""b.innerHTML='<p class="note">'+jmsg()+'</p>';return}""", """b.innerHTML='<p class="note">'+jmsg()+'</p>'+jbtns(s);return}""")
rep('''b.innerHTML='<div class="stats">'+kp("Win rate"''', '''b.innerHTML=jbtns(s)+'<div class="stats">'+kp("Win rate"''')
rep('window.jr=jr;window.sr=sr;', 'window.jr=jr;window.sr=sr;try{SXA.ready().then(function(){try{jr();sr()}catch(e){}})}catch(e){}/* BTN1: repaint when sign-in finishes */')
open(P, 'w', encoding='utf-8').write(s)
print('BTN1 applied')
