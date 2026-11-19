"""R1 checks: the bot saves WHY it took a trade, and the journal and trade pop-up show it. No network. Run: python tests/test_reason1.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, '_reason1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, reason as rsn
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

# ---- 1. the real brain explains itself (two fake strategies agree) ----
def mk(name, side):
    def f(m, h): return {'side': side, 'sl': m[-1]['c'] - 3.0 if side == 'buy' else m[-1]['c'] + 3.0, 'name': name}
    f.__name__ = name; return f
real_all = brain.ALL; t0 = int(time.time()) // 900 * 900 - 900 * 200
M = [{'t': t0 + 900 * i, 'o': 2000, 'h': 2001 + (i % 3) * 0.2, 'l': 1999 - (i % 2) * 0.2, 'c': 2000 + (i % 2) * 0.5, 'v': 1} for i in range(200)]
brain.ALL = [mk('fake_a', 'buy'), mk('fake_b', 'buy'), mk('fake_c', 'sell')]
r = brain.evaluate(M, M, 2, 2.0)
brain.ALL = real_all
T('brain returns a why with the agreeing strategies', r and r['why']['agree'] == ['fake_a', 'fake_b'] and r['score'] == 2)
T('why counts the strategy that disagreed', r and r['why']['against'] == 1)
T('why has the market state, the stop in ATRs and the reward-to-risk', r and r['why']['regime'] in ('strong trend', 'quiet', 'moderate') and r['why']['sl_atr'] > 0 and r['why']['rr'] == 2.0 and r['why']['own_tp'] is False)
T('the old keys of the brain result are unchanged', r and all(k in r for k in ('side', 'entry', 'sl', 'tp', 'strategy', 'score', 'adx')))

# ---- 2. pack / lines / short ----
raw = rsn.pack(r); ln = rsn.lines(raw, r['strategy'])
T('pack gives JSON text', isinstance(raw, str) and json.loads(raw)['agree'] == ['fake_a', 'fake_b'])
T('lines: the setup, the market, the stop, the target and the prices', len(ln) == 5 and 'agreed' in ln[0] and 'ADX' in ln[1] and 'stop loss' in ln[2] and 'target' in ln[3] and ln[4].startswith('Planned prices'))
T('lines: the other-way strategy is mentioned', '1 other strategy pointed the other way' in ln[0])
T('short: one line', rsn.short(raw).startswith('2 strategies agreed') and 'ADX' in rsn.short(raw))
T('nothing saved / garbage: empty, never an error', rsn.lines(None) == [] and rsn.lines('') == [] and rsn.lines('not json') == [] and rsn.lines('[1]') == [] and rsn.short(None) == '' and rsn.short('{{') == '')
T('pack of an old-style result (no why) still works', json.loads(rsn.pack({'side': 'buy', 'entry': 1.0, 'sl': 0.9, 'tp': 1.2, 'strategy': 'x+y', 'score': 2, 'adx': 20}))['agree'] == ['x', 'y'])
T('pack never raises on junk', rsn.pack(None) == '' or isinstance(rsn.pack(None), str))

# ---- 3. the scanner saves it with the signal (and with every entry of a multi-entry setup) ----
risk.global_gate = lambda now=None, uid='': (True, '')
risk.symbol_gate = lambda *a, **k: (True, 'ok')
WHY = {'agree': ['fake_a', 'fake_b'], 'against': 0, 'adx': 24.3, 'regime': 'moderate', 'atr': 2.0, 'sl_atr': 1.5, 'rr': 2.0, 'own_tp': False, 'solo': False, 'min_conf': 2}
brain.evaluate = lambda *a, **k: {'side': 'buy', 'entry': 2000.0, 'sl': 1997.0, 'tp': 2006.0, 'strategy': 'fake_a+fake_b', 'score': 2, 'adx': 24.3, 'why': WHY}
BAR = int(time.time()) // 900 * 900 - 900
def run(uid=''):
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._last_scan.clear()
    A.bars.merge('XAUUSD', 'M15', [[BAR - 900 * i, 2000, 2001, 1999, 2000, 1] for i in range(130)], uid=uid)
    A.bars.merge('XAUUSD', 'H1', [[BAR - 3600 * i, 2000, 2001, 1999, 2000, 1] for i in range(10)], uid=uid)
    A._scan('XAUUSD', uid); return st.q('SELECT * FROM signals ORDER BY id')
st.put('max_open', '10'); st.put('max_open_ceiling', '10'); st.put('max_trades_day', '0')
rows = run()
T('a new signal is saved with its reason', len(rows) == 1 and rows[0]['reason'] and json.loads(rows[0]['reason'])['adx'] == 24.3 and json.loads(rows[0]['reason'])['entry'] == 2000.0)
st.put('multi_entries', '3'); st.put('multi_min_score', '2'); rows = run()
T('every entry of a multi-entry setup carries the same reason', len(rows) == 3 and len({r['reason'] for r in rows}) == 1 and rows[0]['reason'])
st.put('multi_entries', '1')

# ---- 4. the pop-up and the journal show it ----
c = A.app.test_client(); H = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=H)
rows = run(); now = int(time.time())
st.x("UPDATE signals SET status='closed', pnl=5.0, fill=2000.0, closed=? WHERE id=?", (now, rows[0]['id']))
old = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,fill) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ('XAUUSD', 'sell', 2000.0, 2003.0, 1994.0, 'closed', now - 900, -3.0, now - 300, 'ma_cross', 2000.0))
d = c.get('/api/trade/%d' % rows[0]['id'], headers=H).get_json()
T('GET /api/trade/<id> returns the why_taken lines', d and d.get('why_taken') and any('agreed' in x for x in d['why_taken']) and any('Planned prices' in x for x in d['why_taken']))
d2 = c.get('/api/trade/%d' % old, headers=H).get_json()
T('a trade from before R1 has no reason (empty list, nothing made up)', d2 is not None and d2.get('why_taken') == [])
j = c.get('/api/journal', headers=H).get_json(); by = {x['id']: x for x in j['rows']}
T('the journal rows carry a short why (empty for old trades)', by[rows[0]['id']]['why'].startswith('2 strategies agreed') and by[old]['why'] == '')
T('the journal numbers are unchanged', j['stats']['trades'] == 2 and j['stats']['net'] == 2.0)

# ---- 5. the page and the code are wired ----
here = os.path.join(HERE, '..'); page = open(os.path.join(here, 'static', 'index.html'), encoding='utf-8').read(); app_src = open(os.path.join(here, 'backend', 'app.py'), encoding='utf-8').read()
T('the page has the Why the bot took this trade block and the old-trade message', 'Why the bot took this trade' in page and 'before the bot started writing its reasons down' in page and 'whyBlock(d)' in page)
T('app.py saves the reason on both inserts', app_src.count('rsn.pack(s)') == 1 and app_src.count('uid,reason)') == 1 and app_src.count('uid,grp,reason)') == 1)
bad = [n for n, ok in R if not ok]; print('\n%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
