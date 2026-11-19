"""R3 checks: the regime word, results per strategy per regime, the learned switch-off (off by default), the Bot status sentence and the owner's table. No network. Run: python tests/test_regime3.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, '_regime3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, botstate, stats, regime as rg
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

# ---- 1. the regime word ----
T('regime.of: above 28 strong trend, below 18 quiet, between (and at the limits) moderate', rg.of(40) == 'strong trend' and rg.of(10) == 'quiet' and rg.of(22) == 'moderate' and rg.of(28) == 'moderate' and rg.of(18) == 'moderate')
T('a missing or broken ADX is moderate, never a guess', rg.of(None) == 'moderate' and rg.of(float('nan')) == 'moderate' and rg.of('x') == 'moderate' and rg.of(float('inf')) == 'moderate')
T('custom limits are honoured', rg.of(25, 18, 24) == 'strong trend' and rg.of(25, 30, 40) == 'quiet')
T('sentence: names the market and the ADX', 'strong trend (ADX 31)' in rg.sentence('strong trend', 31.2) and 'quiet and ranging (ADX 12)' in rg.sentence('quiet', 12) and 'moderate (ADX 22)' in rg.sentence('moderate', 22))
T('sentence: nothing true to say gives empty', rg.sentence('weird', 20) == '' and rg.sentence('quiet', None) == '' and rg.sentence('quiet', float('nan')) == '')
T('note_text joins the reason and the market; no ADX means the reason alone', rg.note_text({'text': 'None looked.', 'adx': 12.0}).startswith('None looked. Market: quiet and ranging (ADX 12)') and rg.note_text({'text': 'Not enough.'}) == 'Not enough.' and rg.note_text(None) == '')

# ---- 2. results per strategy per regime (from the regime each trade saved at R1) ----
NOW = int(time.time())
def sig(strategy, pnl, regime, grp=None, reason='auto', uid=None, status='closed'):
    rs = json.dumps({'regime': regime, 'adx': 20}) if reason == 'auto' else reason
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,reason,grp,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ('XAUUSD', 'buy', 100.0, 99.0, 102.0, status, NOW - 5000, pnl, NOW - 4000, strategy, rs, grp, uid))
for _ in range(6): sig('fake_a', -2.0, 'quiet')
for _ in range(6): sig('fake_a', 3.0, 'strong trend')
for _ in range(4): sig('fake_b', -5.0, 'quiet')
g = sig('fake_c', -1.0, 'quiet', None)
st.x('UPDATE signals SET grp=? WHERE id=?', (g, g)); sig('fake_c', -1.0, 'quiet', g); sig('fake_c', -1.0, 'quiet', g)
sig('x_one+x_two', 4.0, 'strong trend')
sig('fake_a', -100.0, None, reason=None); sig('fake_a', -100.0, None, reason='not json'); sig('fake_a', -100.0, 'weird'); sig('fake_a', -100.0, 'quiet', status='open')
br = stats.by_regime('')
T('per strategy per regime: count, wins, average, win rate', br['fake_a']['quiet'] == {'n': 6, 'wins': 0, 'pnl': -12.0, 'win_rate': 0.0, 'avg': -2.0} and br['fake_a']['strong trend']['avg'] == 3.0 and br['fake_a']['strong trend']['win_rate'] == 100.0)
T('trades with no saved regime, garbage, an unknown regime or still open are left out', br['fake_a']['quiet']['n'] == 6 and set(br['fake_a']) == {'quiet', 'strong trend'})
T('entries of one setup (same group) count as ONE result, their money added', br['fake_c']['quiet']['n'] == 1 and br['fake_c']['quiet']['pnl'] == -3.0)
T('a trade from "a+b" counts for both strategies', br['x_one']['strong trend']['n'] == 1 and br['x_two']['strong trend']['n'] == 1)
T('another person\'s trades are not mixed in', stats.by_regime('dev-nobody@x.com') == {})
T('learned off-list: only where there are enough trades AND the average is negative', stats.regime_off('', 5) == {'fake_a': {'quiet'}})
T('not enough trades yet: nothing is switched off', stats.regime_off('', 8) == {} and 'fake_b' not in stats.regime_off('', 5))
T('the setting can never go below the floor of 5 trades', stats.regime_off('', 1) == {'fake_a': {'quiet'}} and stats.MIN_FLOOR == 5)
T('the settings exist and are OFF by default', st.DEFAULTS['regime_switch'] == '0' and st.DEFAULTS['regime_min_trades'] == '10' and st.get('regime_switch') == '0')

# ---- 3. the brain skips a strategy only in the regime where it lost ----
def mk(name, side='buy', off=3.0):
    def f(m, h): return {'side': side, 'sl': m[-1]['c'] - off if side == 'buy' else m[-1]['c'] + off, 'name': name}
    f.__name__ = name; return f
real_all, real_adx = brain.ALL, brain.adx
t0 = int(time.time()) // 900 * 900 - 900 * 200
M = [{'t': t0 + 900 * i, 'o': 2000, 'h': 2001 + (i % 3) * 0.2, 'l': 1999 - (i % 2) * 0.2, 'c': 2000 + (i % 2) * 0.5, 'v': 1} for i in range(200)]
def ev(fns, adxv, **kw):
    brain.ALL = fns; brain.adx = lambda m: [adxv] * len(m); info = {}
    try: r = brain.evaluate(M, M, min_conf=1, info=info, **kw)
    finally: brain.ALL = real_all; brain.adx = real_adx
    return r, info
r, i = ev([mk('fake_a')], 10.0); T('without the learned list it trades as before', r and r['side'] == 'buy' and r['why']['regime'] == 'quiet')
r, i = ev([mk('fake_a')], 10.0, off_reg={'fake_a': {'quiet'}}); T('in the regime it lost in, it is skipped and says why', r is None and i['code'] == 'adx' and i['filtered'] == ['fake_a'] and 'their own results were losing' in i['text'] and 'quiet' in i['text'])
r, i = ev([mk('fake_a')], 40.0, off_reg={'fake_a': {'quiet'}}); T('in another regime it still trades', r and r['why']['regime'] == 'strong trend')
r, i = ev([mk('fake_a'), mk('fake_z')], 10.0, off_reg={'fake_a': {'quiet'}}); T('other strategies are not touched', r and r['strategy'] == 'fake_z' and r['score'] == 1)
r, i = ev([mk('fake_a')], 10.0, off_reg={}); T('an empty list changes nothing', r and r['side'] == 'buy')
brain.TREND.add('fake_t'); r, i = ev([mk('fake_t'), mk('fake_a')], 10.0, off_reg={'fake_a': {'quiet'}}); brain.TREND.discard('fake_t')
T('the ADX filter and the learned switch can both speak (one strategy each)', r is None and i['filtered'] == ['fake_t', 'fake_a'] and 'quiet market' in i['text'] and 'switched off there' in i['text'])

# ---- 4. the scanner uses it only when the owner switches it on, and the Bot status names the market ----
risk.global_gate = lambda now=None, uid='': (True, '')
risk.symbol_gate = lambda *a, **k: (True, 'ok')
BAR = int(time.time()) // 900 * 900 - 900
st.put('min_confluence', '1'); st.put('max_open', '10'); st.put('max_open_ceiling', '10'); st.put('max_trades_day', '0'); st.put('regime_min_trades', '5')
def scan(adxv):
    st.x("DELETE FROM signals WHERE status='pending'"); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._last_scan.clear()
    A.bars.merge('XAUUSD', 'M15', [[BAR - 900 * k, 2000, 2001, 1999, 2000, 1] for k in range(130)], uid='')
    A.bars.merge('XAUUSD', 'H1', [[BAR - 3600 * k, 2000, 2001, 1999, 2000, 1] for k in range(10)], uid='')
    brain.ALL = [mk('fake_a')]; brain.adx = lambda m: [adxv] * len(m)
    try: A._scan('XAUUSD', '')
    finally: brain.ALL = real_all; brain.adx = real_adx
    return st.q("SELECT COUNT(*) n FROM signals WHERE status='pending'", (), True)['n']
st.put('regime_switch', '0'); T('switch OFF: the strategy trades even in the regime where it lost', scan(10.0) == 1)
st.put('regime_switch', '1'); n = scan(10.0)
w = botstate._last('')['w']
T('switch ON: the same strategy is skipped in a quiet market', n == 0 and botstate._last('')['c'] == 'nosetup')
T('the Bot status note says why and names the market', 'switched off there' in w and 'Market: quiet and ranging (ADX 10)' in w)
T('switch ON but a different regime: it trades', scan(40.0) == 1)
T('the trade saved with the regime it was taken in', json.loads(st.q("SELECT reason FROM signals WHERE status='pending'", (), True)['reason'])['regime'] == 'strong trend')

# ---- 5. the owner's table and the settings route ----
c = A.app.test_client(); H = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=H)
d = c.get('/api/admin/regimes', headers=H).get_json()
row = next(x for x in d['rows'] if x['strategy'] == 'fake_a' and x['regime'] == 'quiet')
T('GET /api/admin/regimes: the table, with the switch state and which cells are off', d['switch'] is True and d['min_trades'] == 5 and row['n'] == 6 and row['avg'] == -2.0 and row['off'] is True and row['name'] == 'Fake a')
T('a cell that is fine is not marked off', next(x for x in d['rows'] if x['strategy'] == 'fake_a' and x['regime'] == 'strong trend')['off'] is False)
c.get('/api/me', headers={'Authorization': 'Bearer dev:amy@x.com'})
T('only the owner can read it', c.get('/api/admin/regimes', headers={'Authorization': 'Bearer dev:amy@x.com'}).status_code in (401, 403) and c.get('/api/admin/regimes').status_code in (401, 403))
r = c.post('/api/admin/settings', json={'regime_switch': '0', 'regime_min_trades': '12'}, headers=H).get_json()
T('the owner can set both settings', r['regime_switch'] == '0' and r['regime_min_trades'] == '12')
bad = [k for k, ok in R if not ok]; print('\n%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
