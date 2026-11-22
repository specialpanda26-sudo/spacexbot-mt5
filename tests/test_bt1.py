"""BT1 tests: the Burst switch card on the Bot tab. Run: python tests/test_bt1.py (card checks need node)."""
import os, sys, re, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); me = {'Authorization': 'Bearer dev:amy@x.com'}; c.get('/api/me', headers=me)
j = c.get('/api/burst', headers=me).get_json(); T('starts off', j['settings']['on'] is False)
j = c.post('/api/burst', json={'on': True}, headers=me).get_json(); T('switch on saves', j['settings']['on'] is True)
j = c.post('/api/burst', json={'on': False}, headers=me).get_json(); T('switch off saves', j['settings']['on'] is False)
T('bad number refused', c.post('/api/burst', json={'quick_n': 99}, headers=me).status_code == 400)
s = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('card present once', s.count('/*BT1-start*/') == 1 and s.count('/*BT1-end*/') == 1)
blk = s.split('/*BT1-start*/')[1].split('/*BT1-end*/')[0]
if shutil.which('node'):
    js = "var vb={appendChild:function(){}};function card(){return 1}var E={};function $(q){return E[q]||(E[q]={setAttribute:function(k,v){this[k]=v},value:'',textContent:''})}function toast(){}var window={SXA:{api:function(){return Promise.resolve({settings:{on:true,idle_min:5,quick_n:5,quick_usd:0.5},enabled:true,now:{state:'waiting',why:'Watching.'}})}}};var SXA=window.SXA;" + blk + ";setTimeout(function(){console.log(E['#btChip'].textContent+'|'+E['#btNow'].textContent+'|'+E['#btOn']['aria-checked'])},20)"
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    T('card code runs and shows On + the plain-words line', out.stdout.strip() == 'On|Watching.|true')
bad = [n for n, ok in R if not ok]; print('%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
