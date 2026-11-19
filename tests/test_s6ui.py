"""Section 6 page checks: the Trades / Journal / Stats screens and the S6 block in static/index.html. Needs node (skipped if missing).
Run: python tests/test_s6ui.py   No temp files: the page code goes to node through a pipe and runs against a fake page and a fake server."""
import os, sys, re, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok)))
def cut(a, b):
    i = html.index(a); return html[i:html.index(b, i)]
def node(js, data):
    r = subprocess.run(['node', '-e', js], input=json.dumps(data), capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: print(r.stdout[-300:], r.stderr[-800:]); return []

T('the S6 block is in the page exactly once', html.count('/*S6-start*/') == 1 and html.count('/*S6-end*/') == 1)
T('the page has no sample trade data left (HIST, OPEN, EQ, genEq)', not re.search(r'\b(var|let|const)\s+(HIST|OPEN|EQ)\s*=', html))
scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
bad = node("const s=JSON.parse(require('fs').readFileSync(0,'utf8'));const b=[];s.forEach((x,i)=>{try{new Function(x)}catch(e){b.push(i)}});console.log(JSON.stringify(b))", scripts)
T('every script in the page still parses', bad == [])

P = {'sxj': cut('var SXJ=', 'var nextHigh='), 'kl': cut('var KL=', 'function ja('), 'rt': cut('function renderTrades(){', '/* ---------- CONNECT'),
     'jr': cut('function jall(){', '/* ---------- stats'), 'sr': cut('function sr(){', '/* ---------- pairs'), 's6': cut('/*S6-start*/', '/*S6-end*/')}
JS = r"""
const P = JSON.parse(require('fs').readFileSync(0, 'utf8')), OUT = []; const ok = (n, c) => OUT.push([n, !!c]);
const flush = () => new Promise(r => setTimeout(r, 0));
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function page(withS6) {
  const els = {}, E = id => els[id] || (els[id] = {innerHTML: '', textContent: '', style: {}});
  const FB = ['all', 'trade', 'bot', 'rule', 'note'].map(f => ({dataset: {f}, setAttribute(k, v) { this.p = v; }}));
  const g = {calls: [], pend: [], timers: [], h: {}, cur: {u: null, done: true}, mo: {}, vt: {on: true}, doc: {hidden: false}, E, FB};
  g.vt.classList = {contains: c => g.vt.on && c === 'on'};
  const SXA = {api: (u, o) => { g.calls.push(u); return new Promise((res, rej) => g.pend.push({u, res, rej})); }, user: () => g.cur.u, resolved: () => g.cur.done};
  const doc = {getElementById: id => id === 'view-trades' ? g.vt : null, addEventListener: (t, f) => { g.h[t] = f; }, get hidden() { return g.doc.hidden; }};
  class MO { constructor(f) { g.mo.f = f; } observe() {} }
  const body = "var S={filter:'all'},X={j:[],jf:'all'},money=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}),m2=function(v){return(v>=0?'+':'-')+money.format(Math.abs(v))},kp=function(a,b){return '<div class=\"stat\"><span>'+a+'</span><b class=\"num\">'+b+'</b></div>'},ICON_UP='[UP]',ICON_DN='[DN]',ICK='[K]',ICX='[X]',sv=function(){};\n"
    + P.sxj + P.kl + P.rt + P.jr + P.sr + (withS6 ? P.s6 : '') + ';return {SXJ:SXJ,S:S,X:X,renderTrades:renderTrades,jr:jr,sr:sr};';
  g.api = new Function('$', '$$', 'esc', 'document', 'window', 'MutationObserver', 'setInterval', 'SXA', body)(E, s => s === '#jF button' ? FB : [], esc, doc, {SXA}, MO, f => { g.timers.push(f); }, SXA);
  g.tick = (n = 1) => { for (let i = 0; i < n; i++) g.timers[0](); };
  g.html = id => E(id).innerHTML;
  return g;
}
const ROWS = [{t: 1700000000, symbol: 'XAUUSD', side: 'buy', pnl: 10, result: 'win', broker: 'MT5', strategy_name: 'Liquidity sweep scalp'}, {t: 1700000600, symbol: 'EURUSD', side: 'sell', pnl: -4, result: 'loss', broker: 'Deriv', strategy_name: ''}];
const STATS = {trades: 2, wins: 1, losses: 1, win_rate: 50, net: 6, profit_factor: 2.5, best: 10, worst: -4, per_trade: 3, break_even: 40, band: 20, max_drawdown: 4, loss_streak: 1};
const PAIRS = [{symbol: 'XAUUSD', n: 3, wins: 2, pnl: 14, win_rate: 66.7}, {symbol: 'EURUSD', n: 1, wins: 0, pnl: -4, win_rate: 0}];
const J = (extra) => Object.assign({rows: ROWS, total: 2, stats: STATS, pairs: PAIRS, brokers: ['MT5', 'Deriv'], broker: ''}, extra || {});
(async () => {
  // ---- Trades tab (renderTrades) ----
  let g = page(false), A = g.api, S = A.SXJ;
  for (const [st, word] of [['idle', 'Loading your trades'], ['load', 'Loading your trades'], ['out', 'Sign in to see your trades'], ['err', 'Cannot load your trades'], ['ok', 'No trades yet']]) {
    S.state = st; A.renderTrades(); ok('Trades tab, state ' + st + ': says "' + word + '" and shows no numbers', g.html('#tList').includes(word) && g.html('#tStats') === '');
  }
  Object.assign(S, {state: 'ok', rows: ROWS, total: 2, stats: STATS, brokers: ['MT5', 'Deriv']}); A.renderTrades();
  let L = g.html('#tList'), T = g.html('#tStats');
  ok('numbers: Net result, Win rate, Profit factor, Trades', T.includes('Net result') && T.includes('+$6.00') && T.includes('50%') && T.includes('2.50') && /Trades<\/span><b class="num">2<\/b>/.test(T));
  ok('profit factor shows a dash when there is none', (S.stats = Object.assign({}, STATS, {profit_factor: null}), A.renderTrades(), g.html('#tStats').includes('Profit factor</span><b class="num">-</b>')));
  S.stats = STATS; A.renderTrades(); L = g.html('#tList');
  ok('a row shows pair, Buy/Sell, signed money, broker and strategy name', L.includes('XAUUSD Buy') && L.includes('+$10.00') && L.includes('MT5') && L.includes('Liquidity sweep scalp') && L.includes('EURUSD Sell') && L.includes('-$4.00'));
  ok('a win is green (good), a loss is red (bad)', /good">\+\$10\.00/.test(L) && /bad">-\$4\.00/.test(L));
  S.rows = [Object.assign({}, ROWS[0], {symbol: '<img src=x>', strategy_name: '<b>x</b>'})]; A.renderTrades();
  ok('names from the server are escaped (no HTML injection)', !g.html('#tList').includes('<img') && !g.html('#tList').includes('<b>x') && g.html('#tList').includes('&lt;img'));
  S.rows = ROWS; A.S.filter = 'win'; A.renderTrades();
  ok('filter Wins: only winning trades', g.html('#tList').includes('XAUUSD') && !g.html('#tList').includes('EURUSD'));
  A.S.filter = 'loss'; A.renderTrades(); ok('filter Losses: only losing trades', !g.html('#tList').includes('XAUUSD') && g.html('#tList').includes('EURUSD'));
  S.rows = [ROWS[0]]; A.renderTrades(); ok('a filter that matches nothing says "No trades match." (not "No trades yet")', g.html('#tList').includes('No trades match.') && !g.html('#tList').includes('No trades yet'));
  S.rows = ROWS; A.S.filter = 'all'; A.renderTrades();
  ok('filter buttons All / Wins / Losses, the active one is pressed', /data-f="all" aria-pressed="true"/.test(g.html('#tFilter')) && /data-f="win" aria-pressed="false"/.test(g.html('#tFilter')) && g.html('#tFilter').includes('Losses'));
  ok('two brokers: the picker shows All brokers + each broker', g.E('#tBroker').style.display === '' && g.html('#tBroker').includes('All brokers') && g.html('#tBroker').includes('data-b="Deriv"') && /data-b="" aria-pressed="true"/.test(g.html('#tBroker')));
  S.broker = 'Deriv'; A.renderTrades(); ok('the picked broker is the pressed one', /data-b="Deriv" aria-pressed="true"/.test(g.html('#tBroker')) && /data-b="" aria-pressed="false"/.test(g.html('#tBroker')));
  S.broker = ''; S.brokers = ['MT5']; A.renderTrades(); ok('one broker and none picked: the picker is hidden', g.E('#tBroker').style.display === 'none' && g.html('#tBroker') === '');
  S.broker = 'MT5'; A.renderTrades(); ok('one broker but one is picked: the picker stays so you can go back to All', g.E('#tBroker').style.display === '');
  S.broker = ''; S.total = 2; A.renderTrades(); ok('no note when every trade is listed', g.E('#tNote').textContent === '');
  S.total = 250; S.rows = ROWS; A.renderTrades(); ok('more trades than listed: the note says how many are shown and that the numbers count all', /newest 2 of 250/.test(g.E('#tNote').textContent) && g.E('#tNote').textContent.includes('count all'));

  // ---- Journal tab (jr) ----
  g = page(false); A = g.api; S = A.SXJ; Object.assign(S, {state: 'ok', rows: ROWS, total: 2, stats: STATS});
  A.X.j = [{t: Date.now() - 1000, k: 'note', m: 'hello <b>there</b>'}, {t: Date.now() - 500, k: 'bot', m: 'Bot started'}]; A.X.jf = 'all'; A.jr();
  ok('Journal: bot notes and real trades together, count shown', g.E('#jCount').textContent === '4 entries' && g.html('#jList').includes('Bot started') && g.html('#jList').includes('XAUUSD Buy closed +$10.00 (MT5)'));
  ok('Journal: newest first (the bot line is before the older note)', g.html('#jList').indexOf('Bot started') < g.html('#jList').indexOf('hello'));
  ok('Journal: note text is escaped', !g.html('#jList').includes('<b>there') && g.html('#jList').includes('&lt;b&gt;there'));
  const nowS = Math.floor(Date.now() / 1000); S.rows = [Object.assign({}, ROWS[0], {t: nowS - 10})]; A.X.j = [{t: Date.now() - 60000, k: 'note', m: 'older note'}]; A.X.jf = 'all'; A.jr();
  ok('Journal: a trade that closed 10 seconds ago (the server sends seconds) is listed above a note from a minute ago', g.html('#jList').indexOf('XAUUSD Buy') > 0 && g.html('#jList').indexOf('XAUUSD Buy') < g.html('#jList').indexOf('older note'));
  S.rows = ROWS; A.X.j = [{t: Date.now() - 1000, k: 'note', m: 'hello <b>there</b>'}, {t: Date.now() - 500, k: 'bot', m: 'Bot started'}];
  A.X.jf = 'trade'; A.jr(); ok('Journal filter Trade: only the closed trades', g.html('#jList').includes('EURUSD Sell closed -$4.00 (Deriv)') && !g.html('#jList').includes('Bot started') && g.FB[1].p === true && g.FB[0].p === false);
  A.X.jf = 'rule'; A.jr(); ok('Journal: a filter with nothing in it says "Nothing here yet."', g.html('#jList').includes('Nothing here yet.'));
  S.state = 'out'; S.rows = []; A.X.jf = 'trade'; A.jr(); ok('Journal, Trade filter while signed out: says to sign in, shows no trades', g.html('#jList').includes('Sign in to see your trades') && !g.html('#jList').includes('XAUUSD'));

  // ---- Stats tab (sr) ----
  g = page(false); A = g.api; S = A.SXJ; S.state = 'out'; A.sr(); ok('Stats signed out: a sign-in message, no numbers', g.html('#sBody').includes('Sign in') && !g.html('#sBody').includes('Win rate'));
  Object.assign(S, {state: 'ok', stats: Object.assign({}, STATS, {trades: 0}), pairs: []}); A.sr(); ok('Stats with no trades: "No trades yet", no numbers', g.html('#sBody').includes('No trades yet') && !g.html('#sBody').includes('Win rate'));
  S.stats = Object.assign({}, STATS, {trades: 12}); S.pairs = PAIRS; A.sr();
  ok('under 30 trades: says too few to say much', g.html('#sBody').includes('Too few trades'));
  const V = (o) => { S.stats = Object.assign({}, STATS, {trades: 40, break_even: 50, band: 10}, o); A.sr(); return g.html('#sBody'); };
  ok('win rate far below break-even: says you lose money at this rate', V({win_rate: 20}).includes('below break-even'));
  ok('win rate far above break-even: says keep risk small', V({win_rate: 70}).includes('above break-even'));
  ok('win rate inside the luck range: says it cannot be told from chance', V({win_rate: 52}).includes('inside the luck range'));
  ok('win rate a little under break-even but inside the luck range: not called a loss', V({win_rate: 45}).includes('inside the luck range'));
  const B = V({win_rate: 52, per_trade: 3, loss_streak: 4, best: 10, worst: -4, max_drawdown: 4});
  ok('the numbers: win rate, break-even, per trade, loss streak, luck range, best, worst, deepest dip', B.includes('52.0%') && B.includes('50.0%') && B.includes('+$3.00') && />4<\/b>/.test(B) && B.includes('40.0% to 60.0%') && B.includes('Best +$10.00') && B.includes('Worst -$4.00') && B.includes('Deepest dip -$4.00'));
  ok('by pair: trade / trades, win rate, signed money, green or red', B.includes('3 trades · 66.7% won') && B.includes('1 trade · 0% won') && /good">\+\$14\.00/.test(B) && /bad">-\$4\.00/.test(B));

  // ---- the S6 block: asking the server ----
  const pick = (g, b) => g.h.click({target: {closest: s => s === '#tBroker button' ? {getAttribute: k => k === 'data-b' ? b : null} : null}});
  g = page(true); A = g.api; S = A.SXJ;
  ok('on load, before sign-in is known: still "Loading", nothing asked', (g.cur.done = false, g.tick(), g.calls.length === 0 && S.state === 'idle' && g.html('#tList').includes('Loading your trades')));
  g.cur.done = true; g.tick(); ok('signed out: the screen says to sign in and nothing is asked', S.state === 'out' && g.calls.length === 0 && g.html('#tList').includes('Sign in to see your trades'));
  g = page(true); A = g.api; S = A.SXJ; g.cur.u = {uid: 'u1', verified: false}; g.tick();
  ok('signed in but email not verified: nothing is asked of the server', g.calls.length === 0 && S.state === 'out');
  g = page(true); A = g.api; S = A.SXJ; g.cur.u = {uid: 'u1', verified: true}; g.tick();
  ok('signed in and verified: asks GET /api/journal once, shows Loading meanwhile', g.calls.length === 1 && g.calls[0] === '/api/journal' && S.state === 'load' && g.html('#tList').includes('Loading your trades'));
  g.pend[0].res(J()); await flush();
  ok('the answer fills the Trades, Journal and Stats screens', S.state === 'ok' && S.rows.length === 2 && g.html('#tList').includes('XAUUSD Buy') && g.E('#jCount').textContent.includes('entries') && g.html('#sBody').includes('Win rate'));
  ok('the broker picker appears when the server lists two brokers', g.E('#tBroker').style.display === '');
  // refresh timing
  g.tick(13); ok('no new request before 15 seconds have passed', g.calls.length === 1);
  g.tick(1); ok('every 15 seconds while the Trades screen is open: asks again', g.calls.length === 2); g.pend[1].res(J()); await flush();
  g.vt.on = false; g.tick(15); ok('Trades screen closed: no refresh', g.calls.length === 2);
  g.vt.on = true; g.doc.hidden = true; g.tick(15); ok('page hidden (app in background): no refresh', g.calls.length === 2);
  g.doc.hidden = false; g.mo.f(); ok('opening the Trades screen asks right away', g.calls.length === 3); g.pend[2].res(J()); await flush();
  g.h.click; ok('the page listens for taps on the broker picker', typeof g.h.click === 'function');
  // a failed request
  g.calls.length = 0; g.vt.on = true; g.mo.f(); g.pend[3].rej(new Error('offline')); await flush();
  ok('a failed refresh keeps the trades already shown (no error screen over good data)', S.state === 'ok' && S.rows.length === 2 && g.html('#tList').includes('XAUUSD'));
  const g2 = page(true); g2.cur.u = {uid: 'u9', verified: true}; g2.tick(); g2.pend[0].rej(new Error('offline')); await flush();
  ok('a failed first request says so in plain words', g2.api.SXJ.state === 'err' && g2.html('#tList').includes('Cannot load your trades'));
  const g7 = page(true); g7.cur.u = {uid: 'u7', verified: false}; g7.tick(); g7.mo.f(); pick(g7, 'Deriv');
  ok('an unverified email is never asked for trades, even when the screen opens or a broker is tapped', g7.calls.length === 0);
  const g8 = page(true); g8.cur.u = {uid: 'u8', verified: true}; g8.tick(); g8.pend[0].res(J()); await flush(); g8.doc.hidden = true; g8.mo.f();
  ok('the Trades screen class changing while the app is in the background asks nothing', g8.calls.length === 1);
  // two asks never run at once
  const g3 = page(true); g3.cur.u = {uid: 'u3', verified: true}; g3.tick(); g3.mo.f(); g3.mo.f();
  ok('while one request is out, others wait (never two at once)', g3.calls.length === 1);
  g3.pend[0].res(J()); await flush(); ok('and one more is made after it, not many', g3.calls.length === 2);
  // broker picking
  const g4 = page(true); g4.cur.u = {uid: 'u4', verified: true}; g4.tick(); g4.pend[0].res(J()); await flush();
  pick(g4, 'Deriv'); ok('picking a broker asks the server for that broker only', g4.calls[1] === '/api/journal?broker=Deriv' && g4.api.SXJ.broker === 'Deriv');
  g4.pend[1].res(J({rows: [ROWS[1]], total: 1, broker: 'Deriv'})); await flush();
  ok('the screen then shows only that broker\'s trades', g4.api.SXJ.rows.length === 1 && g4.html('#tList').includes('EURUSD') && !g4.html('#tList').includes('XAUUSD'));
  pick(g4, ''); ok('picking All brokers asks without a broker', g4.calls[2] === '/api/journal'); g4.pend[2].res(J()); await flush();
  pick(g4, 'A B&C'); ok('a broker name is URL-encoded in the request', g4.calls[3] === '/api/journal?broker=A%20B%26C'); g4.pend[3].res(J({broker: 'A B&C'})); await flush();
  ok('a tap on something else does nothing', (g4.h.click({target: {closest: () => null}}), g4.calls.length === 4));
  // a late answer for an older pick is ignored
  const g5 = page(true); g5.cur.u = {uid: 'u5', verified: true}; g5.tick(); pick(g5, 'Deriv');
  g5.pend[0].res(J({broker: '', rows: ROWS})); await flush();
  ok('an old answer that arrives after a new pick is thrown away', g5.api.SXJ.rows.length === 0 && g5.calls.length === 2 && g5.calls[1] === '/api/journal?broker=Deriv');
  g5.pend[1].res(J({rows: [ROWS[1]], total: 1, broker: 'Deriv'})); await flush(); ok('and the answer to the new pick is used', g5.api.SXJ.rows.length === 1 && g5.api.SXJ.state === 'ok');
  // sign-out and switching people
  g4.cur.u = null; g4.tick(); ok('signing out clears the trades and says to sign in (nothing of the last person stays)', g4.api.SXJ.rows.length === 0 && g4.api.SXJ.stats === null && g4.api.SXJ.state === 'out' && g4.html('#tList').includes('Sign in') && !g4.html('#tList').includes('XAUUSD'));
  const g6 = page(true); g6.cur.u = {uid: 'a', verified: true}; g6.tick(); g6.pend[0].res(J()); await flush(); pick(g6, 'Deriv'); g6.pend[1].res(J({broker: 'Deriv'})); await flush();
  g6.cur.u = {uid: 'b', verified: true}; g6.tick();
  ok('a different person signing in: the last broker pick is forgotten and the new person is asked fresh', g6.calls[2] === '/api/journal' && g6.api.SXJ.broker === '' && g6.api.SXJ.rows.length === 0);
  console.log(JSON.stringify(OUT));
})();
"""
for n, ok in node(JS, P): T(n, ok)
T('all the page checks ran', len(R) >= 64)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
