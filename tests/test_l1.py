"""L1 tests: learner cards say why they are missing; the quiz button needs every answer. Run: python tests/test_l1.py"""
import os, re, sys, shutil, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
rd = lambda f: open(os.path.join(ROOT, 'static', f), encoding='utf-8').read()
for f, d, w in (('course.js', 'c', 'learning path'), ('roadmap.js', 'r', 'road to Real'), ('guide.js', 'g', 'guide')):
    js = rd(f)
    T(f + ': says to verify the email', 'Verify your email' in js)
    T(f + ': says when it could not load, with a Try again button', 'Could not load' in js and 'data-%s="retry"' % d in js and 'c === "retry"' in js)
    T(f + ': failures are no longer swallowed', 'ERR = true; drawCard();' in js and '.catch(function () {});' not in js.split('function load')[1].split('function close')[0])
    T(f + ': no colours written', not re.search(r'#[0-9a-fA-F]{3,6}\b', js))
    if shutil.which('node'): T(f + ' is valid JavaScript', subprocess.run(['node', '--check', os.path.join(ROOT, 'static', f)], capture_output=True).returncode == 0)
cj = rd('course.js')
T('quiz: button waits for every answer', 'typeof S.pick[i] === "number"' in cj and 'indexOf(undefined)' not in cj)
if shutil.which('node'):
    code = 'var q=[1,2,3],pick=[];pick[1]=0;pick[2]=1;var ok=function(){return q.every(function(x,i){return typeof pick[i]==="number"})};var a=ok();pick[0]=2;process.stdout.write(a+","+ok())'
    T('quiz: skipped first question keeps the button off, all answered turns it on', subprocess.run(['node', '-e', code], capture_output=True, text=True).stdout == 'false,true')
print('%d/%d passed' % (sum(R), len(R))); raise SystemExit(0 if all(R) else 1)
