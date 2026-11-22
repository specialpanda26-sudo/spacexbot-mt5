"""BT2 tests: editable burst stake (0.5 default), fixed Deriv sizing, the Deriv group target for a burst, the card ids, and the 'Find a setting' search.
Run: python tests/test_bt2.py (card + search checks need node; the search runs against a tiny fake page)."""
import os, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt2_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
from backend import store as st, burst, deriv
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); me = {'Authorization': 'Bearer dev:amy@x.com'}; c.get('/api/me', headers=me)
# ---- server
j = c.get('/api/burst', headers=me).get_json(); T('stake starts at 0.5 USD', j['settings']['stake_usd'] == 0.5)
j = c.post('/api/burst', json={'stake_usd': 1.25, 'quick_usd': 1, 'quick_n': 6}, headers=me).get_json(); s = j['settings']
T('stake 1.25, target 1, entries 6 saved', s['stake_usd'] == 1.25 and s['quick_usd'] == 1 and s['quick_n'] == 6)
T('stake 0 (normal sizing) is allowed', c.post('/api/burst', json={'stake_usd': 0}, headers=me).get_json()['settings']['stake_usd'] == 0)
for bad in (-1, 0.05, 'x', True, 5000, None): T('bad stake %r refused' % (bad,), c.post('/api/burst', json={'stake_usd': bad}, headers=me).status_code == 400)
c.post('/api/burst', json={'stake_usd': 0.5}, headers=me)
U = 'dev-amy@x.com'; pl, why = burst.plan(U, 1)
T('plan carries the stake and the entries', pl and pl['stake'] == 0.5 and pl['n'] == 6 and pl['each'] == 1)
ids = burst.create(U, 'EURUSD', {'side': 'buy', 'entry': 1.1, 'sl': 1.099, 'tp': 1.102, 'strategy': 't', 'score': 1}, pl)
m = burst.meta(ids[0]); T('group meta keeps the stake and the Deriv group target 6 x 1 = 6', m['stake'] == 0.5 and m['dtgt'] == 6.0 and 'tgt' not in m)
T('MT5 basket still uses the per-entry target', burst.basket({'id': ids[0], 'symbol': 'EURUSD', 'side': 'buy', 'sl': 1.099, 'tp': 1.102, 'risk_pct': 0.1}, U)['each'] == 1)
row = st.q('SELECT * FROM signals WHERE id=?', (ids[1],), True); T('deriv reads the stake of a burst entry', deriv._burst_stake(row) == 0.5)
row0 = {'grp': None}; T('a normal signal has no burst stake', deriv._burst_stake(row0) == 0.0)
f = burst.fixed_size(1.1, 1.099, 1.102, 100, 0.5, 100); T('fixed size: stake 0.5, x100, stop loss money 0.05 (0.5 x 100 x 0.0909%), target twice that (0.1)', f == (0.5, 0.05, 0.1))
T('fixed size refuses when the stop would lose the whole stake', burst.fixed_size(1.1, 1.0, 1.2, 100, 0.5, 100) is None)
T('fixed size refuses a stake over half the account', burst.fixed_size(1.1, 1.099, 1.102, 10, 6, 10) is None)
from backend import deriv_group as dg
T('deriv_group falls back to dtgt', "or _f((m or {}).get('dtgt'))" in open(os.path.join(ROOT, 'backend', 'deriv_group.py')).read())
# ---- page
s = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('both blocks present once', s.count('/*BT1-start*/') == 1 and s.count('/*BT2-start*/') == 1)
b1 = s.split('/*BT1-start*/')[1].split('/*BT1-end*/')[0]; b2 = s.split('/*BT2-start*/')[1].split('/*BT2-end*/')[0]
for i in ('btOn', 'btMsg', 'btChip', 'btN', 'btUsd', 'btSave', 'btNow', 'btIdle', 'btShow', 'btLoad'): T('old id %s is gone from the burst card' % i, i not in b1.replace('bsw', 'X'))
T("card ids do not clash with other pages' ids", all(s.count('id="' + i + '"') == 1 for i in ('bswOn', 'bswMsg', 'bswStake', 'bswUsd', 'bswN', 'bswSave')))
if shutil.which('node'):
    js = r'''
var out=[];function El(t){this.t=t;this.kids=[];this.cl={};this.textContent="";this.style={};this.value="";var me=this;this.classList={add:function(k){me.cl[k]=1},remove:function(k){delete me.cl[k]},contains:function(k){return!!me.cl[k]}}}
El.prototype.appendChild=function(k){this.kids.push(k);return k};
Object.defineProperty(El.prototype,"innerHTML",{set:function(h){this.kids=h.indexOf("<b></b>")>=0?[new El("b"),new El("small")]:[];this.html=h},get:function(){return this.html||""}});
Object.defineProperty(El.prototype,"firstChild",{get:function(){return this.kids[0]||null}});Object.defineProperty(El.prototype,"lastChild",{get:function(){return this.kids[this.kids.length-1]||null}});
function mkcard(title,note){var c=new El("card");c.h=new El("h2");c.h.textContent=title;c.note=new El("p");c.note.textContent=note||"";c.textContent=title+" "+(note||"");c.scrolled=0;
 c.querySelector=function(s){return s==="h2"?c.h:s===".note"?c.note:null};c.scrollIntoView=function(){c.scrolled++};return c}
var cards={bot:[mkcard("Risk limits","Risk per trade and max daily loss"),mkcard("Burst mode","The bot takes small quick profits in a group when the market is quiet and no strategy gives signals. Stake per entry"),mkcard("Group target and loss","Close the whole group together at the target"),mkcard("Auto-cycle","Open the next group when a group closes at profit")],profile:[],connect:[],trades:[],home:[]};
var document={head:new El("head"),createElement:function(t){return new El(t)},getElementById:function(id){var v=id.replace("view-","");return cards[v]?{querySelectorAll:function(){return cards[v]}}:null}};
var box=null,vbk=[];var vb={insertBefore:function(k){vbk.push(k)},firstChild:null};
function card(h,body){box=mkcard(h[0],"");var inp=new El("input"),R=new El("div");box.querySelector=function(s){return s==="#sxQ"?inp:s==="#sxR"?R:null};box.inp=inp;box.R=R;return box}
var location={hash:"#bot"};var window={dispatchEvent:function(){out.push("hashchange")}};function Event(){}
function setTimeout2(f){f()}var _st=setTimeout;
''' + b2 + r'''
function ask(q){box.R.kids=[];box.R.html="";box.inp.value=q;box.inp.oninput();return box.R.kids.map(function(k){return k.firstChild.textContent})}
var r1=ask("the market is too busy, no strategies");var r2=ask("how do I change the stake per entry");var r3=ask("I want it to repeat the next group");var r4=ask("notifications sound");var r5=ask("zzzz qqqq");var h5=box.R.innerHTML.indexOf("No setting matched")>=0;var r6=ask("daily loss");
console.log(JSON.stringify({r1:r1[0],r2:r2[0],r3:r3[0],r4:r4[0],r5:r5.length,r5h:h5,r6:r6[0]}));
'''
    o = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    try: j = json.loads(o.stdout.strip().splitlines()[-1])
    except Exception: j = {}; print(o.stdout[-600:], o.stderr[-600:])
    T("search: 'market too busy, no strategies' finds Burst mode first", j.get('r1', '').startswith('Burst mode'))
    T("search: 'stake per entry' finds Burst mode first", j.get('r2', '').startswith('Burst mode'))
    T("search: 'repeat the next group' finds Auto-cycle first", j.get('r3', '').startswith('Auto-cycle'))
    T("search: 'notifications' finds the Profile page through the built-in list", j.get('r4', '').startswith('Notifications') and 'Profile' in j.get('r4', ''))
    T('search: nonsense shows the helpful no-match line', j.get('r5') == 0 and j.get('r5h') is True)
    T("search: 'daily loss' finds Risk limits first", j.get('r6', '').startswith('Risk limits'))
bad = [n for n, ok in R if not ok]; print('%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
