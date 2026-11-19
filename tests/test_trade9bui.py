"""Section 9B page checks: the trade chart pop-up (the P9B block in static/index.html), the tappable Trades rows and the tappable profit curve (P9A). Needs node (skipped if missing).
Run: python tests/test_trade9bui.py   No temp files: the blocks go to node through a pipe and run against a fake page and a fake server."""
import os, sys, re, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok)))
def block(a, b): m = re.search(r'/\*%s-start\*/(.*?)/\*%s-end\*/' % (a, b), html, re.S); return m.group(1) if m else ''
C9B, C9A = block('P9B', 'P9B'), block('P9A', 'P9A')
T('the P9B block is in the page exactly once, right after the Profit and loss card (P9A)', html.count('/*P9B-start*/') == 1 and html.count('/*P9B-end*/') == 1 and html.find('/*P9A-end*/') < html.find('/*P9B-start*/') < html.find('/*S7-start*/'))
T('it reuses the page bottom sheet that already exists (#sheet, #sheetBody) and the Close button', 'id="sheet"' in html and 'id="sheetBody"' in html and 'data-close="1"' in C9B)
T('no made-up numbers in the block (no random, no sample data, no stored copy)', not re.search(r'Math\.random|sample|HIST|localStorage|sessionStorage', C9B))
T('only the site colours (CSS variables), no hard-coded colours', not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsl', C9B) and '--good' in C9B and '--bad' in C9B and 'var(' in C9B)
T('the only thing it reads from the "exit" part of the answer is the plain-words note (never a price or a reason)', re.findall(r'\.exit\.(\w+)', C9B) == ['note'] and not re.search(r'exit_price|close_price|\.reason', C9B))
T('Trades rows carry the trade id and are real buttons for the keyboard (data-tid, role, tabindex)', 'data-tid="\'+(Number(t.id)||0)+\'" role="button" tabindex="0"' in html)
T('the profit curve says it can be tapped and shows a pointer cursor (CSS), and its own markup is untouched', 'Tap a point on the curve to see that trade' in C9A and '#pnlc .chart svg{cursor:pointer}' in html and 'function tapCurve' in C9A and 'aria-label="Profit curve">' in C9A)
scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
HARNESS = r'''
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = [], ok = (n, c) => OUT.push([n, !!c]), tick = () => new Promise(r => setTimeout(r, 5));
const el = () => { const e = {_h: '', hidden: true, className: '', style: {}, cls: new Set(), handlers: {}, inserted: [],
  classList: {add: c => e.cls.add(c), remove: c => e.cls.delete(c), contains: c => e.cls.has(c) || (c === 'on' && e.on)},
  insertBefore(n, ref) { e.inserted.push([n, ref]); }, addEventListener(t, f) { e.handlers[t] = f; }};
  Object.defineProperty(e, 'innerHTML', {get: () => e._h, set: v => { e._h = v; }}); return e; };
const rowEl = id => ({closest: s => s === '[data-tid]' ? {getAttribute: () => id} : null});
function sheetPage(next) {
  const w = el(), body = el(), calls = [], doc = {activeElement: null, handlers: {}, getElementById: id => id === 'sheet' ? w : id === 'sheetBody' ? body : null, addEventListener(t, f) { doc.handlers[t] = f; }};
  const SXA = {api: (u, o) => { calls.push(u); return next(u); }}, win = {SXA}, raf = f => f();
  new Function('document', 'window', 'SXA', 'requestAnimationFrame', P.c9b)(doc, win, SXA, raf);
  return {w, body, calls, doc, win, click: id => doc.handlers.click({target: rowEl(id)}), key: (k, id) => { let pd = false; doc.handlers.keydown({key: k, target: rowEl(id), preventDefault() { pd = true; }}); return pd; }};
}
const rows = n => Array.from({length: n}, (_, i) => [1000 + i * 900, 100 + i * 0.1, 100.6 + i * 0.1, 99.6 + i * 0.1, 100.2 + i * 0.1]);
const TRADE = o => Object.assign({id: 7, symbol: 'XAUUSD', side: 'buy', strategy: 'gold_scalp', strategy_name: 'Liquidity sweep scalp', broker: 'MT5', lots: 0.1, pnl: 5, result: 'win', opened: 1000 + 24 * 900, closed: 1000 + 28 * 900,
  levels: {entry: 100.0, fill: 100.2, sl: 99.0, tp: 102.0}, dec: 2, exit: {recorded: false, price: null, reason: null, note: 'EXIT NOTE: not recorded here.'},
  candles: {tf: 'M15', secs: 900, rows: rows(40), covers_open: true, covers_close: true, merged: 1}}, o || {});
const okp = j => () => Promise.resolve(j);
const ys = h => (h.match(/<text [^>]*y="([\d.]+)"/g) || []).map(t => Number(t.match(/y="([\d.]+)"/)[1]));
(async () => {
  ok('every script in the page still parses', P.scripts.every(x => { try { new Function(x); return true; } catch (e) { return false; } }));
  let s = sheetPage(okp(TRADE()));
  ok('the block starts quietly: it only listens, nothing is asked until a trade is tapped', s.calls.length === 0 && s.w.hidden === true && typeof s.win.SXT.open === 'function');
  s.click(7); ok('tapping a trade opens the sheet at once with a loading line, and asks the server for that one trade', s.w.hidden === false && s.w.classList.contains('open') && s.body.innerHTML.includes('Loading') && s.calls.join() === '/api/trade/7');
  await tick(); let h = s.body.innerHTML;
  ok('then it shows the symbol, Buy, the profit in dollars and a Close button', h.includes('XAUUSD') && h.includes('>Buy<') && h.includes('+$5.00') && h.includes('data-close="1"'));
  ok('one candle drawn per candle sent (40 wicks and 40 bodies), good and bad colours from the site', (h.match(/<rect /g) || []).length === 40 && h.includes('var(--good)') && h.includes('var(--bad)'));
  ok('the four stored prices are drawn and listed with their own numbers (TP 102.00, Entry 100.00, Fill 100.20, SL 99.00)', ['TP 102.00', 'Entry 100.00', 'Fill 100.20', 'SL 99.00'].every(t => h.includes(t)) && ['Take profit', 'Planned entry', 'Filled at', 'Stop loss'].every(t => h.includes(t)));
  ok('the open and close TIMES are marked (Opened / Closed), but there is no exit price label anywhere', /<text[^>]*text-anchor="end"[^>]*>Opened</.test(h) && /<text[^>]*text-anchor="start"[^>]*>Closed</.test(h) && !/<text[^>]*>\s*(Exit|Close price|Exit price)/i.test(h));
  ok('it says in the server\'s own words that the exit is not recorded', h.includes('EXIT NOTE: not recorded here.'));
  ok('lots, strategy, broker and the times are listed', h.includes('>0.1<') && h.includes('Liquidity sweep scalp') && h.includes('>MT5<') && h.includes('Held for') && h.includes('<dt>Opened</dt>') && h.includes('<dt>Closed</dt>'));
  ok('with full candles and a fill there are no apology notes (only the exit note)', (h.match(/<p class="note">/g) || []).length === 1);
  ok('the profit label colour follows the result (win good, loss bad)', h.includes('class="num good"') && (s.body.innerHTML = '', s.click(8), true));
  s = sheetPage(okp(TRADE({pnl: -3.5, result: 'loss', side: 'sell'}))); s.click(8); await tick(); h = s.body.innerHTML;
  ok('a losing sell: Sell chip, -$3.50, bad colour', h.includes('>Sell<') && h.includes('chip stop') && h.includes('-$3.50') && h.includes('class="num bad"'));
  s = sheetPage(okp(TRADE({candles: {tf: 'M15', secs: 900, rows: [], covers_open: false, covers_close: false, merged: 1}}))); s.click(7); await tick(); h = s.body.innerHTML;
  ok('no candles held: no candle bodies, the price levels still drawn, and it says why', !h.includes('<rect ') && h.includes('TP 102.00') && h.includes('no longer holds the candles') && !/<text[^>]*>(Opened|Closed)</.test(h));
  s = sheetPage(okp(TRADE({candles: {tf: 'M15', secs: 900, rows: rows(10), covers_open: false, covers_close: true, merged: 1}}))); s.click(7); await tick();
  ok('only some candles held: it says so', s.body.innerHTML.includes('only some of the candles'));
  s = sheetPage(okp(TRADE({levels: {entry: 100, fill: null, sl: null, tp: null}}))); s.click(7); await tick(); h = s.body.innerHTML;
  ok('missing prices are left out, never invented, and a missing fill is explained', h.includes('Entry 100.00') && !h.includes('TP ') && !h.includes('SL ') && !h.includes('Fill ') && !h.includes('<dt>Take profit</dt>') && !h.includes('<dt>Stop loss</dt>') && h.includes('No fill price was recorded'));
  s = sheetPage(okp(TRADE({levels: {entry: null, fill: null, sl: null, tp: null}, candles: {tf: 'M15', secs: 900, rows: [], covers_open: false, covers_close: false, merged: 1}}))); s.click(7); await tick(); h = s.body.innerHTML;
  ok('nothing to draw at all: no chart box, still the facts and the notes', !h.includes('<svg') && h.includes('+$5.00') && h.includes('EXIT NOTE'));
  s = sheetPage(okp(TRADE({levels: {entry: 100.0, fill: 100.001, sl: 99.0, tp: 102.0}, dec: 3, candles: {tf: 'M15', secs: 900, rows: [], covers_open: false, covers_close: false, merged: 1}}))); s.click(7); await tick(); const yy = ys(s.body.innerHTML).sort((a, b) => a - b);
  ok('price labels that would sit on top of each other are pushed apart (at least 12 apart)', yy.length >= 4 && yy.every((v, i) => !i || v - yy[i - 1] >= 11.9));
  s = sheetPage(okp(TRADE({symbol: '<img src=x onerror=alert(1)>', strategy_name: '<b>x</b>', broker: '"><script>'}))); s.click(7); await tick(); h = s.body.innerHTML;
  ok('text from the server is escaped (no tag can be injected)', !h.includes('<img') && !h.includes('<b>x') && !h.includes('<script>') && h.includes('&lt;img'));
  s = sheetPage(() => Promise.reject(Object.assign(new Error('x'), {status: 404}))); s.click(9); await tick();
  ok('a trade that is gone (404): a plain message and a Close button', s.body.innerHTML.includes('not available any more') && s.body.innerHTML.includes('data-close="1"'));
  s = sheetPage(() => Promise.reject(new Error('offline'))); s.click(9); await tick();
  ok('no internet: a plain message, not a blank sheet', s.body.innerHTML.includes('Cannot load this trade') && s.body.innerHTML.includes('data-close="1"'));
  let res = {}; s = sheetPage(u => new Promise(r => { res[u] = r; })); s.click(1); s.click(2); res['/api/trade/2'](TRADE({id: 2, symbol: 'SECOND'})); await tick(); res['/api/trade/1'](TRADE({id: 1, symbol: 'FIRST'})); await tick();
  ok('a slow answer for an older tap never replaces the trade tapped last', s.body.innerHTML.includes('SECOND') && !s.body.innerHTML.includes('FIRST'));
  s = sheetPage(okp(TRADE())); s.click('0'); s.click('abc'); s.click('-4'); s.doc.handlers.click({target: {closest: () => null}}); s.doc.handlers.click({target: {}});
  ok('a tap on anything that is not a trade (no id, id 0, text, negative, other element) does nothing', s.calls.length === 0 && s.w.hidden === true);
  const pd = s.key('Enter', 5), pd2 = s.key(' ', 6), pd3 = s.key('a', 7), pd4 = s.key('Tab', 8);
  ok('Enter or Space on a trade row opens it (and does not scroll); other keys do nothing', pd && pd2 && !pd3 && !pd4 && s.calls.join() === '/api/trade/5,/api/trade/6');
  ok('the sheet block does nothing when the page has no signed-in layer (no SXA)', (() => { try { const w = el(), b = el(), d = {getElementById: i => i === 'sheet' ? w : b, addEventListener() { throw new Error('should not listen'); }}; new Function('document', 'window', 'SXA', 'requestAnimationFrame', P.c9b)(d, {}, undefined, f => f()); return true; } catch (e) { return false; } })());

  /* ---- the profit curve (P9A): a tap opens the nearest trade ---- */
  function home(curve) {
    const timers = [], vh = el(), le = el(); le.nextSibling = {after: 'liveempty'}; vh.hidden = false;
    const doc = {hidden: false, createElement: el, addEventListener() {}, getElementById: id => id === 'view-home' ? vh : id === 'liveempty' ? le : null}, opened = [];
    const user = {uid: 'u1', verified: true, active: true}, SXA = {user: () => user, api: () => Promise.resolve({today: {pnl: 1, n: 1}, week: {pnl: 1, n: 1}, total: {pnl: 30, n: 5}, stats: {trades: 5, wins: 3, losses: 2, win_rate: 60, max_drawdown: 4, best: 20, worst: -4}, curve, curve_n: curve.length, brokers: ['MT5'], broker: ''})};
    const MO = function () { this.observe = () => {}; }, win = {SXA, SXT: {open: id => opened.push(id)}};
    new Function('document', 'window', 'SXA', 'setInterval', 'MutationObserver', P.c9a)(doc, win, SXA, f => timers.push(f), MO);
    return {C: vh.inserted[0][0], opened, win, run: async () => { timers[0](); await tick(); }};
  }
  const CV = [{t: 1, v: 20, id: 11}, {t: 2, v: 18, id: 12}, {t: 3, v: 24, id: 13}, {t: 4, v: 20, id: 14}, {t: 5, v: 30, id: 15}];
  const svg = {getBoundingClientRect: () => ({left: 10, width: 300})}, tap = (p, f) => p.C.handlers.click({target: {closest: s => s === 'svg' ? svg : null}, clientX: 10 + f * 300});
  let p = home(CV); await p.run();
  ok('the curve is drawn with the tap hint', p.C.innerHTML.includes('Tap a point on the curve'));
  tap(p, (8 + 284 * 3 / 5) / 300); tap(p, (8 + 284 * 1 / 5) / 300); tap(p, (8 + 284 * 5 / 5) / 300);
  ok('a tap on the curve opens the trade whose point is nearest (3rd, 1st and last point)', p.opened.join() === '13,11,15');
  tap(p, 0); tap(p, 1); ok('taps far left and far right open the first and the last trade (never off the end)', p.opened.slice(3).join() === '11,15');
  const q = home([{t: 1, v: 1, id: 21}, {t: 2, v: 2}, {t: 3, v: 3, id: 0}]); await q.run(); tap(q, (8 + 284 * 2 / 3) / 300); tap(q, 1);
  ok('a point with no trade id (or 0) opens nothing', q.opened.length === 0);
  p.win.SXT = undefined; tap(p, 0.5); ok('without the pop-up block a tap does nothing and never breaks', p.opened.length === 5);
  p.C.handlers.click({target: {closest: s => s === 'svg' ? {} : null}, clientX: 5}); p.C.handlers.click({target: {closest: () => null}}); p.C.handlers.click({target: {}});
  ok('odd taps (no size, nothing under the finger, not an element) never break', true);
  ok('the broker picker still works when it is tapped', (() => { let seen = ''; const b = {getAttribute: () => 'Deriv'}; try { p.C.handlers.click({target: {closest: s => s === '[data-pb]' ? b : null}}); seen = 'ok'; } catch (e) { seen = 'err'; } return seen === 'ok'; })());
  console.log(JSON.stringify(OUT));
})();
'''
def run():
    r = subprocess.run(['node', '-e', HARNESS], input=json.dumps({'c9b': C9B, 'c9a': C9A, 'scripts': scripts}), capture_output=True, text=True, timeout=120)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: print(r.stdout[-400:], r.stderr[-1500:]); return [['the page harness ran', False]]
for n, ok in run(): T(n, ok)
for n, ok in R: print('PASS' if ok else 'FAIL', n)
bad = [n for n, ok in R if not ok]
print('\n%d/%d passed' % (len(R) - len(bad), len(R))); sys.exit(1 if bad else 0)
