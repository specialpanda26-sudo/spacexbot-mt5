import sys, os
P = 'backend/store.py'
if not os.path.isfile(P): print('STOP: run this from the repo folder'); sys.exit(1)
t = open(P, encoding='utf-8', newline='').read()
if 'IMP3' in t: print('already applied'); sys.exit(0)
EDITS = [
 ("PG = bool(URL)\n",
  "PG = bool(URL)\nif PG:          # IMP3: load the driver once, now, before any background thread exists\n    import psycopg2, psycopg2.extras, psycopg2.pool, psycopg2.extensions\n"),
 ("cur.execute(_ph(sql), tuple(a)); rows =",
  "cur.execute(_ph(sql), tuple(a) or None); rows ="),
 ("try: cur.execute(s, tuple(a))\n",
  "try: cur.execute(s, tuple(a) or None)\n"),
]
for old, new in EDITS:
    if t.count(old) != 1: print('STOP: cannot find exactly once ->', old[:60]); sys.exit(1)
for old, new in EDITS: t = t.replace(old, new)
open(P, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
