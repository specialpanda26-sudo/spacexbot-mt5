"""Tests for Section SW1: check boxes for btc_sunday_bounce, btc_short_pullback, orb_session in the admin Advanced settings. Run: python tests/test_sw1.py"""
import os, sys, re, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'sw1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import alerts; alerts.stop()
from backend import store as st
R = []
def T(name, ok): R.append((name, bool(ok)))
KEYS = ['btc_sunday_bounce', 'btc_short_pullback', 'orb_session']
html = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
m = re.search(r'S4A=(\[\[.*?\]\]);', html)
T('the S4A list is found in index.html', m is not None)
S4A = []
if m and shutil.which('node'):
    S4A = json.loads(subprocess.run(['node', '-e', 'console.log(JSON.stringify(%s))' % m.group(1)], capture_output=True, text=True).stdout or '[]')
elif m: S4A = json.loads(m.group(1))                      # the list is plain JSON too
byk = {f[0]: f for f in S4A}
for k in KEYS:
    T('%s is a check box in Advanced' % k, k in byk and byk[k][2] == 'c' and len(byk[k][1]) > 10)
    T('%s is a known setting (store DEFAULTS), default 0' % k, k in st.DEFAULTS and st.DEFAULTS[k] == '0')
T('the three are listed once each', all(sum(1 for f in S4A if f[0] == k) == 1 for k in KEYS))
T('the old Advanced rows are still there', all(any(f[0] == k for f in S4A) for k in ('min_confluence', 'multi_min_score', 'regime_switch', 'auto_disable', 'auto_markets', 'symbols_pool', 'max_trades_day')))
T('every row has a unique key (a check box id is s4_<key>)', len({f[0] for f in S4A}) == len(S4A))
T('the labels say they are unproven', all('unproven' in byk[k][1] for k in KEYS if k in byk))
# the page's own fill and save logic, run in node against the real list
if shutil.which('node') and m:
    js = """
var S4A=%s;
var els={}; function mk(id){els[id]={checked:false,value:''};}
S4A.forEach(function(f){mk('s4_'+f[0])});
function $(s){return els[s.slice(1)]}
function s4Fill(j){S4A.forEach(function(f){var e=$("#s4_"+f[0]);if(!e)return;if(f[2]==="c")e.checked=j[f[0]]==="1";else e.value=j[f[0]]==null?"":j[f[0]]})}
function s4Body(list){var o={};for(var i=0;i<list.length;i++){var f=list[i],e=$("#s4_"+f[0]);if(!e)continue;if(f[2]==="c")o[f[0]]=e.checked?"1":"0";else if(f[2]==="s")o[f[0]]=String(e.value||"").toUpperCase().replace(/[^A-Z0-9.,]/g,"");else{var v=String(e.value).trim();if(v==="")continue;o[f[0]]=String(+v)}}return{body:o}}
s4Fill({btc_sunday_bounce:"1",btc_short_pullback:"0",orb_session:"1"});
var a=s4Body(S4A).body; s4Fill({btc_sunday_bounce:"0",btc_short_pullback:"0",orb_session:"0"}); var b=s4Body(S4A).body;
console.log(JSON.stringify({a:a,b:b}));""" % json.dumps(S4A)
    out = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True).stdout or '{}')
    T('node: ticked boxes are sent as "1" and unticked as "0"', out.get('a', {}).get('btc_sunday_bounce') == '1' and out['a']['btc_short_pullback'] == '0' and out['a']['orb_session'] == '1')
    T('node: all three are always in the saved body (so unticking works)', all(k in out.get('b', {}) and out['b'][k] == '0' for k in KEYS))
    T('node: nothing else is sent as a switch value', all(v in ('0', '1') for k, v in out['a'].items() if k in KEYS))
# the API round trip the page does
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
C.get('/api/me', headers=A); C.get('/api/me', headers=U)
x = C.post('/api/admin/settings', json={}, headers=A); j = x.get_json() or {}
T('loading the page values (POST {}) returns all three, "0" by default', x.status_code == 200 and all(j.get(k) == '0' for k in KEYS))
x = C.post('/api/admin/settings', json={'btc_sunday_bounce': '1', 'btc_short_pullback': '0', 'orb_session': '1', 'max_trades_day': '0'}, headers=A); j = x.get_json() or {}
T('Save advanced with two ticked: the server keeps them', x.status_code == 200 and j.get('btc_sunday_bounce') == '1' and j.get('btc_short_pullback') == '0' and j.get('orb_session') == '1')
x = C.post('/api/admin/settings', json={}, headers=A); j = x.get_json() or {}
T('reloading shows the saved state (what the boxes will show)', j.get('btc_sunday_bounce') == '1' and j.get('orb_session') == '1' and j.get('btc_short_pullback') == '0')
x = C.post('/api/admin/settings', json={'btc_sunday_bounce': '0', 'btc_short_pullback': '0', 'orb_session': '0'}, headers=A)
T('unticking all three switches them off again', x.status_code == 200 and all(st.get(k) == '0' for k in KEYS))
x = C.post('/api/admin/settings', json={'orb_session': '1'}, headers=U)
T('a subscriber cannot flip any of them', x.status_code in (401, 403) and st.get('orb_session') == '0')
import backend.strategies as S
T('the strategies behind the switches exist', all(n in [f.__name__ for f in S.ALL] for n in ('btc_sunday_bounce', 'btc_pullback_short', 'orb_session')))
bad = [n for n, ok in R if not ok]
for n in bad: print('FAIL:', n)
print('%d checks, %d failed' % (len(R), len(bad)))
if os.path.exists(DB): os.remove(DB)
sys.exit(1 if bad else 0)
