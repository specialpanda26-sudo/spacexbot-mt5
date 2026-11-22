"""PH3: Suggest. The screen assistant (card and phone bubble) now also shows a lot size worked out from the balance and risk you set in Phone mode.
Run from the repo folder: python apply_ph3.py   (add --test to also run the tests). Safe to run twice; if any old text is not found exactly once, NOTHING is changed.
Needs a new APK build after you push for the bubble part. Nothing is placed: it is a number to look at."""
import os, sys, subprocess
E = [
 ('backend/screenread.py', r"""def ask_bot(uid, read, ctx):""",
  r"""def _size(uid, sym, sig):
    # PH3 Suggest: how many lots fit THIS person's balance and risk (set in Phone mode). A number to look at; nothing is placed.
    try:
        from . import assist
        a = assist.get(uid)
        if a.get('balance') is None: return {'lots': None, 'why': 'Set your balance and risk in Phone mode to see a lot size.'}
        return assist.size(sym, sig['entry'], sig['sl'], sig['tp'], a['balance'], a['risk'])
    except Exception: return {'lots': None, 'why': 'No lot size right now.'}

def ask_bot(uid, read, ctx):""", "PH3 Suggest: how many lots"),
 ('backend/screenread.py', r"""    if bias == s['side']: return _v('agree', 'The bot agrees: its strategies (%s) also see a %s. Its own stop loss and target are shown.' % (sig['strategy_name'], s['side']), sig)""",
  r"""    if bias == s['side']:
        v = _v('agree', 'The bot agrees: its strategies (%s) also see a %s. Its own stop loss and target are shown.' % (sig['strategy_name'], s['side']), sig)
        if ctx != 'learn': v['size'] = _size(uid, sym, sig)
        return v""", "v['size'] = _size(uid, sym, sig)"),
 ('static/screen.js', r"""    if (g) o.push("The bot's own plan: " + g.side + " near " + g.entry + ", stop loss " + g.sl + ", target " + g.tp + (g.strategy_name ? " (" + g.strategy_name + ")" : "") + ".");""",
  r"""    if (g) o.push("The bot's own plan: " + g.side + " near " + g.entry + ", stop loss " + g.sl + ", target " + g.tp + (g.strategy_name ? " (" + g.strategy_name + ")" : "") + ".");
    var z = g && bot.code === "agree" && bot.size;          /* PH3 Suggest: a lot size for THIS person's balance and risk */
    if (z) o.push(typeof z.lots === "number" ? "Suggested size: " + z.lots + " lot (risks about $" + z.risk_usd + ", aims for about $" + z.win_usd + "). Assumes a USD account. Check it in your MT5 order screen." : String(z.why || "No lot size right now."));""", "Suggested size: "),
 ('static/screen.js', r"""<button type="button" aria-pressed="true">Explain</button><button type="button" aria-pressed="false" disabled>Suggest · soon</button>""",
  r"""<button type="button" aria-pressed="false" disabled>Explain</button><button type="button" aria-pressed="true" disabled>Suggest</button>""", """aria-pressed="true" disabled>Suggest</button>"""),
 ('android-wrapper/native/ScreenLogic.java', r"""        if ("agree".equals(code)) return new Verdict("ok", "I see a possible trade.", say + side(b), GREEN, false);""",
  r"""        if ("agree".equals(code)) return new Verdict("ok", "I see a possible trade.", say + side(b) + sizeText(b), GREEN, false);""", "say + side(b) + sizeText(b)"),
 ('android-wrapper/native/ScreenLogic.java', r"""    private static String num(Object o) {""",
  r"""    /** PH3 Suggest: the lot size the server worked out from the person's own balance and risk, or its plain-words reason. Empty when the server sent none. */
    @SuppressWarnings("unchecked")
    private static String sizeText(Map<String, Object> bot) {
        Object z0 = bot.get("size"); if (!(z0 instanceof Map)) return "";
        Map<String, Object> z = (Map<String, Object>) z0;
        if (z.get("lots") instanceof Number) return "  Suggested size " + num(z.get("lots")) + " lot" + (z.get("risk_usd") instanceof Number ? ", risk about $" + num(z.get("risk_usd")) : "") + ". Check it in your MT5 order screen.";
        String w = s(z.get("why")); return w.length() > 0 ? "  " + w : "";
    }

    private static String num(Object o) {""", "private static String sizeText"),
]
TEST = r'''"""PH3 checks: Suggest. A screen read where the bot agrees also carries a lot size for the person's own balance and risk. Run: python tests/test_ph3.py"""
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
'''
files, bad = {}, []
for p, old, new, mk in E:
    s = files.get(p)
    if s is None: s = files[p] = open(p, encoding='utf-8').read()
    if mk in s: print('skip (already there):', mk[:46]); continue
    if s.count(old) != 1: bad.append((p, old[:60], s.count(old))); continue
    files[p] = s.replace(old, new, 1); print('edited:', mk[:46])
if bad:
    for b in bad: print('STOP: not found exactly once (found %d) in %s -> %s' % (b[2], b[0], b[1]))
    print('Nothing was changed.'); sys.exit(1)
files['tests/test_ph3.py'] = TEST
for p, s in files.items():
    open(p + '.new', 'w', encoding='utf-8').write(s); os.replace(p + '.new', p)
print('edits done.')
if '--test' not in sys.argv: print('Not testing (add --test to run the tests). Next: git add -A, commit, push, then build the APK.'); sys.exit(0)
fails = []
for f in sorted(os.listdir('tests')):
    if not (f.startswith('test_') and f.endswith('.py')) or f == 'test_rk5.py': continue
    r = subprocess.run([sys.executable, 'tests/' + f], capture_output=True, text=True, timeout=300)
    if r.returncode: fails.append(f); print('FAIL', f, (r.stdout.strip().splitlines() or [''])[-1])
print('RESULT:', 'ALL TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
