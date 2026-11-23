"""Small account presets (backend/presets.py): writes the right values, respects the owner's ceilings, undo restores exactly,
no change for anyone who never taps, owner scope refused, demo first, rollback. Offline. Run: python tests/test_presets.py (last line: N checks, M failed)"""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'presets_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, limits, prefs, groupcap, burst, presets
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, B, O = 'dev-amy@x.com', 'dev-bob@x.com', 'dev-boss@x.com'
for u in (A, B): links.new_key(u)
def raw(uid): return presets._read_raw(uid)
def allkv(): return {r['k']: r['v'] for r in st.q('SELECT k,v FROM kv')}
def refused(fn, *a):
    try: fn(*a); return False
    except ValueError: return True

# ---- B never taps: everything of theirs and every global setting stays identical ----
links.set_risk(B, 1.5); prefs.save(B, {'min_conf': 3}); limits.save(B, max_open=4)
before_b = raw(B); g_keys = {k: v for k, v in allkv().items() if not k.endswith(A)}
# ---- A has own choices first, so undo has something real to restore ----
prefs.save(A, {'entries': 2, 'fast': True, 'min_conf': 2}); links.set_risk(A, 1.8); burst.save(A, {'on': True, 'quick_n': 7})
old_a = raw(A)

# ---- the right values ----
s = presets.apply(A, 20)
T('apply returns the active tier and can_undo', s['active'] == 20 and s['can_undo'])
p = prefs.get(A)
T('strategies: only the three, may trade alone, 1 must agree, 1 entry', p['strategies'] == ['jg_pullback', 'heikin_flip', 'fvg_retrace'] and p['alone'] is True and p['min_conf'] == 1 and p['entries'] == 1)
T('burst switch off and every-minute off', burst.get(A)['on'] is False and burst.get(A)['minute'] is False)
T('risk per trade is at most 1 percent', links.risk(A) <= 1.0)
T('one open position at a time and loss streak stop 2', limits.max_open(A) == 1 and limits.streak(A) == 2)
T('group loss limit on at 2.5 percent for the $20 tier', groupcap.get(A)['on'] is True and groupcap.get(A)['loss_pct'] == 2.5)
T('tiers differ only where meant: $10 -> 2.0, $30 -> 3.0', presets.TIERS[10]['loss_pct'] == 2.0 and presets.TIERS[30]['loss_pct'] == 3.0)
T('things the tap does not change stay as they were (fast scan)', prefs.get(A)['fast'] is True)

# ---- ceilings ----
st.put('max_open_ceiling', 1); st.put('max_losing_streak', 1); st.put('risk_pct', 0.5)
v = presets.values(30, A)
T('owner ceiling: entries and positions never above limits.ceiling()', v['entries'] <= limits.ceiling() and v['max_open'] <= limits.ceiling())
T("owner's stricter streak wins (1 beats 2)", limits.streak(A) == 1)
presets.apply(A, 30)
T("risk is cut to the owner's risk setting (0.5)", links.risk(A) == 0.5)
T('burst is never raised: nothing above burst.ceiling()', burst.get(A)['on'] is False and burst.get(A)['quick_n'] <= burst.ceiling())
st.put('max_open_ceiling', 6); st.put('max_losing_streak', 0); st.put('risk_pct', 1.0)
T('a second tap keeps the ORIGINAL snapshot (tier changes, undo target does not)', presets.status(A)['active'] == 30 and presets._snap(A)['prev'] == old_a)

# ---- undo restores exactly ----
presets.undo(A)
T('undo restores the exact raw values (prefs, limits, group, burst, risk)', raw(A) == old_a)
T('undo clears the active tier', presets.status(A)['active'] is None and not presets.status(A)['can_undo'])
T('undo twice is refused', refused(presets.undo, A))
presets.apply(B, 10); presets.undo(B)
T('undo also removes keys that did not exist before (B had no group/burst rows)', raw(B) == before_b)

# ---- no change for anyone who never taps ----
after = {k: v for k, v in allkv().items() if not k.endswith(A) and not k.endswith(B)}
T('global settings and other people untouched by taps', all(g_keys.get(k) == v for k, v in after.items() if k in g_keys and not k.startswith('preset:')) )
presets.apply(A, 10)
T('B (never tapped this time) is exactly as before while A is on a preset', raw(B) == before_b)
T('a person who never taps has no preset state and nothing active', presets.status(B)['active'] is None and presets._snap(B) is None)
presets.undo(A)

# ---- refusals ----
T('owner scope refused (would write global settings)', refused(presets.apply, '', 10) and refused(presets.apply, O, 10))
gl = {k: st.get(k) for k in ('max_trades_day', 'max_losing_streak', 'max_open', 'risk_pct', 'max_daily_loss_pct')}
refused(presets.apply, O, 10)
T('owner refusal leaves global settings alone', gl == {k: st.get(k) for k in gl})
T('a bad tier is refused', refused(presets.apply, A, 15) and refused(presets.apply, A, 'x') and refused(presets.apply, A, None))
st.x("UPDATE links SET mode='real' WHERE uid=?", (A,)); b4 = raw(A)
T('Real mode: refused, nothing changes (demo first)', refused(presets.apply, A, 10) and raw(A) == b4 and presets._snap(A) is None)
st.x("UPDATE links SET mode='demo' WHERE uid=?", (A,))

# ---- rollback when a save fails halfway ----
real = groupcap.save
def boom(*a, **k): raise ValueError('forced')
groupcap.save = boom; b4 = raw(A)
T('a failing save refuses the tap', refused(presets.apply, A, 10))
groupcap.save = real
T('and rolls everything back (nothing half-applied, no snapshot left)', raw(A) == b4 and presets._snap(A) is None)

# ---- S3: minimum-lot check ----
import time as _t
st.x("UPDATE users SET plan_until=? WHERE uid=?", (int(_t.time()) + 86400 * 30, A))
KEY = links.new_key(A); EH = {'X-EA-Key': KEY}
def candles(rng=2.0, n=40):
    t0 = int(_t.time()) - n * 900; return [[t0 + i * 900, 2000, 2000 + rng / 2, 2000 - rng / 2, 2000, 1] for i in range(n)]
GOLD = {'XAUUSD': {'vol_min': 0.01, 'tick_value': 1.0, 'tick_size': 0.01}}
def sync(bal, sym=None, bars=True):
    acct = {'balance': bal, 'equity': bal, 'open': 0, 'demo': True, 'allow_live': False, 'login': 1}
    if sym is not None: acct['sym'] = sym
    return c.post('/api/ea/sync', json={'account': acct, 'bars': {'XAUUSD': {'M15': candles()}} if bars else {}}, headers=EH)

T('clean_sym drops bad numbers, names and shapes', presets.clean_sym({'XAUUSD': {'vol_min': 0.01, 'tick_value': 1, 'tick_size': 0.01}, 'bad name': GOLD['XAUUSD'], 'X': {'vol_min': -1, 'tick_value': 1, 'tick_size': 1}, 'Y': {'vol_min': True, 'tick_value': 1, 'tick_size': 1}, 'Z': 5, 'W': {'vol_min': float('nan'), 'tick_value': 1, 'tick_size': 1}}).keys() == {'XAUUSD'})
T('clean_sym: not a dict gives nothing', presets.clean_sym(None) == {} and presets.clean_sym([1]) == {})
r = sync(1000)
a0 = st.acct(A)
T('OLD EA payload (no sym field): sync works exactly as before', r.status_code == 200 and 'sym' not in a0 and a0.get('balance') == 1000)
m = presets.min_lot(A, 20)
T('no min-lot facts: nothing is claimed, no warning, tap not blocked', m['known'] is False and not m['warn'] and not m['blocked'] and m['message'] == '')
presets.apply(A, 20); presets.undo(A)
T('new EA payload with sym is accepted and kept', sync(1000, GOLD).status_code == 200 and st.acct(A).get('sym') == GOLD)
T('garbage sym is dropped, the rest of the sync still works', sync(1000, {'XAUUSD': {'vol_min': 'x'}, 'q': 1}).status_code == 200 and 'sym' not in st.acct(A) and st.acct(A).get('balance') == 1000)
sync(1000, GOLD)
m = presets.min_lot(A, 20); row = m['rows'][0]
T('worst case = min lot x (3.5 ATR / tick size) x tick value (gold, range 2 -> 7 dollars)', abs(row['worst_usd'] - 7.0) < 0.2 and abs(row['best_usd'] - 1.0) < 0.1 and row['min_lot'] == 0.01)
T('1000 balance: limit 10 dollars, no warning', m['known'] and m['risk_usd'] == 10.0 and not m['warn'] and m['message'] == '')
sync(100, GOLD); m = presets.min_lot(A, 20)
T('100 balance: limit 1 dollar, worst case 7 -> the plain warning shows, but the tap is allowed (some setups still fit)', m['warn'] and m['message'] == presets.WORDS and not m['blocked'] and presets.status(A)['minlot']['20']['warn'])
sync(50, GOLD); b4 = raw(A)
T('50 balance: even the smallest stop is too big -> blocked with the plain message', presets.min_lot(A, 20)['blocked'] and 'cent account or a demo' in presets.WORDS)
try: presets.apply(A, 20); ok = False
except ValueError as e: ok = str(e) == presets.WORDS
T('blocked tap is refused with that message and NOTHING changes', ok and raw(A) == b4 and presets._snap(A) is None)
sync(1000, GOLD)
T('balance grows: the check clears and the tap works again', presets.apply(A, 20)['active'] == 20); presets.undo(A)
from backend import bars as _bars
_bars.merge('EURUSD', 'M15', candles(), uid=A); st.set_acct({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'sym': dict(GOLD, EURUSD={'vol_min': 1.0, 'tick_value': 1.0, 'tick_size': 0.00001})}, A)
T('min-lot check only looks at markets the owner allows (EURUSD is not in Symbols, so it is ignored)', [x['symbol'] for x in presets.min_lot(A, 20)['rows']] == ['XAUUSD'])

n = len(R); bad = [x for x, ok in R if not ok]
print('%d checks, %d failed' % (n, len(bad)))
for f in glob.glob(DB + '*'): os.remove(f)
sys.exit(1 if bad else 0)
