"""Section A3 checks: admin switch 'may trade alone' per strategy. Run: python tests/test_solo.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'solo_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as appmod
from backend.app import app
from backend import brain, store as st, strategy_info as si, strategies as S
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
C.get('/api/me', headers=A); C.get('/api/me', headers=U)

# ---- the brain, with two fake strategies on a flat chart (candle range 1.0, so ATR is about 1)
M = [{'t': 1700000000 + i * 900, 'o': 100.0, 'h': 100.5, 'l': 99.5, 'c': 100.0, 'v': 1} for i in range(200)]
def mk(name, side, sl=98.5):
    def f(m, h): return {'side': side, 'sl': sl if side == 'buy' else 200 - sl, 'name': name}
    f.__name__ = name; return f
fa, fb, fs = mk('fa', 'buy'), mk('fb', 'buy'), mk('fs', 'sell')
def run(fns, **kw):
    old = brain.ALL; brain.ALL = fns
    try: return brain.evaluate(M, [], **kw)
    finally: brain.ALL = old
T('one strategy alone does not trade (2 must agree)', run([fa]) is None)
r = run([fa], solo=('fa',))
T('the same strategy trades alone once it is in the solo set', r and r['side'] == 'buy' and r['strategy'] == 'fa' and r['score'] == 1)
T('a solo switch on another strategy does not help this one', run([fa], solo=('fb',)) is None)
T('a strategy that is switched OFF never trades, solo or not', run([fa], solo=('fa',), off=('fa',)) is None)
T('two agreeing strategies still trade without any solo (nothing changed)', (run([fa, fb]) or {}).get('strategy') == 'fa+fb')
T('a solo buy against a normal sell is a tie: no trade (solo does not outvote)', run([fa, fs], solo=('fa',)) is None)
T('a solo buy wins when the other side has fewer votes', (run([fa, fb, fs], solo=('fa',)) or {}).get('side') == 'buy')
T('the stop rule still applies to a solo trade (stop wider than 3.5 ATR: no trade)', run([mk('fa', 'buy', sl=90.0)], solo=('fa',)) is None)
T('old positional calls still work (solo is the last, optional argument)', brain.evaluate(M, [], 2, 2.0, ()) is None)
hit = {'side': 'buy', 'sl': 98.5, 'name': 'fa'}; g = lambda m, h: hit; g.__name__ = 'fa'
old = brain.ALL; brain.ALL = [g]
try: brain.evaluate(M, [], solo=('fa',))
finally: brain.ALL = old
T("the strategy's own result is not changed by the switch", 'solo' not in hit)

# ---- the setting and the admin routes
T('the setting exists and is empty by default', 'strategies_solo' in st.DEFAULTS and st.get('strategies_solo') == '')
rows = C.get('/api/admin/strategies', headers=A).json
T('list: every row has a solo field and all are off by default', all('solo' in x for x in rows) and not any(x['solo'] for x in rows))
T('a normal user cannot change the setting', C.post('/api/admin/settings', json={'strategies_solo': 'ma_cross'}, headers=U).status_code == 403)
T('...and it stays empty', st.get('strategies_solo') == '')
r = C.post('/api/admin/settings', json={'strategies_solo': 'ma_cross,gold_scalp'}, headers=A)
T('admin saves the list', r.status_code == 200 and r.json['strategies_solo'] == 'ma_cross,gold_scalp')
rows = {x['id']: x for x in C.get('/api/admin/strategies', headers=A).json}
T('list shows solo only for the saved strategies', rows['ma_cross']['solo'] and rows['gold_scalp']['solo'] and not rows['pa_level']['solo'])
C.post('/api/admin/settings', json={'strategies_off': 'ma_cross'}, headers=A)
mc = {x['id']: x for x in C.get('/api/admin/strategies', headers=A).json}['ma_cross']
T('solo and on/off are independent: switching it off keeps its solo flag', mc['solo'] is True and mc['on'] is False)
C.post('/api/admin/settings', json={'strategies_off': ''}, headers=A)
T('listing() takes solo as a set', [x['solo'] for x in si.listing(['a', 'b'], set(), set(), solo={'b'})] == [False, True])

# ---- the bot's scan passes the setting to the brain
seen = {}
def fake_eval(m15, h1, min_conf=2, rr=2.0, off=(), *a, **kw): seen.update(kw); seen['off'] = off; return None
appmod.brain.evaluate = fake_eval
appmod.bars.get = lambda sym, tf, uid='': M
appmod.risk.global_gate = lambda *a, **k: (True, '')
appmod._last_scan.clear()
st.put('strategies_solo', 'ma_cross,gold_scalp')
appmod._scan('XAUUSD')
T('_scan passes the solo set to brain.evaluate', seen.get('solo') == {'ma_cross', 'gold_scalp'})
seen.clear(); appmod._last_scan.clear(); st.put('lastbar:XAUUSD', ''); st.put('strategies_solo', '')
appmod._scan('XAUUSD')
T('an empty setting gives an empty set', seen.get('solo') == set())

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
