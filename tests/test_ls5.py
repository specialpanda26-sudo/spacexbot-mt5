"""LS5 checks: tiny-account safety check. If even the smallest lot would lose more than X% of the balance at the stop, nothing is opened. No network.
Run: python tests/test_ls5.py   (last line: N checks, M failed)"""
import os, sys, types, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
_f = os.path.join(HERE, 'test_desktop.py')
D = types.ModuleType('D'); D.__file__ = _f
exec(compile(open(_f, encoding='utf-8').read().split('\nw = max(len(n)')[0], _f, 'exec'), D.__dict__)
from backend import store as st, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def lots(fb): return [o['lots'] for o in fb.orders]
def clear(): st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent')")
def single(bal, **kw):
    clear(); clock, fb, web, e, sf = D.rig(**kw); fb.acct['balance'] = float(bal); D.go(e, clock, 3); clear(); i = D.new_signal(risk=5.0); D.go(e, clock, 2); return fb, i
def group(bal, n=3):
    clear(); clock, fb, web, e, sf = D.rig(); fb.acct['balance'] = float(bal); D.go(e, clock, 3); clear()
    s = {'side': 'buy', 'entry': 2300.0, 'sl': 2295.0, 'tp': 2310.0, 'strategy': 't', 'score': 2}
    ids = burst.create('', 'XAUUSD', s, {'kind': 'quick', 'n': n, 'each': 0.5, 'giveback': 40, 'stake': 0}, 'test'); D.go(e, clock, 2); return fb, ids
def note(i): return str((D.sig(i) or {}).get('note') or '')

# the smallest lot here (0.01) loses about $5.10 at this stop
st.put('tiny_risk_pct', '10'); burst.save('', {'lot_mode': 'auto', 'lot': 0, 'max_lot': 100})
T('server default is 10 percent', burst.tiny_pct() == 10.0)
st.put('tiny_risk_pct', 'junk'); T('junk setting falls back to 10', burst.tiny_pct() == 10.0)
st.put('tiny_risk_pct', '500'); T('setting is clamped to 100', burst.tiny_pct() == 100.0)
st.put('tiny_risk_pct', '-3'); T('negative setting is clamped to 0 (off)', burst.tiny_pct() == 0.0)
st.put('tiny_risk_pct', '10')

fb, i = single(40); T('$40 account, smallest lot loses 12.8%: refused, nothing opened', lots(fb) == [])
T('the refusal says why', 'smallest lot' in note(i) or 'smallest lot' in str(D.sig(i)))
fb, i = single(120); T('$120 account, smallest lot loses 4.3%: trades', len(lots(fb)) == 1)
fb, ids = group(40); T('$40 account: the whole burst group is refused', lots(fb) == [])
fb, ids = group(100000); T('big account: the burst group opens (the check does not get in the way)', len(lots(fb)) == 3)
burst.save('', {'lot_mode': 'fixed', 'lot': 0.01})
fb, i = single(40); T('a fixed 0.01 lot does not bypass the check', lots(fb) == [])
burst.save('', {'lot_mode': 'smallest'})
fb, i = single(40); T('Smallest mode does not bypass the check', lots(fb) == [])
burst.save('', {'lot_mode': 'fixed', 'lot': 0.01, 'max_lot': 100})
st.put('tiny_risk_pct', '0'); fb, i = single(40); T('0 switches the check off', len(lots(fb)) == 1)
st.put('tiny_risk_pct', '15'); fb, i = single(40); T('raising X to 15 lets the $40 account through', len(lots(fb)) == 1)
st.put('tiny_risk_pct', '10')

here = os.path.join(HERE, '..')
src = open(os.path.join(here, 'ea', 'SpaceXBridge.mq5'), encoding='utf-8').read(); app = open(os.path.join(here, 'backend', 'app.py'), encoding='utf-8').read()
T('EA: both Execute and ExecuteBasket take tinyPct and check it', src.count('double tinyPct = 0') == 2 and src.count('LS5') >= 2 and 'RejectAll(ids, "even the smallest lot' in src and 'Reject(id, "even the smallest lot' in src)
T('EA: the poll passes tiny_pct to both', src.count('JStr(res, "tiny_pct")') == 2)
T('EA: version raised so the recompile is visible', '#property version "1.26"' in src)
T('server sends tiny_pct on the single and the burst payload', app.count("['tiny_pct'] = burst.tiny_pct()") == 2)
print('%d checks, %d failed' % (len(R), sum(1 for _, o in R if not o)))
sys.exit(1 if any(not o for _, o in R) else 0)
