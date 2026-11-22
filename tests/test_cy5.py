"""CY5 tests: Binance group close, group loss limit, auto-cycle. Fake Binance (no network). Run: python tests/test_cy5.py"""
import os, sys, json, time, glob
from decimal import Decimal
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_cy5_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='BTCUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, cycle, groupcap, risk, deriv_group as dg, binance_bot as bb, binance_trade as bt, binance_group as bg
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
NOW = 1767225600 + 3600 * 10; U = 'u1'
PX = {'BTCUSDT': 100.0}; SOLD = []; FAIL = set()
bb._price = lambda p, http: PX.get(p)
def fake_close(key, secret, symbol, qty, cid, http=None, now_ms=None):
    i = int(cid.split('-')[1])
    if i in FAIL: return {'ok': False, 'msg': 'Binance is not answering right now. Try again in a minute.'}
    SOLD.append(i); q = Decimal(qty) * Decimal(str(PX[symbol])); return {'ok': True, 'quote': q, 'fee_quote': Decimal(0), 'avg': Decimal(str(PX[symbol]))}
bt.close_long = fake_close
G0, S0, W0, D0 = risk.global_gate, risk.symbol_gate, risk.weekend_skip, risk.weekday_skip
risk.global_gate = lambda *a, **k: (True, 'ok'); risk.symbol_gate = lambda *a, **k: (True, 'ok'); risk.weekend_skip = lambda *a, **k: False; risk.weekday_skip = lambda *a, **k: False
def wipe():
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'cyc%' OR k LIKE 'bg:%' OR k LIKE 'gcap:%' OR k LIKE 'cycle:%' OR k LIKE 'closedby:%' OR k LIKE 'bnpos:%' OR k LIKE 'pref:%'"); SOLD.clear(); FAIL.clear(); PX['BTCUSDT'] = 100.0
def group(n=3, tgt=0.0, loss=0.0, bal0=0.0, status='open'):
    ids = []; sql = "INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason,ticket,broker,lots) VALUES('BTCUSD','buy',100,90,120,0.33,'strat',3,?,?,?,?,'why',?,'Binance',1.0)"
    for i in range(n):
        ids.append(st.x(sql, (status, NOW - 60, U, ids[0] if ids else None, str(500 + i))))
        st.put('bnpos:%d' % ids[-1], json.dumps({'pair': 'BTCUSDT', 'qty': '1', 'cost': '100', 'fee_q': '0'}))          # each leg: 1 coin bought for 100
    st.x('UPDATE signals SET grp=? WHERE id=?', (ids[0], ids[0]))
    m = {'k': 'multi', 'n': n, 'each': 0, 'gb': 0, 'tgt': tgt, 'loss': loss, 't': NOW - 60}
    if bal0: m['bal0'] = bal0
    st.put('bg:%d' % ids[0], json.dumps(m)); return ids
def row(i): return st.q('SELECT * FROM signals WHERE id=?', (i,), True)
def chk(**k): return bg.check(U, 'K', 'S', None, NOW, **k)

wipe(); ids = group(tgt=0.7); PX['BTCUSDT'] = 100.4          # each leg: 100.4 x 0.999 - 100 = +0.2996; three legs = +0.90
r = chk()
T('target reached: every open leg is sold and closed with closedby basket', sorted(SOLD) == sorted(ids) and all(row(i)['status'] == 'closed' and st.get('closedby:%d' % i) == 'basket' for i in ids))
T('the result lists the group with its total and no next group (cycle off)', len(r) == 1 and r[0]['total'] > 0.7 and r[0]['next'] is None)
wipe(); ids = group(tgt=0.7); PX['BTCUSDT'] = 100.2          # +0.1002 x 3 = +0.30
T('below the target: nothing is sold', chk() == [] and SOLD == [] and all(row(i)['status'] == 'open' for i in ids))
wipe(); ids = group(loss=2.0, bal0=1000.0); PX['BTCUSDT'] = 92.0          # limit 20; each leg about -8.09, three = -24
r = chk()
T('loss limit reached: every leg sold, total is a loss, no next group', sorted(SOLD) == sorted(ids) and r and r[0]['total'] < -20 and r[0]['next'] is None)
wipe(); ids = group(loss=2.0, bal0=1000.0); PX['BTCUSDT'] = 94.0          # about -6.1 x 3 = -18.3, inside the limit
T('inside the loss limit: left alone', chk() == [] and SOLD == [])
wipe(); ids = group(loss=2.0, bal0=0); PX['BTCUSDT'] = 50.0
T('no saved balance: the limit is not guessed', chk() == [] and SOLD == [])
wipe(); ids = group(tgt=0.0, loss=0.0); PX['BTCUSDT'] = 500.0
T('no target and no limit: nothing happens', chk() == [] and SOLD == [])
wipe(); ids = group(tgt=0.7); st.x("UPDATE signals SET status='closed',pnl=0.5 WHERE id=?", (ids[0],)); PX['BTCUSDT'] = 100.3          # 0.5 booked + 2 x 0.1997
r = chk()
T('a profit already booked by one leg counts toward the target', sorted(SOLD) == sorted(ids[1:]) and bool(r) and r[0]['total'] > 0.7)
for bad in ('pending', 'sent', 'closing'):
    wipe(); ids = group(tgt=0.7); st.x("UPDATE signals SET status=? WHERE id=?", (bad, ids[1])); PX['BTCUSDT'] = 105.0
    T('a %s leg: the group is skipped, no guess' % bad, chk() == [] and SOLD == [])
wipe(); ids = group(tgt=0.7); PX['BTCUSDT'] = None
T('price cannot be read: skipped', chk() == [] and SOLD == [])
wipe(); ids = group(tgt=0.7); PX['BTCUSDT'] = 105.0; FAIL.add(ids[1]); r = chk()
T('one sell fails: it goes back to open, the others are closed, no next group', row(ids[1])['status'] == 'open' and row(ids[0])['status'] == 'closed' and row(ids[2])['status'] == 'closed' and r[0]['next'] is None)
FAIL.clear(); r = chk()
T('next round: the leg left open is sold and the group is finished', row(ids[1])['status'] == 'closed' and len(r) == 1)
wipe(); ids = group(tgt=0.7); PX['BTCUSDT'] = 105.0; cycle.save(U, {'on': True, 'max_per_day': 5}); groupcap.save(U, {'on': True, 'target_usd': 0.7})
r = chk(may_reopen=False)
T('cycle on but the bot may not trade: no next group', r and r[0]['next'] is None and st.q("SELECT COUNT(*) n FROM signals WHERE status='pending'", (), True)['n'] == 0)
wipe(); ids = group(tgt=0.7); PX['BTCUSDT'] = 105.0; cycle.save(U, {'on': True, 'max_per_day': 5}); groupcap.save(U, {'on': True, 'target_usd': 0.7})
r = chk(may_reopen=True); nxt = r[0]['next'] if r else None
T('cycle on and allowed: the next group of 3 is queued as pending signals around the price', bool(nxt) and len(nxt) == 3 and all(row(i)['status'] == 'pending' and row(i)['entry'] == 105.0 for i in nxt))
wipe(); ids = group(loss=2.0, bal0=1000.0); PX['BTCUSDT'] = 92.0
r = chk(may_reopen=True)
T('a loss never starts the next group', r and r[0]['next'] is None and st.q("SELECT COUNT(*) n FROM signals WHERE status='pending'", (), True)['n'] == 0)
wipe(); st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,ticket,broker) VALUES('BTCUSD','buy',100,90,120,0.3,'s',3,'open',?,'other',77,'9','Binance')", (NOW,))
T("another person's group is not touched", bg._groups(U) == [])
wipe(); gid = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES('BTCUSD','buy',100,90,120,0.3,'s',3,'sent',?,?,NULL)", (NOW, U)); st.x('UPDATE signals SET grp=? WHERE id=?', (gid, gid)); st.put('bg:%d' % gid, json.dumps({'k': 'multi', 'n': 3, 'tgt': 0.7, 'loss': 2.0, 't': NOW}))
T('first buy of a group: the balance for the loss limit is saved once', dg.note_open_balance(gid, 1000.0) is True and dg.note_open_balance(gid, 5.0) is False and json.loads(st.get('bg:%d' % gid))['bal0'] == 1000.0)
src = open(os.path.join(ROOT, 'backend', 'binance_bot.py'), encoding='utf-8').read()
T('binance_bot calls the group check after _track and notes the balance after a buy', 'binance_group.check(' in src and 'note_open_balance(s[' in src)
print('%d/%d passed' % (sum(1 for _, o in R if o), len(R))); sys.exit(0 if all(o for _, o in R) else 1)
