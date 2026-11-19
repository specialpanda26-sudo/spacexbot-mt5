"""Burst mode Section 3 tests: a burst group goes to the EA all at once, normal trades are untouched, the close reason 'basket' is kept, one alert per group,
and the EA source has the basket pieces in place. No network. Run: python tests/test_burst3.py
(The MQL5 code cannot be compiled or run here: compile SpaceXBridge.mq5 in MetaEditor and watch a DEMO account first.)"""
import os, sys, json, time, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_burst3_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, burst
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); H = {'X-EA-Key': 'k'}
def sync(): return c.post('/api/ea/sync', json={'account': {'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True}}, headers=H).get_json()
def report(**d): return c.post('/api/ea/report', json=d, headers=H)
def clean(): st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'bg:%' OR k LIKE 'closedby:%'")
SET = {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 'macd_cross', 'score': 1}
def mk(n=5, uid='', kind='quick', each=0.5):
    return burst.create(uid, 'XAUUSD', SET, {'kind': kind, 'n': n, 'each': each, 'giveback': 40}, '{}')
st.put('bot_enabled', '1')

# ---------- the server hands out a whole burst group at once
clean(); ids = mk(5); j = sync()
T('a burst group comes as ONE basket, signal is empty (an old EA can never half-open it)', j['signal'] is None and 'basket' in j)
b = j['basket']
T('the basket names the group, symbol, side, stop, target and the per-entry USD target', b['gid'] == ids[0] and b['symbol'] == 'XAUUSD' and b['side'] == 'buy' and b['sl'] == 1990.0 and b['tp'] == 2020.0 and b['each'] == 0.5)
T('the basket lists ALL five entries and the give-back percent', b['ids'] == ','.join(str(i) for i in ids) and b['gb'] == 40)
T('all five are marked sent in the same poll', {r['status'] for r in st.q('SELECT status FROM signals')} == {'sent'})
j2 = sync(); T('the next poll gives nothing again (no double delivery)', j2['signal'] is None and 'basket' not in j2)
T('the share of the normal risk per entry is passed to the EA', abs(b['risk_pct'] * 5 - st.fget('risk_pct')) < 0.001)

# ---------- things that are NOT bursts stay exactly as before
clean(); st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created) VALUES('XAUUSD','buy',2000,1990,2020,1.0,'macd_cross',1,'pending',?)", (int(time.time()),))
j = sync(); T('a normal single signal still comes as signal, no basket', j['signal'] and j['signal']['symbol'] == 'XAUUSD' and 'basket' not in j)
clean(); now = int(time.time()); first = None
for i in range(3):
    rid = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,grp) VALUES('XAUUSD','buy',2000,1990,2020,0.3,'macd_cross',1,'pending',?,?)", (now, first))
    first = first or rid
    if i == 0: st.x('UPDATE signals SET grp=? WHERE id=?', (rid, rid))
j = sync(); T('a normal multi-entry group (not a burst) still goes one entry per poll', j['signal'] and 'basket' not in j and len(st.q("SELECT 1 FROM signals WHERE status='sent'")) == 1)
clean(); mk(5, uid='u1'); j = sync(); T("someone else's burst group is never handed to the owner's EA", j['signal'] is None and 'basket' not in j and {r['status'] for r in st.q('SELECT status FROM signals')} == {'pending'})
clean(); ids = mk(3); st.x("UPDATE signals SET status='rejected' WHERE id=?", (ids[1],)); j = sync()
T('only entries still pending go out (a rejected one is left alone)', j['basket']['ids'] == '%d,%d' % (ids[0], ids[2]))

# ---------- reports: the reason basket is kept, alerts are once per group
SEEN = []
A.sbauth.notify = lambda title, body, key=None, only=None: SEEN.append(('mail', key, title, body))
A.push.notify = lambda kind, key=None, **f: SEEN.append(('push', key, kind, f.get('pnl')))
clean(); ids = mk(3); g = ids[0]; sync()
for i in ids: report(id=i, status='open', ticket=900 + i, lots=0.01, price=2000.0)
T('the three entries are open with their tickets', [r['status'] for r in st.q('SELECT status FROM signals ORDER BY id')] == ['open'] * 3)
T('open alerts: one per group, not one per entry', len({x[1] for x in SEEN if x[0] == 'mail'}) == 1 and ('mail', 'bg%d-open' % g) == SEEN[0][:2])
SEEN.clear()
for i in ids: report(id=i, status='closed', pnl=0.6, reason='basket', gpnl=1.8)
T('close reason basket is stored for every entry', all(st.get('closedby:%d' % i) == 'basket' for i in ids))
T('all three are closed with their own profit', [r['pnl'] for r in st.q('SELECT pnl FROM signals ORDER BY id')] == [0.6] * 3)
T('close alerts: ONE key for the whole group', {x[1] for x in SEEN} == {'bg%d-closed' % g})
T('the alert shows the GROUP profit (1.8), not one entry', all(x[3] == 1.8 for x in SEEN if x[0] == 'push') and any('Burst P/L 1.8' in x[3] for x in SEEN if x[0] == 'mail'))
clean(); st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created) VALUES('XAUUSD','buy',2000,1990,2020,1.0,'macd_cross',1,'sent',?)", (int(time.time()),))
sid = st.q('SELECT id FROM signals', (), True)['id']; SEEN.clear(); report(id=sid, status='closed', pnl=-5.0, reason='sl')
T('a normal trade keeps its own alert key and reason', st.get('closedby:%d' % sid) == 'sl' and {x[1] for x in SEEN} == {'sig%d-closed' % sid})
report(id=sid, status='closed', pnl=-5.0, reason='weird'); T('an unknown reason is never stored', st.get('closedby:%d' % sid) == 'sl')
T('a bad group profit is ignored, not a crash', report(id=sid, status='closed', pnl=-5.0, reason='tp', gpnl='abc').status_code == 200)

# ---------- the EA source
ea = open(os.path.join(ROOT, 'ea', 'SpaceXBridge.mq5'), encoding='utf-8').read()
def code_only(s):          # drop comments, "strings" and 'chars' so a brace inside a text does not count
    o = []; i = 0; n = len(s)
    while i < n:
        if s.startswith('//', i):
            while i < n and s[i] != '\n': i += 1
        elif s[i] in '"\'':
            q = s[i]; i += 1
            while s[i] != q: i += 2 if s[i] == '\\' else 1
            i += 1
        else: o.append(s[i]); i += 1
    return ''.join(o)
co = code_only(ea)
T('EA brackets and braces are balanced (comments and texts ignored)', all(co.count(a) == co.count(b) for a, b in ('{}', '()', '[]')))
T('EA has the basket pieces', all(x in ea for x in ('void ExecuteBasket(', 'void ManageBaskets()', 'void CloseBasket(', 'long CmGid(', 'void PollServer()', 'EventSetMillisecondTimer(BasketCheckMs)')))
T('EA basket orders carry the group in the comment (SXB<id>G<gid>)', '"SXB" + (string)ids[i] + "G" + (string)gid' in ea)
eb = ea[ea.index('void ExecuteBasket('):ea.index('void CloseBasket(')]
T('EA basket open keeps every safety check of a normal trade', all(x in eb for x in ('AllowLive', 'MaxSpreadPoints', 'stale signal', 'SYMBOL_TRADE_STOPS_LEVEL', 'MaxLots')))
T('EA reports the close reason basket, and tp / sl / manual / bot for the rest', '"basket"' in ea and all(x in ea for x in ('why = "tp"', 'why = "sl"', 'why = "manual"', 'why = "bot"')))
T('EA closes the group at target OR on give-back, and only after the arm level', 'sum[j] >= target' in ea and 'BasketArmPct' in ea and 'gbp > 0' in ea)
T('EA never closes a position that is not its own (magic) or not in the group', ea.count('POSITION_MAGIC) != Magic') >= 2 and 'CmGid(PositionGetString(POSITION_COMMENT)) != gid' in ea)
T('the normal one-signal path is still there', 'void Execute(long id' in ea and 'Execute(id, JStr(res, "symbol")' in ea)

# ---------- the patch is safe to run twice
def h(p): return hashlib.md5(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()
before = [h(p) for p in ('backend/app.py', 'backend/burst.py', 'ea/SpaceXBridge.mq5')]
out = subprocess.run([sys.executable, 'apply_burst3.py'], cwd=ROOT, capture_output=True, text=True).stdout
T('running apply_burst3.py again changes nothing', 'patched OK' in out and before == [h(p) for p in ('backend/app.py', 'backend/burst.py', 'ea/SpaceXBridge.mq5')])

p = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (p, len(R)))
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
sys.exit(0 if p == len(R) else 1)
