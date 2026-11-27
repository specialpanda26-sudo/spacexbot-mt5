"""Burst mode Section 1 tests: settings, the quiet timer, the gates a burst relaxes (and the ones it does not), the size of a burst, the group written to the
database, one burst at a time, and the two routes. No network. Run: python tests/test_burst1.py"""
import os, sys, json, time, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_burst1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, risk, burst, limits
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def bad(f, *a):
    try: f(*a)
    except ValueError: return True
    return False

WED = int(dt.datetime(2026, 11, 11, 12, 0, tzinfo=dt.timezone.utc).timestamp())          # a Wednesday noon, so the weekend gate never decides a test
SAT = int(dt.datetime(2026, 11, 14, 12, 0, tzinfo=dt.timezone.utc).timestamp())
def acct(open_n=0, seen=WED, bal=1000):
    st.put('acct', json.dumps({'balance': bal, 'equity': bal, 'open': open_n, 'demo': True, 'allow_live': False, 'seen': seen}))
def clean():
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'bg:%' OR k LIKE 'burst:%'")
    for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', burst_big_score='3', risk_pct='1.0', news_lock='0').items(): st.put(k, v)
    acct()
def D(now, uid=''):
    acct(seen=now); return burst.due(uid, now)          # the bridge reported at that moment, so MT5 is online
SETUP = {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 'macd_cross', 'score': 1}

clean()
# ---- settings ----
p = burst.get('')
T('defaults: off, 5 minutes quiet, 5 quick / 15 big entries, 0.5 and 1.0 USD each, 40 percent give-back',
  p == {'on': False, 'idle_min': 5, 'quick_n': 5, 'big_n': 15, 'quick_usd': 0.5, 'big_usd': 1.0, 'giveback': 40, 'stake_usd': 0.5, 'minute': False, 'minute_n': 2, 'loss_usd': 0.0, 'lot': 0.0, 'max_lot': 0.0, 'lot_mode': 'auto', 'plan_usd': 0, 'tiny_pct': 0.0})
o = burst.save('', {'on': True, 'idle_min': 4, 'quick_usd': 0.8, 'big_usd': 2, 'giveback': 30})
T('save keeps the choices, USD amounts are per entry', o['on'] is True and o['idle_min'] == 4 and o['quick_usd'] == 0.8 and o['big_usd'] == 2.0 and o['giveback'] == 30 and o['quick_n'] == 5)
before = burst.get('')
T('bad input is refused and nothing is saved', all(bad(burst.save, '', d) for d in ({'idle_min': 0}, {'idle_min': 61}, {'idle_min': 2.5}, {'quick_n': 0}, {'quick_n': 16}, {'quick_usd': 0}, {'quick_usd': 'x'},
  {'big_usd': -1}, {'giveback': 95}, {'on': 'yes'}, {'quick_usd': True}, {'quick_usd': float('nan')}, 'nope')) and burst.get('') == before)
st.put('burst_ceiling', '8'); T('the owner ceiling caps the entries (a saved 15 reads as 8)', burst.get('')['big_n'] == 8 and bad(burst.save, '', {'big_n': 9}))
burst.save('', {'quick_n': 8}); burst.save('', {'big_n': 3})
T('big is never smaller than quick', burst.get('')['big_n'] >= burst.get('')['quick_n'])
st.put('burst_ceiling', '15'); st.put('burst:', '{garbage'); T('garbage saved settings fall back to the defaults', burst.get('') == p)
burst.save('', {'on': True, 'quick_n': 5, 'big_n': 15, 'idle_min': 5, 'quick_usd': 0.5, 'big_usd': 1.0, 'giveback': 40})
burst.save('u1', {'on': True, 'quick_usd': 0.1}); T('each person has their own settings', burst.get('u1')['quick_usd'] == 0.1 and burst.get('')['quick_usd'] == 0.5)

# ---- the quiet timer and the gates ----
clean(); burst.save('', {'on': True, 'idle_min': 5})
ok, why = burst.due('', WED); T('a bot that has just been quiet since 1970 is due', ok)
burst.closed('', WED - 120); ok, why = burst.due('', WED); T('not due before the quiet minutes pass (2 of 5)', not ok and why == 'quiet for 2 of 5 minutes')
ok, why = D(WED + 180); T('due once 5 quiet minutes have passed', ok)
st.x("INSERT INTO signals(symbol,side,status,created) VALUES('XAUUSD','buy','expired',?)", (WED + 100,)); ok, why = D(WED + 180)
T('a signal made 80 seconds ago restarts the quiet time', not ok and why.startswith('quiet for'))
clean(); burst.save('', {'on': False}); T('off means never due', burst.due('', WED)[0] is False)
burst.save('', {'on': True}); st.put('burst_enabled', '0'); T('the owner switch beats the person', burst.due('', WED)[0] is False); st.put('burst_enabled', '1')
st.put('bot_enabled', '0'); T('bot stopped: not due', burst.due('', WED) == (False, 'bot off')); st.put('bot_enabled', '1')
acct(seen=WED - 500); T('MT5 offline: not due', burst.due('', WED) == (False, 'EA offline')); acct()
T('weekend: not due (the weekend gate still holds)', burst.due('', SAT)[0] is False)
acct(); st.x("INSERT INTO signals(symbol,side,status,created,pnl,closed) VALUES('XAUUSD','buy','closed',?,-80,?)", (WED - 7200, WED - 3600)); st.put('max_daily_loss_pct', '3.0')
ok, why = burst.due('', WED); T('a hit daily loss limit still stops it', (ok, why) == (False, 'daily loss limit hit'))
clean()

# ---- relaxed gates: only max-open and cooldown ----
acct(open_n=3); st.put('max_open', '3')
T('normal gate: 3 open of max 3 is blocked', risk.global_gate(WED, uid='') == (False, 'max open positions'))
T('burst gate: the same account passes (the burst ceiling decides instead)', risk.global_gate(WED, uid='', burst=True)[0] is True)
st.put('bot_enabled', '0'); T('burst gate still refuses a stopped bot', risk.global_gate(WED, uid='', burst=True) == (False, 'bot off')); st.put('bot_enabled', '1')
acct(); st.x("INSERT INTO signals(symbol,side,status,created) VALUES('XAUUSD','buy','closed',?)", (WED - 600,))
T('symbol cooldown blocks a normal signal', risk.symbol_gate('XAUUSD', 'buy', WED, '') == (False, 'symbol cooldown'))
T('symbol cooldown is skipped for a burst', risk.symbol_gate('XAUUSD', 'buy', WED, '', cool=False)[0] is True)
clean()

# ---- the size of a burst ----
pl, why = burst.plan('', 1); T('one agreeing strategy = a quick burst of 5 entries at 0.5 USD each', pl and pl['kind'] == 'quick' and pl['n'] == 5 and pl['each'] == 0.5 and pl['giveback'] == 40)
pl, why = burst.plan('', 3); T('three agreeing strategies = a big burst of 15 entries at 1.0 USD each', pl and pl['kind'] == 'big' and pl['n'] == 15 and pl['each'] == 1.0)
pl, why = burst.plan('', 2); T('two agreeing is still quick', pl['kind'] == 'quick')
st.put('burst_big_score', '4'); pl, why = burst.plan('', 3); T('the owner decides how many strategies make it big', pl['kind'] == 'quick'); st.put('burst_big_score', '3')
acct(open_n=12); pl, why = burst.plan('', 3); T('never above the ceiling: 12 open of 15 leaves room for 3 entries', pl and pl['n'] == 3)
acct(open_n=14); pl, why = burst.plan('', 3); T('less than 2 free = no burst, and it says why', pl is None and 'not enough room' in why)
acct(); st.put('max_trades_day', '4'); pl, why = burst.plan('', 3); T('max trades a day also limits the entries', pl and pl['n'] == 4); st.put('max_trades_day', '0')
burst.save('', {'big_n': 5, 'quick_n': 5}); pl, why = burst.plan('', 3); T('when big = quick the burst stays quick', pl['kind'] == 'quick' and pl['n'] == 5)
burst.save('', {'big_n': 15})

# ---- the group in the database ----
clean(); burst.save('', {'on': True})
pl, why = burst.plan('', 3); ids = burst.create('', 'XAUUSD', dict(SETUP, score=3), pl, 'reason text', WED)
rows = st.q('SELECT * FROM signals ORDER BY id')
T('15 pending signals, one group, same side / stop / target', len(rows) == 15 and ids == [r['id'] for r in rows] and {r['grp'] for r in rows} == {ids[0]} and {r['status'] for r in rows} == {'pending'}
  and len({(r['side'], r['entry'], r['sl'], r['tp']) for r in rows}) == 1)
T('the entries SHARE the normal risk (total = one trade)', abs(sum(r['risk_pct'] for r in rows) - 1.0) < 0.001)
m = burst.meta(ids[0]); T('the group remembers its kind, size, USD target per entry and give-back', m and m['k'] == 'big' and m['n'] == 15 and m['each'] == 1.0 and m['gb'] == 40)
T('a normal group has no burst facts', burst.meta(999999) is None and burst.meta('x') is None)
T('one burst at a time: while it is open it is not due again', burst.active('') and D(WED + 5000) == (False, 'a burst is already running'))
st.x("UPDATE signals SET status='closed',pnl=1,closed=?", (WED + 60,)); T('after it closes it is no longer active', not burst.active(''))
st.x('DELETE FROM signals'); ids2 = burst.create('u1', 'XAUUSD', SETUP, {'kind': 'quick', 'n': 2, 'each': 0.5, 'giveback': 0}, '', WED)
T('a subscriber burst is kept under that person only', st.q("SELECT COUNT(*) n FROM signals WHERE uid='u1'", (), True)['n'] == 2 and not burst.active('') and burst.active('u1'))

# ---- words for the app ----
clean(); burst.save('', {'on': False}); T('words: off', burst.explain('', WED)['state'] == 'off')
burst.save('', {'on': True}); burst.closed('', WED - 60); e = burst.explain('', WED); T('words: waiting with the minutes', e['state'] == 'waiting' and '1 of 5 minutes' in e['why'])
acct(seen=WED + 400); e = burst.explain('', WED + 400); T('words: ready', e['state'] == 'ready')
st.put('bot_enabled', '0'); e = burst.explain('', WED); T('words: a stopped bot says why in plain words', e['state'] == 'waiting' and 'stopped' in e['why']); st.put('bot_enabled', '1')

# ---- routes ----
c = A.app.test_client(); H = {'Authorization': 'Bearer dev:boss@x.com'}
def dev(email): return {'Authorization': 'Bearer dev:' + email}
clean()
r = c.get('/api/burst'); T('routes need a sign-in', r.status_code == 401)
rr = A.app.test_client()
r = rr.get('/api/burst', headers=H)
T('GET works for the owner', r.status_code == 200)
if r.status_code == 200:
    j = r.get_json(); T('GET shows settings, ceiling and words', set(j) >= {'settings', 'enabled', 'ceiling', 'big_score', 'now'} and j['ceiling'] == 15)
    r2 = rr.post('/api/burst', json={'on': True, 'quick_usd': 0.8}, headers=H); T('POST saves', r2.status_code == 200 and r2.get_json()['settings']['quick_usd'] == 0.8 and r2.get_json()['settings']['on'] is True)
    r3 = rr.post('/api/burst', json={'quick_usd': 0}, headers=H); T('POST with bad input is a clean 400 and keeps the old value', r3.status_code == 400 and burst.get('')['quick_usd'] == 0.8)

bad_n = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad_n), len(R)))
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.exit(1 if bad_n else 0)
