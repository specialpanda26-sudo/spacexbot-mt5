"""NL1 checks: the owner's stopping limits are off (also over old saved values), once. Offline. Run: python tests/test_nl1.py"""
import os, sys, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'nl1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, risk, userlim
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c.get('/api/me', headers=H('amy@x.com')); A = 'dev-amy@x.com'
WD = 1700000000 - (1700000000 % 86400) + 86400 * 4 + 12 * 3600
while time.gmtime(WD).tm_wday >= 4: WD += 86400
st.put('acct', json.dumps({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'seen': WD})); st.put('bot_enabled', '1')
for k, v in (('max_daily_loss_pct', '3'), ('max_weekly_loss_pct', '6'), ('max_losing_streak', '3'), ('streak_cooldown_h', '4'), ('max_ccy_exposure', '2'), ('cooldown_min', '60'), ('news_lock', '1'), ('max_trades_day', '2')): st.put(k, v)
st.put('nolimits_v1', '0')
for i in range(3): st.x("INSERT INTO signals(symbol,side,status,created,closed,pnl,uid) VALUES('XAUUSD','buy','closed',?,?,-200,'')", (WD - 3600, WD - 100 - i))
g = risk.global_gate(WD + 5, uid='')
T('old saved limits stop the owner (trades a day / daily loss)', g[0] is False and g[1] in ('max trades today', 'daily loss limit hit'))
st.nolimits_once()
T('after NL1: the same owner is not stopped', risk.global_gate(WD + 5, uid='') == (True, 'ok'))
T('streak, cooldown, exposure, news and trades a day are all off', all(userlim.val('', k) == 0 for k in ('daily_loss', 'weekly_loss', 'streak', 'cooldown', 'same_dir', 'news_min', 'max_trades')))
st.x("INSERT INTO signals(symbol,side,status,created,uid) VALUES('XAUUSD','buy','closed',?,'')", (WD - 60,))
T('no symbol cooldown: the same market can trade again at once', risk.symbol_gate('XAUUSD', 'buy', now=WD + 5, uid='') == (True, 'ok'))
st.put('max_daily_loss_pct', '5'); st.nolimits_once()
T('runs once: a number saved later is kept', st.get('max_daily_loss_pct') == '5')
r = c.post('/api/admin/settings', headers=H('boss@x.com'), json={'max_daily_loss_pct': '0', 'max_weekly_loss_pct': '0'})
T('the admin page accepts 0 (off) for daily and weekly loss', r.status_code == 200 and st.get('max_daily_loss_pct') == '0')
links.new_key(A); st.x('UPDATE links SET acct=? WHERE uid=?', (json.dumps({'balance': 1000, 'demo': False, 'seen': WD}), A))
T("a customer's real account keeps its own safe start values", userlim.val(A, 'daily_loss') == 3.0 and userlim.val(A, 'streak') == 3.0)
print('%d checks, %d failed' % (len(R), sum(1 for _, ok in R if not ok)))
