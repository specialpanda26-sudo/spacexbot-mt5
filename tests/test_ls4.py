"""LS4 checks: a perfect setup gets one lot step above the base ceiling (automatic mode only), never above the person's biggest lot. No network.
Run: python tests/test_ls4.py   (last line: N checks, M failed)"""
import os, sys, json, tempfile
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_ls4.db'), BASE_URL='http://t')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from backend.app import app
from backend import store as st, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def bal(b): st.put('burst:', '{}'); burst._balance = lambda uid, _b=b: float(_b)
def mode(**kw): st.put('burst:', json.dumps(kw))

bal(20)
T('normal setup at $20 keeps the base 0.01', burst.strength_cap('', False) == 0.01)
T('perfect setup at $20 gets one step: 0.02', burst.strength_cap('', True) == 0.02)
bal(45); T('perfect at $45: 0.02 -> 0.03', burst.strength_cap('', True) == 0.03 and burst.strength_cap('', False) == 0.02)
bal(150); T('perfect at $150: 0.04 -> 0.05', burst.strength_cap('', True) == 0.05)
bal(300); T('perfect at $300: 0.05 -> 0.06 (the cap)', burst.strength_cap('', True) == 0.06)
bal(1000); T('perfect at $1000 never passes 0.06', burst.strength_cap('', True) == 0.06 and burst.strength_cap('', False) == 0.06)
bal(0); T('unknown balance: no step past the cap', burst.strength_cap('', True) == 0.06)
bal(20); mode(lot_mode='smallest'); T('smallest mode is never raised', burst.strength_cap('', True) == burst.eff_max_lot(''))
mode(lot_mode='fixed', lot=0.01, max_lot=0.03); T('fixed mode is never raised', burst.strength_cap('', True) == 0.03)
mode(lot_mode='auto', max_lot=0.02); T('a typed biggest lot is never raised', burst.strength_cap('', True) == 0.02)
mode(lot_mode='auto', max_lot=0.02); T('the cap result never exceeds top_lot', burst.strength_cap('', True) <= burst.top_lot(''))
T('is_perfect follows burst_big_score', burst.is_perfect(burst.big_score()) and not burst.is_perfect(burst.big_score() - 1) and not burst.is_perfect(None) and not burst.is_perfect('x'))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend', 'app.py'), encoding='utf-8').read()
T('both poll paths use strength_cap and keep max_lot_soft', src.count('burst.strength_cap(') == 2 and src.count("max_lot_soft'] = burst.max_lot_soft(who)") == 2)
T('the single-signal query now reads the score', "risk_pct,score FROM signals WHERE status='pending'" in src)
print('%d checks, %d failed' % (len(R), sum(1 for _, o in R if not o)))
sys.exit(1 if any(not o for _, o in R) else 0)
