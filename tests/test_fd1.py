"""Section FD1: the sample backtest must not feed the go-live verdict or the Journal."""
import os, re, sys
H = os.path.dirname(os.path.abspath(__file__))
S = open(os.path.join(H, '..', 'static', 'index.html'), encoding='utf-8').read()
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1
    else: bad += 1; print('FAIL', name)

m = re.search(r'function rc\(\)\{.*?\n\n', S, re.S)
rc = m.group(0) if m else ''
chk('rc found', len(rc) > 500)
chk('verdict ignores sample result', 'c4=null,c5=' in rc and 'b.pf>1' not in rc)
chk('evidence row never reads the sample', 'b.pf.toFixed' not in rc and 'Not tested on real candles yet' in rc)
chk('pass needs real trades', 'else if(c5!==true)' in rc and 'c4===null' not in rc)
chk('pass text still guarded', 'Conditions pass. Treat it as unproven' in rc and 'c4===false||c5===false' in rc)
chk('no Journal write from the sample', 'ja("note","Backtest ran' not in S)
chk('click still runs the demo', '$("#btGo").onclick=function(){' in S and 'runBt()},450)' in S)
chk('card says it does not count', 'does not count in the go-live check' in S)
print('%d/%d passed' % (ok, ok + bad))
sys.exit(1 if bad else 0)
