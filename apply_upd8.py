import sys, os
P = 'static/update.js'
if not os.path.isfile(P): print('STOP: run this from the repo folder'); sys.exit(1)
t = open(P, encoding='utf-8', newline='').read()
if 'UPD8' in t: print('already applied'); sys.exit(0)
EDITS = [
 ('cart.innerHTML = pic(o.pic); c.appendChild(cart);',
  'cart.innerHTML = (o.pic === "download" ? art() : pic(o.pic)); c.appendChild(cart);          /* UPD8: "download" = the update cartoon (arrow), not the mail phone */'),
 ('{ pic: "phone", title: "Downloading update"',
  '{ pic: "download", title: "Downloading update"'),
]
for old, new in EDITS:
    if t.count(old) != 1: print('STOP: cannot find exactly once ->', old[:60]); sys.exit(1)
for old, new in EDITS: t = t.replace(old, new)
open(P, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
