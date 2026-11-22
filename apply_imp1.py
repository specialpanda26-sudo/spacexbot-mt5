import sys, os
P = 'backend/app.py'
OLD = "print('500', request.path, repr(e)[:200]); return"
NEW = "import traceback; print('500', request.path, repr(e)[:300]); traceback.print_exc(); return"
if not os.path.isdir('backend'): print('STOP: run this from the repo folder'); sys.exit(1)
t = open(P, encoding='utf-8', newline='').read()
if 'traceback.print_exc()' not in t:
    if t.count(OLD) != 1: print('STOP: handler line not found exactly once'); sys.exit(1)
    open(P, 'w', encoding='utf-8', newline='').write(t.replace(OLD, NEW))
open('.python-version', 'w').write('3.12\n')
print('patched OK')
