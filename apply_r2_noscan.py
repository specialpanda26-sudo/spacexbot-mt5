"""R2: when the bot looks at a candle and does NOT trade, it now says exactly why (in the Bot status card). Safe to run twice. Run from the repo folder. Needs R1 first."""
import os, sys
if not os.path.isdir('backend') or not os.path.isdir('tests'): print('STOP: run this from the repo folder (the one with backend/ and tests/)'); sys.exit(1)
if not os.path.exists('backend/reason.py'): print('STOP: R1 is not in yet. Run apply_r1_reason.py first.'); sys.exit(1)
if os.path.exists('tests/test_nosetup2.py'): print('skip: R2 is already in'); sys.exit(0)
FILES = {}
def rd(p):
    if p not in FILES: FILES[p] = open(p, encoding='utf-8').read()
    return FILES[p]
def edit(p, old, new, label=''):
    """Replace `old` (must appear exactly once). Nothing is written to disk until every edit has worked."""
    s = rd(p)
    if s.count(old) != 1: print('STOP:', p, 'cannot find exactly once:', old[:70].replace('\n', ' '), '| found', s.count(old)); sys.exit(1)
    FILES[p] = s.replace(old, new); print('ok  ', p, label)

# 1. brain: evaluate() takes an optional info dict and fills it with the reason when there is no setup. What it returns does not change.
edit('backend/brain.py', """from .indicators import atr, adx

def evaluate(m15, h1, min_conf=2, rr=2.0, off=(), adx_trend_min=18.0, adx_rev_max=28.0, solo=()):
    if len(m15) < 120: return None
    ax = adx(m15)[-1]; hits = []
""", """from .indicators import atr, adx
from . import strategy_info as si

def _say(info, code, text, **kw):
    \"\"\"Tell the caller WHY there is no setup. `info` is an optional dict the caller passes in; it never changes what evaluate returns.\"\"\"
    if info is not None: info.clear(); info.update(dict(kw, code=code, text=text))

def _names(xs):
    xs = list(xs); return ', '.join(si.name(x) for x in xs[:3]) + (' and %d more' % (len(xs) - 3) if len(xs) > 3 else '')

def _filt_text(filt, ax, rev_max, trend_min):
    n = len(filt)
    kinds = {k for _, k in filt}
    why = ('ADX %.0f is a strong trend, so reversal setups are skipped above %g' % (ax, rev_max)) if kinds == {'rev'} else \\
          ('ADX %.0f is a quiet market, so trend setups are skipped below %g' % (ax, trend_min)) if kinds == {'trend'} else \\
          ('ADX %.0f: reversal setups are skipped in strong trends and trend setups in quiet markets' % ax)
    return '%d setup%s seen (%s) but skipped: %s.' % (n, '' if n == 1 else 's', _names([x for x, _ in filt]), why)

def evaluate(m15, h1, min_conf=2, rr=2.0, off=(), adx_trend_min=18.0, adx_rev_max=28.0, solo=(), info=None):
    if len(m15) < 120: _say(info, 'history', 'Not enough candle history yet (%d of 120 candles).' % len(m15)); return None
    ax = adx(m15)[-1]; hits = []; ran = 0; filt = []
""", 'brain helpers + start')
edit('backend/brain.py', """        if fn.__name__ in off: continue
        try: r = fn(m15, h1)""", """        if fn.__name__ in off: continue
        ran += 1
        try: r = fn(m15, h1)""", 'brain count')
edit('backend/brain.py', """        if ax and r['name'] in REVERSION and ax > adx_rev_max: continue
        if ax and r['name'] in TREND and ax < adx_trend_min: continue
""", """        if ax and r['name'] in REVERSION and ax > adx_rev_max: filt.append((r['name'], 'rev')); continue
        if ax and r['name'] in TREND and ax < adx_trend_min: filt.append((r['name'], 'trend')); continue
""", 'brain filter')
edit('backend/brain.py', """    if len(buys) == len(sells): return None
""", """    if len(buys) == len(sells):
        if not hits and filt: _say(info, 'adx', _filt_text(filt, ax, adx_rev_max, adx_trend_min), ran=ran, adx=round(ax, 1), filtered=[n for n, _ in filt])
        elif not hits: _say(info, 'none', ('None of the %d strategies saw a setup on this candle.' % ran) if ran else 'All strategies are switched off.', ran=ran, adx=round(ax, 1))
        else: _say(info, 'split', 'The strategies disagreed: %s said buy, %s said sell, so it stayed out.' % (_names([x['name'] for x in buys]), _names([x['name'] for x in sells])), ran=ran, adx=round(ax, 1))
        return None
""", 'brain none/adx/split')
edit('backend/brain.py', """    if len(grp) < min_conf and not any(x.get('solo') for x in grp): return None
""", """    if len(grp) < min_conf and not any(x.get('solo') for x in grp):
        _say(info, 'conf', 'Only %d strateg%s (%s) saw a %s, and %d must agree before it trades.' % (len(grp), 'y' if len(grp) == 1 else 'ies', _names([x['name'] for x in grp]), side, min_conf), ran=ran, adx=round(ax, 1), filtered=[n for n, _ in filt]); return None
""", 'brain conf')
edit('backend/brain.py', """    if not (0.5 * a <= dist <= 3.5 * a): return None
""", """    if not (0.5 * a <= dist <= 3.5 * a):
        _say(info, 'stop', 'A %s setup (%s) was found, but its stop loss was %.1f ATR away and the bot only allows 0.5 to 3.5.' % (side, _names([x['name'] for x in grp]), dist / a if a else 0.0), ran=ran, adx=round(ax, 1)); return None
""", 'brain stop')

# 2. scanner: pass the info dict in and save the reason with the 'no setup' note
edit('backend/app.py', "    s = brain.evaluate(m15, h1, int(st.fget('min_confluence')), st.fget('rr'), off, solo=solo)\n    if not s: botstate.note(uid, sym, 'nosetup'); return",
"    info = {}; s = brain.evaluate(m15, h1, int(st.fget('min_confluence')), st.fget('rr'), off, solo=solo, info=info)\n    if not s: botstate.note(uid, sym, 'nosetup', info.get('text', '')); return", 'scan note')

# 3. Bot status: the 'no setup' sentence now carries the reason and how long ago the last signal was
edit('backend/botstate.py', "'w': str(why)[:120]}", "'w': str(why)[:240]}", 'note length')
edit('backend/botstate.py', "why=SCAN[n['c']], code=n['c'])", "why=_scan_words(n, sc, now), code=n['c'])", 'explain wording')
edit('backend/botstate.py', "def explain(uid, admin, paid=True, now=None):", '''def _quiet_for(sc, now):
    """' Last signal: 3 h ago.' for this scope, or '' when it never had one."""
    r = st.q("SELECT MAX(created) c FROM signals WHERE COALESCE(uid,'')=?", (sc or '',), True) or {}
    c = r.get('c')
    if not c: return ''
    s = max(0, int(now - c)); t = '%d min' % (s // 60) if s < 5400 else '%d h' % round(s / 3600) if s < 129600 else '%d days' % round(s / 86400)
    return ' Last signal: %s ago.' % t

def _scan_words(n, sc='', now=None):
    """The scanner note in words. A 'nosetup' note that carries a reason says WHY nothing was taken; an older note (no reason) keeps the standard sentence."""
    base = SCAN[n['c']]
    if n.get('c') != 'nosetup' or not n.get('w'): return base
    return 'Looked at the market. No good setup yet. ' + str(n['w']).strip() + _quiet_for(sc, now or time.time())

def explain(uid, admin, paid=True, now=None):''', 'explain helper')

NEW = {}
NEW['tests/test_nosetup2.py'] = r'''"""R2 checks: when the bot does not trade, it says why. brain.evaluate(info=...), the scanner note, and the Bot status wording. No network. Run: python tests/test_nosetup2.py"""
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
T('after a candle with no setup the note has the reason', n and n['c'] == 'nosetup' and n['w'] == 'None of the 1 strategies saw a setup on this candle.')
botstate.note('', 'XAUUSD', 'nosetup', 'x' * 400); T('a long reason is cut, never an error', len(botstate._last('')['w']) == 240)

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
'''
for p in NEW:
    if os.path.exists(p): print('STOP: already exists:', p); sys.exit(1)
for p, txt in FILES.items(): open(p, 'w', encoding='utf-8').write(txt)
for p, txt in NEW.items(): open(p, 'w', encoding='utf-8').write(txt); print('new ', p)
print('\nR2 done. Now run: python tests/test_nosetup2.py')
