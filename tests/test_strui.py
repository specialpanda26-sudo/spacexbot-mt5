"""Section A2 checks: the admin 'Strategies' card + results table in static/index.html. Needs node (skipped if missing). Run: python tests/test_strui.py
The card's code sits between /*A2-start*/ and /*A2-end*/ and is run here against a fake page and a fake server."""
import os, sys, re, json, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(name, ok): R.append((name, bool(ok)))

T('the card code is in the page exactly once', html.count('/*A2-start*/') == 1 and html.count('/*A2-end*/') == 1)
T('the panel has the Strategies and Results places (#aStr, #aStrT) before the Subscribers part', 0 < html.find('id="aStr"') < html.find('id="aStrT"') < html.find('>Subscribers</h3>'))
bad = []
for i, x in enumerate(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)):
    p = os.path.join(tempfile.gettempdir(), 'sxb_strui_%d.js' % i); open(p, 'w', encoding='utf-8').write(x)
    if subprocess.run(['node', '--check', p], capture_output=True).returncode: bad.append(i)
T('every script in the page still parses (nothing broken by the new card)', not bad)

m = re.search(r'/\*A2-start\*/(.*?)/\*A2-end\*/', html, re.S); CODE = m.group(1) if m else ''
HARNESS = r'''
const code = process.argv[1]; const OUT = [];
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tick = () => new Promise(r => setTimeout(r, 5));
function page(rows, api) {
  const els = {'#aStr': {innerHTML: ''}, '#aStrT': {innerHTML: ''}}, calls = [], toasts = []; let btns = [];
  const $ = s => els[s] || null;
  const $$ = () => { btns = [...els['#aStr'].innerHTML.matchAll(/data-st="(\d+)"/g)].map(x => ({dataset: {st: x[1]}, disabled: false, onclick: null})); return btns; };
  const SXA = {api: (u, o) => { calls.push({u, o}); return api(u, o, rows); }};
  const f = new Function('$', '$$', 'esc', 'tst', 'SXA', 'ovEl', code + '; return {STR: () => STR};');
  const h = f($, $$, esc, t => toasts.push(t), SXA, {});
  return {els, calls, toasts, btns: () => btns, h};
}
const ok = (u, o, rows) => u === '/api/admin/strategies' ? Promise.resolve(rows) : Promise.resolve({});
const mk = (id, name, extra) => Object.assign({id, name, desc: name + ' desc', group: 'trend', on: true, n: 0, wins: 0, win_rate: null, avg: null, pnl: null}, extra || {});
(async () => {
  const rows = [mk('a', 'Alpha', {n: 30, wins: 20, win_rate: 66.7, avg: 2.5, pnl: 75}), mk('b', 'Beta', {on: false, group: 'reversion', n: 5, wins: 1, win_rate: 20, avg: -1.5, pnl: -7.5}), mk('c', 'Gamma'), mk('d', '<img src=x onerror=alert(1)>')];
  let p = page(rows, ok); await tick();
  const S = p.els['#aStr'].innerHTML, Tb = p.els['#aStrT'].innerHTML;
  OUT.push(['asks the server for the strategy list', p.calls[0] && p.calls[0].u === '/api/admin/strategies']);
  OUT.push(['one switch per strategy, with its name and description', (S.match(/data-st=/g) || []).length === 4 && S.includes('Alpha') && S.includes('Alpha desc') && S.includes('Gamma desc')]);
  OUT.push(['switch state follows on/off (aria-checked)', /aria-checked="true" data-st="0"/.test(S) && /aria-checked="false" data-st="1"/.test(S)]);
  OUT.push(['trend / reversion tag shown', S.includes('>trend<') && S.includes('>reversion<')]);
  OUT.push(['results line: trades, win rate, average; or no trades yet', S.includes('30 trades · 66.7% wins · avg 2.5') && S.includes('5 trades · 20% wins · avg -1.5') && S.includes('no trades yet')]);
  OUT.push(['a strategy name is escaped (no HTML injection)', !S.includes('<img') && S.includes('&lt;img')]);
  OUT.push(['table lists only strategies with trades, best average first', Tb.indexOf('Alpha') > 0 && Tb.indexOf('Alpha') < Tb.indexOf('Beta') && !Tb.includes('Gamma')]);
  OUT.push(['table: "few" tag under 20 trades, none at 20 or more', /Beta<\/b> <span class="chip watch">few/.test(Tb) && !/Alpha<\/b> <span class="chip watch">few/.test(Tb)]);
  OUT.push(['table: negative average is red, positive green', Tb.includes('var(--bad)">-1.5') && Tb.includes('var(--good)">2.5')]);
  // switch Alpha off: Beta was already off, so both go in the list
  p.btns()[0].onclick(); await tick();
  const c = p.calls.find(x => x.u === '/api/admin/settings');
  OUT.push(['switching off posts the full off list (already-off ones kept)', c && c.o.method === 'POST' && c.o.body.strategies_off.split(',').sort().join() === 'a,b']);
  OUT.push(['after saving, the switch shows off and a toast says so', /aria-checked="false" data-st="0"/.test(p.els['#aStr'].innerHTML) && p.toasts.includes('Alpha is off')]);
  // switch Beta back on: only Alpha stays in the list
  p.btns()[1].onclick(); await tick();
  const c2 = p.calls.filter(x => x.u === '/api/admin/settings')[1];
  OUT.push(['switching on removes it from the off list', c2 && c2.o.body.strategies_off === 'a' && /aria-checked="true" data-st="1"/.test(p.els['#aStr'].innerHTML) && p.toasts.includes('Beta is on')]);
  // all on: empty list
  p.btns()[0].onclick(); await tick();
  const c3 = p.calls.filter(x => x.u === '/api/admin/settings')[2];
  OUT.push(['everything back on sends an empty off list', c3 && c3.o.body.strategies_off === '']);
  // a failed save changes nothing
  p = page(rows.map(r => Object.assign({}, r)), (u, o, r) => u === '/api/admin/strategies' ? Promise.resolve(r) : Promise.reject(new Error('server said no'))); await tick();
  p.btns()[2].onclick(); await tick();
  OUT.push(['a failed save: switch stays as it was, the error is shown, the button works again', /aria-checked="true" data-st="2"/.test(p.els['#aStr'].innerHTML) && p.toasts.includes('server said no') && p.btns()[2].disabled === false && p.h.STR()[2].on === true]);
  // empty / failing loads
  p = page([], ok); await tick();
  OUT.push(['no strategies: friendly message', p.els['#aStr'].innerHTML.includes('No strategies found')]);
  OUT.push(['no closed trades: friendly message, no fake table', p.els['#aStrT'].innerHTML.includes('No closed trades yet') && !p.els['#aStrT'].innerHTML.includes('Wins')]);
  p = page([], () => Promise.reject(new Error('admin only'))); await tick();
  OUT.push(['load fails: the reason is shown', p.els['#aStr'].innerHTML.includes('admin only')]);
  console.log(JSON.stringify(OUT));
})();
'''
r = subprocess.run(['node', '-e', HARNESS, CODE], capture_output=True, text=True, timeout=30)
try: out = json.loads(r.stdout.strip().splitlines()[-1])
except Exception: out = []; print(r.stdout[-400:], r.stderr[-600:])
for n, ok in out: T(n, ok)
T('the card test ran all its checks', len(out) == 17)

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
