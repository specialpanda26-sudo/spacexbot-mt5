"""Checks Section 8e: the Home speech bubble follows the Home picture (locked, loss limit, stopped, profit target, market closed, running).
The text rule (b8eText) and the whole B8e block run in node against a fake page with a fake Node.prototype.textContent; the H7 side is checked as text. No temp files. Run: python tests/test_bub8e.py"""
import os, re, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def cut(a, b):
    i = S.find(a); j = S.find(b, i + 1) if i > -1 else -1
    return S[i:j + len(b)] if i > -1 and j > -1 else ''
blk = cut('/*B8e-start*/', '/*B8e-end*/'); pure = cut('/*B8e-pure-start*/', '/*B8e-pure-end*/'); h7 = cut('/*H7-start*/', '/*H7-end*/')
T('the B8e block is in the page once, in its own script tag after H8c', S.count('/*B8e-start*/') == 1 and S.count('/*B8e-end*/') == 1 and S.find('/*H8c-end*/') < S.find('/*B8e-start*/') and S.count('/*B8e-pure-start*/') == 1)
T('H7 publishes window.SXH7 once, inside its own block, with k, say and why', S.count('window.SXH7 = {') == 1 and 'window.SXH7 = {' in h7 and 'why: (fresh(window.SXBOT)' in h7)
T('H7 publishes after it has settled the state (after the IL2-missing fallback)', h7.find('r = { k: k }; inner = HOME;') < h7.find('window.SXH7 = {'))
T('the older #bubble writers are untouched (render, locked sync, S4 home)', 'state==="paused"?"I\'m taking a break.' in S and 'The bot is locked. Choose a plan to switch it on."' in S and 'bu.textContent !== s) bu.textContent = s;' in S)
T('no hard-coded colour in the block', not re.search(r'#[0-9a-fA-F]{3,8}\b|rgb\(', blk))
T('wording is facts only: no fixes, guarantee, earn, will profit', not re.search(r'(?i)\bfix|guarantee|you will (earn|win|profit)|make money', blk))
js = r"""
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
const txt = new Function(P.pure + ';return b8eText;')();
ok('text: nothing known -> nothing held', txt(undefined) === '' && txt(null) === '' && txt({k: 'run'}) === '');
ok('text: lock', txt({k: 'lock'}) === 'The bot is locked. Choose a plan to switch it on.');
ok('text: loss limit uses the server sentence', txt({k: 'loss', say: 'The daily loss limit was reached.'}) === 'The daily loss limit was reached.');
ok('text: loss limit without a sentence still says the true thing', txt({k: 'loss', say: ''}) === 'A loss limit was reached, so the bot is not opening new trades.');
ok('text: stopped uses the server sentence', txt({k: 'stopped', why: 'Your plan has ended.'}) === 'Your plan has ended.');
ok('text: stopped without a sentence', txt({k: 'stopped', why: ''}) === 'The bot is stopped. Tap Start bot.');
ok('text: target and closed use the line of the grey note', txt({k: 'target', say: 'T'}) === 'T' && txt({k: 'closed', say: 'C'}) === 'C');
ok('text: target / closed with no line hold nothing', txt({k: 'target', say: ''}) === '' && txt({k: 'closed', say: ''}) === '');
ok('text: an unknown state holds nothing', txt({k: 'zzz', say: 'x'}) === '');

function page(o) {
  const timers = [];
  function NodeC() {}
  Object.defineProperty(NodeC.prototype, 'textContent', {configurable: true, get() { return this._t === undefined ? '' : this._t; }, set(v) { this._t = String(v); this.sets = (this.sets || 0) + 1; }});
  const bu = Object.create(NodeC.prototype); bu._t = 'sample';
  const doc = {getElementById: id => id === 'bubble' && !o.nobubble ? bu : null};
  const win = {};
  new Function('document', 'window', 'Node', 'setInterval', P.blk)(doc, win, o.badNode ? {prototype: {}} : NodeC, f => timers.push(f));
  return {bu, win, tick: () => timers.forEach(f => f()), timers};
}
let p = page({});
ok('block: starts by leaving the page text alone', p.bu.textContent === 'sample' && p.timers.length === 1);
p.bu.textContent = 'I am watching 8 pairs.'; p.tick();
ok('block: running (no SXH7): older writers show as before', p.bu.textContent === 'I am watching 8 pairs.');
p.win.SXH7 = {k: 'run', say: '', why: ''}; p.bu.textContent = 'older text A'; p.tick();
ok('block: SXH7 run: older writers show as before', p.bu.textContent === 'older text A');
p.win.SXH7 = {k: 'loss', say: 'The daily loss limit was reached.', why: 'w'}; p.tick();
ok('block: loss limit replaces the bubble text with the server sentence', p.bu.textContent === 'The daily loss limit was reached.');
p.bu.textContent = "I'm watching 8 pairs. XAUUSD looks the most interesting right now.";
ok('block: an older writer cannot overwrite the held text (even before the next tick)', p.bu.textContent === 'The daily loss limit was reached.');
p.tick();
ok('block: still held after a tick', p.bu.textContent === 'The daily loss limit was reached.');
const sets = p.bu.sets; p.tick(); p.tick();
ok('block: a held text is not rewritten every tick', p.bu.sets === sets);
p.win.SXH7 = {k: 'stopped', say: '', why: 'The bot is stopped. Tap Start bot.'}; p.tick();
ok('block: stopped shows the server sentence', p.bu.textContent === 'The bot is stopped. Tap Start bot.');
p.win.SXH7 = {k: 'target', say: "Today's profit is $4.20, at or above your daily target of $3.", why: ''}; p.tick();
ok('block: profit target shows the numbers line', p.bu.textContent.startsWith("Today's profit is $4.20"));
p.win.SXH7 = {k: 'closed', say: 'Markets are closed or too risky now.', why: ''}; p.tick();
ok('block: market closed shows the server sentence', p.bu.textContent === 'Markets are closed or too risky now.');
p.win.SXH7 = {k: 'lock', say: '', why: ''}; p.tick();
ok('block: locked shows the locked line', p.bu.textContent === 'The bot is locked. Choose a plan to switch it on.');
p.bu.textContent = "I'm watching 8 pairs. Nothing worth trading yet."; p.win.SXH7 = {k: 'run', say: '', why: ''}; p.tick();
ok('block: back to running gives the last older text back (not the held one)', p.bu.textContent === "I'm watching 8 pairs. Nothing worth trading yet.");
p.bu.textContent = 'newer older text'; 
ok('block: after the hold ends, older writers show again at once', p.bu.textContent === 'newer older text');
p.win.SXH7 = undefined; p.tick();
ok('block: SXH7 gone (H7 not there) holds nothing', p.bu.textContent === 'newer older text');
p = page({}); p.win.SXH7 = {k: 'stopped', why: 'S'}; p.tick(); p.win.SXH7 = {k: 'run'}; p.tick();
ok('block: held from the very first write and released with nothing written by others: no crash, text stays', p.bu.textContent === 'S');
p = page({nobubble: true});
ok('block: no #bubble on the page -> does nothing, no timer', p.timers.length === 0);
p = page({badNode: true});
ok('block: a browser without the textContent accessor -> does nothing, no timer', p.timers.length === 0);
console.log(JSON.stringify(OUT));
"""
if shutil.which('node'):
    r = subprocess.run(['node', '-e', js], input=json.dumps({'pure': pure, 'blk': blk.replace('/*B8e-start*/', '', 1)}), capture_output=True, text=True, timeout=60)
    try: res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: res = []; print(r.stdout[-300:], r.stderr[-800:])
    for n, ok in res: T(n, ok)
    T('the node run produced all its answers (26)', len(res) == 26)
else: print('SKIP node not installed')
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
