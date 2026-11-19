"""R3: the bot knows the market regime (strong trend / quiet / moderate), says it in the Bot status, and can learn to switch a strategy OFF in a regime where its own results are losing. Safe to run twice. Run from the repo folder. Needs R1 and R2 first."""
import os, sys
if not os.path.isdir('backend') or not os.path.isdir('tests'): print('STOP: run this from the repo folder (the one with backend/ and tests/)'); sys.exit(1)
if not os.path.exists('tests/test_nosetup2.py'): print('STOP: R1 and R2 are not in yet. Run apply_r1_reason.py and apply_r2_noscan.py first.'); sys.exit(1)
if os.path.exists('backend/regime.py'): print('skip: R3 is already in'); sys.exit(0)
FILES = {}
def rd(p):
    if p not in FILES: FILES[p] = open(p, encoding='utf-8').read()
    return FILES[p]
def edit(p, old, new, label=''):
    """Replace `old` (must appear exactly once). Nothing is written to disk until every edit has worked."""
    s = rd(p)
    if s.count(old) != 1: print('STOP:', p, 'cannot find exactly once:', old[:70].replace('\n', ' '), '| found', s.count(old)); sys.exit(1)
    FILES[p] = s.replace(old, new); print('ok  ', p, label)

# 1. settings: the owner's switch (off by default) and how many trades a strategy needs in a regime before it can be switched off there
edit('backend/store.py', "'auto_disable_min_trades': '20', 'plans': ''}", "'auto_disable_min_trades': '20', 'regime_switch': os.getenv('REGIME_SWITCH', '0'), 'regime_min_trades': os.getenv('REGIME_MIN_TRADES', '10'), 'plans': ''}", 'settings')

# 2. results per strategy per regime, and the learned off-list
edit('backend/stats.py', "from . import store as st\n", "import json\nfrom . import store as st, regime as rgm\n", 'stats import')
edit('backend/stats.py', "    return {k for k, v in by_strategy(uid).items() if v['n'] >= min_trades and v['avg'] < 0}", '''    return {k for k, v in by_strategy(uid).items() if v['n'] >= min_trades and v['avg'] < 0}

MIN_FLOOR = 5          # never switch a strategy off on fewer trades than this, whatever the setting says (a couple of losses is noise)

def by_regime(uid=''):
    """{strategy: {regime: {n, wins, pnl, avg, win_rate}}} from this scope's closed trades that saved their regime (R1). Older trades have none and are left out.
    Entries opened together for one setup (same grp) count as ONE result. A trade fired by 'a+b' counts for both, as in by_strategy."""
    setups = {}
    for r in st.q("SELECT id,grp,strategy,pnl,reason FROM signals WHERE status='closed' AND pnl IS NOT NULL AND reason IS NOT NULL AND COALESCE(uid,'')=?", (uid,)):
        try: rg = json.loads(r['reason']).get('regime')
        except (TypeError, ValueError, AttributeError): continue
        if rg not in rgm.LABELS: continue
        o = setups.setdefault(r['grp'] or -r['id'], {'strategy': r['strategy'], 'regime': rg, 'pnl': 0.0}); o['pnl'] += r['pnl']
    out = {}
    for o in setups.values():
        for name in (o['strategy'] or '').split('+'):
            if not name: continue
            c = out.setdefault(name, {}).setdefault(o['regime'], {'n': 0, 'wins': 0, 'pnl': 0.0}); c['n'] += 1; c['wins'] += o['pnl'] > 0; c['pnl'] += o['pnl']
    for cells in out.values():
        for c in cells.values(): c['win_rate'] = round(100 * c['wins'] / c['n'], 1); c['avg'] = round(c['pnl'] / c['n'], 2); c['pnl'] = round(c['pnl'], 2)
    return out

def regime_off(uid='', min_trades=None):
    """{strategy: {regimes}}: the regimes where this strategy has enough trades (at least MIN_FLOOR) and a negative average. Used only when regime_switch is on."""
    try: mt = int(min_trades if min_trades is not None else st.fget('regime_min_trades'))
    except (TypeError, ValueError): mt = 10
    mt = max(MIN_FLOOR, mt); out = {}
    for name, cells in by_regime(uid).items():
        bad = {rg for rg, c in cells.items() if c['n'] >= mt and c['avg'] < 0}
        if bad: out[name] = bad
    return out''', 'stats by_regime + regime_off')

# 3. brain: one regime word (same limits as the ADX filter), learned switch-off, regime named in the reason
edit('backend/brain.py', "from . import strategy_info as si\n", "from . import strategy_info as si, regime as rgm\n", 'brain import')
edit('backend/brain.py', """def _filt_text(filt, ax, rev_max, trend_min):
    n = len(filt)
    kinds = {k for _, k in filt}
    why = ('ADX %.0f is a strong trend, so reversal setups are skipped above %g' % (ax, rev_max)) if kinds == {'rev'} else \\
          ('ADX %.0f is a quiet market, so trend setups are skipped below %g' % (ax, trend_min)) if kinds == {'trend'} else \\
          ('ADX %.0f: reversal setups are skipped in strong trends and trend setups in quiet markets' % ax)
    return '%d setup%s seen (%s) but skipped: %s.' % (n, '' if n == 1 else 's', _names([x for x, _ in filt]), why)""",
"""def _filt_text(filt, ax, rev_max, trend_min, rg=''):
    n = len(filt); kinds = {k for _, k in filt}; why = []
    if 'rev' in kinds: why.append('ADX %.0f is a strong trend, so reversal setups are skipped above %g' % (ax, rev_max))
    if 'trend' in kinds: why.append('ADX %.0f is a quiet market, so trend setups are skipped below %g' % (ax, trend_min))
    if 'learned' in kinds: why.append('in a %s market their own results were losing, so they are switched off there' % (rg or 'this'))
    return '%d setup%s seen (%s) but skipped: %s.' % (n, '' if n == 1 else 's', _names([x for x, _ in filt]), '; '.join(why))""", 'brain filt text')
edit('backend/brain.py', "adx_rev_max=28.0, solo=(), info=None):", "adx_rev_max=28.0, solo=(), info=None, off_reg=None):", 'brain signature')
edit('backend/brain.py', "ax = adx(m15)[-1]; hits = []; ran = 0; filt = []", "ax = adx(m15)[-1]; hits = []; ran = 0; filt = []; rg = rgm.of(ax, adx_trend_min, adx_rev_max)", 'brain regime')
edit('backend/brain.py', "filt.append((r['name'], 'trend')); continue\n        hits.append(r)", "filt.append((r['name'], 'trend')); continue\n        if off_reg and rg in off_reg.get(r['name'], ()): filt.append((r['name'], 'learned')); continue          # R3: lost money in this regime before\n        hits.append(r)", 'brain learned off')
edit('backend/brain.py', "_filt_text(filt, ax, adx_rev_max, adx_trend_min)", "_filt_text(filt, ax, adx_rev_max, adx_trend_min, rg)", 'brain call')
edit('backend/brain.py', "'regime': 'strong trend' if ax > adx_rev_max else 'quiet' if ax < adx_trend_min else 'moderate',", "'regime': rg,", 'brain why regime')

# 4. scanner and API
edit('backend/app.py', 'reason as rsn,', 'reason as rsn, regime as rgm,', 'app import')
edit('backend/app.py', "    info = {}; s = brain.evaluate(m15, h1, int(st.fget('min_confluence')), st.fget('rr'), off, solo=solo, info=info)\n    if not s: botstate.note(uid, sym, 'nosetup', info.get('text', '')); return",
"    orf = stats.regime_off(uid) if st.get('regime_switch') == '1' else None          # R3: strategies that keep losing in this kind of market (off unless the owner switches it on)\n    info = {}; s = brain.evaluate(m15, h1, int(st.fget('min_confluence')), st.fget('rr'), off, solo=solo, info=info, off_reg=orf)\n    if not s: botstate.note(uid, sym, 'nosetup', rgm.note_text(info)); return", 'scan')
edit('backend/app.py', "@app.post('/api/admin/plans')\n@need(admin=True)\ndef admin_plans(u):", '''@app.get('/api/admin/regimes')
@need(admin=True)
def admin_regimes(u):
    """R3: how each strategy did in each market regime (the owner's closed trades that saved their regime), and which ones the learned switch has turned off."""
    mt = max(stats.MIN_FLOOR, int(st.fget('regime_min_trades'))); off = stats.regime_off(_mine(u), mt); rows = []
    for n, cells in sorted(stats.by_regime(_mine(u)).items()):
        for rg, c in sorted(cells.items()): rows.append(dict(c, strategy=n, name=si.name(n), regime=rg, off=rg in off.get(n, ())))
    return jsonify(switch=st.get('regime_switch') == '1', min_trades=mt, rows=rows)

@app.post('/api/admin/plans')
@need(admin=True)
def admin_plans(u):''', 'admin endpoint')

# 5. the Bot status note: a longer cap, and the two R2 checks that pinned the old wording
edit('backend/botstate.py', "'w': str(why)[:240]}", "'w': str(why)[:300]}", 'note length')
edit('tests/test_nosetup2.py', "n['w'] == 'None of the 1 strategies saw a setup on this candle.'", "n['w'].startswith('None of the 1 strategies saw a setup on this candle.')", 'R2 test wording')
edit('tests/test_nosetup2.py', "len(botstate._last('')['w']) == 240", "len(botstate._last('')['w']) == 300", 'R2 test cap')

NEW = {}
NEW['backend/regime.py'] = r'''"""R3: the market regime, in one place. Pure (no database), so the backtest tool can use it too.
The limits are the ones the brain already uses to skip setups: ADX above rev_max = strong trend (reversal setups skipped),
ADX below trend_min = quiet (trend setups skipped), in between = moderate (both kinds allowed)."""
STRONG, QUIET, MODERATE = 'strong trend', 'quiet', 'moderate'
LABELS = (STRONG, QUIET, MODERATE)

def _ok(x):
    try: x = float(x)
    except (TypeError, ValueError): return None
    return x if x == x and abs(x) != float('inf') else None

def of(ax, trend_min=18.0, rev_max=28.0):
    """The regime for this ADX. A missing or broken ADX counts as moderate (nothing is skipped on a guess)."""
    x = _ok(ax)
    if x is None: return MODERATE
    return STRONG if x > rev_max else QUIET if x < trend_min else MODERATE

def sentence(rg, ax):
    """One plain sentence about the market, or '' when there is nothing true to say."""
    x = _ok(ax)
    t = {STRONG: 'Market: strong trend (ADX %.0f), so trend strategies lead and reversal setups are skipped.',
         QUIET: 'Market: quiet and ranging (ADX %.0f), so reversal strategies lead and trend setups are skipped.',
         MODERATE: 'Market: moderate (ADX %.0f), so both kinds of strategy are allowed.'}.get(rg)
    return (t % x) if t and x is not None else ''

def note_text(info):
    """The 'no setup' reason from brain.evaluate(info=...) plus one sentence about the market."""
    info = info or {}; t = str(info.get('text') or ''); ax = info.get('adx')
    s = sentence(of(ax), ax) if ax is not None else ''
    return (t + ' ' + s).strip()
'''
NEW['tests/test_regime3.py'] = r'''"""R3 checks: the regime word, results per strategy per regime, the learned switch-off (off by default), the Bot status sentence and the owner's table. No network. Run: python tests/test_regime3.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, '_regime3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, botstate, stats, regime as rg
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

# ---- 1. the regime word ----
T('regime.of: above 28 strong trend, below 18 quiet, between (and at the limits) moderate', rg.of(40) == 'strong trend' and rg.of(10) == 'quiet' and rg.of(22) == 'moderate' and rg.of(28) == 'moderate' and rg.of(18) == 'moderate')
T('a missing or broken ADX is moderate, never a guess', rg.of(None) == 'moderate' and rg.of(float('nan')) == 'moderate' and rg.of('x') == 'moderate' and rg.of(float('inf')) == 'moderate')
T('custom limits are honoured', rg.of(25, 18, 24) == 'strong trend' and rg.of(25, 30, 40) == 'quiet')
T('sentence: names the market and the ADX', 'strong trend (ADX 31)' in rg.sentence('strong trend', 31.2) and 'quiet and ranging (ADX 12)' in rg.sentence('quiet', 12) and 'moderate (ADX 22)' in rg.sentence('moderate', 22))
T('sentence: nothing true to say gives empty', rg.sentence('weird', 20) == '' and rg.sentence('quiet', None) == '' and rg.sentence('quiet', float('nan')) == '')
T('note_text joins the reason and the market; no ADX means the reason alone', rg.note_text({'text': 'None looked.', 'adx': 12.0}).startswith('None looked. Market: quiet and ranging (ADX 12)') and rg.note_text({'text': 'Not enough.'}) == 'Not enough.' and rg.note_text(None) == '')

# ---- 2. results per strategy per regime (from the regime each trade saved at R1) ----
NOW = int(time.time())
def sig(strategy, pnl, regime, grp=None, reason='auto', uid=None, status='closed'):
    rs = json.dumps({'regime': regime, 'adx': 20}) if reason == 'auto' else reason
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,reason,grp,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ('XAUUSD', 'buy', 100.0, 99.0, 102.0, status, NOW - 5000, pnl, NOW - 4000, strategy, rs, grp, uid))
for _ in range(6): sig('fake_a', -2.0, 'quiet')
for _ in range(6): sig('fake_a', 3.0, 'strong trend')
for _ in range(4): sig('fake_b', -5.0, 'quiet')
g = sig('fake_c', -1.0, 'quiet', None)
st.x('UPDATE signals SET grp=? WHERE id=?', (g, g)); sig('fake_c', -1.0, 'quiet', g); sig('fake_c', -1.0, 'quiet', g)
sig('x_one+x_two', 4.0, 'strong trend')
sig('fake_a', -100.0, None, reason=None); sig('fake_a', -100.0, None, reason='not json'); sig('fake_a', -100.0, 'weird'); sig('fake_a', -100.0, 'quiet', status='open')
br = stats.by_regime('')
T('per strategy per regime: count, wins, average, win rate', br['fake_a']['quiet'] == {'n': 6, 'wins': 0, 'pnl': -12.0, 'win_rate': 0.0, 'avg': -2.0} and br['fake_a']['strong trend']['avg'] == 3.0 and br['fake_a']['strong trend']['win_rate'] == 100.0)
T('trades with no saved regime, garbage, an unknown regime or still open are left out', br['fake_a']['quiet']['n'] == 6 and set(br['fake_a']) == {'quiet', 'strong trend'})
T('entries of one setup (same group) count as ONE result, their money added', br['fake_c']['quiet']['n'] == 1 and br['fake_c']['quiet']['pnl'] == -3.0)
T('a trade from "a+b" counts for both strategies', br['x_one']['strong trend']['n'] == 1 and br['x_two']['strong trend']['n'] == 1)
T('another person\'s trades are not mixed in', stats.by_regime('dev-nobody@x.com') == {})
T('learned off-list: only where there are enough trades AND the average is negative', stats.regime_off('', 5) == {'fake_a': {'quiet'}})
T('not enough trades yet: nothing is switched off', stats.regime_off('', 8) == {} and 'fake_b' not in stats.regime_off('', 5))
T('the setting can never go below the floor of 5 trades', stats.regime_off('', 1) == {'fake_a': {'quiet'}} and stats.MIN_FLOOR == 5)
T('the settings exist and are OFF by default', st.DEFAULTS['regime_switch'] == '0' and st.DEFAULTS['regime_min_trades'] == '10' and st.get('regime_switch') == '0')

# ---- 3. the brain skips a strategy only in the regime where it lost ----
def mk(name, side='buy', off=3.0):
    def f(m, h): return {'side': side, 'sl': m[-1]['c'] - off if side == 'buy' else m[-1]['c'] + off, 'name': name}
    f.__name__ = name; return f
real_all, real_adx = brain.ALL, brain.adx
t0 = int(time.time()) // 900 * 900 - 900 * 200
M = [{'t': t0 + 900 * i, 'o': 2000, 'h': 2001 + (i % 3) * 0.2, 'l': 1999 - (i % 2) * 0.2, 'c': 2000 + (i % 2) * 0.5, 'v': 1} for i in range(200)]
def ev(fns, adxv, **kw):
    brain.ALL = fns; brain.adx = lambda m: [adxv] * len(m); info = {}
    try: r = brain.evaluate(M, M, min_conf=1, info=info, **kw)
    finally: brain.ALL = real_all; brain.adx = real_adx
    return r, info
r, i = ev([mk('fake_a')], 10.0); T('without the learned list it trades as before', r and r['side'] == 'buy' and r['why']['regime'] == 'quiet')
r, i = ev([mk('fake_a')], 10.0, off_reg={'fake_a': {'quiet'}}); T('in the regime it lost in, it is skipped and says why', r is None and i['code'] == 'adx' and i['filtered'] == ['fake_a'] and 'their own results were losing' in i['text'] and 'quiet' in i['text'])
r, i = ev([mk('fake_a')], 40.0, off_reg={'fake_a': {'quiet'}}); T('in another regime it still trades', r and r['why']['regime'] == 'strong trend')
r, i = ev([mk('fake_a'), mk('fake_z')], 10.0, off_reg={'fake_a': {'quiet'}}); T('other strategies are not touched', r and r['strategy'] == 'fake_z' and r['score'] == 1)
r, i = ev([mk('fake_a')], 10.0, off_reg={}); T('an empty list changes nothing', r and r['side'] == 'buy')
brain.TREND.add('fake_t'); r, i = ev([mk('fake_t'), mk('fake_a')], 10.0, off_reg={'fake_a': {'quiet'}}); brain.TREND.discard('fake_t')
T('the ADX filter and the learned switch can both speak (one strategy each)', r is None and i['filtered'] == ['fake_t', 'fake_a'] and 'quiet market' in i['text'] and 'switched off there' in i['text'])

# ---- 4. the scanner uses it only when the owner switches it on, and the Bot status names the market ----
risk.global_gate = lambda now=None, uid='': (True, '')
risk.symbol_gate = lambda *a, **k: (True, 'ok')
BAR = int(time.time()) // 900 * 900 - 900
st.put('min_confluence', '1'); st.put('max_open', '10'); st.put('max_open_ceiling', '10'); st.put('max_trades_day', '0'); st.put('regime_min_trades', '5')
def scan(adxv):
    st.x("DELETE FROM signals WHERE status='pending'"); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._last_scan.clear()
    A.bars.merge('XAUUSD', 'M15', [[BAR - 900 * k, 2000, 2001, 1999, 2000, 1] for k in range(130)], uid='')
    A.bars.merge('XAUUSD', 'H1', [[BAR - 3600 * k, 2000, 2001, 1999, 2000, 1] for k in range(10)], uid='')
    brain.ALL = [mk('fake_a')]; brain.adx = lambda m: [adxv] * len(m)
    try: A._scan('XAUUSD', '')
    finally: brain.ALL = real_all; brain.adx = real_adx
    return st.q("SELECT COUNT(*) n FROM signals WHERE status='pending'", (), True)['n']
st.put('regime_switch', '0'); T('switch OFF: the strategy trades even in the regime where it lost', scan(10.0) == 1)
st.put('regime_switch', '1'); n = scan(10.0)
w = botstate._last('')['w']
T('switch ON: the same strategy is skipped in a quiet market', n == 0 and botstate._last('')['c'] == 'nosetup')
T('the Bot status note says why and names the market', 'switched off there' in w and 'Market: quiet and ranging (ADX 10)' in w)
T('switch ON but a different regime: it trades', scan(40.0) == 1)
T('the trade saved with the regime it was taken in', json.loads(st.q("SELECT reason FROM signals WHERE status='pending'", (), True)['reason'])['regime'] == 'strong trend')

# ---- 5. the owner's table and the settings route ----
c = A.app.test_client(); H = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=H)
d = c.get('/api/admin/regimes', headers=H).get_json()
row = next(x for x in d['rows'] if x['strategy'] == 'fake_a' and x['regime'] == 'quiet')
T('GET /api/admin/regimes: the table, with the switch state and which cells are off', d['switch'] is True and d['min_trades'] == 5 and row['n'] == 6 and row['avg'] == -2.0 and row['off'] is True and row['name'] == 'Fake a')
T('a cell that is fine is not marked off', next(x for x in d['rows'] if x['strategy'] == 'fake_a' and x['regime'] == 'strong trend')['off'] is False)
c.get('/api/me', headers={'Authorization': 'Bearer dev:amy@x.com'})
T('only the owner can read it', c.get('/api/admin/regimes', headers={'Authorization': 'Bearer dev:amy@x.com'}).status_code in (401, 403) and c.get('/api/admin/regimes').status_code in (401, 403))
r = c.post('/api/admin/settings', json={'regime_switch': '0', 'regime_min_trades': '12'}, headers=H).get_json()
T('the owner can set both settings', r['regime_switch'] == '0' and r['regime_min_trades'] == '12')
bad = [k for k, ok in R if not ok]; print('\n%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
'''
for p in NEW:
    if os.path.exists(p): print('STOP: already exists:', p); sys.exit(1)
for p, txt in FILES.items(): open(p, 'w', encoding='utf-8').write(txt)
for p, txt in NEW.items(): open(p, 'w', encoding='utf-8').write(txt); print('new ', p)
print('\nR3 done. Now run: python tests/test_regime3.py')
