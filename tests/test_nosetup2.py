"""R2 checks: when the bot does not trade, it says why. brain.evaluate(info=...), the scanner note, and the Bot status wording. No network. Run: python tests/test_nosetup2.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, '_nosetup2_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, botstate, links
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

def mk(name, side, off=3.0):
    def f(m, h): return {'side': side, 'sl': m[-1]['c'] - off if side == 'buy' else m[-1]['c'] + off, 'name': name}
    f.__name__ = name; return f
def nothing(m, h): return None
real_all, real_adx = brain.ALL, brain.adx
t0 = int(time.time()) // 900 * 900 - 900 * 200
M = [{'t': t0 + 900 * i, 'o': 2000, 'h': 2001 + (i % 3) * 0.2, 'l': 1999 - (i % 2) * 0.2, 'c': 2000 + (i % 2) * 0.5, 'v': 1} for i in range(200)]
def ev(fns, adxv=None, **kw):
    brain.ALL = fns; info = {}
    if adxv is not None: brain.adx = lambda m: [adxv] * len(m)
    try: r = brain.evaluate(M, M, info=info, **kw)
    finally: brain.ALL = real_all; brain.adx = real_adx
    return r, info

# ---- 1. the brain says why there is no setup ----
i = {}; r = brain.evaluate(M[:50], M, info=i)
T('too few candles: says how many it has', r is None and i['code'] == 'history' and '50 of 120' in i['text'])
r, i = ev([nothing, nothing]); T('two strategies looked, none fired', r is None and i['code'] == 'none' and i['ran'] == 2 and 'None of the 2 strategies' in i['text'])
r, i = ev([nothing]); T('one strategy looked, none fired', r is None and i['code'] == 'none' and i['ran'] == 1 and 'None of the 1 strategies' in i['text'])
r, i = ev([nothing], off={'nothing'}); T('all switched off is said plainly', r is None and i['text'] == 'All strategies are switched off.' and i['ran'] == 0)
brain.REVERSION.add('fake_rev'); r, i = ev([mk('fake_rev', 'buy')], adxv=40.0); brain.REVERSION.discard('fake_rev')
T('a reversal setup skipped in a strong trend: says ADX and the limit', r is None and i['code'] == 'adx' and 'strong trend' in i['text'] and 'above 28' in i['text'] and i['filtered'] == ['fake_rev'])
brain.TREND.add('fake_tr'); r, i = ev([mk('fake_tr', 'sell')], adxv=10.0); brain.TREND.discard('fake_tr')
T('a trend setup skipped in a quiet market: says ADX and the limit', r is None and i['code'] == 'adx' and 'quiet market' in i['text'] and 'below 18' in i['text'])
r, i = ev([mk('fake_a', 'buy'), mk('fake_b', 'sell')], min_conf=1); T('buy and sell tied: says they disagreed', r is None and i['code'] == 'split' and 'disagreed' in i['text'])
r, i = ev([mk('fake_a', 'buy'), nothing], min_conf=2); T('one strategy but two needed: says so', r is None and i['code'] == 'conf' and 'Only 1 strategy' in i['text'] and '2 must agree' in i['text'])
r, i = ev([mk('fake_a', 'buy', off=40.0)], min_conf=1); T('stop too far: says how many ATR away and the limits', r is None and i['code'] == 'stop' and 'ATR away' in i['text'] and '0.5 to 3.5' in i['text'])
r, i = ev([mk('fake_a', 'buy'), mk('fake_b', 'buy')], min_conf=2); T('a real setup still returns a signal and leaves info empty', r and r['side'] == 'buy' and r['score'] == 2 and i == {})
T('old callers (no info) still work', brain.evaluate(M[:50], M) is None and brain.evaluate(M[:50], M, 2, 2.0, ()) is None)

# ---- 2. the scanner saves the reason with its note ----
risk.global_gate = lambda now=None, uid='': (True, '')
BAR = int(time.time()) // 900 * 900 - 900
st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._last_scan.clear()
A.bars.merge('XAUUSD', 'M15', [[BAR - 900 * k, 2000, 2001, 1999, 2000, 1] for k in range(130)], uid='')
A.bars.merge('XAUUSD', 'H1', [[BAR - 3600 * k, 2000, 2001, 1999, 2000, 1] for k in range(10)], uid='')
brain.ALL = [nothing]; A._scan('XAUUSD', ''); brain.ALL = real_all
n = botstate._last('')
T('after a candle with no setup the note has the reason', n and n['c'] == 'nosetup' and n['w'].startswith('None of the 1 strategies saw a setup on this candle.'))
botstate.note('', 'XAUUSD', 'nosetup', 'x' * 400); T('a long reason is cut, never an error', len(botstate._last('')['w']) == 300)

# ---- 3. the Bot status words ----
T('an older note (no reason) keeps the standard sentence', botstate._scan_words({'c': 'nosetup', 't': 1}, '', 1000) == botstate.SCAN['nosetup'])
T('a signal note is unchanged', botstate._scan_words({'c': 'signal', 't': 1, 'w': 'ignored'}, '', 1000) == botstate.SCAN['signal'])
c = A.app.test_client(); c.get('/api/me', headers={'Authorization': 'Bearer dev:amy@x.com'}); U = 'dev-amy@x.com'
WD = 1700000000 - (1700000000 % 86400) + 86400 * 4 + 12 * 3600
while time.gmtime(WD).tm_wday >= 4: WD += 86400
links.new_key(U); links.set_bot(U, True)
st.x('UPDATE links SET acct=?,seen=? WHERE uid=?', (json.dumps({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'seen': WD}), WD, U))
botstate.note(U, 'XAUUSD', 'nosetup', 'None of the 24 strategies saw a setup on this candle.')
x = botstate.explain(U, False, True, WD + 10)
T('Bot status says why: still "No good setup yet", plus the reason', x['state'] == 'watching' and 'No good setup yet.' in x['why'] and 'None of the 24 strategies saw a setup' in x['why'])
T('no signal ever: no "Last signal" text', 'Last signal' not in x['why'])
st.x("INSERT INTO signals(symbol,side,status,created,uid) VALUES('XAUUSD','buy','closed',?,?)", (WD - 7200, U))
x = botstate.explain(U, False, True, WD + 10)
T('with an earlier signal it says how long ago', 'Last signal: 2 h ago.' in x['why'])
bad = [k for k, ok in R if not ok]; print('\n%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
