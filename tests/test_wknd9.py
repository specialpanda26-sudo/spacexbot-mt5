"""Checks the weekend rule per market (owner, Nov 21): gold and forex stay blocked at the weekend, a BTC market is let through,
every other gate still applies, and the owner can switch the exemption off (crypto_weekend = 0). Run: python tests/test_wknd9.py"""
import os, sys, glob, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'wknd9_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app   # creates the tables
from backend import store as st, risk, links
APP = open(os.path.join(ROOT, 'backend', 'app.py'), encoding='utf-8').read()
RSK = open(os.path.join(ROOT, 'backend', 'risk.py'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def at(y, m, d, h, mi=0): return dt.datetime(y, m, d, h, mi, tzinfo=dt.timezone.utc).timestamp()
WED = at(2026, 11, 18, 12); SAT = at(2026, 11, 21, 12); SUN = at(2026, 11, 22, 9); MON0 = at(2026, 11, 23, 0); FRI19 = at(2026, 11, 20, 19, 59); FRI20 = at(2026, 11, 20, 20)
SEEN = 4e9          # an EA that always looks online, whatever day the test pretends it is
st.acct = lambda uid='': {'seen': SEEN, 'balance': 1000, 'open': 0, 'demo': True}
links.bot_on = lambda uid='': True
def syms(v): st.put('symbols', v)
st.put('bot_enabled', 1)
T('weekend_shut: Saturday, Sunday and Friday 20:00 are shut', risk.weekend_shut(SAT) and risk.weekend_shut(SUN) and risk.weekend_shut(FRI20))
T('weekend_shut: Friday 19:59, Monday 00:00 and Wednesday are open', not risk.weekend_shut(FRI19) and not risk.weekend_shut(MON0) and not risk.weekend_shut(WED))
T('is_crypto: BTCUSD and its broker spellings', all(risk.is_crypto(x) for x in ('BTCUSD', 'btcusd', 'BTCUSDm', 'BTCUSD.a', ' BTCUSDT ')))
T('is_crypto: gold, forex, empty and ETH are not', not any(risk.is_crypto(x) for x in ('XAUUSD', 'EURUSD', 'GBPJPY', '', None, 'ETHUSD')))
syms('XAUUSD,EURUSD')
T('Saturday, gold and forex only: the gate is shut exactly as before', risk.global_gate(SAT) == (False, 'weekend/Friday-night risk'))
T('Friday 20:00, gold and forex only: shut as before', risk.global_gate(FRI20) == (False, 'weekend/Friday-night risk'))
T('Wednesday, gold and forex only: open as before', risk.global_gate(WED) == (True, 'ok'))
syms('XAUUSD,BTCUSD')
T('Saturday with BTCUSD listed: the gate lets the bot look', risk.global_gate(SAT) == (True, 'ok'))
T('Sunday and Friday night with BTCUSD listed: also open', risk.global_gate(SUN) == (True, 'ok') and risk.global_gate(FRI20) == (True, 'ok'))
T('weekend_skip: gold and forex are skipped on Saturday', risk.weekend_skip('XAUUSD', SAT) and risk.weekend_skip('EURUSD', SAT) and risk.weekend_skip('GBPJPY', SUN))
T('weekend_skip: BTC (and broker spellings) are not skipped at the weekend', not risk.weekend_skip('BTCUSD', SAT) and not risk.weekend_skip('BTCUSDm', SUN) and not risk.weekend_skip('BTCUSD.a', FRI20))
T('weekend_skip: nothing is skipped on a weekday or Friday 19:59', not risk.weekend_skip('XAUUSD', WED) and not risk.weekend_skip('XAUUSD', FRI19) and not risk.weekend_skip('XAUUSD', MON0))
T('weekend_skip: a Friday-night gold scan is skipped even with BTC listed', risk.weekend_skip('XAUUSD', FRI20))
st.put('crypto_weekend', '0')
T('switch crypto_weekend = 0: the old rule is back for everything (gate shut)', risk.global_gate(SAT) == (False, 'weekend/Friday-night risk'))
T('switch crypto_weekend = 0: BTC is skipped at the weekend too', risk.weekend_skip('BTCUSD', SAT))
st.put('crypto_weekend', '1'); syms('BTCUSDm')
T('BTCUSDm listed alone: open on Saturday', risk.global_gate(SAT) == (True, 'ok'))
syms('XAUUSD,EURUSD,BTCUSD')
# the other gates still apply to BTC at the weekend
st.put('bot_enabled', 1)
links.bot_on = lambda uid='': False
T('BTC weekend: bot switched off is still refused', risk.global_gate(SAT) == (False, 'bot off'))
links.bot_on = lambda uid='': True
st.acct = lambda uid='': {'seen': SAT - 500, 'balance': 1000, 'open': 0, 'demo': True}
T('BTC weekend: EA offline is still refused', risk.global_gate(SAT) == (False, 'EA offline'))
st.acct = lambda uid='': {'seen': SEEN, 'balance': 1000, 'open': 0, 'demo': False, 'allow_live': False}
ok, w = risk.global_gate(SAT)
T('BTC weekend: a real account without Real mode is still refused', (not ok) and ('Real mode' in w or w == 'live account not allowed in EA'))
st.acct = lambda uid='': {'seen': SEEN, 'balance': 1000, 'open': 0, 'demo': True}
st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,closed,pnl) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
     ('BTCUSD', 'buy', 1, 1, 1, 1, 's', 1, 'closed', int(SAT - 600), '', int(SAT - 300), -500.0))
T('BTC weekend: the daily loss limit still stops the bot', risk.global_gate(SAT) == (False, 'daily loss limit hit'))
# wiring in the real code
T('app.py: the normal scan skips non-crypto markets at the weekend, only when a BTC market made the gate pass (once)', APP.count("if ok and risk.crypto_open() and risk.weekend_skip(sym): ok, why = False, 'weekend/Friday-night risk'") == 1)
T('app.py: the burst scan skips them too (once)', APP.count('if not ok or (risk.crypto_open() and risk.weekend_skip(sym)): return') == 1)
T('risk.py: global_gate no longer shuts every weekend by itself, it asks crypto_open()', "if weekend_shut(now) and not crypto_open(): return False, 'weekend/Friday-night risk'" in RSK and "if d.weekday() >= 5 or (d.weekday() == 4 and d.hour >= 20): return False" not in RSK)
T('the stop reason text is unchanged (the app words and the Home picture still match)', "'weekend/Friday-night risk': 'Markets are closed or too risky now (weekend or Friday night). It waits.'" in open(os.path.join(ROOT, 'backend', 'botstate.py'), encoding='utf-8').read())
for f in glob.glob(DB + '*'): os.remove(f)
print('\n%d/%d passed' % (sum(1 for _, o in R if o), len(R))); sys.exit(0 if all(o for _, o in R) else 1)
