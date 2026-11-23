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

n = len(R); bad = [x for x, ok in R if not ok]
print('%d checks, %d failed' % (n, len(bad)))
for f in glob.glob(DB + '*'): os.remove(f)
sys.exit(1 if bad else 0)
