"""Section 3 tests: stake levels, sizing, owner settings checks, the stake line in the trade detail, Deriv 'Closed by'. No network.
Run: python tests/test_stake.py   (the stake line is also run in node when node is installed)"""
import os, sys, json, time, subprocess, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_stake_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, stake, deriv
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); BOSS = {'Authorization': 'Bearer dev:boss@x.com'}; JOE = {'Authorization': 'Bearer dev:joe@x.com'}

# ---------- levels
T('very: 3+ agree with ADX 25+, or 2+ with ADX 40+', stake.tier(3, 25) == 'very' and stake.tier(4, 30) == 'very' and stake.tier(2, 40) == 'very')
T('strong: 2+ agree with ADX 25+', stake.tier(2, 25) == 'strong' and stake.tier(2, 39.9) == 'strong')
T('no level otherwise, and bad input is no level', stake.tier(2, 24.9) == '' and stake.tier(1, 60) == '' and stake.tier(None, None) == '' and stake.tier('x', 1) == '')

# ---------- mark / info (the owner)
st.put('stake_on', '1'); st.put('stake_very_pct', '40'); st.put('stake_strong_pct', '15')
stake.mark(101, '', 3, 30); stake.mark(102, '', 2, 30); stake.mark(103, '', 1, 50)
T('very setup: 40% and the level is remembered', stake.pct(101) == 40.0 and stake.info(101) == {'pct': 40.0, 'tier': 'very'})
T('strong setup: 15% and the level is remembered', stake.pct(102) == 15.0 and stake.info(102) == {'pct': 15.0, 'tier': 'strong'})
T('normal setup: no stake, info is None', stake.pct(103) == 0 and stake.info(103) is None)
st.put('stake_on', '0'); stake.mark(104, '', 3, 30)
T('switched off: nothing is marked', stake.info(104) is None); st.put('stake_on', '1')
real = st.acct; st.acct = lambda uid='': {'demo': False}; stake.mark(105, 'joe', 3, 30); st.acct = lambda uid='': {'demo': True}; stake.mark(106, 'joe', 3, 30); st.acct = real
T('a subscriber on a REAL account never gets a big stake; on a demo account does', stake.info(105) is None and stake.info(106) == {'pct': 40.0, 'tier': 'very'})

# ---------- sizing: margin share first, then the loss cap
z = stake.size(2000, 1990, 2020, 1000, 40, 100)
T('wide stop: 40% would lose 200, the 10% cap cuts the stake to 200 (loss 100, target 200)', z == (200.0, 100.0, 200.0))
z = stake.size(2000, 1999, 2002, 1000, 40, 100)
T('tight stop: the full 40% stake is used (loss 20, target 40)', z == (400.0, 20.0, 40.0))
T('too small, no balance, or no stop distance: no big stake', stake.size(2000, 1990, 2020, 2, 40, 100) is None and stake.size(2000, 1990, 2020, 0, 40, 100) is None and stake.size(2000, 2000, 2020, 1000, 40, 100) is None)

# ---------- owner settings: checked before anything is saved
def post(j, h=BOSS): return c.post('/api/admin/settings', json=j, headers=h)
before = {k: st.get(k) for k in ('stake_on', 'stake_very_pct', 'stake_strong_pct', 'stake_max_risk_pct')}
T('a person who is not the owner cannot change them', post({'stake_very_pct': '30'}, JOE).status_code in (401, 403))
T('too high, too low and not-a-number are all refused', post({'stake_very_pct': '60'}).status_code == 400 and post({'stake_max_risk_pct': '0.1'}).status_code == 400 and post({'stake_strong_pct': 'abc'}).status_code == 400)
r = post({'stake_very_pct': '30', 'stake_strong_pct': '99'})
T('one bad number saves none of them', r.status_code == 400 and st.get('stake_very_pct') == before['stake_very_pct'])
r = post({'stake_on': '1', 'stake_very_pct': '35', 'stake_strong_pct': '12.5', 'stake_max_risk_pct': '8'}); j = r.get_json()
T('good numbers are saved and handed back for the page', r.status_code == 200 and j['stake_very_pct'] == '35' and j['stake_strong_pct'] == '12.5' and j['stake_max_risk_pct'] == '8' and stake.max_risk() == 8.0)
post({k: v for k, v in before.items()})

# ---------- trade detail
def mkclosed(sid_mark=None, why=None):
    sid = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,pnl,closed,lots) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               ('XAUUSD', 'buy', 2000.0, 1990.0, 2020.0, 1.0, 'macd_cross', 3, 'closed', int(time.time()) - 600, '', 12.5, int(time.time()) - 60, 0.5))
    if sid_mark: stake.mark(sid, '', *sid_mark)
    if why: st.put('closedby:%d' % sid, why)
    return sid
a = mkclosed((3, 30), 'tp'); b = mkclosed()
da = c.get('/api/trade/%d' % a, headers=BOSS).get_json(); db = c.get('/api/trade/%d' % b, headers=BOSS).get_json()
T('trade detail carries the stake and level for a big-stake trade', da.get('stake') == {'pct': 40.0, 'tier': 'very'} and da['closed_by'] == 'tp')
T('trade detail has stake None for a normal trade, and says closed-by is not recorded', db.get('stake') is None and db['closed_by'] is None)
T('the exit note no longer talks about what the broker reports', 'broker' not in da['exit']['note'] and 'broker' not in db['exit']['note'])

# ---------- Deriv: closed by is worked out from the profit, never from its sign alone
row = {'lots': 200, 'note': 'x100', 'entry': 2000, 'sl': 1990, 'tp': 2020}     # stop = -100, target = +200
T('Deriv: profit at the stop amount is sl, at the target amount is tp', deriv._closed_by(row, -100.0) == 'sl' and deriv._closed_by(row, -97.0) == 'sl' and deriv._closed_by(row, 200.0) == 'tp' and deriv._closed_by(row, 195.0) == 'tp')
T('Deriv: any other profit (closed by hand, early) is other, as is a row it cannot read', deriv._closed_by(row, -40.0) == 'other' and deriv._closed_by(row, 150.0) == 'other' and deriv._closed_by(row, 0.0) == 'other' and deriv._closed_by(dict(row, note=None), -100.0) == 'other')
class Sess:
    def ask(self, q): return {'proposal_open_contract': {'is_sold': 1, 'profit': -100.0}}
seen = []; old = (deriv._report, deriv._resnap); deriv._report = lambda uid, sid, stt, reason='': seen.append((sid, stt, reason)); deriv._resnap = lambda *a, **k: None
sid = st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,ticket,lots,note,broker) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
           ('XAUUSD', 'buy', 2000.0, 1990.0, 2020.0, 1.0, 'macd_cross', 3, 'open', int(time.time()) - 600, 'joe', '777', 200, 'x100', 'Deriv'))
deriv._track(Sess(), 'joe', {'demo': True, 'currency': 'USD'}); deriv._report, deriv._resnap = old
T('Deriv: a closed trade stores its closed-by, the alert reason is unchanged', st.get('closedby:%d' % sid) == 'sl' and seen == [(sid, 'closed', 'sl')])

# ---------- the page
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page has the four owner stake settings and a Save button', all(('id="%s"' % i) in html for i in ('skOn', 'skVery', 'skStrong', 'skMax', 'skSave', 'skMsg')) and html.count('stake_max_risk_pct') >= 2)
T('page no longer tells the person about server memory', 'kept in memory only' not in html and 'reports only its profit' not in html)
m = re.search(r'  function stakeLine\(d\) \{.*?\n  function render\(d\)', html, re.S)
if m and subprocess.run(['node', '-v'], capture_output=True).returncode == 0:
    js = 'function esc(s){return String(s)}\n' + m.group(0)[:-len('  function render(d)')] + '''
var a = whyBlock({why_taken: ["Two strategies agreed"], stake: {pct: 40, tier: "very"}}), b = whyBlock({why_taken: ["x"], stake: {pct: 12.5, tier: "strong"}}),
    n = whyBlock({why_taken: ["x"], stake: null}), e = whyBlock({why_taken: [], stake: {pct: 15, tier: "strong"}}), z = whyBlock({why_taken: [], stake: null});
console.log(JSON.stringify([a.indexOf("<li>Stake: 40% of balance (very strong)</li>") > 0, b.indexOf("Stake: 12.5% of balance (strong)") > 0, n.indexOf("Stake") < 0, e.indexOf("Stake: 15% of balance (strong)") > 0 && e.indexOf("not saved") > 0, z.indexOf("Stake") < 0]));'''
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    T('trade detail shows "Stake: 40% of balance (very strong)" in the why block, and nothing for a normal trade', out.stdout.strip() == '[true,true,true,true,true]')
else: T('node not found or stakeLine missing (needs node)', m is None and False)

p = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (p, len(R)))
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
sys.exit(0 if p == len(R) else 1)
