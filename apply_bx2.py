"""apply_bx2.py: burst journal and stats. Run inside the repo folder:  python apply_bx2.py
Every old text must appear exactly once or NOTHING is changed. Safe to run twice. Writes are atomic. Runs the tests at the end."""
import os, sys, subprocess
PAIRS = [
('backend/journal.py',
r'''from . import store as st, strategy_info as si, reason as rsn
''',
r'''from . import store as st, strategy_info as si, reason as rsn, burst_results
'''),
('backend/journal.py',
r'''def snapshot(uid, admin=False, broker='', result='all', limit=LIMIT, now=None):
''',
r'''def burst_groups(uid, admin, limit=30):
    """BX2: the person's finished BURST groups (a normal multi-entry group is not a burst). A group's result = the sum of the profit of its closed entries.
    A group with any entry still pending/open/closing is left out. -> {'stats': {...}, 'groups': newest first}. Words and numbers only."""
    a, b = scope(uid, admin)
    rows = st.q("SELECT id,grp,symbol,side,pnl,status,closed,created FROM signals WHERE grp IS NOT NULL AND COALESCE(uid,'') IN (?,?) ORDER BY grp DESC, id LIMIT 3000", (a, b)) or []
    g = {}
    for r in rows: g.setdefault(r['grp'], []).append(r)
    out = []
    for k, es in g.items():
        if any(e['status'] in ('pending', 'sent', 'open', 'closing') for e in es): continue
        done = [e for e in es if e['status'] == 'closed' and _num(e.get('pnl')) is not None]
        if not done or not burst_results._burst(k): continue
        t = round(sum(_num(e['pnl']) for e in done), 2)
        out.append({'grp': k, 't': int(max(int(e.get('closed') or e.get('created') or 0) for e in done)), 'symbol': es[0]['symbol'], 'side': str(es[0]['side'] or '').lower(),
                    'entries': len(done), 'pnl': t, 'result': 'win' if t > 0.005 else 'loss' if t < -0.005 else 'flat'})
    out.sort(key=lambda o: (o['t'], o['grp']), reverse=True)
    n = len(out); won = sum(1 for o in out if o['result'] == 'win'); lost = sum(1 for o in out if o['result'] == 'loss'); net = round(sum(o['pnl'] for o in out), 2)
    run = mx = 0
    for o in reversed(out):                      # oldest first
        run = run + 1 if o['result'] == 'loss' else 0; mx = max(mx, run)
    return {'stats': {'groups': n, 'won': won, 'lost': lost, 'flat': n - won - lost, 'win_rate': round(won * 100.0 / n, 1) if n else 0.0, 'net': net,
                      'per_group': round(net / n, 2) if n else 0.0, 'best': max((o['pnl'] for o in out), default=0.0), 'worst': min((o['pnl'] for o in out), default=0.0), 'loss_streak': mx},
            'groups': out[:max(1, int(limit))]}


def snapshot(uid, admin=False, broker='', result='all', limit=LIMIT, now=None):
'''),
('backend/journal.py',
r''''pairs': by_pair(rows), 'brokers': brokers, 'broker': want,
''',
r''''pairs': by_pair(rows), 'brokers': brokers, 'broker': want, 'burst': burst_groups(uid, admin),          # BX2
'''),
('static/index.html',
r'''SXJ.open = j.open || []; SXJ.state = "ok";''',
r'''SXJ.open = j.open || []; SXJ.burst = j.burst || null; SXJ.state = "ok";'''),
('static/index.html',
r'''}).join("")+'</ul>'}

/* ---------- pairs, analysis, backtest ---------- */''',
r'''}).join("")+'</ul>'+bxs()}
function bxs(){/* BX2: finished burst groups, from SXJ.burst (GET /api/journal) */
 var B=SXJ.burst,s=B&&B.stats;if(!s||!s.groups)return"";
 return '<b style="font-size:13px" class="muted">BURST GROUPS</b><div class="stats">'+kp("Groups",s.groups)+kp("Won",s.won)+kp("Lost",s.lost)+kp("Win rate",s.win_rate.toFixed(0)+"%")+'</div><div class="note">Net '+m2(s.net)+' \u00b7 Per group '+m2(s.per_group)+' \u00b7 Best '+m2(s.best)+' \u00b7 Worst '+m2(s.worst)+' \u00b7 Losing run '+s.loss_streak+'</div><ul class="list">'+B.groups.slice(0,15).map(function(o){return'<li class="row"><span class="ic '+(o.pnl>=0?"up":"dn")+'">'+(o.pnl>=0?ICK:ICX)+'</span><span class="t">'+esc(o.symbol)+' '+esc(o.side)+'</span><span class="r num '+(o.pnl>=0?"good":"bad")+'">'+m2(o.pnl)+'</span><span class="s">'+o.entries+' entr'+(o.entries>1?"ies":"y")+' \u00b7 '+new Date(o.t*1000).toLocaleString()+'</span></li>'}).join("")+'</ul>'}

/* ---------- pairs, analysis, backtest ---------- */'''),
('static/index.html',
r'''SXJ.rows = []; SXJ.total = 0; SXJ.stats = null; SXJ.pairs = []; SXJ.brokers = [];''',
r'''SXJ.rows = []; SXJ.total = 0; SXJ.stats = null; SXJ.pairs = []; SXJ.burst = null; SXJ.brokers = [];'''),
]
NEW = {
'tests/test_bx2.py':
r'''"""BX2 tests: the Journal and Stats show finished burst groups (won, lost, win rate, net, losing run). No network. Run: python tests/test_bx2.py"""
import os, sys, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bx2_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, journal
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; c.get('/api/me', headers=OW); UID = 'dev-boss@x.com'
NOW = int(time.time())
def sig(grp, pnl, status='closed', sym='XAUUSD', ago=0):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,closed,pnl,uid,grp,broker) VALUES(?,?,1,1,1,1,'x',1,?,?,?,?,?,?,'Deriv')", (sym, 'buy', status, NOW - ago - 60, NOW - ago if status == 'closed' else None, pnl if status == 'closed' else None, UID, grp))
def grp(kind, entries, status='closed', ago=0):
    first = sig(None, entries[0], status, ago=ago); st.x('UPDATE signals SET grp=id WHERE id=?', (first,))
    for p in entries[1:]: sig(first, p, status, ago=ago)
    st.put('bg:%d' % first, json.dumps({'k': kind, 'n': len(entries), 't': NOW})); return first
grp('burst', [0.5, 0.5, -0.2], ago=500)          # win +0.80
grp('burst', [-0.5, -0.5, 0.1], ago=400)         # loss -0.90
grp('burst', [-0.4, -0.4], ago=300)              # loss -0.80
grp('multi', [3.0, 3.0], ago=200)                # a normal group, NOT a burst
grp('burst', [0.5, 0.5], status='open', ago=100) # still open, not counted
grp('burst', [0.3, 0.3], ago=50)                 # win +0.60
sn = journal.snapshot(UID, True); B = sn['burst']; s = B['stats']
T('the snapshot carries a burst block', isinstance(B, dict) and 'stats' in B and 'groups' in B)
T('4 finished burst groups (normal group and open group left out)', s['groups'] == 4 and len(B['groups']) == 4)
T('2 won, 2 lost, win rate 50', (s['won'], s['lost'], s['win_rate']) == (2, 2, 50.0))
T('net is the sum of the groups (+0.80 -0.90 -0.80 +0.60 = -0.30)', s['net'] == -0.3 and s['per_group'] == -0.07 or s['per_group'] == -0.08)
T('best +0.80 and worst -0.90', s['best'] == 0.8 and s['worst'] == -0.9)
T('losing run of 2 groups in a row', s['loss_streak'] == 2)
T('newest group first and each shows its entries and result', B['groups'][0]['pnl'] == 0.6 and B['groups'][0]['entries'] == 2 and B['groups'][0]['result'] == 'win')
T('a person with no bursts gets zero groups, not an error', journal.snapshot('nobody@x', False)['burst']['stats']['groups'] == 0)
T('the ordinary numbers are unchanged', sn['stats']['trades'] >= 8 and 'pairs' in sn)
r = c.get('/api/journal', headers=OW).get_json(); T('GET /api/journal returns the burst block', r['burst']['stats']['groups'] == 4)
h = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('the page stores and draws the burst block', 'SXJ.burst = j.burst || null' in h and 'function bxs()' in h and 'BURST GROUPS' in h and "+bxs()}" in h)
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
for t in ('tests/test_bx2.py', 'tests/test_bx1.py', 'tests/test_s6ui.py', 'tests/test_bt8.py', 'tests/test_live3.py'):
    if os.path.exists(t):
        p = subprocess.run([sys.executable, t], capture_output=True, text=True); last = (p.stdout.strip().splitlines() or ['?'])[-1]
        print(('OK   ' if p.returncode == 0 else 'FAIL ') + t + '  ' + last); r |= p.returncode
print('ALL GOOD' if r == 0 else 'SOMETHING FAILED: send me the FAIL lines'); sys.exit(r)
