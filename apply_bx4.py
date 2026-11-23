"""apply_bx4.py: the phone banner shows each open trade with its stop loss and take profit. Run inside the repo folder: python apply_bx4.py
Every old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import os, sys, subprocess
PAIRS = [
('backend/livestats.py',
r""""SELECT id,symbol,side,fill,entry,strategy FROM signals WHERE status='open'""",
r""""SELECT id,symbol,side,fill,entry,strategy,sl,tp FROM signals WHERE status='open'"""),
('backend/livestats.py',
r''''strategy_name': si.label(r['strategy']), 'pnl': ol.get(r['id'])} for r in rows],''',
r''''strategy_name': si.label(r['strategy']), 'pnl': ol.get(r['id']), 'sl': r.get('sl'), 'tp': r.get('tp')} for r in rows],          # BX4'''),
('backend/live.py',
r'''def _burst(uid, admin, now):
''',
r'''def _lv(label, v):
    """BX4: '  SL 2640.5' for a price level, '' when the trade has none."""
    try: x = float(v)
    except (TypeError, ValueError): return ''
    return '' if x != x or x == 0 else '  %s %s' % (label, format(round(x, 5 if abs(x) < 100 else 2), 'g'))

def _burst(uid, admin, now):
'''),
('backend/live.py',
r'''str(o.get('fill') or o.get('entry') or o.get('price') or '--') + ('   ' + _m(o['pnl'], True) if o.get('pnl') is not None else ''))
''',
r'''str(o.get('fill') or o.get('entry') or o.get('price') or '--') + _lv('SL', o.get('sl')) + _lv('TP', o.get('tp')) + ('   ' + _m(o['pnl'], True) if o.get('pnl') is not None else ''))          # BX4
'''),
]
NEW = {
'tests/test_bx4.py':
r'''"""BX4 tests: the banner lists each open trade with its stop loss and take profit. No network. Run: python tests/test_bx4.py"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bx4_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, livestats, live, brokers as bk, tradeon
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=OW); UID = 'dev-boss@x.com'
NOW = time.time()
st.x("INSERT OR REPLACE INTO broker_links(uid,broker,kind,label,mode,status,created,updated) VALUES(?,'Deriv','oauth','x','demo','verified',1,1)", (UID,))
st.set_acct({'balance': 500, 'equity': 500, 'open': 2, 'demo': True, 'src': 'deriv'}, UID); bk.set_bal(UID, 'Deriv', 500, 'USD', True); tradeon.set_(UID, True, 'Deriv')
def op(side, fill, sl, tp): return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,ticket,broker,fill) VALUES('XAUUSD',?,?,?,?,1,'macd_cross',1,'open',?,?,'7','Deriv',?)", (side, fill, sl, tp, int(NOW), UID, fill))
a = op('buy', 2650.12, 2640.5, 2670.25); b = op('sell', 2651.0, None, None)
sn = livestats.snapshot(UID, True, NOW); tr = {t['id']: t for t in sn['trades']}
T('each open trade carries its stop loss and take profit', tr[a]['sl'] == 2640.5 and tr[a]['tp'] == 2670.25 and tr[b]['sl'] is None)
big = live.build(True, live.snapshot(NOW, UID))['big']
T('the banner shows SL and TP for a trade that has them', 'BUY XAUUSD at 2650.12  SL 2640.5  TP 2670.25' in big)
T('a trade without levels shows no empty SL/TP', 'SELL XAUUSD at 2651.0' in big and 'SELL XAUUSD at 2651.0  SL' not in big)
T('the balance shows in the title and the expanded text for the owner', 'Bot running' in live.build(True, live.snapshot(NOW, UID))['title'] and 'Balance $500.00' in big and 'Equity $500.00' in big)
f = sum(1 for _, ok in R if not ok); print('%d/%d passed' % (len(R) - f, len(R))); sys.exit(1 if f else 0)
''',
}
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, t): open(p + '.tmp', 'w', encoding='utf-8').write(t); os.replace(p + '.tmp', p)
if not os.path.isdir('backend'): sys.exit('Run this inside the spacexbot-mt5 folder (the one with backend/).')
plan, todo, bad = {}, 0, []
for f, o, n in PAIRS:
    t = plan[f] if f in plan else rd(f)
    if n in t: plan[f] = t; continue
    if t.count(o) != 1: bad.append('%s: old text found %d times: %s' % (f, t.count(o), o[:60].replace(chr(10), ' '))); continue
    plan[f] = t.replace(o, n); todo += 1
if bad: sys.exit('NOTHING CHANGED. Problems:\n' + '\n'.join(bad))
for f, t in plan.items():
    if t != rd(f): wr(f, t)
for f, t in NEW.items():
    if not os.path.exists(f) or rd(f) != t: wr(f, t); todo += 1
print('applied %d changes' % todo if todo else 'already applied, nothing to do')
r = 0
for t in ('tests/test_bx4.py', 'tests/test_bx1.py', 'tests/test_live1.py', 'tests/test_live2.py', 'tests/test_live3.py'):
    p = subprocess.run([sys.executable, t], capture_output=True, text=True); last = (p.stdout.strip().splitlines() or ['?'])[-1]
    print(('OK   ' if p.returncode == 0 else 'FAIL ') + t + '  ' + last); r |= p.returncode
print('ALL GOOD' if r == 0 else 'SOMETHING FAILED: send me the FAIL lines'); sys.exit(r)
