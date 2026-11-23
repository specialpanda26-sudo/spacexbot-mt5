"""apply_bx1.py: burst fix + live banner. Run inside the repo folder:  python apply_bx1.py
Every old text must appear exactly once or NOTHING is changed. Safe to run twice. Writes are atomic. Runs the tests at the end."""
import os, sys, subprocess
PAIRS = [
('backend/deriv.py',
r'''    done = False
    for r in st.q("SELECT id,ticket,lots,note,entry,sl,tp FROM signals WHERE uid=? AND status='open' AND ticket IS NOT NULL ORDER BY id LIMIT 20", (uid,)):
''',
r'''    done = False; live = {}          # BX1: the profit Deriv just reported for every trade that is still open
    for r in st.q("SELECT id,ticket,lots,note,entry,sl,tp FROM signals WHERE uid=? AND status='open' AND ticket IS NOT NULL ORDER BY id LIMIT 20", (uid,)):
'''),
('backend/deriv.py',
r'''        if not isinstance(p, dict) or str(p.get('is_sold')).lower() not in ('1', 'true'): continue
        try: pnl = round(float(p.get('profit')), 2)
''',
r'''        if isinstance(p, dict) and str(p.get('is_sold')).lower() not in ('1', 'true'): live[r['id']] = p.get('profit')          # BX1
        if not isinstance(p, dict) or str(p.get('is_sold')).lower() not in ('1', 'true'): continue
        try: pnl = round(float(p.get('profit')), 2)
'''),
('backend/deriv.py',
r''''other'); done = True
    if done: _resnap(sess, uid, acct)
''',
r''''other'); done = True
    try: from . import openlive; openlive.save(uid, live)          # BX1: the banner and Home card read this
    except Exception as e: print('[deriv] live profit not saved', repr(e)[:80])
    if done: _resnap(sess, uid, acct)
'''),
('backend/burst.py',
r'''from . import store as st, links, risk, limits, multi, groupcap, burst_look, burst_live, burst_results
''',
r'''from . import store as st, links, risk, limits, multi, groupcap, burst_look, burst_live, burst_results, automode
'''),
('backend/burst.py',
r'''HI = 30
DEF = {''',
r'''HI = 30
AUTO_WHY = 'Auto mode is on, and Auto mode turns burst off'          # BX1: the scanner always stopped here, the card never said so
DEF = {'''),
('backend/burst.py',
r'''    if not p['on']: return False, 'burst mode is off'
    ok, why = risk.global_gate(now, uid=uid, burst=True)
''',
r'''    if not p['on']: return False, 'burst mode is off'
    if automode.on(): return False, AUTO_WHY          # BX1
    ok, why = risk.global_gate(now, uid=uid, burst=True)
'''),
('backend/burst.py',
r'''why in ('a burst is already running', 'burst mode is off', 'burst mode is switched off by the owner')''',
r'''why in ('a burst is already running', 'burst mode is off', 'burst mode is switched off by the owner', AUTO_WHY)'''),
('backend/burst.py',
r"""    ok, why = due(uid, now)
    if ok: return {'state': 'ready'""",
r"""    ok, why = due(uid, now)
    if why == AUTO_WHY: return {'state': 'waiting', 'blocked': 'auto', 'why': 'Paused: Auto mode is ON, and Auto mode turns burst off. Switch Auto mode off (admin page, or AUTO_MODE=0 on Render) and burst starts.'}          # BX1
    if ok: return {'state': 'ready'"""),
('backend/app.py',
r'''    if automode.on() or not burst.get(uid)['on']: return
    k = (uid, sym, 'burst')
''',
r'''    if not burst.get(uid)['on']: return
    if automode.on(): burst_look.note(uid, 'Auto mode is ON, so burst is paused. Switch Auto mode off to let burst trade.'); return          # BX1
    k = (uid, sym, 'burst')
'''),
('backend/livestats.py',
r'''pnlreset as pr, tradeon, burst_live
''',
r'''pnlreset as pr, tradeon, burst_live, openlive
'''),
('backend/livestats.py',
r'''def sources(uid, admin, now):
''',
r'''def _dfloat(uid, admin, now):
    """BX1: live profit of the person's open Deriv trades: every open trade (openlive) when fresh, else the old burst-group figure (BT6)."""
    v = openlive.floating(uid, now)
    return v if v is not None else burst_live.floating(('' if admin else uid, uid), now)


def _results(sc, bq, since):
    """BX1: today's finished setups -> (wins, losses, last 3 as {symbol, pnl}). Entries opened together (same grp) count as ONE result, like the loss streak."""
    rows = st.q("SELECT id,grp,symbol,pnl FROM signals WHERE closed>=? AND pnl IS NOT NULL AND COALESCE(uid,'') IN (?,?)" + bq + " ORDER BY closed DESC, id DESC LIMIT 500", (since, sc[0], sc[1])) or []
    seen, out = {}, []
    for r in rows:
        p = _f(r['pnl'])
        if p is None: continue
        k = ('g', r['grp']) if r.get('grp') else ('i', r['id'])
        if k in seen: seen[k]['pnl'] = round(seen[k]['pnl'] + p, 2); continue
        seen[k] = {'symbol': r['symbol'], 'pnl': round(p, 2)}; out.append(seen[k])
    return sum(1 for o in out if o['pnl'] > 0), sum(1 for o in out if o['pnl'] < 0), out[:3]


def sources(uid, admin, now):
'''),
('backend/livestats.py',
r''''equity': round(bal + (burst_live.floating(('' if admin else uid, uid), now) if b['name'] == 'Deriv' else 0.0), 2), 'open': None,          # BT6''',
r''''equity': round(bal + (_dfloat(uid, admin, now) if b['name'] == 'Deriv' else 0.0), 2), 'open': None,          # BT6, BX1'''),
('backend/livestats.py',
r'''    base = bal - today
''',
r'''    base = bal - today
    ol = openlive.get(uid, now) or {}; tw, tl, recent = _results(sc, bq, pr.since(uid))          # BX1
'''),
('backend/livestats.py',
r"""'today': today, 'today_reset'""",
r"""'today': today, 'today_w': tw, 'today_l': tl, 'recent': recent, 'today_reset'"""),
('backend/livestats.py',
r''''strategy_name': si.label(r['strategy'])} for r in rows],''',
r''''strategy_name': si.label(r['strategy']), 'pnl': ol.get(r['id'])} for r in rows],'''),
('tests/test_bt5.py',
r'''src.count('burst_look.note(uid') == 6)''',
r'''src.count('burst_look.note(uid') == 7)'''),
('backend/live.py',
r'''def build(admin, s):
    a = s['a']; bal, eq = a.get('balance'), a.get('equity'); n = int(a.get('open') or len(s['open']) or 0)
    title = 'Bot running' + ('  |  ' + _m(bal) if admin and bal is not None else '')
    text = 'Today ' + _m(s['today'], True) + '  |  ' + (str(n) + ' open' if n else 'no open trades')
    lines = []
    if admin and bal is not None: lines.append('Balance ' + _m(bal) + (a.get('label') or '') + ('   Equity ' + _m(eq) if eq is not None else ''))
    if admin and bal is not None and eq is not None: lines.append('Floating P/L ' + _m(float(eq) - float(bal), True))
    lines.append('Today ' + _m(s['today'], True))
    if s['open']:
        lines.append('Open trades:')
        for o in s['open']: lines.append('  ' + str(o['side']).upper() + ' ' + str(o['symbol']) + ' at ' + str(o.get('fill') or o.get('entry') or o.get('price') or '--'))
    else: lines.append('No open trades right now')
    return {'type': 'live', 'title': title, 'text': text, 'big': '\n'.join(lines), 'ts': int(s['now'])}

''',
r'''def _burst(uid, admin, now):
    """BX1: one short line about burst for the banner, or '' when burst is off for this person."""
    try:
        from . import burst, burst_scope, burst_live
        sc = burst_scope.scope({'uid': uid, 'admin': admin}); ex = burst.explain(sc, now)
        if ex['state'] == 'off': return ''
        if ex.get('blocked'): return 'paused, Auto mode is on'
        if ex['state'] == 'running':
            g = burst_live.group(sc, now); return 'running. ' + g if g else 'running'
        return 'on, ready for a chance' if ex['state'] == 'ready' else 'on, watching'
    except Exception: return ''

def build(admin, s):
    a = s['a']; bal, eq = a.get('balance'), a.get('equity'); n = int(a.get('open') or len(s['open']) or 0)
    fl = s.get('float')
    if fl is None and bal is not None and eq is not None: fl = float(eq) - float(bal)
    w, l = int(s.get('w') or 0), int(s.get('l') or 0)
    title = 'Bot running' + ('  |  ' + _m(bal) if admin and bal is not None else '')
    text = 'Float ' + _m(fl, True) + '  |  Today ' + _m(s['today'], True) + '  |  W' + str(w) + ' L' + str(l) + '  |  ' + (str(n) + ' open' if n else 'none open')
    lines = []
    if admin and bal is not None: lines.append('Balance ' + _m(bal) + (a.get('label') or '') + ('   Equity ' + _m(eq) if eq is not None else ''))
    lines.append('Floating P/L ' + _m(fl, True))
    lines.append('Today ' + _m(s['today'], True) + '   Wins ' + str(w) + '   Losses ' + str(l) + ('   Win rate %d%%' % round(w * 100.0 / (w + l)) if w + l else ''))
    if s.get('burst'): lines.append('Burst: ' + s['burst'])
    if s['open']:
        lines.append('Open trades:')
        for o in s['open']:
            lines.append('  ' + str(o['side']).upper() + ' ' + str(o['symbol']) + ' at ' + str(o.get('fill') or o.get('entry') or o.get('price') or '--') + ('   ' + _m(o['pnl'], True) if o.get('pnl') is not None else ''))
    else: lines.append('No open trades right now')
    if s.get('recent'):
        lines.append('Last results:')
        for r in s['recent']: lines.append('  ' + ('Win  ' if r['pnl'] > 0 else 'Loss ' if r['pnl'] < 0 else 'Flat ') + str(r['symbol']) + '  ' + _m(r['pnl'], True))
    return {'type': 'live', 'title': title, 'text': text, 'big': '\n'.join(lines), 'ts': int(s['now'])}

'''),
('backend/live.py',
r'''    return {'on': _running(uid, admin, srcs), 'a': a, 'today': ls['today'], 'open': list(ls.get('trades') or []), 'now': now}
''',
r'''    return {'on': _running(uid, admin, srcs), 'a': a, 'today': ls['today'], 'open': list(ls.get('trades') or []), 'now': now,
            'float': ls.get('floating'), 'w': ls.get('today_w', 0), 'l': ls.get('today_l', 0), 'recent': ls.get('recent') or [], 'burst': _burst(uid, admin, now)}          # BX1
'''),
]
NEW = {
'backend/openlive.py':
r'''"""BX1: live profit of every OPEN Deriv trade. Deriv has no floating figure of its own, so the phone banner and the Home card showed Floating $0.00
for normal trades (BT6 only read burst groups with a target). deriv._track already asks Deriv about every open trade each round; it now hands
the profit it just read to save(). Only a figure read in the last FRESH seconds is used; an older one is ignored, never guessed.
Words and numbers only: nothing here places or closes a trade."""
import json, time
from . import store as st

FRESH = 150          # seconds a saved figure still counts (the Deriv round runs about every 60 s)


def _f(x):
    try: v = float(x)
    except (TypeError, ValueError): return None
    return v if v == v and abs(v) < 1e12 else None


def save(uid, live, now=None):
    """live = {signal id: profit now (USD)}. Saved as one row per person; an empty dict means 'nothing open, read just now'."""
    d = {}
    for k, v in (live or {}).items():
        f = _f(v)
        try: k = int(k)
        except (TypeError, ValueError): continue
        if f is not None: d[str(k)] = round(f, 2)
    st.put('olive:%s' % (uid or ''), json.dumps({'t': int(now or time.time()), 'p': d}))


def get(uid, now=None):
    """-> {signal id (int): profit} when it was read in the last FRESH seconds, else None."""
    now = now or time.time()
    try: j = json.loads(st.get('olive:%s' % (uid or '')) or 'null')
    except (TypeError, ValueError): return None
    if not isinstance(j, dict) or _f(j.get('t')) is None or not isinstance(j.get('p'), dict): return None
    if not 0 <= now - float(j['t']) <= FRESH: return None
    return {int(k): float(v) for k, v in j['p'].items() if _f(v) is not None}


def floating(uid, now=None):
    """-> the sum of the fresh live profits (USD), or None when there is no fresh reading (the caller falls back)."""
    g = get(uid, now)
    return None if g is None else round(sum(g.values()), 2)
''',
'tests/test_bx1.py':
r'''"""BX1 tests: burst says why Auto mode stops it, live profit of every open Deriv trade, and the banner shows floating, wins/losses and each trade. No network. Run: python tests/test_bx1.py"""
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
''',
}
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, t):
    d = os.path.dirname(p)
    if d: os.makedirs(d, exist_ok=True)
    open(p + '.tmp', 'w', encoding='utf-8').write(t); os.replace(p + '.tmp', p)
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
for t in ('tests/test_bx1.py', 'tests/test_bt5.py', 'tests/test_live1.py', 'tests/test_live2.py', 'tests/test_live3.py', 'tests/test_bt1.py', 'tests/test_bt9.py', 'tests/test_burst1.py', 'tests/test_bt7.py', 'tests/test_exit4.py'):
    if os.path.exists(t):
        p = subprocess.run([sys.executable, t], capture_output=True, text=True); last = (p.stdout.strip().splitlines() or ['?'])[-1]
        print(('OK   ' if p.returncode == 0 else 'FAIL ') + t + '  ' + last); r |= p.returncode
print('ALL GOOD' if r == 0 else 'SOMETHING FAILED: send me the FAIL lines'); sys.exit(r)
