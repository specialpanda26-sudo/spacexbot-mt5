"""Section 5 (BTC plan) checks: Auto mode USD profit target per position. No network. Run: python tests/test_s5.py
The scanner is driven like tests/test_multi8.py (brain.evaluate and the gate are faked, candles are real rows)."""
import os, sys, json, time, re
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, '_s5_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, automode, burst, groupcap, alerts
try: alerts.stop()
except Exception: pass
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
brain.evaluate = lambda *a, **k: {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 't', 'score': 3, 'adx': 20}
risk.global_gate = lambda now=None, uid='': (True, '')
BAR = [int(time.time()) // 900 * 900 - 900]
def seed(uid=''):
    A.bars.merge('XAUUSD', 'M15', [[BAR[0] - 900 * i, 2000, 2001, 1999, 2000, 1] for i in range(130)], uid=uid)
    A.bars.merge('XAUUSD', 'H1', [[BAR[0] - 3600 * i, 2000, 2001, 1999, 2000, 1] for i in range(10)], uid=uid)
def run(uid=''):
    """Clean slate, then ONE scan. Returns the new signal rows."""
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%' OR k LIKE 'bg:%'"); A._last_scan.clear(); seed(uid)
    A._scan('XAUUSD', uid)
    return st.q('SELECT * FROM signals ORDER BY id')
def S(**kv):
    for k, v in kv.items(): st.put(k, v)
S(risk_pct='1.0', max_open='10', max_open_ceiling='10', max_trades_day='0', cooldown_min='0')

# ---- the helper ----
S(auto_mode='0', auto_target_usd='5'); T('target_usd is 0 while Auto mode is off, whatever is saved', automode.target_usd() == 0.0)
S(auto_mode='1', auto_target_usd='0'); T('0 means no target', automode.target_usd() == 0.0)
S(auto_target_usd='2.5'); T('Auto mode on: the number is used', automode.target_usd() == 2.5)
S(auto_target_usd='abc'); T('garbage means no target', automode.target_usd() == 0.0)
S(auto_target_usd='99999'); T('huge is cut to 1000', automode.target_usd() == 1000.0)
S(auto_target_usd='-4'); T('negative means no target', automode.target_usd() == 0.0)

# ---- a single position ----
S(auto_mode='1', auto_target_usd='2', auto_positions='1')
rows = run()
T('one position is made', len(rows) == 1)
g = rows[0]['grp'] if rows else None
m = burst.meta(g) if g else None
T('it is a group of one (grp = its own id)', g == rows[0]['id'])
T('the group target is the USD number', m and m['tgt'] == 2.0 and m['n'] == 1 and m['loss'] == 0)
bk = burst.basket(st.q('SELECT id,symbol,side,sl,tp,risk_pct FROM signals', one=True), '')
T('the EA gets it as a basket with the USD target', bk and bk['tgt'] == 2.0 and bk['each'] == 2.0 and bk['ids'] == str(rows[0]['id']) and bk['sl'] == 1990.0 and bk['tp'] == 2020.0)
T('the normal stop loss and take profit are still on the signal', rows[0]['sl'] == 1990.0 and rows[0]['tp'] == 2020.0)

# ---- several positions ----
S(auto_positions='3', auto_target_usd='2')
rows = run()
m = burst.meta(rows[0]['grp'])
T('three positions are made in one group', len(rows) == 3 and len({r['grp'] for r in rows}) == 1)
T('the group target is USD x positions (6)', m and m['tgt'] == 6.0 and m['n'] == 3)
bk = burst.basket(st.q('SELECT id,symbol,side,sl,tp,risk_pct FROM signals ORDER BY id', one=True), '')
T('the basket shows 2 USD for each position and lists all three', bk and bk['each'] == 2.0 and len(bk['ids'].split(',')) == 3)

# ---- off states leave everything as before ----
S(auto_target_usd='0', auto_positions='1'); rows = run()
T('target 0: a plain trade, no group, no basket', len(rows) == 1 and rows[0]['grp'] is None)
S(auto_mode='0', auto_target_usd='5'); rows = run()
T('Auto mode off: a plain trade, no group', len(rows) == 1 and rows[0]['grp'] is None)

# ---- the person's own group target wins over the Auto number ----
S(auto_mode='1', auto_target_usd='2', auto_positions='3')
groupcap.put('', {'on': True, 'target_usd': 9, 'loss_pct': 0}) if hasattr(groupcap, 'put') else st.put('gcap:', json.dumps({'on': True, 'target_usd': 9, 'loss_pct': 0}))
rows = run(); m = burst.meta(rows[0]['grp']) if rows and rows[0]['grp'] else None
T('a group target the person set wins (9, not 6)', m and m['tgt'] == 9.0)
st.x("DELETE FROM kv WHERE k LIKE 'gcap:%'")

# ---- never reopens by itself ----
S(auto_mode='1', auto_target_usd='2', auto_positions='1')
rows = run(); st.x("UPDATE signals SET status='closed', pnl=2.0, closed=? WHERE id=?", (int(time.time()), rows[0]['id']))
A._last_scan.clear(); A._scan('XAUUSD', '')          # same candle, the target was just hit
T('after a target close, the same candle opens nothing new', st.q('SELECT COUNT(*) n FROM signals', one=True)['n'] == 1)
BAR[0] += 900; seed(); A._last_scan.clear(); A._scan('XAUUSD', '')
T('a NEW candle with a fresh valid signal may open a new trade', st.q('SELECT COUNT(*) n FROM signals', one=True)['n'] == 2)

# ---- the route ----
C = A.app.test_client(); H = {'Authorization': 'Bearer dev:boss@x.com'}; C.get('/api/me', headers=H)
for v in ('-1', '1001', 'abc'):
    before = st.get('auto_target_usd'); r = C.post('/api/admin/settings', json={'auto_target_usd': v}, headers=H)
    T('auto_target_usd=%s is refused and nothing is saved' % v, r.status_code == 400 and st.get('auto_target_usd') == before)
r = C.post('/api/admin/settings', json={'auto_target_usd': '3.5'}, headers=H)
T('a good number is saved and comes back', r.status_code == 200 and r.json['auto_target_usd'] == '3.5')

# ---- the page ----
html = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('the Auto card has the USD box, filled and saved', 'id="auUsd"' in html and '$("#auUsd").value=j.auto_target_usd' in html and 'auto_target_usd:$("#auUsd").value' in html)
T('the stop box is called Stop loss limit', 'placeholder="Stop loss limit ATR"' in html and 'placeholder="Stop limit ATR"' not in html)

bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
