"""PH4: VISION_PROVIDER picks the screen-reading AI. Run: python tests/test_ph4.py"""
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
