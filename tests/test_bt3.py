"""BT3 tests: Big burst fields on the Burst card. Run: python tests/test_bt3.py (card checks need node)."""
import os, sys, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_bt3_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); me = {'Authorization': 'Bearer dev:amy@x.com'}; c.get('/api/me', headers=me)
j = c.post('/api/burst', json={'big_n': 12, 'big_usd': 1.5}, headers=me).get_json()
T('big numbers save on the server', j['settings']['big_n'] == 12 and j['settings']['big_usd'] == 1.5)
T('view tells the card how many strategies must agree', isinstance(j.get('big_score'), int) and j['big_score'] >= 2)
T('big entries over the ceiling refused', c.post('/api/burst', json={'big_n': 99}, headers=me).status_code == 400)
s = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('big burst part present once', s.count('/*BT3*/') == 1 and s.count('id="bswBigN"') == 1 and s.count('id="bswBigUsd"') == 1)
blk = s.split('/*BT1-start*/')[1].split('/*BT1-end*/')[0]
if shutil.which('node'):
    js = ("var vb={appendChild:function(){},insertBefore:function(){},firstChild:null};function card(){return 1}var E={};function $(q){return E[q]||(E[q]={setAttribute:function(k,v){this[k]=v},value:'',textContent:''})}function toast(){}"
          "var window={SXA:{api:function(){return Promise.resolve({settings:{on:true,idle_min:5,quick_n:5,quick_usd:0.5,big_n:15,big_usd:1},enabled:true,ceiling:15,big_score:3,now:{state:'waiting',why:'Watching.'}})}}};var SXA=window.SXA;" + blk +
          ";setTimeout(function(){E['#bswBigN'].value='3';bswBigPrev();var a=E['#bswBigPrev'].textContent;E['#bswBigN'].value='5';bswBigPrev();var b=E['#bswBigPrev'].textContent;E['#bswBigN'].value='15';E['#bswBigUsd'].value='1';bswBigPrev();var d=E['#bswBigPrev'].textContent;"
          "console.log([E['#bswBigN'].max,E['#bswBigWhy'].textContent.indexOf('3 strategies')>-1,a.indexOf('refused')>-1,b.indexOf('never happens')>-1,d].join('|'))},20)")
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    T('card shows big fields, the strategy count and the three warnings', out.stdout.strip() == '15|true|true|true|15 entries x 1 USD each: a big burst closes at 15 USD in total.')
    if out.returncode: print(out.stderr[:400])
else: print('node not found: card checks skipped')
os.remove(os.environ['DB_PATH']) if os.path.exists(os.environ['DB_PATH']) else None
bad = [n for n, ok in R if not ok]; print('%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
