"""LS6: the lot rules as one regression suite, so they cannot silently break. Covers the server payload for single trades and burst groups,
the Windows desktop app end to end (fake MT5), and the EA source. Rules: LS1 modes, 0.06 cap, LS3 balance tiers, LS4 perfect-setup step, LS5 tiny-account check.
No network. Run: python tests/test_lot_rules.py   (last line: N checks, M failed)   Mutation proof: python tests/mutate_lot_rules.py"""
import os, sys, types, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
_f = os.path.join(HERE, 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import store as st, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def clear(): st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")
def lots(fb): return [o['lots'] for o in fb.orders]
def mode(**kw): st.put('tiny_risk_pct', '10'); burst.save('', dict({'lot_mode': 'auto', 'lot': 0, 'max_lot': 0}, **kw))

# ---------- server payload: what the EA and the desktop app are told ----------
def poll(bal, score=2, kind=None):
    """One sync as the owner's EA at this balance; returns the signal or basket dict the server hands out."""
    clear(); clock, fb, web, e, sf = D.rig(); c = D.Client('http://t', 'ownerkey', web)
    acct = {'balance': float(bal), 'equity': float(bal), 'login': 7, 'demo': True, 'trade_allowed': True}
    c.sync(acct); clear()
    if kind:
        s = {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': score}
        burst.create('', 'XAUUSD', s, {'kind': kind, 'n': 3, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test')
    else:
        i = D.new_signal(risk=1.0); st.x('UPDATE signals SET score=? WHERE id=?', (score, i))
    r = c.sync(acct); return (r.get('basket') or r.get('signal') or {})
mode()
TIER = [(0, 0.06, 0.06), (20, 0.01, 0.02), (45, 0.02, 0.03), (80, 0.03, 0.04), (150, 0.04, 0.05), (300, 0.05, 0.06), (1000, 0.06, 0.06)]
for bal, base, perfect in TIER:
    T('single $%g: normal setup ceiling %g' % (bal, base), poll(bal, 2).get('max_lot') == base)
    T('single $%g: perfect setup ceiling %g' % (bal, perfect), poll(bal, 3).get('max_lot') == perfect)
    T('burst  $%g: quick group ceiling %g' % (bal, base), poll(bal, 2, 'quick').get('max_lot') == base)
    T('burst  $%g: BIG group ceiling %g' % (bal, perfect), poll(bal, 3, 'big').get('max_lot') == perfect)
T('nothing ever goes out above 0.06', all(poll(b, 9).get('max_lot', 0) <= 0.06 for b in (0, 20, 500, 5000, 1e6)))
for md, kw, want in (('smallest', {}, 0.06), ('fixed', {'lot': 0.01}, 0.06), ('typed cap', {'max_lot': 0.02}, 0.02)):
    mode(lot_mode='fixed' if md == 'fixed' else 'smallest' if md == 'smallest' else 'auto', **kw)
    T('%s mode: a perfect setup is never raised above %g' % (md, want), poll(20, 3).get('max_lot') == want and poll(20, 3, 'big').get('max_lot') == want)
mode(); T('payload carries tiny_pct (default 10) on both paths', poll(100, 2).get('tiny_pct') == 10 and poll(100, 2, 'quick').get('tiny_pct') == 10)
st.put('tiny_risk_pct', '25'); T('payload follows the setting', poll(100, 2).get('tiny_pct') == 25); st.put('tiny_risk_pct', '10')
mode(); T('payload still carries the soft flag and lot', 'max_lot_soft' in poll(100, 2) and 'lot' in poll(100, 2))

# ---------- Windows desktop app end to end (fake MT5; tick value lowered so risk sizing wants a lot above every ceiling) ----------
def single(bal, score=2, tv=0.05, sl=2295.0):
    clear(); clock, fb, web, e, sf = D.rig(); fb.acct['balance'] = float(bal); fb.info['XAUUSD']['tick_value'] = tv
    D.go(e, clock, 3); clear(); i = D.new_signal(sl=sl, risk=5.0); st.x('UPDATE signals SET score=? WHERE id=?', (score, i)); D.go(e, clock, 2); return fb, i
mode()
for bal, base, perfect in TIER[1:]:
    T('desktop $%g: trade sized %g (normal), %g (perfect)' % (bal, base, perfect), lots(single(bal, 2)[0]) == [base] and lots(single(bal, 3)[0]) == [perfect])
mode(lot_mode='smallest'); T('desktop: Smallest mode trades 0.01 even for a perfect setup', lots(single(300, 3)[0]) == [0.01])
mode(lot_mode='fixed', lot=0.03); T('desktop: Fixed 0.03 trades 0.03 even for a perfect setup', lots(single(300, 3)[0]) == [0.03])
mode(max_lot=0.02); T('desktop: a typed biggest lot 0.02 holds for a perfect setup', lots(single(300, 3)[0]) == [0.02])
# tiny-account check: 0.01 lot loses about $5.10 at this stop (tick value 1.0)
mode(); fb, i = single(40, 2, tv=1.0); T('desktop: $40 account, smallest lot loses 12.8%: refused', lots(fb) == [])
mode(lot_mode='fixed', lot=0.01); T('desktop: Fixed lot does not bypass the tiny-account check', lots(single(40, 2, tv=1.0)[0]) == [])
mode(lot_mode='smallest'); T('desktop: Smallest mode does not bypass the tiny-account check', lots(single(40, 2, tv=1.0)[0]) == [])
mode(lot_mode='fixed', lot=0.01); st.put('tiny_risk_pct', '0'); T('desktop: X = 0 switches the check off', lots(single(40, 2, tv=1.0)[0]) == [0.01]); st.put('tiny_risk_pct', '10')
def group(bal):
    clear(); clock, fb, web, e, sf = D.rig(); fb.acct['balance'] = float(bal); D.go(e, clock, 3); clear()
    burst.create('', 'XAUUSD', {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 3}, {'kind': 'big', 'n': 3, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test'); D.go(e, clock, 2); return fb
mode(lot_mode='fixed', lot=0.01)          # a fixed lot always fits the group sizing, so only the tiny-account check can refuse here
st.put('tiny_risk_pct', '0'); T('desktop: control, X = 0: the fixed-lot group opens on the $40 account', lots(group(40)) == [0.01] * 3)
st.put('tiny_risk_pct', '10'); T('desktop: a burst group on the $40 account is refused as a whole by the tiny-account check', lots(group(40)) == [])
T('desktop: the same group opens on a $400 account', lots(group(400)) == [0.01] * 3)

# ---------- EA source ----------
ea = open(os.path.join(ROOT, 'ea', 'SpaceXBridge.mq5'), encoding='utf-8').read()
app = open(os.path.join(ROOT, 'backend', 'app.py'), encoding='utf-8').read()
T('EA: single trade cuts to max_lot AFTER the stake sizing', ea.index('big stake not possible') < ea.index('lot cut to your biggest lot'))
T('EA: a fixed lot is lifted to the broker minimum in both Execute and ExecuteBasket', ea.count('MathMax(fixedLot, mn)') == 2)
T('EA: tiny check runs before any sizing in both Execute and ExecuteBasket', ea.index('LS5: tiny-account check:') < ea.index('double riskMoney') and ea.index('LS5: tiny-account check for the whole group') < ea.index('// riskPct is ONE entry'))
T('EA: both tiny checks are live (guarded by tinyPct > 0) and compare against the balance share', ea.count('if(tinyPct > 0)\n   {  // LS5: tiny-account check') == 2 and ea.count('minLoss > balT * tinyPct / 100.0 + 1e-9') == 2)
T('EA: the tiny check uses the broker smallest lot and rejects', ea.count('SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN) * (MathAbs(price - sl) / ts) * tv') == 2)
T('EA: poll passes max_lot, max_lot_soft and tiny_pct to both', ea.count('JStr(res, "tiny_pct")') == 2 and ea.count('JStr(res, "max_lot_soft")') == 2 and ea.count('JStr(res, "max_lot")') == 2)
T('EA: version 1.25', '#property version "1.25"' in ea)
T('server: both poll paths use strength_cap and send tiny_pct', app.count('burst.strength_cap(') == 2 and app.count("['tiny_pct'] = burst.tiny_pct(who)") == 2)
T('server: the tier table and the 0.06 cap are unchanged', burst.SAFE_MAX_LOT == 0.06 and burst.TIERS == ((30, 0.01), (60, 0.02), (100, 0.03), (200, 0.04), (400, 0.05)))
print('%d checks, %d failed' % (len(R), sum(1 for _, o in R if not o)))
sys.exit(1 if any(not o for _, o in R) else 0)
