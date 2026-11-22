"""GL1 tests: the group LOSS limit on Deriv. Fake Deriv session, no network. Run: python tests/test_gl1.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_gl1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, cycle, groupcap, risk, deriv_group as dg, deriv
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
NOW = 1767225600 + 3600 * 10
ACCT = {'id': 'VRTC1', 'demo': True, 'currency': 'USD'}; U = 'u1'
class Fake:
    def __init__(s, prof, spot=2000.0): s.prof, s.spot, s.sold, s.fail, s.log = dict(prof), spot, set(), set(), []
    def ask(s, m):
        s.log.append(m)
        if 'proposal_open_contract' in m:
            c = m['contract_id']; return {'proposal_open_contract': {'is_sold': 1 if c in s.sold else 0, 'profit': s.prof.get(c, 0), 'current_spot': s.spot}}
        if 'sell' in m:
            c = m['sell']
            if c in s.fail: return {'error': {'message': 'nope'}}
            s.sold.add(c); return {'sell': {'contract_id': c, 'sold_for': 1}}
        return {'error': {'message': 'x'}}
    def sells(s): return [m['sell'] for m in s.log if 'sell' in m]
def wipe():
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'cyc%' OR k LIKE 'bg:%' OR k LIKE 'gcap:%' OR k LIKE 'cycle:%' OR k LIKE 'closedby:%' OR k LIKE 'pref:%'")
def group(n=3, tgt=0.0, loss=2.0, bal0=1000.0, status='open', ticket0=101):
    ids = []; sql = "INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason,ticket,broker,lots) VALUES('XAUUSD','buy',2000,1990,2020,0.33,'strat',3,?,?,?,?,'why',?,'Deriv',1.0)"
    for i in range(n): ids.append(st.x(sql, (status, NOW - 60, U, ids[0] if ids else None, str(ticket0 + i))))
    st.x('UPDATE signals SET grp=? WHERE id=?', (ids[0], ids[0]))
    m = {'k': 'multi', 'n': n, 'each': 0, 'gb': 0, 'tgt': tgt, 'loss': loss, 't': NOW - 60}
    if bal0: m['bal0'] = bal0
    st.put('bg:%d' % ids[0], json.dumps(m)); return ids
def row(i): return st.q('SELECT * FROM signals WHERE id=?', (i,), True)
G0, S0, W0, D0 = risk.global_gate, risk.symbol_gate, risk.weekend_skip, risk.weekday_skip
risk.global_gate = lambda *a, **k: (True, 'ok'); risk.symbol_gate = lambda *a, **k: (True, 'ok'); risk.weekend_skip = lambda *a, **k: False; risk.weekday_skip = lambda *a, **k: False

wipe(); ids = group(); f = Fake({101: -7, 102: -7, 103: -7}); r = dg.check(f, U, ACCT, NOW)          # limit = 2% of 1000 = 20; total -21
T('loss limit reached: every open entry is sold at market', sorted(f.sells()) == [101, 102, 103] and all(m.get('price') == 0 for m in f.log if 'sell' in m))
T('each entry is closed with its own loss and closedby basket', [row(i)['pnl'] for i in ids] == [-7, -7, -7] and all(row(i)['status'] == 'closed' and st.get('closedby:%d' % i) == 'basket' for i in ids))
T('the result lists the group with its total loss and no next group', len(r) == 1 and r[0]['total'] == -21 and r[0]['next'] is None)
wipe(); ids = group(); f = Fake({101: -7, 102: -6.5, 103: -6}); r = dg.check(f, U, ACCT, NOW)          # -19.5, inside the limit
T('inside the limit: nothing is sold', r == [] and f.sells() == [] and all(row(i)['status'] == 'open' for i in ids))
wipe(); ids = group(); st.x("UPDATE signals SET status='closed',pnl=-10 WHERE id=?", (ids[0],)); f = Fake({102: -5.5, 103: -5.5}); r = dg.check(f, U, ACCT, NOW)          # -10 booked + -11 live
T('a loss already booked by one entry counts toward the limit', sorted(f.sells()) == [102, 103] and bool(r) and r[0]['total'] == -21)
wipe(); ids = group(bal0=None); f = Fake({101: -50, 102: -50, 103: -50}); r = dg.check(f, U, ACCT, NOW)
T('no recorded balance: the limit is not guessed, the group is left alone', r == [] and f.log == [])
wipe(); ids = group(loss=0); f = Fake({101: -50, 102: -50, 103: -50})
T('loss limit 0 (off): nothing happens', dg.check(f, U, ACCT, NOW) == [] and f.log == [])
wipe(); ids = group(tgt=0.7); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
T('the profit target still works with a loss limit set', sorted(f.sells()) == [101, 102, 103] and bool(r) and r[0]['total'] == 0.8)
wipe(); ids = group(tgt=0.7); f = Fake({101: -1, 102: 0, 103: 0}); T('between the target and the limit: nothing is sold', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])
wipe(); ids = group(); f = Fake({101: -7, 102: -7, 103: -7}); f.fail = {102}; r = dg.check(f, U, ACCT, NOW)
T('a refused sell leaves that entry open, the others are closed, nothing restarts', row(ids[1])['status'] == 'open' and row(ids[0])['status'] == 'closed' and row(ids[2])['status'] == 'closed' and bool(r) and r[0]['next'] is None)
wipe(); ids = group(); groupcap.save(U, {'on': True, 'target_usd': 0.7}); cycle.save(U, {'on': True, 'max_per_day': 10}); st.put('pref:%s' % U, json.dumps({'entries': 3}))
f = Fake({101: -7, 102: -7, 103: -7}); r = dg.check(f, U, ACCT, NOW)
T('with the cycle on, a loss never starts the next group', bool(r) and r[0]['next'] is None and st.q("SELECT COUNT(*) n FROM signals WHERE status='pending'", (), True)['n'] == 0)

# the balance is recorded when the first entry really opens
wipe(); ids = group(n=2, loss=2.0, bal0=None, status='pending', ticket0=0); st.x("UPDATE signals SET ticket=NULL WHERE grp=?", (ids[0],))
T('note_open_balance saves the balance once', dg.note_open_balance(ids[0], 1000) is True and dg.note_open_balance(ids[0], 900) is False and json.loads(st.get('bg:%d' % ids[0]))['bal0'] == 1000)
T('a missing group or a bad balance is refused', dg.note_open_balance(999999, 1000) is False and dg.note_open_balance(ids[0], 'x') is False)
wipe(); ids = group(n=2, loss=2.0, bal0=None, status='pending'); st.x("UPDATE signals SET ticket=NULL,created=?,uid=? WHERE grp=?", (NOW - 10, U, ids[0]))
deriv._place = lambda sess, s, bal, cur: ('open', {'contract_id': 500 + s['id'], 'stake': 1.0, 'mult': 100}); deriv._bot = lambda uid: True; deriv._resnap = lambda *a, **k: None; deriv._report = lambda *a, **k: None
deriv._trade_one(None, U, ACCT, 1000.0, NOW); deriv._trade_one(None, U, ACCT, 990.0, NOW)
T('opening the group on Deriv records the balance from BEFORE the first buy', json.loads(st.get('bg:%d' % ids[0]))['bal0'] == 1000.0 and all(row(i)['status'] == 'open' for i in ids))
s = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the group card no longer says only the MT5 bridge closes the group', 'The MT5 bridge closes the group; phone-only' not in s and 'On Deriv the server closes the group' in s)
import re, shutil, subprocess
if shutil.which('node'):
    ok = True
    for body in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.S):
        if body.strip() and subprocess.run(['node', '-e', 'new Function(require("fs").readFileSync(0,"utf8"))'], input=body, capture_output=True, text=True).returncode: ok = False
    T('every script in the page still parses (a stray apostrophe in the new card text would break the whole page)', ok)
risk.global_gate, risk.symbol_gate, risk.weekend_skip, risk.weekday_skip = G0, S0, W0, D0
if os.path.exists(DB): os.remove(DB)
bad = [n for n, ok in R if not ok]; print('%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
