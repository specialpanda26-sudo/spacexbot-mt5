"""PH3 checks: Suggest. A screen read where the bot agrees also carries a lot size for the person's own balance and risk. Run: python tests/test_ph3.py"""
import os, sys, time, glob, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_ph3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, screenread as sr, bars, brain, alerts, assist
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c.get('/api/me', headers=H('amy@x.com')); A = 'dev-amy@x.com'
rows = [(1_700_000_000 + i * 900, 2000, 2001, 1999, 2000, 1) for i in range(130)]
bars.merge('XAUUSD', 'M15', rows); bars.merge('XAUUSD', 'H1', rows)
SIG = {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 'ma_bounce', 'score': 2, 'adx': 25, 'why': {}}
brain.evaluate = lambda *a, **k: dict(SIG)
from backend import risk
risk.global_gate = lambda *a, **k: (True, 'ok'); risk.symbol_gate = lambda *a, **k: (True, 'ok'); risk.weekend_skip = lambda s: False; risk.weekday_skip = lambda s: False   # the bot is allowed to trade, so the read says agree
READ = {'readable': True, 'symbol': 'XAU/USD', 'bias': 'buy'}
v = sr.ask_bot(A, READ, 'trade')
T('no balance yet: agree, but the size says to set it in Phone mode', v['code'] == 'agree' and v['size']['lots'] is None and 'Phone mode' in v['size']['why'])
assist.save(A, None, 1000, 1.0)
v = sr.ask_bot(A, READ, 'trade')
T('balance 1000, risk 1 percent, 10 dollar stop on gold: 0.01 lot', v['code'] == 'agree' and v['size']['lots'] == 0.01 and v['size']['risk_usd'] == 10.0)
assist.save(A, None, 10000, 1.0)
v = sr.ask_bot(A, READ, 'trade')
T('balance 10000: 0.1 lot, risk 100, win 200', v['size']['lots'] == 0.1 and v['size']['risk_usd'] == 100.0 and v['size']['win_usd'] == 200.0)
T('the bot levels are the bot\'s own, unchanged', v['signal']['entry'] == 2000.0 and v['signal']['sl'] == 1990.0 and v['signal']['tp'] == 2020.0)
v = sr.ask_bot(A, READ, 'learn')
T('the learning path gets no size', v['code'] == 'agree' and 'size' not in v)
brain.evaluate = lambda *a, **k: dict(SIG, side='sell', sl=2010.0, tp=1980.0)
v = sr.ask_bot(A, dict(READ, bias='buy'), 'trade')
T('AI and bot disagree: no size is offered', v['code'] == 'disagree' and 'size' not in v)
J = open(os.path.join(ROOT, 'static', 'screen.js'), encoding='utf-8').read()
T('the card shows the suggested size and Suggest is on', 'Suggested size: ' in J and 'aria-pressed="true" disabled>Suggest</button>' in J and 'Suggest · soon' not in J)
JV = open(os.path.join(ROOT, 'android-wrapper', 'native', 'ScreenLogic.java'), encoding='utf-8').read()
T('the bubble shows the suggested size', 'sizeText(b)' in JV and 'Suggested size' in JV)
for f in glob.glob(DB + '*'): os.remove(f)
print('%d/%d passed' % (sum(1 for _, o in R if o), len(R))); sys.exit(0 if all(o for _, o in R) else 1)
