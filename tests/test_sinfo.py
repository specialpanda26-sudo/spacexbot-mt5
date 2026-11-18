"""Section A1 checks: readable strategy names + admin strategy list. Run: python tests/test_sinfo.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'sinfo_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import strategies as S, strategy_info as si, learn
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
C.get('/api/me', headers=A); C.get('/api/me', headers=U)

built = [f.__name__ for f in S.ALL if f.__module__ != 'backend.taught']       # taught strategies are exempt, they get a made-up name
T('every built-in strategy has a readable name and description (add a line to strategy_info.INFO when you add a strategy)', [n for n in built if n not in si.INFO] == [])
T('no stale line for a strategy that does not exist any more', [n for n in si.INFO if n not in [f.__name__ for f in S.ALL]] == [])
T('names fit a phone card (1-32 characters), descriptions one line (1-140)', all(0 < len(si.name(n)) <= 32 and 0 < len(si.desc(n)) <= 140 for n in si.INFO))
T('no two strategies share a name', len({si.name(n) for n in si.INFO}) == len(si.INFO))
T('names never show the underscore id', all('_' not in si.name(n) for n in si.INFO))
T('gold_scalp reads as Liquidity sweep scalp', si.name('gold_scalp') == 'Liquidity sweep scalp')
T('label turns a combined signal name into readable words', si.label('ma_cross+gold_scalp') == '20/50 EMA cross + Liquidity sweep scalp')
T('label of one strategy, of nothing, of None', si.label('gold_scalp') == 'Liquidity sweep scalp' and si.label('') == '' and si.label(None) == '')
T('an unknown (taught) strategy gets a name from its id and a taught description', si.name('my_cool_idea') == 'My cool idea' and 'taught' in si.desc('my_cool_idea'))

rows = si.listing(['gold_scalp', 'bb_reversion', 'zzz'], {'gold_scalp'}, {'bb_reversion'}, off={'bb_reversion'}, results={'gold_scalp': {'n': 4, 'wins': 3, 'pnl': 20.0, 'win_rate': 75.0}})
g, b, z = rows
T('listing: group comes from the TREND / REVERSION sets, else other', (g['group'], b['group'], z['group']) == ('trend', 'reversion', 'other'))
T('listing: a strategy that is switched off shows on = False', g['on'] is True and b['on'] is False)
T('listing: results are carried over, average worked out when missing', g['n'] == 4 and g['wins'] == 3 and g['win_rate'] == 75.0 and g['avg'] == 5.0 and g['pnl'] == 20.0)
T('listing: no trades yet = n 0 and empty results (not a fake 0%)', b['n'] == 0 and b['win_rate'] is None and b['avg'] is None and b['pnl'] is None)

# ---- the admin route
T('admin list needs a sign-in', C.get('/api/admin/strategies').status_code == 401)
T('a normal user cannot read it', C.get('/api/admin/strategies', headers=U).status_code == 403)
r = C.get('/api/admin/strategies', headers=A)
T('admin gets one row per registered strategy', r.status_code == 200 and [x['id'] for x in r.json] == [f.__name__ for f in S.ALL])
T('every row has name, desc, group, on and results fields', r.status_code == 200 and all({'id', 'name', 'desc', 'group', 'on', 'n', 'wins', 'win_rate', 'avg', 'pnl'} <= set(x) for x in r.json))
T('all on by default', all(x['on'] for x in r.json))
C.post('/api/admin/settings', json={'strategies_off': 'gold_scalp,ma_cross'}, headers=A)
rows = {x['id']: x for x in C.get('/api/admin/strategies', headers=A).json}
T('switching strategies off in settings shows in the list', not rows['gold_scalp']['on'] and not rows['ma_cross']['on'] and rows['pa_level']['on'])
for pnl in (10.0, 6.0, -4.0): learn.log('', 'closed', 'gold_scalp', 'XAUUSD', 'buy', pnl)
learn.log('u2', 'closed', 'gold_scalp+ma_cross', 'XAUUSD', 'sell', 2.0)
rows = {x['id']: x for x in C.get('/api/admin/strategies', headers=A).json}
gs = rows['gold_scalp']
T('results come from the closed trades of everyone: 4 trades, 3 wins, 75%, total 14, average 3.5', gs['n'] == 4 and gs['wins'] == 3 and gs['win_rate'] == 75.0 and gs['pnl'] == 14.0 and gs['avg'] == 3.5)
T('a trade fired by two strategies counts for both', rows['ma_cross']['n'] == 1 and rows['ma_cross']['pnl'] == 2.0)
T('a strategy with no trades has no results yet', rows['pa_level']['n'] == 0 and rows['pa_level']['win_rate'] is None)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
