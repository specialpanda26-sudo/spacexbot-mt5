"""Checks Section 7: the Home cartoon follows the bot's real situation (locked, loss limit, stopped, profit target, market closed, running).
The decision code (h7pick) and the whole H7 block run in node against a fake page; the rest is plain text checks. No temp files. Run: python tests/test_home7.py"""
import os, re, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def cut(a, b):
    i = S.find(a); j = S.find(b, i + 1) if i > -1 else -1
    return S[i:j + len(b)] if i > -1 and j > -1 else ''
blk = cut('/*H7-start*/', '/*H7-end*/'); pure = cut('/*H7-pure-start*/', '/*H7-pure-end*/')
T('the H7 block is in the page once, with its own script tag after S4', S.count('/*H7-start*/') == 1 and S.count('/*H7-end*/') == 1 and S.find('/*S4-end*/') < S.find('/*H7-start*/') and S.count('/*H7-pure-start*/') == 1)
T('S4 publishes window.SXBOT and S3 publishes window.SXLIVE (once each)', S.count('window.SXBOT = {') == 1 and S.count('window.SXLIVE = {') == 1)
T('every picture the states use exists in IL2 (lock, shield, wait, yay, sleep)', all(x in S for x in ('lock:il2(', 'IL2.shield=il2(', 'wait:il2(', 'yay:il2(', 'IL2.sleep=il2(')))
T('the five pictures are the ones asked for (lock, shield, wait, yay, sleep)', all(x in blk for x in ('lock: I.lock', 'loss: I.shield', 'stopped: I.wait', 'target: I.yay', 'closed: I.sleep')))
T('the character is wrapped in the bd class so the Section 4 bob moves it', "'<g class=\"bd\">'" in blk and '.buddy .bd{animation-name:sxbb!important' in S)
T('no hard-coded colour, no Arial in the block', not re.search(r'#[0-9a-fA-F]{3,8}\b|Arial|rgb\(', blk))
T('wording is facts only: no fixes, guarantee, earn, will profit', not re.search(r'(?i)\bfix|guarantee|you will (earn|win|profit)|make money', blk))
T('the profit line says the target is the person\'s own setting, never that the bot stopped', 'daily target of $' in blk and 'stopped' not in blk.split('"target"')[-1][:200])
js = r"""
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
const pick = new Function(P.pure + ';return h7pick;')();
const bot = (state, code, why) => ({state, code, why});
const live = (today, state) => ({state: state || 'live', today});
ok('pick: locked wins over everything', pick({locked: true, bot: bot('watching', 'daily loss limit hit', 'x'), live: live(9), tp: 3}).k === 'lock');
ok('pick: daily loss limit -> loss, with the server sentence', JSON.stringify(pick({bot: bot('waiting', 'daily loss limit hit', 'The daily loss limit was reached.'), tp: 3})) === JSON.stringify({k: 'loss', say: 'The daily loss limit was reached.'}));
ok('pick: weekly loss limit -> loss', pick({bot: bot('waiting', 'weekly loss limit hit', 'w'), tp: 3}).k === 'loss');
ok('pick: loss limit beats profit target', pick({bot: bot('waiting', 'daily loss limit hit', 'x'), live: live(50), tp: 3}).k === 'loss');
ok('pick: stopped -> stopped', pick({bot: bot('stopped', 'bot off'), tp: 3}).k === 'stopped');
ok('pick: stopped beats profit target', pick({bot: bot('stopped', 'bot off'), live: live(50), tp: 3}).k === 'stopped');
ok('pick: today at the target counts (>=)', pick({bot: bot('watching', 'watching'), live: live(3), tp: 3}).k === 'target');
ok('pick: just under the target is not a target', pick({bot: bot('watching', 'watching'), live: live(2.99), tp: 3}).k === 'run');
ok('pick: target line is facts with the numbers', pick({bot: bot('watching', 'x'), live: live(4.2), tp: 3}).say === "Today's profit is $4.20, at or above your daily target of $3.");
ok('pick: a target of 0 means no target', pick({bot: bot('watching', 'x'), live: live(5), tp: 0}).k === 'run');
ok('pick: stale or offline live numbers do not celebrate', pick({bot: bot('watching', 'x'), live: live(5, 'stale'), tp: 3}).k === 'run' && pick({bot: bot('watching', 'x'), live: live(5, 'none'), tp: 3}).k === 'run');
ok('pick: a loss today is never a target', pick({bot: bot('watching', 'x'), live: live(-5), tp: 3}).k === 'run');
ok('pick: weekend rule -> market closed with the server sentence', JSON.stringify(pick({bot: bot('waiting', 'weekend/Friday-night risk', 'Markets are closed.'), tp: 3})) === JSON.stringify({k: 'closed', say: 'Markets are closed.'}));
ok('pick: profit target beats market closed', pick({bot: bot('waiting', 'weekend/Friday-night risk', 'm'), live: live(9), tp: 3}).k === 'target');
ok('pick: running, waiting for EA, no data yet -> usual candles', ['watching', 'EA offline', ''].every(c => pick({bot: bot('waiting', c), tp: 3}).k === 'run') && pick({tp: 3}).k === 'run');

// the whole block against a fake page
function page(o) {
  const g = {timers: [], icons: {lock: '<svg class="ill2" a><g>LOCK</g><path d="M114 146c-14 4-26 2-38-4"/><g>CH</g></svg>'}};
  const mk = () => ({innerHTML: '', textContent: '', hidden: false, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; }, insertAdjacentElement(w, e) { this.after = e; }});
  const sv = mk(); sv.writes = 0; let _h = 'HOMEART'; Object.defineProperty(sv, 'innerHTML', {get: () => _h, set: v => { _h = v; sv.writes++; }}); const actions = mk();
  const card = {querySelector: s => s === 'svg.buddy.cart' ? sv : s === '.buddy-actions' ? actions : null};
  const win = {IL2: o.il2 === undefined ? {lock: '<svg class="ill2"><g>LOCK</g><path d="M114 146c-14 4-26 2-38-4"/><g transform="translate(112 40)">CH</g></svg>', shield: '<svg class="ill2"><g>SHIELD</g><path d="M114 146c-14 4-26 2-38-4"/><g>CH</g></svg>', wait: '<svg class="ill2"><g>WAIT</g><path d="M114 146c-14 4-26 2-38-4"/><g>CH</g></svg>', yay: '<svg class="ill2"><g>YAY</g><path d="M114 146c-14 4-26 2-38-4"/><g>CH</g></svg>', sleep: '<svg class="ill2"><g>SLEEP</g><path d="M114 146c-14 4-26 2-38-4"/><g>CH</g></svg>'} : o.il2};
  const g2 = {user: o.user, resolved: o.resolved === undefined ? true : o.resolved, tp: o.tp};
  const SXA = {user: () => g2.user, resolved: () => g2.resolved};
  const doc = {querySelector: s => s === '#view-home .buddy-card' ? card : null, createElement: () => mk()};
  const ls = {getItem: k => k === 'sxb_up' && g2.tp !== undefined ? JSON.stringify({tp: g2.tp}) : null};
  new Function('document', 'window', 'SXA', 'setInterval', 'localStorage', P.blk)(doc, win, SXA, f => g.timers.push(f), ls);
  return Object.assign(g, {sv, note: actions.after, win, g2, tick: () => g.timers[0]()});
}
const paid = {uid: 'u1', verified: true, active: true}, now = () => Date.now();
let p = page({user: paid});
ok('block: starts with the usual Home candles and no note', p.sv.innerHTML === 'HOMEART' && p.note.hidden === true && p.sv.attrs['data-h7'] === 'run');
p.win.SXBOT = {u: 'u1', t: now(), j: bot('waiting', 'daily loss limit hit', 'The daily loss limit was reached.')}; p.tick();
ok('block: loss limit shows the shield, the character bobs (bd), and the server sentence', p.sv.innerHTML.includes('SHIELD') && p.sv.innerHTML.includes('<g class="bd"><path d="M114 146') && p.sv.innerHTML.endsWith('</g></g>') && p.note.textContent === 'The daily loss limit was reached.' && p.note.hidden === false);
ok('block: the svg wrapper tag of the prop is not nested into the Home svg', !p.sv.innerHTML.includes('<svg'));
p.win.SXBOT = {u: 'u1', t: now(), j: bot('watching', 'watching', 'ok')}; p.tick();
ok('block: back to running puts the candles back and hides the note', p.sv.innerHTML === 'HOMEART' && p.note.hidden === true);
p.win.SXBOT = {u: 'u1', t: now(), j: bot('stopped', 'bot off', 'The bot is stopped.')}; p.tick();
ok('block: stopped shows the clock and no extra line', p.sv.innerHTML.includes('WAIT') && p.note.hidden === true);
p.win.SXBOT = {u: 'u1', t: now(), j: bot('watching', 'watching', 'ok')}; p.win.SXLIVE = {u: 'u1', t: now(), j: live(4.2)}; p.tick();
ok('block: profit at the default $3 target shows the party and the numbers', p.sv.innerHTML.includes('YAY') && p.note.textContent.includes('$4.20') && p.note.textContent.includes('$3.'));
p.g2.tp = 10; p.tick();
ok('block: the Bot tab target (localStorage sxb_up) is used', p.sv.innerHTML === 'HOMEART');
p.g2.tp = 3; p.win.SXLIVE = {u: 'u1', t: now(), j: live(4.2)}; p.tick(); const before = p.sv.innerHTML;
const w0 = p.sv.writes; p.win.SXLIVE = {u: 'u1', t: now(), j: live(4.3)}; p.tick();
ok('block: a number change updates the line but does not redraw the picture (so its motion does not restart)', p.sv.innerHTML === before && p.sv.writes === w0 && p.note.textContent.includes('$4.30'));
p.g2.tp = null; p.win.SXLIVE = {u: 'u1', t: now(), j: live(4.3)}; p.tick();
ok('block: an empty saved target falls back to the page default $3 (not 0)', p.sv.innerHTML.includes('YAY'));
p.g2.tp = 3;
p.win.SXBOT = {u: 'u1', t: now(), j: bot('waiting', 'weekend/Friday-night risk', 'Markets are closed or too risky now.')}; p.win.SXLIVE = null; p.tick();
ok('block: weekend rule shows the moon and the server sentence', p.sv.innerHTML.includes('SLEEP') && p.note.textContent.startsWith('Markets are closed'));
p.win.SXBOT = {u: 'u2', t: now(), j: bot('waiting', 'daily loss limit hit', 'x')}; p.tick();
ok('block: numbers that belong to another person are ignored', p.sv.innerHTML === 'HOMEART');
p.win.SXBOT = {u: 'u1', t: now() - 200000, j: bot('waiting', 'daily loss limit hit', 'x')}; p.tick();
ok('block: answers older than 2 minutes are ignored', p.sv.innerHTML === 'HOMEART');
p.g2.user = {uid: 'u1', verified: true, active: false, plan_until: 0}; p.tick();
ok('block: no plan -> lock picture', p.sv.innerHTML.includes('LOCK'));
p.g2.user = {uid: 'u1', verified: true, active: false, plan_until: Date.now() / 1000 + 9999}; p.tick();
ok('block: a plan that has not run out is not locked', p.sv.innerHTML === 'HOMEART');
p.g2.user = {uid: 'o', verified: true, admin: true}; p.tick();
ok('block: the owner is not locked', p.sv.innerHTML === 'HOMEART');
p.g2.user = null; p.tick();
ok('block: signed out -> lock picture', p.sv.innerHTML.includes('LOCK'));
p.g2.resolved = false; p.tick();
ok('block: while sign-in is still being worked out, no lock flash', p.sv.innerHTML === 'HOMEART');
p = page({user: paid, il2: null}); p.win.SXBOT = {u: 'u1', t: now(), j: bot('stopped', 'bot off')}; p.tick();
ok('block: if IL2 is missing the usual candles stay (no blank picture)', p.sv.innerHTML === 'HOMEART' && p.sv.attrs['data-h7'] === 'run');
console.log(JSON.stringify(OUT));
"""
if shutil.which('node'):
    r = subprocess.run(['node', '-e', js], input=json.dumps({'pure': pure, 'blk': blk.replace('/*H7-start*/', '', 1)}), capture_output=True, text=True, timeout=60)
    try: res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: res = []; print(r.stdout[-300:], r.stderr[-800:])
    for n, ok in res: T(n, ok)
    T('the node run produced all its answers (33)', len(res) == 33)
else: print('SKIP node not installed')
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
