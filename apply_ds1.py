"""Apply DS1 changes to wire deriv_sym.name() into Deriv symbol lookups."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
deriv_path = os.path.join(ROOT, 'backend', 'deriv.py')

if os.path.exists(deriv_path):
    src = open(deriv_path, encoding='utf-8').read()
    orig = src

    if 'deriv_sym' not in src:
        if 'from . import risk' in src:
            src = src.replace('from . import risk', 'from . import deriv_sym, risk', 1)
        elif 'import ' in src:
            lines = src.splitlines(True)
            for idx, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    continue
                lines.insert(idx, 'from backend import deriv_sym\n')
                src = ''.join(lines)
                break

    src = src.replace("'frx' + str(sym).strip().upper()", 'deriv_sym.name(sym)')
    src = src.replace('"frx" + str(sym).strip().upper()', 'deriv_sym.name(sym)')
    src = src.replace("'frx' + sym.upper()", 'deriv_sym.name(sym)')
    src = src.replace('"frx" + sym.upper()', 'deriv_sym.name(sym)')

    if src != orig:
        with open(deriv_path, 'w', encoding='utf-8') as f:
            f.write(src)
        print('edited: backend/deriv.py')

if '--test' in sys.argv:
    sys.exit(subprocess.call([sys.executable, os.path.join(ROOT, 'tests', 'test_ds1.py')]))
