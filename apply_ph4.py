"""PH4: choose the screen-reading AI with one Render variable. Run from the repo folder: python apply_ph4.py   (add --test to run the tests)
Adds VISION_PROVIDER (anthropic, grok, gemini or custom). The admin choice still wins if one was ever saved. Default stays anthropic.
Safe to run twice; if the old text is not found exactly once, NOTHING is changed."""
import os, sys, subprocess
P = 'backend/visionmodel.py'
OLD = "    p = st.get('vision_provider') or DEFAULT\n"
NEW = "    p = st.get('vision_provider') or os.getenv('VISION_PROVIDER', '').strip().lower() or DEFAULT          # PH4: Render variable VISION_PROVIDER\n"
TEST = '''"""PH4: VISION_PROVIDER picks the screen-reading AI. Run: python tests/test_ph4.py"""
import os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_ph4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, visionmodel as vm, alerts
try: alerts.stop()
except Exception: pass
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
os.environ.pop('VISION_PROVIDER', None)
T('no variable, nothing saved: anthropic', vm.provider() == 'anthropic')
os.environ['VISION_PROVIDER'] = 'gemini'
T('VISION_PROVIDER=gemini picks Gemini', vm.provider() == 'gemini')
os.environ['VISION_PROVIDER'] = ' Gemini '
T('spaces and capitals do not matter', vm.provider() == 'gemini')
os.environ['VISION_PROVIDER'] = 'nonsense'
T('an unknown name falls back to anthropic', vm.provider() == 'anthropic')
os.environ['VISION_PROVIDER'] = 'gemini'; st.put('vision_provider', 'grok')
T('a choice saved by the admin still wins', vm.provider() == 'grok')
for f in glob.glob(DB + '*'): os.remove(f)
print('%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
'''
s = open(P, encoding='utf-8').read()
if NEW in s: print('skip (already there): VISION_PROVIDER')
elif s.count(OLD) != 1: print('STOP: old text not found exactly once. Nothing was changed.'); sys.exit(1)
else:
    open(P + '.new', 'w', encoding='utf-8').write(s.replace(OLD, NEW, 1)); os.replace(P + '.new', P); print('edited: VISION_PROVIDER')
open('tests/test_ph4.py', 'w', encoding='utf-8').write(TEST)
if '--test' not in sys.argv: print('Done. Next: git add -A, commit, push (Render redeploys by itself; no new APK needed).'); sys.exit(0)
r = subprocess.run([sys.executable, 'tests/test_ph4.py'], capture_output=True, text=True); print(r.stdout[-600:]); sys.exit(r.returncode)
