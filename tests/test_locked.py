"""Section 7 check: the bot lock follows the server plan, not the old on-device list. Needs node. Run: python tests/test_locked.py"""
import os, re, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
m = re.search(r'function locked\(\)\{.*?\}catch\(e\)\{return true\}\}', html)
if not m: print('FAIL locked() not found'); sys.exit(1)
js = ('var U=null;var SXA={user:function(){return U}};' + m.group(0) + ';var now=Date.now()/1e3,out=[];'
      'out.push(locked());U={admin:false,active:false,plan_until:0};out.push(locked());U={admin:false,active:false,plan_until:now-5};out.push(locked());'
      'U={admin:false,active:true,plan_until:now+999};out.push(locked());U={admin:true,active:false,plan_until:0};out.push(locked());U={plan_until:now+86400};out.push(locked());'
      'SXA=null;out.push(locked());console.log(JSON.stringify(out))')
try: got = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=20).stdout)
except Exception as e: print('FAIL could not run node:', e); sys.exit(1)
want = [True, True, True, False, False, False, True]
names = ['signed out', 'no plan', 'expired plan', 'active plan', 'admin', 'plan_until in the future', 'page not ready']
for n, g, w in zip(names, got, want): print(('PASS ' if g == w else 'FAIL ') + n + (' locked' if w else ' unlocked'))
ok = got == want; print('\n%d/%d passed' % (sum(g == w for g, w in zip(got, want)), len(want))); sys.exit(0 if ok else 1)
