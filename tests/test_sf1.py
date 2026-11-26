"""SF1 checks. Offline. Run: python tests/test_sf1.py"""
import os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'sf1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, botstate
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c.get('/api/me', headers=H('boss@x.com'))
for k, v in (('max_daily_loss_pct', '3'), ('max_weekly_loss_pct', '6'), ('max_losing_streak', '3'), ('streak_cooldown_h', '4'), ('max_ccy_exposure', '2'), ('cooldown_min', '60'), ('news_lock', '1'), ('news_before_min', '30'), ('max_trades_day', '10'), ('no_open_cap', '0'), ('max_open', '3')): st.put(k, v)
f = botstate.fix_for
d = f('daily loss limit hit', '')
T('daily loss: names the setting, its value, and where it is', d and 'Daily loss' in d['name'] and d['value'] == '3' and d['view'] == 'bot' and d['card'] == 'My limits' and '0' in d['hint'])
T('weekly loss', f('weekly loss limit hit', '')['value'] == '6')
T('max open positions', f('max open positions', '')['value'] == '3' and 'Most trades open' in f('max open positions', '')['name'])
T('max trades today', f('max trades today', '')['value'] == '10')
T('losing streak (the code carries the count)', f('3 losses in a row: cooling down', '')['value'] == '3')
T('symbol cooldown', f('symbol cooldown', '')['value'] == '60')
T('correlated exposure', f('USD exposure already at limit (correlated trades)', '')['value'] == '2')
T('news lock', f('news: USD CPI', '')['value'] == '30')
T('a limit that is off says off', (st.put('max_daily_loss_pct', '0'), f('daily loss limit hit', '')['value'])[1] == 'off')
T('bot off points at Home', f('bot off', '')['view'] == 'home' and f('bot off', '')['name'] == 'Start bot')
T('EA offline points at Connect and says it is not a setting', f('EA offline', '')['view'] == 'connect' and 'Not a setting' in f('EA offline', '')['hint'])
T('weekend pause has nothing to open', f('weekend/Friday-night risk', '')['view'] is None)
T('running or unknown codes give nothing', f('watching', '') is None and f('nosetup', '') is None and f('something new', '') is None)
st.put('bot_enabled', '0'); r = c.get('/api/botstate', headers=H('boss@x.com'))
T('the API returns the fix for a stopped bot', r.status_code == 200 and (r.json.get('fix') or {}).get('name') == 'Start bot')
print('%d checks, %d failed' % (len(R), sum(1 for _, ok in R if not ok)))
