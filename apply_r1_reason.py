"""R1: the bot writes down WHY it took each trade, and the Trades pop-up shows it. Safe to run twice. Run from the repo folder (the one that holds backend/)."""
import os, sys
if not os.path.isdir('backend') or not os.path.isdir('tests'): print('STOP: run this from the repo folder (the one with backend/ and tests/)'); sys.exit(1)
if os.path.exists('backend/reason.py'): print('skip: R1 is already in'); sys.exit(0)
FILES = {}
def rd(p):
    if p not in FILES: FILES[p] = open(p, encoding='utf-8').read()
    return FILES[p]
def edit(p, old, new, label=''):
    """Replace `old` (must appear exactly once). Nothing is written to disk until every edit has worked."""
    s = rd(p)
    if s.count(old) != 1: print('STOP:', p, 'cannot find exactly once:', old[:70].replace('\n', ' '), '| found', s.count(old)); sys.exit(1)
    FILES[p] = s.replace(old, new); print('ok  ', p, label)

# 1. database: one new column on signals (SQLite migration, Postgres schema, supabase_schema.sql)
edit('backend/store.py', "for col in ('uid TEXT', 'broker TEXT', 'grp INTEGER'):", "for col in ('uid TEXT', 'broker TEXT', 'grp INTEGER', 'reason TEXT'):", 'sqlite column')
edit('backend/store.py', "ALTER TABLE signals ADD COLUMN IF NOT EXISTS grp BIGINT;\n", "ALTER TABLE signals ADD COLUMN IF NOT EXISTS grp BIGINT;\nALTER TABLE signals ADD COLUMN IF NOT EXISTS reason TEXT;\n", 'postgres column')
edit('supabase_schema.sql', "ALTER TABLE signals ADD COLUMN IF NOT EXISTS grp BIGINT;\n", "ALTER TABLE signals ADD COLUMN IF NOT EXISTS grp BIGINT;\nALTER TABLE signals ADD COLUMN IF NOT EXISTS reason TEXT;\n", 'supabase_schema.sql')

# 2. brain: the result now says which strategies agreed, the market state, and how the stop and target were set
edit('backend/brain.py', """    return {'side': side, 'entry': round(entry, 5), 'sl': round(sl, 5), 'tp': round(tp, 5),
            'strategy': '+'.join(x['name'] for x in grp), 'score': len(grp), 'adx': round(ax, 1)}""",
"""    why = {'agree': [x['name'] for x in grp], 'against': len(sells if side == 'buy' else buys), 'adx': round(ax, 1),
           'regime': 'strong trend' if ax > adx_rev_max else 'quiet' if ax < adx_trend_min else 'moderate',
           'atr': round(a, 5), 'sl_atr': round(dist / a, 2) if a else None, 'rr': round(abs(tp - entry) / dist, 2) if dist else None,
           'own_tp': bool(len(grp) == 1 and grp[0].get('tp') and tp == grp[0]['tp']), 'solo': len(grp) < min_conf, 'min_conf': min_conf}
    return {'side': side, 'entry': round(entry, 5), 'sl': round(sl, 5), 'tp': round(tp, 5),
            'strategy': '+'.join(x['name'] for x in grp), 'score': len(grp), 'adx': round(ax, 1), 'why': why}""", 'brain why')

# 3. scanner: store the reason with every new signal (and with each extra entry of a multi-entry setup)
edit('backend/app.py', 'strategy_info as si,', 'strategy_info as si, reason as rsn,', 'import')
edit('backend/app.py', """    sid = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
         (sym, s['side'], s['entry'], s['sl'], s['tp'], multi.share(base, n), s['strategy'], s['score'], 'pending', int(time.time()), uid or None))""",
"""    rz = rsn.pack(s)
    sid = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
         (sym, s['side'], s['entry'], s['sl'], s['tp'], multi.share(base, n), s['strategy'], s['score'], 'pending', int(time.time()), uid or None, rz))""", 'scan insert 1')
edit('backend/app.py', """            sib = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (sym, s['side'], s['entry'], s['sl'], s['tp'], multi.share(base, n), s['strategy'], s['score'], 'pending', int(time.time()), uid or None, sid))""",
"""            sib = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (sym, s['side'], s['entry'], s['sl'], s['tp'], multi.share(base, n), s['strategy'], s['score'], 'pending', int(time.time()), uid or None, sid, rz))""", 'scan insert 2')

# 4. the trade pop-up (GET /api/trade/<id>) and the journal rows carry the reason
edit('backend/tradeview.py', 'from . import store as st, bars, journal as jn, strategy_info as si', 'from . import store as st, bars, journal as jn, strategy_info as si, reason as rsn', 'tradeview import')
edit('backend/tradeview.py', 'note,broker,status FROM signals "', 'note,broker,status,reason FROM signals "', 'tradeview select')
edit('backend/tradeview.py', "'opened_by': 'bot', 'closed_by': why,", "'why_taken': rsn.lines(r.get('reason'), r['strategy']), 'opened_by': 'bot', 'closed_by': why,", 'tradeview reason')
edit('backend/journal.py', 'from . import store as st, strategy_info as si', 'from . import store as st, strategy_info as si, reason as rsn', 'journal import')
edit('backend/journal.py', 'created,note,broker FROM signals "', 'created,note,broker,reason FROM signals "', 'journal select')
edit('backend/journal.py', "'tp': r.get('tp'), 'lots': r.get('lots')})", "'tp': r.get('tp'), 'lots': r.get('lots'), 'why': rsn.short(r.get('reason'))})", 'journal why')

# 5. the page: a "Why the bot took this trade" block in the trade pop-up
edit('static/index.html', '  function render(d) {\n    var buy = d.side === "buy", win',
'''  function whyBlock(d) {
    var L = d.why_taken || [];
    if (!L.length) return '<p style="margin:10px 0 0;font-size:13px;color:var(--muted)">Why the bot took it: not saved. This trade was opened before the bot started writing its reasons down.</p>';
    return '<h3 style="margin:14px 0 6px;font-size:15px">Why the bot took this trade</h3><ul class="note" style="margin:0 0 8px;padding-left:18px">' + L.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") + "</ul>";
  }
  function render(d) {
    var buy = d.side === "buy", win''', 'page whyBlock')
edit('static/index.html', 'rows.join("") + "</dl>" +', 'rows.join("") + "</dl>" + whyBlock(d) +', 'page insert')

edit('tests/test_trade9b.py', "'candles', 'status', 'opened_by', 'closed_by'}", "'candles', 'status', 'opened_by', 'closed_by', 'why_taken'}", 'test_trade9b key list')

NEW = {}
NEW['backend/reason.py'] = r'''"""R1: why the bot took a trade, in plain words. brain.evaluate() returns a 'why' dict; pack() saves it as JSON in signals.reason;
lines() turns it into sentences for the trade pop-up and short() into one line for the journal. Facts only: nothing here is invented, and a trade
saved before R1 has no reason (lines() = [], short() = ''), so the page says so instead of guessing."""
import json
from . import strategy_info as si

def pack(s):
    """A brain result -> JSON text for signals.reason. Never raises (a failure just means no reason is saved)."""
    try:
        w = dict(s.get('why') or {})
        w.setdefault('agree', [x for x in str(s.get('strategy') or '').split('+') if x])
        w.setdefault('adx', s.get('adx'))
        for k in ('side', 'entry', 'sl', 'tp', 'score'): w[k] = s.get(k)
        return json.dumps(w)[:1500]
    except Exception: return ''

def _load(raw):
    try: j = json.loads(raw) if raw else None
    except (TypeError, ValueError): return None
    return j if isinstance(j, dict) else None

def _n(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError): return None

def lines(raw, strategy=''):
    """Plain sentences, in order: the setup, the market, the stop, the target. [] when nothing was saved."""
    j = _load(raw)
    if not j: return []
    out = []; ag = [x for x in (j.get('agree') or []) if x] or [x for x in str(strategy or '').split('+') if x]
    names = ', '.join(si.name(x) for x in ag); side = str(j.get('side') or '').lower()
    if ag:
        k = len(ag); ag_n = int(_n(j.get('against')) or 0)
        t = ('%d strategies agreed on a %s: %s.' % (k, side, names)) if k > 1 else ('One strategy took this %s: %s.' % (side, names))
        if k == 1 and j.get('solo'): t += ' It is allowed to trade on its own.'
        if ag_n: t += ' %d other strateg%s pointed the other way.' % (ag_n, 'y' if ag_n == 1 else 'ies')
        out.append(t)
    adx = _n(j.get('adx')); rg = j.get('regime')
    if adx is not None:
        out.append('Market strength (ADX) was %.1f: %s.' % (adx, {'strong trend': 'a strong trend, so trend setups are favoured and reversal setups are skipped',
                   'quiet': 'a quiet, ranging market', 'moderate': 'a moderate market, both kinds of setup were allowed'}.get(rg, 'recorded for this trade')))
    sa = _n(j.get('sl_atr'))
    if sa is not None: out.append('The stop loss is %.1f x ATR (the normal candle range) from the entry; with several strategies the widest stop is used.' % sa)
    rr = _n(j.get('rr'))
    if rr is not None: out.append('The target is %s: %.1f times the distance to the stop.' % ('set by the strategy itself' if j.get('own_tp') else 'the usual reward-to-risk', rr))
    px = [(l, _n(j.get(k))) for l, k in (('entry', 'entry'), ('stop', 'sl'), ('target', 'tp'))]
    if all(v is not None for _, v in px): out.append('Planned prices: ' + ', '.join('%s %s' % (l, ('%.5f' % v).rstrip('0').rstrip('.')) for l, v in px) + '.')
    return out

def short(raw):
    """One short line for the journal list, or ''."""
    j = _load(raw)
    if not j: return ''
    ag = [x for x in (j.get('agree') or []) if x]; p = []
    if ag: p.append('%d strateg%s agreed' % (len(ag), 'y' if len(ag) == 1 else 'ies'))
    adx = _n(j.get('adx'))
    if adx is not None: p.append('ADX %.0f' % adx)
    rr = _n(j.get('rr'))
    if rr is not None: p.append('reward %.1fx risk' % rr)
    return ' · '.join(p)
'''
NEW['tests/test_reason1.py'] = r'''"""R1 checks: the bot saves WHY it took a trade, and the journal and trade pop-up show it. No network. Run: python tests/test_reason1.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, '_reason1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, brain, risk, reason as rsn
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)

# ---- 1. the real brain explains itself (two fake strategies agree) ----
def mk(name, side):
    def f(m, h): return {'side': side, 'sl': m[-1]['c'] - 3.0 if side == 'buy' else m[-1]['c'] + 3.0, 'name': name}
    f.__name__ = name; return f
real_all = brain.ALL; t0 = int(time.time()) // 900 * 900 - 900 * 200
M = [{'t': t0 + 900 * i, 'o': 2000, 'h': 2001 + (i % 3) * 0.2, 'l': 1999 - (i % 2) * 0.2, 'c': 2000 + (i % 2) * 0.5, 'v': 1} for i in range(200)]
brain.ALL = [mk('fake_a', 'buy'), mk('fake_b', 'buy'), mk('fake_c', 'sell')]
r = brain.evaluate(M, M, 2, 2.0)
brain.ALL = real_all
T('brain returns a why with the agreeing strategies', r and r['why']['agree'] == ['fake_a', 'fake_b'] and r['score'] == 2)
T('why counts the strategy that disagreed', r and r['why']['against'] == 1)
T('why has the market state, the stop in ATRs and the reward-to-risk', r and r['why']['regime'] in ('strong trend', 'quiet', 'moderate') and r['why']['sl_atr'] > 0 and r['why']['rr'] == 2.0 and r['why']['own_tp'] is False)
T('the old keys of the brain result are unchanged', r and all(k in r for k in ('side', 'entry', 'sl', 'tp', 'strategy', 'score', 'adx')))

# ---- 2. pack / lines / short ----
raw = rsn.pack(r); ln = rsn.lines(raw, r['strategy'])
T('pack gives JSON text', isinstance(raw, str) and json.loads(raw)['agree'] == ['fake_a', 'fake_b'])
T('lines: the setup, the market, the stop, the target and the prices', len(ln) == 5 and 'agreed' in ln[0] and 'ADX' in ln[1] and 'stop loss' in ln[2] and 'target' in ln[3] and ln[4].startswith('Planned prices'))
T('lines: the other-way strategy is mentioned', '1 other strategy pointed the other way' in ln[0])
T('short: one line', rsn.short(raw).startswith('2 strategies agreed') and 'ADX' in rsn.short(raw))
T('nothing saved / garbage: empty, never an error', rsn.lines(None) == [] and rsn.lines('') == [] and rsn.lines('not json') == [] and rsn.lines('[1]') == [] and rsn.short(None) == '' and rsn.short('{{') == '')
T('pack of an old-style result (no why) still works', json.loads(rsn.pack({'side': 'buy', 'entry': 1.0, 'sl': 0.9, 'tp': 1.2, 'strategy': 'x+y', 'score': 2, 'adx': 20}))['agree'] == ['x', 'y'])
T('pack never raises on junk', rsn.pack(None) == '' or isinstance(rsn.pack(None), str))

# ---- 3. the scanner saves it with the signal (and with every entry of a multi-entry setup) ----
risk.global_gate = lambda now=None, uid='': (True, '')
risk.symbol_gate = lambda *a, **k: (True, 'ok')
WHY = {'agree': ['fake_a', 'fake_b'], 'against': 0, 'adx': 24.3, 'regime': 'moderate', 'atr': 2.0, 'sl_atr': 1.5, 'rr': 2.0, 'own_tp': False, 'solo': False, 'min_conf': 2}
brain.evaluate = lambda *a, **k: {'side': 'buy', 'entry': 2000.0, 'sl': 1997.0, 'tp': 2006.0, 'strategy': 'fake_a+fake_b', 'score': 2, 'adx': 24.3, 'why': WHY}
BAR = int(time.time()) // 900 * 900 - 900
def run(uid=''):
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); A._last_scan.clear()
    A.bars.merge('XAUUSD', 'M15', [[BAR - 900 * i, 2000, 2001, 1999, 2000, 1] for i in range(130)], uid=uid)
    A.bars.merge('XAUUSD', 'H1', [[BAR - 3600 * i, 2000, 2001, 1999, 2000, 1] for i in range(10)], uid=uid)
    A._scan('XAUUSD', uid); return st.q('SELECT * FROM signals ORDER BY id')
st.put('max_open', '10'); st.put('max_open_ceiling', '10'); st.put('max_trades_day', '0')
rows = run()
T('a new signal is saved with its reason', len(rows) == 1 and rows[0]['reason'] and json.loads(rows[0]['reason'])['adx'] == 24.3 and json.loads(rows[0]['reason'])['entry'] == 2000.0)
st.put('multi_entries', '3'); st.put('multi_min_score', '2'); rows = run()
T('every entry of a multi-entry setup carries the same reason', len(rows) == 3 and len({r['reason'] for r in rows}) == 1 and rows[0]['reason'])
st.put('multi_entries', '1')

# ---- 4. the pop-up and the journal show it ----
c = A.app.test_client(); H = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=H)
rows = run(); now = int(time.time())
st.x("UPDATE signals SET status='closed', pnl=5.0, fill=2000.0, closed=? WHERE id=?", (now, rows[0]['id']))
old = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,fill) VALUES(?,?,?,?,?,?,?,?,?,?,?)", ('XAUUSD', 'sell', 2000.0, 2003.0, 1994.0, 'closed', now - 900, -3.0, now - 300, 'ma_cross', 2000.0))
d = c.get('/api/trade/%d' % rows[0]['id'], headers=H).get_json()
T('GET /api/trade/<id> returns the why_taken lines', d and d.get('why_taken') and any('agreed' in x for x in d['why_taken']) and any('Planned prices' in x for x in d['why_taken']))
d2 = c.get('/api/trade/%d' % old, headers=H).get_json()
T('a trade from before R1 has no reason (empty list, nothing made up)', d2 is not None and d2.get('why_taken') == [])
j = c.get('/api/journal', headers=H).get_json(); by = {x['id']: x for x in j['rows']}
T('the journal rows carry a short why (empty for old trades)', by[rows[0]['id']]['why'].startswith('2 strategies agreed') and by[old]['why'] == '')
T('the journal numbers are unchanged', j['stats']['trades'] == 2 and j['stats']['net'] == 2.0)

# ---- 5. the page and the code are wired ----
here = os.path.join(HERE, '..'); page = open(os.path.join(here, 'static', 'index.html'), encoding='utf-8').read(); app_src = open(os.path.join(here, 'backend', 'app.py'), encoding='utf-8').read()
T('the page has the Why the bot took this trade block and the old-trade message', 'Why the bot took this trade' in page and 'before the bot started writing its reasons down' in page and 'whyBlock(d)' in page)
T('app.py saves the reason on both inserts', app_src.count('rsn.pack(s)') == 1 and app_src.count('uid,reason)') == 1 and app_src.count('uid,grp,reason)') == 1)
bad = [n for n, ok in R if not ok]; print('\n%d checks, %d failed' % (len(R), len(bad))); sys.exit(1 if bad else 0)
'''
for p, txt in NEW.items():
    if os.path.exists(p): print('STOP: already exists:', p); sys.exit(1)
for p, txt in FILES.items(): open(p, 'w', encoding='utf-8').write(txt)
for p, txt in NEW.items(): open(p, 'w', encoding='utf-8').write(txt); print('new ', p)
print('\nR1 done. Now run: python tests/test_reason1.py')
