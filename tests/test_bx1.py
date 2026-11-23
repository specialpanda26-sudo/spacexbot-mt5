"""BX1 tests: burst says why Auto mode stops it, live profit of every open Deriv trade, and the banner shows floating, wins/losses and each trade. No network. Run: python tests/test_bx1.py"""
import os, sys, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bx1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, burst, burst_look, automode, openlive, livestats, live, deriv, tradeon, brokers as bk, risk
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for k, v in dict(bot_enabled='1', max_open='3', max_open_ceiling='6', max_trades_day='0', burst_enabled='1', burst_ceiling='15', risk_pct='1.0', news_lock='0', auto_mode='0').items(): st.put(k, v)
risk.weekend_shut = lambda now=None: False
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=OW); UID = 'dev-boss@x.com'
NOW = time.time()
# 1) openlive
openlive.save('u1', {5: '1.25', 6: -0.5, 7: 'x', 'bad': 1}, NOW)
T('openlive keeps only real numbers', openlive.get('u1', NOW) == {5: 1.25, 6: -0.5})
T('openlive sums the fresh figures', openlive.floating('u1', NOW) == 0.75)
T('openlive ignores a figure older than %d s' % openlive.FRESH, openlive.get('u1', NOW + openlive.FRESH + 5) is None and openlive.floating('u1', NOW + 999) is None)
openlive.save('u2', {}, NOW); T('nothing open, read just now = 0.0 (not "unknown")', openlive.floating('u2', NOW) == 0.0)
T('never read = None', openlive.floating('nobody', NOW) is None)
# 2) Auto mode blocks burst and the card says so
burst.save(UID, {'on': True, 'minute': True}); tradeon.set_(UID, True, 'Deriv'); bk.set_bot(UID, 'Deriv', True)
st.set_acct({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'src': 'deriv'}, UID)
st.put('auto_mode', '1'); ok, why = burst.due(UID, NOW)
T('Auto mode on: due() says so', ok is False and why == burst.AUTO_WHY)
ex = burst.explain(UID, NOW); T('Auto mode on: the card says Paused and names the fix', ex['blocked'] == 'auto' and 'Paused' in ex['why'] and 'AUTO_MODE=0' in ex['why'])
brain.evaluate = lambda *a, **k: None
def bars(step, n, slope):
    t0 = int(time.time()) // step * step - step
    return [[t0 - step * (n - 1 - i), 2000 + slope * i, 2000 + slope * i + 1, 2000 + slope * i - 1, 2000 + slope * i, 1] for i in range(n)]
A.bars._d.clear()
for tf, step, n in (('M15', 900, 130), ('H1', 3600, 10), ('M5', 300, 130)): A.bars.merge('XAUUSD', tf, bars(step, n, 0.05), uid=UID)
st.x('DELETE FROM signals'); A._last_scan.clear(); st.put('burst:closed:' + UID, 0)
A._scan('XAUUSD', UID)
T('Auto mode on: the scan opens nothing', st.q('SELECT COUNT(*) n FROM signals', (), True)['n'] == 0)
T('Auto mode on: Last look says why', 'Auto mode is ON' in (burst_look.last(UID, NOW) or {}).get('why', ''))
st.put('auto_mode', '0'); A._last_scan.clear(); st.put('burst:closed:' + UID, 0); A._scan('XAUUSD', UID)
T('Auto mode off: the same scan opens the burst group', st.q('SELECT COUNT(*) n FROM signals', (), True)['n'] == 2)
# 3) _track hands over the live profit of open trades
st.x('DELETE FROM signals')
def row(tk, sym='XAUUSD'): return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,ticket,broker,fill) VALUES(?,?,2000,1990,2020,1,'macd_cross',1,'open',?,?,?,'Deriv',2000)", (sym, 'buy', int(NOW), UID, tk))
a, b, d = row('901'), row('902'), row('903')
PR = {901: {'profit': 1.5, 'is_sold': 0}, 902: {'profit': -0.4, 'is_sold': 0}, 903: {'profit': 0.8, 'is_sold': 1}}
class S:
    def ask(s, q): return {'balance': {'balance': 1000, 'currency': 'USD'}} if 'balance' in q else {'proposal_open_contract': PR[q['contract_id']]}
deriv._track(S(), UID, {'demo': True, 'currency': 'USD'})
g = openlive.get(UID)
T('every still-open trade gets its live profit saved', g == {a: 1.5, b: -0.4})
T('a trade Deriv already sold is recorded as closed and not listed as floating', st.q('SELECT status FROM signals WHERE id=?', (d,), True)['status'] == 'closed' and d not in g)
# 4) livestats: floating, per-trade profit, wins and losses
st.x("INSERT OR REPLACE INTO broker_links(uid,broker,kind,label,mode,status,created,updated) VALUES(?,'Deriv','oauth','x','demo','verified',1,1)", (UID,))
st.set_acct({'balance': 1000, 'equity': 1000, 'open': 2, 'demo': True, 'src': 'deriv'}, UID); bk.set_bal(UID, 'Deriv', 1000, 'USD', True)
def closed(grp, pnl, sym='XAUUSD'): return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,closed,pnl,uid,grp,broker) VALUES(?,?,1,1,1,1,'x',1,'closed',?,?,?,?,?,'Deriv')", (sym, 'buy', int(NOW), int(NOW), pnl, UID, grp))
g1 = closed(None, 0.5); st.x('UPDATE signals SET grp=id WHERE id=?', (g1,)); closed(g1, 0.5); closed(g1, -0.2)
l1 = closed(None, -0.9, 'EURUSD')
tradeon.set_(UID, True, 'Deriv'); sn = livestats.snapshot(UID, True, NOW)
T('floating = the live profit of the open trades (+1.10)', sn['floating'] == 1.1 and sn['equity'] == 1001.1)
T('each open trade carries its own profit', {t['id']: t['pnl'] for t in sn['trades']} == {a: 1.5, b: -0.4})
T('a burst group of 3 entries counts as ONE win; with the sold trade (+0.8) that is 2 wins, and the loose loss is 1 loss', (sn['today_w'], sn['today_l']) == (2, 1))
T('last results list the newest setups with their profit', sn['recent'][0]['pnl'] in (-0.9, 0.8) and len(sn['recent']) >= 2)
st.x('DELETE FROM kv WHERE k=?', ('olive:' + UID,)); T('no fresh reading: floating falls back to 0, never a guess', livestats.snapshot(UID, True, NOW)['floating'] == 0.0)
openlive.save(UID, {a: 1.5, b: -0.4}, NOW)
# 5) the banner text
s = live.snapshot(NOW, UID); d1 = live.build(True, s)
T('collapsed line: Float, Today, W/L and open count', 'Float +$1.10' in d1['text'] and 'W2 L1' in d1['text'] and '2 open' in d1['text'])
T('expanded: floating, wins, losses and win rate', 'Floating P/L +$1.10' in d1['big'] and 'Wins 2' in d1['big'] and 'Losses 1' in d1['big'] and 'Win rate 67%' in d1['big'])
T('expanded: each open trade shows its own profit', 'BUY XAUUSD at 2000' in d1['big'] and '+$1.50' in d1['big'] and '-$0.40' in d1['big'])
T('expanded: the last results are listed', 'Last results:' in d1['big'] and 'Loss ' in d1['big'])
burst.save(UID, {'on': True}); d2 = live.build(True, live.snapshot(NOW, UID))
T('expanded: a Burst line when burst is on', 'Burst: ' in d2['big'])
st.put('auto_mode', '1'); d3 = live.build(True, live.snapshot(NOW, UID)); st.put('auto_mode', '0')
T('expanded: the Burst line says paused when Auto mode is on', 'Burst: paused, Auto mode is on' in d3['big'])
d4 = live.build(False, live.snapshot(NOW, UID)); T('a subscriber still never sees the balance or equity', 'Balance' not in d4['big'] and '|  $' not in d4['title'])
T('an old snapshot without the new keys still builds', 'Float' in live.build(False, {'a': {}, 'today': 0, 'open': [], 'now': NOW})['text'])
f = sum(1 for _, ok in R if not ok); print('%d/%d passed' % (len(R) - f, len(R))); sys.exit(1 if f else 0)
