"""CY4 tests: the auto-cycle on MT5 (server side; the EA code is unchanged). No network. Run: python tests/test_cy4.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_cy4_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, cycle, groupcap, risk, mt5_cycle as mc, deriv_group as dg
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); H = {'X-EA-Key': 'k'}
risk.weekend_shut = lambda now=None: False          # the tests may run on a weekend; the weekend rule has its own tests
st.put('bot_enabled', '1'); st.put('max_open', '6'); st.put('news_lock', '0')
def sync(opn=0): return c.post('/api/ea/sync', json={'account': {'balance': 1000, 'equity': 1000, 'open': opn, 'demo': True}}, headers=H).get_json()
def report(**d): return c.post('/api/ea/report', json=d, headers=H)
def wipe():
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'cyc%' OR k LIKE 'bg:%' OR k LIKE 'gcap:%' OR k LIKE 'cycle:%' OR k LIKE 'closedby:%' OR k LIKE 'pref:%' OR k LIKE 'trade_on:%'"); sync(0)
def on(n=3, tgt=0.7, cap=10): groupcap.save('', {'on': True, 'target_usd': tgt}); cycle.save('', {'on': True, 'max_per_day': cap}); st.put('pref:', json.dumps({'entries': n}))
def group(n=3, tgt=0.7, kind='multi', side='buy', entry=2000.0, sl=1990.0, tp=2020.0):
    ids = []; sql = "INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason,ticket,broker,lots) VALUES('XAUUSD',?,?,?,?,0.33,'strat',3,'open',?,NULL,?,'why',?,'MT5',0.01)"
    for i in range(n): ids.append(st.x(sql, (side, entry, sl, tp, int(time.time()) - 60, ids[0] if ids else None, str(900 + i))))
    st.x('UPDATE signals SET grp=? WHERE id=?', (ids[0], ids[0])); st.put('bg:%d' % ids[0], json.dumps({'k': kind, 'n': n, 'each': 0, 'gb': 0, 'tgt': tgt, 'loss': 0, 't': int(time.time())})); return ids
def close(i, pnl, reason='basket', price=2005.0): return report(id=i, status='closed', pnl=pnl, reason=reason, **({'price': price} if price is not None else {}))
def pend(): return st.q("SELECT * FROM signals WHERE status IN('pending','sent') ORDER BY id")
def one(ids, pnls, **k):
    r = None
    for i, p in zip(ids, pnls): r = close(i, p, **k)
    return r

# 1 the happy path: the cycle starts only when the LAST entry has been reported
wipe(); on(); ids = group(); close(ids[0], 0.3); close(ids[1], 0.3)
T('two of three entries closed: nothing new yet', not pend())
close(ids[2], 0.2); p = pend()
T('the last entry closes: a new group of 3 is queued', len(p) == 3 and {x['grp'] for x in p} == {p[0]['id']} and p[0]['id'] not in ids)
T('...same symbol and side, entry at the closing price 2005, distances 10 and 20 kept', all(x['symbol'] == 'XAUUSD' and x['side'] == 'buy' and x['entry'] == 2005.0 and x['sl'] == 1995.0 and x['tp'] == 2025.0 for x in p))
m = json.loads(st.get('bg:%d' % p[0]['id'])); T('...it is a normal group with the same target', m['k'] == 'multi' and m['n'] == 3 and m['tgt'] == 0.7)
j = sync(0); T('the next EA poll hands the new group out as ONE basket', j['signal'] is None and 'basket' in j and len(j['basket']['ids'].split(',')) == 3 and j['basket']['tgt'] == 0.7)
T('the day counter is 1', dg.used_today('') == 1)

# 2 one group starts one successor, even when the last report arrives twice
wipe(); on(); ids = group(); one(ids, [0.3, 0.3, 0.2]); n1 = len(pend()); close(ids[2], 0.2); close(ids[2], 0.2)
T('a repeated last report does not start a second group', n1 == 3 and len(pend()) == 3 and dg.used_today('') == 1)

# 3 things that must NOT cycle
wipe(); on(); ids = group(); one(ids, [-0.3, -0.3, -0.2]); T('a group closed at a loss never starts the next', not pend())
wipe(); on(); ids = group(); one(ids, [0.3, 0.3, 0.2], reason='sl'); T('entries closed by a stop loss (reason sl) never start the next', not pend())
wipe(); on(); ids = group(); one(ids, [0.3, 0.3, 0.2], reason='manual'); T('a group closed by hand never starts the next', not pend())
wipe(); groupcap.save('', {'on': True, 'target_usd': 0.7}); ids = group(); one(ids, [0.3, 0.3, 0.2]); T('cycle off: nothing is queued', not pend())
wipe(); on(); ids = group(kind='quick'); one(ids, [0.3, 0.3, 0.2]); T('a burst group never cycles', not pend())
wipe(); on(); ids = group(tgt=0); one(ids, [0.3, 0.3, 0.2]); T('a group without a target never cycles', not pend())
wipe(); on(); ids = group(n=1); one(ids, [0.5]); T('a single trade is not a group', not pend())
wipe(); on(); ids = group(); one(ids, [0.3, 0.3, 0.2], price=None); T('the EA sent no closing price: nothing is queued and it says why', not pend() and 'price' in dg.why(''))
wipe(); on(cap=1); ids = group(); one(ids, [0.3, 0.3, 0.2]); a = len(pend()); ids2 = [x['id'] for x in pend()]
for i in ids2: st.x("UPDATE signals SET status='open',ticket=?,broker='MT5' WHERE id=?", (str(700 + i), i))
one(ids2, [0.3, 0.3, 0.2]); T('the daily limit stops it', a == 3 and len([x for x in pend()]) == 0 and 'daily limit' in dg.why(''))

# 4 the closing report of a trade that is not this caller's, and bad input, change nothing and never break the report
wipe(); on(); ids = group(); r = report(id='x', status='closed', pnl=1, reason='basket'); T('a bad id still answers ok', r.status_code == 200 and not pend())

# 5 the snapshot still shows the old positions open: wait, then try again on the next polls
wipe(); on(); ids = group(); sync(6); one(ids, [0.3, 0.3, 0.2])
T('stale snapshot (EA still says 6 open): no group yet, but it waits for the next poll', not pend() and st.get('cyc_retry:') not in (None, '') and 'max open' in dg.why(''))
j = sync(0)
T('the next poll has the fresh snapshot: the new group is queued and handed out at once', 'basket' in j and len(j['basket']['ids'].split(',')) == 3 and st.get('cyc_retry:') == '' and dg.used_today('') == 1)
wipe(); on(); ids = group(); sync(6); one(ids, [0.3, 0.3, 0.2]); k = json.loads(st.get('cyc_retry:')); k['t'] -= 200; st.put('cyc_retry:', json.dumps(k)); j = sync(0)
T('waited longer than 90 seconds: it gives up and says so', 'basket' not in j and not pend() and st.get('cyc_retry:') == '' and 'no room' in dg.why(''))
wipe(); on(); ids = group(); sync(6); one(ids, [0.3, 0.3, 0.2]); risk.weekend_shut = lambda now=None: True; j = sync(0); risk.weekend_shut = lambda now=None: False
T('a different refusal on the retry ends the wait (weekend rule)', not pend() and st.get('cyc_retry:') == '' and 'weekend' in dg.why(''))
wipe(); T('no waiting refusal: a poll changes nothing', mc.retry('') is None)

wipe(); on(); ids = group(); sync(4); one(ids, [0.3, 0.3, 0.2])
T("stale snapshot with only 2 free places: 'not enough room' also waits", not pend() and 'room' in dg.why('') and st.get('cyc_retry:') not in (None, ''))
sync(0); T('...and goes through on the next poll', dg.used_today('') == 1)

# 6 wired in
src = open(os.path.join(ROOT, 'backend', 'app.py'), encoding='utf-8').read()
T('app.py calls retry in /api/ea/sync and after_close in /api/ea/report', 'mt5_cycle.retry(who)' in src and 'mt5_cycle.after_close(who, sid' in src and src.index('mt5_cycle.retry(who)') < src.index("@app.post('/api/ea/report')") < src.index('mt5_cycle.after_close(who, sid'))

bad_ = [n for n, ok in R if not ok]
print('\n%d passed, %d failed' % (len(R) - len(bad_), len(bad_)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_ else 0)
