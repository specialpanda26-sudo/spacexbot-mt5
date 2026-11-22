"""AU1 tests: every server setting has a field, and the 7 new ones are range-checked. Run: python tests/test_au1.py"""
import os, sys, re, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_au1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A, store as st
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
txt = ''.join(open(f, encoding='utf-8').read() for f in glob.glob(os.path.join(ROOT, 'static', '*.html')) + glob.glob(os.path.join(ROOT, 'static', '*.js')))
OWN_CARD = {'feed_on': 'the price-feed switch saves through /api/admin/feed, not the settings route'}
none = [k for k in st.DEFAULTS if k not in OWN_CARD and not re.search(r'(?<![a-z_])' + re.escape(k) + r'(?![a-z_0-9])', txt)]
T('every server setting has a field in the app (missing: %s)' % none, not none)
c = A.app.test_client(); ad = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=ad)
good = {'news_before_min': 45, 'news_after_min': 20, 'cooldown_min': 90, 'max_ccy_exposure': 3, 'multi_entries': 4, 'regime_min_trades': 20, 'practice_trades_needed': 8}
r = c.post('/api/admin/settings', json=good, headers=ad); j = r.get_json()
T('good values save', r.status_code == 200 and all(float(j[k]) == v for k, v in good.items()))
bad = {'news_before_min': 999, 'news_after_min': -1, 'cooldown_min': 5000, 'max_ccy_exposure': 0, 'multi_entries': 11, 'regime_min_trades': 4, 'practice_trades_needed': 101}
for k, v in bad.items():
    r = c.post('/api/admin/settings', json={k: v}, headers=ad); T('%s=%s refused' % (k, v), r.status_code == 400)
j = c.post('/api/admin/settings', json={}, headers=ad).get_json(); T('refused values changed nothing', float(j['cooldown_min']) == 90 and float(j['max_ccy_exposure']) == 3)
os.remove(os.environ['DB_PATH']) if os.path.exists(os.environ['DB_PATH']) else None
bad_n = [n for n, ok in R if not ok]; print('%d/%d passed' % (len(R) - len(bad_n), len(R))); sys.exit(1 if bad_n else 0)
