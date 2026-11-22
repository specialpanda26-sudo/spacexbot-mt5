"""BT8 patch: a burst RESULTS line on the Bot tab. Of the burst groups that are fully closed in the last 7 days it says how many won, lost or ended flat,
the win and loss percent, the net USD, and whether the loss rate is inside your target (default 25 percent, owner setting burst_loss_target).
Words and numbers only: it never places or closes a trade. Each old text must appear exactly once or NOTHING is changed. Safe to run twice.
Run from the repo root: python apply_bt8_results.py"""
import os, sys
M = 'backend/burst_results.py'
T = 'tests/test_bt8.py'
B = 'backend/burst.py'
F = 'static/index.html'
H = 'docs/HANDOFF.md'

MOD = r'''"""BT8: the burst card's RESULTS line. Of the burst groups that are fully closed in the last DAYS days it counts how many won, lost or ended flat
(a group's result = the sum of the profit of its closed entries), the win and loss percent and the net USD, and says whether the loss rate is inside
the target (owner setting burst_loss_target, default 25 percent, 1 to 99). A group still open or closing is not counted. A normal multi-entry group is not a burst. Entries that never filled (rejected, expired) have no profit and are ignored.
Under MIN_GROUPS groups the line says it is only a rough guide. Words and numbers only: nothing here places or closes a trade."""
import json, time
from . import store as st

DAYS = 7
MIN_GROUPS = 10
EPS = 0.005          # a group within half a cent of zero ended flat


def target():
    try: v = int(float(st.get('burst_loss_target')))
    except (TypeError, ValueError): v = 25
    return max(1, min(99, v))


def _burst(grp):
    try: m = json.loads(st.get('bg:%d' % int(grp)) or 'null')
    except (TypeError, ValueError): return False
    return isinstance(m, dict) and m.get('k') != 'multi'


def stats(uid='', now=None, days=DAYS):
    """-> {n, won, lost, flat, net, win_pct, loss_pct, days, target}. Counts only fully closed burst groups whose last entry closed in the window."""
    now = now or time.time(); since = int(now - days * 86400)
    rows = st.q("SELECT grp, "
                "SUM(CASE WHEN status='closed' AND pnl IS NOT NULL THEN pnl ELSE 0 END) tot, "
                "SUM(CASE WHEN status='closed' AND pnl IS NOT NULL THEN 1 ELSE 0 END) k, "
                "SUM(CASE WHEN status IN('pending','sent','open','closing') THEN 1 ELSE 0 END) live, "
                "MAX(closed) c FROM signals WHERE grp IS NOT NULL AND COALESCE(uid,'')=? AND created>=? GROUP BY grp ORDER BY grp DESC LIMIT 500",
                (uid or '', since - 86400))
    won = lost = flat = 0; net = 0.0
    for r in rows:
        if int(r.get('live') or 0) > 0 or int(r.get('k') or 0) < 1: continue
        if int(r.get('c') or 0) < since or not _burst(r['grp']): continue
        t = float(r.get('tot') or 0); net += t
        if t > EPS: won += 1
        elif t < -EPS: lost += 1
        else: flat += 1
    n = won + lost + flat
    return {'n': n, 'won': won, 'lost': lost, 'flat': flat, 'net': round(net, 2), 'days': days, 'target': target(),
            'win_pct': round(won * 100.0 / n) if n else 0, 'loss_pct': round(lost * 100.0 / n) if n else 0}


def _usd(v): return '%s$%.2f' % ('+' if v >= 0 else '-', abs(v))


def line(uid='', now=None):
    """-> one plain sentence for the burst card."""
    s = stats(uid, now)
    if not s['n']: return 'Results: no closed burst groups in the last %d days yet.' % s['days']
    out = 'Results (last %d days): %d closed groups, %d won (%d%%), %d lost (%d%%)%s. Net %s. ' % (
        s['days'], s['n'], s['won'], s['win_pct'], s['lost'], s['loss_pct'], ', %d flat' % s['flat'] if s['flat'] else '', _usd(s['net']))
    out += 'Your target is %d%% losses or fewer: %s.' % (s['target'], 'you are inside it' if s['loss_pct'] <= s['target'] else 'you are above it')
    if s['n'] < MIN_GROUPS: out += ' Only %d groups so far, so treat it as a rough guide.' % s['n']
    return out
'''

TEST = r'''"""BT8 tests: the burst results line. No network. Run: python tests/test_bt8.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt8_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, burst, burst_results as br
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
NOW = int(time.time()); G = [100]
def reset():
    st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'bg:%' OR k='burst_loss_target'")
def group(pnls, status='closed', uid='', age=3600, kind='quick', meta=True):
    G[0] += 10; g = G[0]
    for i, p in enumerate(pnls):
        st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,pnl,closed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
             ('XAUUSD', 'buy', 2000, 1990, 2010, 0.1, 's', 1, status, NOW - age - 60, uid or None, g, p, NOW - age if status == 'closed' else None))
    if meta: st.put('bg:%d' % g, json.dumps({'k': kind, 'n': len(pnls)}))
    return g

reset()
T('no groups: says none closed yet', br.stats('')['n'] == 0 and 'no closed burst groups' in br.line(''))
group([0.5, 0.4]); group([-1.0, -0.2]); group([0.3, 0.3]); group([0.0, 0.0])
group([1, 1], status='open'); group([5, 5], kind='multi'); group([2, 2], age=8 * 86400); group([9, 9], uid='u1'); group([3, 3], meta=False)
s = br.stats('')
T('counts only closed burst groups of this person in the last 7 days: 4 groups', s['n'] == 4)
T('2 won, 1 lost, 1 flat', (s['won'], s['lost'], s['flat']) == (2, 1, 1))
T('percents 50 and 25, net is +0.30', s['win_pct'] == 50 and s['loss_pct'] == 25 and s['net'] == 0.3)
L = br.line('')
T('line: 4 groups, 2 won (50%), 1 lost (25%), 1 flat, net +$0.30', '4 closed groups, 2 won (50%), 1 lost (25%), 1 flat. Net +$0.30.' in L)
T('line: 25 percent loss is inside the 25 percent target', 'inside it' in L)
T('line: under 10 groups is called a rough guide', 'rough guide' in L)
st.put('burst_loss_target', '10'); T('target 10: the same 25 percent loss is above it', 'you are above it' in br.line('') and br.stats('')['target'] == 10)
st.put('burst_loss_target', 'abc'); T('a bad target falls back to 25', br.target() == 25)
st.put('burst_loss_target', '500'); T('a target of 500 is held at 99', br.target() == 99)
reset()
for _ in range(8): group([0.4])
for _ in range(2): group([-0.5])
L = br.line('')
T('10 groups: no rough guide note, 20 percent loss is inside', 'rough guide' not in L and '20%' in L and 'inside it' in L)
reset(); group([0.2, None]); group([None, None])
T('entries with no profit are ignored; a group of only those is not counted', br.stats('')['n'] == 1 and br.stats('')['won'] == 1)
reset(); group([0.4]); st.put('bg:%d' % G[0], 'not json')
T('a bad saved group value is skipped and does not crash', br.stats('')['n'] == 0)
reset(); group([0.4], uid='u1')
T('another person has their own numbers', br.stats('u1')['n'] == 1 and br.stats('')['n'] == 0)
T('burst.view carries the results line', 'results' in burst.view('') and burst.view('u1')['results'].startswith('Results (last 7 days)'))
bad = [n for n, ok in R if not ok]
print('%d passed, %d failed' % (len(R) - len(bad), len(bad)))
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
sys.exit(1 if bad else 0)
'''

NOTE = '''

## Section BT8 (burst results line) DONE (Nov 23)
- Asked for: a real win rate and loss rate of closed burst groups, to compare with the 25% loss rate wanted.
- backend/burst_results.py: of the burst groups fully closed in the last 7 days (a group is closed when none of its entries is pending, sent, open or closing; a normal multi-entry group is not a burst) it counts won, lost and flat (a group's result = the sum of the profit of its closed entries; within half a cent of zero = flat), win and loss percent, net USD. The Bot tab shows it after the Last look line: 'Results (last 7 days): N closed groups, W won (P%), L lost (Q%). Net +$x. Your target is 25% losses or fewer: you are inside it.'
- The target is owner setting burst_loss_target (default 25, 1 to 99, no admin page field yet). Under 10 closed groups the line says it is only a rough guide.
- Words and numbers only. It does not change what the bot does. The profit of each entry is whatever the broker bridge saved (MT5 from the EA, Deriv from the sell), so a wrong figure there shows up here too.
- Tests: tests/test_bt8.py.
'''

def put(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: f.write(text)

# 1. new files (overwritten each run, so a second run is harmless)
put(M, MOD); put(T, TEST); print('wrote', M, T)

# 2. burst.py: import and view
s = open(B, encoding='utf-8').read()
A1 = 'from . import store as st, links, risk, limits, multi, groupcap, burst_look, burst_live\n'
A2 = "'group': burst_live.group(uid, now)}"
if 'burst_results' in s: print(B, 'already patched')
else:
    if s.count(A1) != 1 or s.count(A2) != 1: sys.exit('STOP: anchors in %s found %d and %d times (need 1 and 1). Nothing changed.' % (B, s.count(A1), s.count(A2)))
    s = s.replace(A1, A1.replace('burst_live\n', 'burst_live, burst_results\n')).replace(A2, "'group': burst_live.group(uid, now), 'results': burst_results.line(uid, now)}")
    put(B, s); print('patched', B)

# 3. index.html: add the results sentence after the Last look sentence
h = open(F, encoding='utf-8').read()
O = '(j.look?" Last look ("+j.look.ago+"): "+j.look.why:"")'
if '/*BT8*/' in h: print(F, 'already patched')
else:
    if h.count(O) != 1: sys.exit('STOP: Last look text found %d times in %s (need 1). Nothing changed in the page.' % (h.count(O), F))
    put(F, h.replace(O, O + '+(j.results?" "+j.results:"")/*BT8*/')); print('patched', F)

# 4. handoff
d = open(H, encoding='utf-8').read()
if '## Section BT8' in d: print(H, 'already has BT8')
else: put(H, d.rstrip('\n') + NOTE); print('patched', H)
print('done. Now run: python tests/test_bt8.py')
