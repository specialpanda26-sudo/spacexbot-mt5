"""Section 4 tests: the exit price. EA source sends it, the server keeps it only when it is a real number, the trade detail shows it, Deriv keeps one only if Deriv sent it. No network.
Run: python tests/test_exit4.py"""
import os, sys, time, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_exit4_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, deriv
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); H = {'X-EA-Key': 'k'}; BOSS = {'Authorization': 'Bearer dev:boss@x.com'}
def openrow(uid='', ticket=None):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,ticket,lots,fill,broker,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ('XAUUSD', 'buy', 2000.0, 1990.0, 2020.0, 1.0, 'macd_cross', 3, 'open', int(time.time()) - 600, uid, ticket, 0.5, 2000.1, 'Deriv' if ticket else 'MT5', 'x100' if ticket else None))
def close(sid, **extra): return c.post('/api/ea/report', json=dict({'id': sid, 'status': 'closed', 'pnl': 12.5, 'reason': 'tp'}, **extra), headers=H)
def detail(sid): return c.get('/api/trade/%d' % sid, headers=BOSS).get_json()

# ---------- EA source
ea = open(os.path.join(ROOT, 'ea', 'SpaceXBridge.mq5'), encoding='utf-8').read()
T('EA is version 1.21 and reads the price of the closing deal', '#property version "1.21"' in ea and 'HistoryDealGetDouble(t.deal, DEAL_PRICE)' in ea)
T('EA adds the price to the CLOSED report only', ea.count('\\"price\\":" + DoubleToString(exitPx, exitDg)') == 1 and ea.find('exitPx > 0') > ea.find('string extra = ') and ea.find('exitPx > 0') < ea.find('Report(sid, "closed", extra)'))

# ---------- server
a = openrow(); close(a, price=2019.8); d = detail(a)
T('a price from the EA is kept and shown as the exit', d['exit']['recorded'] is True and d['exit']['price'] == 2019.8 and d['exit']['reason'] == 'tp' and d['closed_by'] == 'tp')
T('with a price and a reason there is no "not recorded" note at all', d['exit']['note'] is None)
bad = []
for v in ('abc', -5, 0, 'nan', 'inf', None, 1e12, ''):
    s = openrow(); close(s, price=v); bad.append(detail(s)['exit']['recorded'])
T('a price that is not a real positive number is never stored', bad == [False] * 8)
s = openrow(); c.post('/api/ea/report', json={'id': s, 'status': 'closed', 'pnl': 3.0}, headers=H); d = detail(s)
T('an old EA (no price, no reason): both are said to be not recorded', d['exit']['recorded'] is False and d['exit']['price'] is None and 'not recorded' in d['exit']['note'])
s = openrow(); c.post('/api/ea/report', json={'id': s, 'status': 'closed', 'pnl': 3.0, 'price': 2005.5}, headers=H); d = detail(s)
T('a price without a reason: shows the price, says only the reason is missing', d['exit']['price'] == 2005.5 and 'reason' in d['exit']['note'] and 'price' not in d['exit']['note'])
s = openrow(); close(s)
T('a reason without a price: says the price is not recorded', 'price' in detail(s)['exit']['note'] and detail(s)['exit']['price'] is None)
s = openrow(); c.post('/api/ea/report', json={'id': s, 'status': 'open', 'ticket': 5, 'lots': 0.5, 'price': 2000.3}, headers=H)
T('the fill price on an OPEN report is never taken as an exit price', st.get('exitpx:%d' % s) is None)
other = openrow(uid='someone-else'); close(other, price=1.0)
T('a report for another person\'s trade changes nothing', st.get('exitpx:%d' % other) is None)

# ---------- Deriv: only a price Deriv really sent
class Sess:
    def __init__(s, **p): s.p = dict({'is_sold': 1, 'profit': -100.0}, **p)
    def ask(s, q): return {'proposal_open_contract': s.p}
old = (deriv._report, deriv._resnap); deriv._report = lambda *a, **k: None; deriv._resnap = lambda *a, **k: None
x1 = openrow('joe', '701'); deriv._track(Sess(sell_spot='1983.45'), 'joe', {'demo': True, 'currency': 'USD'})
x2 = openrow('joe', '702'); deriv._track(Sess(exit_tick=1.0851), 'joe', {'demo': True, 'currency': 'USD'})
x3 = openrow('joe', '703'); deriv._track(Sess(), 'joe', {'demo': True, 'currency': 'USD'})
x4 = openrow('joe', '704'); deriv._track(Sess(sell_spot='n/a'), 'joe', {'demo': True, 'currency': 'USD'})
deriv._report, deriv._resnap = old
T('Deriv: sell_spot or exit_tick is kept when Deriv sent it', st.get('exitpx:%d' % x1) == '1983.45' and st.get('exitpx:%d' % x2) == '1.0851')
T('Deriv: no price from Deriv (or an unreadable one) means nothing stored', st.get('exitpx:%d' % x3) is None and st.get('exitpx:%d' % x4) is None)

# ---------- page
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page shows an Exit price row from the recorded price and no longer always adds the not-recorded note', '<dt>Exit price</dt>' in html and 'if (ex.note) notes.push(ex.note)' in html)

p = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (p, len(R)))
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
sys.exit(0 if p == len(R) else 1)
