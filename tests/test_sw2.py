"""SW2 tests: strategy switching in plain view + the person's own learned switch. Run: python tests/test_sw2.py (card checks need node)."""
import os, sys, json, time, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_sw2_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend import app as A, store as st, prefs, stats
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); me = {'Authorization': 'Bearer dev:amy@x.com'}; uid = c.get('/api/me', headers=me).get_json().get('uid')
j = c.get('/api/regimes', headers=me).get_json()
T('starts automatic only: own switch off, owner off, ADX limits shown', j['mine'] is False and j['owner'] is False and j['active'] is False and j['adx_quiet'] == 18 and j['adx_strong'] == 28 and j['rows'] == [])
T('a person can turn the learned switch on', c.post('/api/prefs', json={'regime': True}, headers=me).status_code == 200 and c.get('/api/regimes', headers=me).get_json()['active'] is True)
T('a wrong value is refused', c.post('/api/prefs', json={'regime': 'yes'}, headers=me).status_code == 400)
c.post('/api/prefs', json={'alone': False, 'entries': 0}, headers=me)
T('the Profile page saving other choices keeps the switch', prefs.get(uid)['regime'] is True)
NOW = int(time.time()); st.put('regime_min_trades', '5')          # 6 trades per market type below are enough for this test
def sig(strategy, pnl, regime):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,status,created,pnl,closed,strategy,reason,grp,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", ('XAUUSD', 'buy', 100.0, 99.0, 102.0, 'closed', NOW - 5000, pnl, NOW - 4000, strategy, json.dumps({'regime': regime, 'adx': 20}), None, uid))
for _ in range(6): sig('bb_reversion', -2.0, 'strong trend')
for _ in range(6): sig('bb_reversion', 3.0, 'quiet')
j = c.get('/api/regimes', headers=me).get_json(); r = {(x['strategy'], x['regime']): x for x in j['rows']}
T('rows: losing market type is weak and paused, winning one is not', r[('bb_reversion', 'strong trend')]['paused'] is True and r[('bb_reversion', 'quiet')]['paused'] is False and r[('bb_reversion', 'strong trend')]['group'] == 'reversion')
T('the scanner really pauses it for this person', 'strong trend' in stats.regime_off(uid).get('bb_reversion', set()))
c.post('/api/prefs', json={'regime': False}, headers=me)
j = c.get('/api/regimes', headers=me).get_json(); x = [y for y in j['rows'] if y['regime'] == 'strong trend'][0]
T('switch off: still shown as losing, but not paused', x['weak'] is True and x['paused'] is False and j['active'] is False)
c.post('/api/prefs', json={'regime': True}, headers=me); st.put('auto_mode', '1')
j = c.get('/api/regimes', headers=me).get_json(); T('Auto settings turns the learned switch off', j['auto'] is True and j['active'] is False)
st.put('auto_mode', '0'); st.put('regime_switch', '1'); c.post('/api/prefs', json={'regime': False}, headers=me)
j = c.get('/api/regimes', headers=me).get_json(); T("the owner's switch alone also activates it", j['owner'] is True and j['mine'] is False and j['active'] is True)
st.put('scan:%s:XAUUSD' % uid, json.dumps({'t': int(time.time()) - 120, 'c': 'nosetup', 'w': 'None looked. Market: quiet and ranging (ADX 12), so reversal strategies lead and trend setups are skipped.'}))
j = c.get('/api/regimes', headers=me).get_json(); T('latest reading comes from the real scan note', j['market'].startswith('Market: quiet and ranging (ADX 12)') and 100 <= j['market_age'] <= 200)
src = open(os.path.join(ROOT, 'backend', 'app.py'), encoding='utf-8').read() + open(os.path.join(ROOT, 'backend', 'screenread.py'), encoding='utf-8').read()
T("all 3 scanner places use the person's own switch too", src.count("prefs.get(uid)['regime']") == 3)
s = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('card present once', s.count('/*SW2-start*/') == 1 and s.count('/*SW2-end*/') == 1 and s.index('/*SW2-start*/') > s.index('/*BT1-end*/'))
blk = s.split('/*SW2-start*/')[1].split('/*SW2-end*/')[0]
if shutil.which('node'):
    js = ("var vb={insertBefore:function(){},firstChild:null};function card(){return 1}function esc(x){return String(x)}var E={};function $(q){return E[q]||(E[q]={setAttribute:function(k,v){this[k]=v},value:'',textContent:'',innerHTML:''})}function toast(){}"
          "var window={SXA:{api:function(){return Promise.resolve({owner:false,mine:true,auto:false,active:true,min_trades:10,adx_quiet:18,adx_strong:28,market:'Market: quiet (ADX 12).',market_age:120,rows:[{name:'Bollinger reversion',group:'reversion',regime:'quiet',n:6,win_rate:50,avg:0.5,weak:true,paused:true}]})}}};var SXA=window.SXA;" + blk +
          ";setTimeout(function(){console.log([E['#swcChip'].textContent,E['#swcOn']['aria-checked'],E['#swcAuto'].textContent.indexOf('Above 28')>-1&&E['#swcAuto'].textContent.indexOf('Below 18')>-1,E['#swcMarket'].textContent.indexOf('2 min ago')>-1,E['#swcRows'].innerHTML.indexOf('paused here')>-1].join('|'))},20)")
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    T('card shows the switch, the real limits, the reading and the paused row', out.stdout.strip() == 'Learned switch on|true|true|true|true')
    if out.returncode: print(out.stderr[:400])
else: print('node not found: card checks skipped')
if os.path.exists(DB): os.remove(DB)
bad = [n for n, ok in R if not ok]; print('%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
