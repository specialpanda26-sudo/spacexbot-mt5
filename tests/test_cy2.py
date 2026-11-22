"""CY2 tests: Deriv group close + auto-cycle. Fake Deriv session, no network. Run: python tests/test_cy2.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_cy2_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, cycle, groupcap, risk, links, deriv_group as dg, deriv
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
NOW = 1767225600 + 3600 * 10          # a Thursday 10:00 UTC, a normal trading hour
ACCT = {'id': 'VRTC1', 'demo': True, 'currency': 'USD'}
U = 'u1'

class Fake:
    """Stands in for deriv.Session. prof = live profit per contract id, sold = ids already sold, fail = ids whose sell is refused."""
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
    st.set_acct({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'allow_live': False, 'src': 'deriv'}, U)

def group(uid=U, n=3, tgt=0.7, kind='multi', side='buy', entry=2000.0, sl=1990.0, tp=2020.0, status='open', first_id=None):
    """n members of one group, tickets 101.., and the group facts. -> list of signal ids."""
    ids = []; sql = "INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason,ticket,broker,lots) VALUES('XAUUSD',?,?,?,?,0.33,'strat',3,?,?,?,?,'why',?,'Deriv',1.0)"
    for i in range(n):
        ids.append(st.x(sql, (side, entry, sl, tp, status, NOW - 60, uid or None, ids[0] if ids else None, str(101 + i + (first_id or 0)))))
    st.x('UPDATE signals SET grp=? WHERE id=?', (ids[0], ids[0]))
    st.put('bg:%d' % ids[0], json.dumps({'k': kind, 'n': n, 'each': 0, 'gb': 0, 'tgt': tgt, 'loss': 0, 't': NOW - 60}))
    return ids

def row(i): return st.q('SELECT * FROM signals WHERE id=?', (i,), True)
def allow_gates():
    risk.global_gate = lambda *a, **k: (True, 'ok'); risk.symbol_gate = lambda *a, **k: (True, 'ok'); risk.weekend_skip = lambda *a, **k: False; risk.weekday_skip = lambda *a, **k: False
G0, S0, W0, D0 = risk.global_gate, risk.symbol_gate, risk.weekend_skip, risk.weekday_skip
def real_gates(): risk.global_gate, risk.symbol_gate, risk.weekend_skip, risk.weekday_skip = G0, S0, W0, D0
def cyc_on(n=3, tgt=0.7, cap=10, uid=U): groupcap.save(uid, {'on': True, 'target_usd': tgt}); cycle.save(uid, {'on': True, 'max_per_day': cap}); st.put('pref:%s' % uid, json.dumps({'entries': n}))

# 1 below the target: nothing is sold
wipe(); allow_gates(); ids = group(); f = Fake({101: 0.2, 102: 0.2, 103: 0.2})          # total 0.60 < 0.70
T('below the group target: nothing is sold and nothing changes', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [] and all(row(i)['status'] == 'open' for i in ids))

# 2 target reached: every open entry is sold at market
wipe(); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2})          # total 0.80 >= 0.70
r = dg.check(f, U, ACCT, NOW)
T('target reached: all three entries are sold, once each, at market price 0', sorted(f.sells()) == [101, 102, 103] and all(m.get('price') == 0 for m in f.log if 'sell' in m))
T('each entry is recorded closed with its own profit and closedby basket', all(row(i)['status'] == 'closed' and row(i)['closed'] == NOW for i in ids) and [row(i)['pnl'] for i in ids] == [0.3, 0.3, 0.2] and all(st.get('closedby:%d' % i) == 'basket' for i in ids))
T('the result lists the group, its total, and no next group while the cycle is off', len(r) == 1 and r[0]['grp'] == ids[0] and r[0]['total'] == 0.8 and r[0]['next'] is None)
T('a second look finds nothing left to sell', dg.check(f, U, ACCT, NOW) == [] and len(f.sells()) == 3)

# 3 profit already booked by a member counts toward the target
wipe(); ids = group(); st.x("UPDATE signals SET status='closed',pnl=0.5,closed=? WHERE id=?", (NOW - 5, ids[2]))
f = Fake({101: 0.1, 102: 0.15})          # 0.5 booked + 0.25 live = 0.75
dg.check(f, U, ACCT, NOW); T('profit booked by a member that already closed counts toward the total', sorted(f.sells()) == [101, 102])
wipe(); ids = group(); st.x("UPDATE signals SET status='closed',pnl=0.5,closed=? WHERE id=?", (NOW - 5, ids[2]))
f = Fake({101: 0.05, 102: 0.05}); dg.check(f, U, ACCT, NOW); T('...and 0.60 in total is still below 0.70', f.sells() == [])

# 4 waiting rules
wipe(); ids = group(); st.x("UPDATE signals SET status='pending',ticket=NULL WHERE id=?", (ids[2],)); f = Fake({101: 5, 102: 5})
T('an entry still pending: the group is left alone', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])
wipe(); ids = group(); st.x("UPDATE signals SET status='sent' WHERE id=?", (ids[2],)); f = Fake({101: 5, 102: 5})
T('an unconfirmed buy (sent): the group is left alone', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])
wipe(); ids = group(); f = Fake({101: 5, 102: 5, 103: 5}); f.sold.add(102)
T('an entry Deriv already sold is left for _track first: nothing is sold', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])
wipe(); ids = group(tgt=0); f = Fake({101: 5, 102: 5, 103: 5})
T('a group with no target is not touched', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])
wipe(); ids = group(n=1, tgt=0.7); st.x("DELETE FROM kv WHERE k LIKE 'bg:%'"); f = Fake({101: 5})
T('a trade that is not a marked group is not touched', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])
wipe(); ids = group(uid='other'); f = Fake({101: 5, 102: 5, 103: 5})
T("another person's group is never touched", dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])
wipe(); ids = group(); st.x("UPDATE signals SET broker='MT5' WHERE grp=?", (ids[0],)); f = Fake({101: 5, 102: 5, 103: 5})
T('a group that was not opened on Deriv is not touched', dg.check(f, U, ACCT, NOW) == [] and f.sells() == [])

# 5 a refused sell
st.put('max_open', '6'); wipe(); allow_gates(); cyc_on(); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.3}); f.fail.add(102); r = dg.check(f, U, ACCT, NOW)
T('one sell refused: the others are closed, that one stays open', [row(i)['status'] for i in ids] == ['closed', 'open', 'closed'])
T('...and a half-closed group never starts the next one', r[0]['next'] is None and len(st.q("SELECT id FROM signals WHERE status='pending'")) == 0); st.put('max_open', '3')
f2 = Fake({102: 0.1}); r = dg.check(f2, U, ACCT, NOW + 60)
T('the next round counts the booked profit and finds the group', len(r) == 1 and r[0]['grp'] == ids[0]); T('...after 0.6 booked and 0.1 live (0.70) it is sold', f2.sells() == [102] and row(ids[1])['status'] == 'closed')

# 6 the cycle
wipe(); allow_gates(); cyc_on(); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}, spot=2005.0); r = dg.check(f, U, ACCT, NOW)
new = r[0]['next']; rows = [row(i) for i in new] if new else []
T('cycle on: a new group of the same size is queued as pending entries', new and len(new) == 3 and all(x['status'] == 'pending' for x in rows))
T('...same symbol and side, uid kept, one new group id', all(x['symbol'] == 'XAUUSD' and x['side'] == 'buy' and x['uid'] == U for x in rows) and {x['grp'] for x in rows} == {new[0]} and new[0] not in ids)
T('...stop and target keep their distances (10 and 20) around the current price 2005', all(x['entry'] == 2005.0 and x['sl'] == 1995.0 and x['tp'] == 2025.0 for x in rows))
T('...risk is shared across the entries like a normal group, strategy and reason copied', all(x['risk_pct'] == round(float(links.risk(U)) / 3, 4) for x in rows) and all(x['strategy'] == 'strat' and x['reason'] == 'why' for x in rows))
m = json.loads(st.get('bg:%d' % new[0])); T('...the new group is marked with the same group target', m['k'] == 'multi' and m['n'] == 3 and m['tgt'] == 0.7)
T('...the day counter went up and the link to the old group is saved', dg.used_today(U, NOW) == 1 and st.get('cyc_from:%d' % new[0]) == str(ids[0]))
wipe(); allow_gates(); cyc_on(); ids = group(side='sell', entry=2000.0, sl=2010.0, tp=1980.0); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}, spot=2005.0); r = dg.check(f, U, ACCT, NOW); rows = [row(i) for i in r[0]['next']]
T('a sell group mirrors: stop above, target below the current price', all(x['side'] == 'sell' and x['sl'] == 2015.0 and x['tp'] == 1985.0 for x in rows))

wipe(); allow_gates(); groupcap.save(U, {'on': True, 'target_usd': 0.7}); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
T('cycle off: the group is closed at its target but no new group is opened', r[0]['next'] is None and not st.q("SELECT id FROM signals WHERE status='pending'"))

wipe(); allow_gates(); cyc_on(); ids = group(kind='quick'); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
T('a burst group is closed at its target but never cycled', r[0]['next'] is None)

wipe(); allow_gates(); cyc_on(); ids = group()
st.x("UPDATE signals SET status='closed',pnl=-0.9,closed=? WHERE id=?", (NOW - 9, ids[0])); f = Fake({102: 0.9, 103: 0.9}); r = dg.check(f, U, ACCT, NOW)
T('a member that booked a loss earlier does not stop the cycle when the group total is still above target', r and r[0]['total'] == 0.9 and r[0]['next'] is not None)
wipe(); allow_gates(); cyc_on(); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); orig = f.ask
def slip(m, o=orig):
    d = o(m)
    if 'proposal_open_contract' in m and m['contract_id'] in f.sold: d['proposal_open_contract']['profit'] = -0.5          # the market moved while selling
    return d
f.ask = slip; r = dg.check(f, U, ACCT, NOW)
T('sold into a loss (price moved while selling): no next group', r[0]['total'] < 0 and r[0]['next'] is None)

# 7 the daily limit
wipe(); allow_gates(); cyc_on(cap=2); ids = group(); NN = NOW; made = 0
for k in range(4):
    f = Fake({}); opn = st.q("SELECT ticket FROM signals WHERE status='open' AND uid=?", (U,)); f.prof = {int(x['ticket']): 0.3 for x in opn}
    r = dg.check(f, U, ACCT, NN + k)
    if not r or not r[0]['next']: break
    made += 1
    for i in r[0]['next']: st.x("UPDATE signals SET status='open',ticket=?,broker='Deriv' WHERE id=?", (str(500 + k * 10 + i), i))
T('the daily limit stops the cycle after 2 new groups', made == 2 and dg.used_today(U, NOW) == 2)
T('...and says why in plain words', 'daily limit of 2' in dg.why(U))
T('...a new day starts the count again', dg.used_today(U, NOW + 86400) == 0)

# 8 the risk gates still apply (each stub below returns False; the new group must then not be opened)
for name, why_ in (('global_gate', 'daily loss limit hit'), ('symbol_gate', 'news lock')):
    wipe(); allow_gates(); cyc_on(); setattr(risk, name, lambda *a, w=why_, **k: (False, w)); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
    T('%s says no: the group closes but no new group opens' % name, r[0]['next'] is None and not st.q("SELECT id FROM signals WHERE status='pending'"))
    T('...and the reason is shown (%s)' % why_, why_ in dg.why(U))
wipe(); allow_gates(); cyc_on(); risk.weekend_skip = lambda *a, **k: True; ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
T('the weekend rule says no: no new group', r[0]['next'] is None and 'weekend' in dg.why(U))
wipe(); allow_gates(); cyc_on(); risk.weekday_skip = lambda *a, **k: True; ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
T('the Bitcoin weekday rule says no: no new group', r[0]['next'] is None)
wipe(); allow_gates(); cyc_on(); st.put('max_open', '2'); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
T('not enough room for 3 entries (limit 2): no new group', r[0]['next'] is None and 'room' in dg.why(U)); st.put('max_open', '3')
wipe(); allow_gates(); cyc_on(); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); f.spot = None; r = dg.check(f, U, ACCT, NOW)
T('no price from Deriv: no new group', r[0]['next'] is None and 'price' in dg.why(U))

# 9 the real gates (not stubbed): the bot is off for this uid, so the real global_gate refuses
wipe(); real_gates(); cyc_on(); ids = group(); f = Fake({101: 0.3, 102: 0.3, 103: 0.2}); r = dg.check(f, U, ACCT, NOW)
T('with the real risk gates and the bot off, the group closes but nothing new opens', r[0]['next'] is None and 'bot off' in dg.why(U))

# 10 wired into the Deriv round
src = open(os.path.join(ROOT, 'backend', 'deriv.py')).read()
T('deriv._run_once calls deriv_group.check after _track and before the trade step', 'deriv_group.check(sess, uid, acct, now)' in src and src.index("'[deriv] track failed'") < src.index('deriv_group.check(sess, uid, acct, now)') < src.index('_trade(sess, uid, acct, bal, now)'))

bad_ = [n for n, ok in R if not ok]
print('\n%d passed, %d failed' % (len(R) - len(bad_), len(bad_)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_ else 0)
