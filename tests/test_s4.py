"""Section 4 (BTC plan) checks: settings cleanup in the admin panel. Run: python tests/test_s4.py
Server: the new numbers are range-checked BEFORE anything is saved. Page: Main settings on top, Advanced (collapsed) holds the rest and the moved cards;
nothing was removed. The page code (/*S4S-start*/../*S4S-end*/) is run in node against a fake page and a fake server (that part is skipped without node)."""
import os, sys, re, json, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 's4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, alerts
try: alerts.stop()
except Exception: pass
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
C.get('/api/me', headers=U); C.get('/api/me', headers=A)

# ---- server: ranges ----
BAD = {'max_open': '99', 'max_daily_loss_pct': '50', 'max_weekly_loss_pct': '0', 'max_losing_streak': '-1', 'streak_cooldown_h': '500', 'burst_ceiling': '1', 'burst_big_score': '1',
       'min_confluence': '0', 'multi_min_score': '1', 'auto_disable_min_trades': '1', 'auto_markets_max': '11', 'max_trades_day': '101'}
for k, v in BAD.items():
    before = st.get(k); r = C.post('/api/admin/settings', json={k: v}, headers=A)
    T('%s=%s is refused and nothing is saved' % (k, v), r.status_code == 400 and st.get(k) == before)
r = C.post('/api/admin/settings', json={'max_open': '4', 'burst_ceiling': 'abc'}, headers=A)
T('a text number is refused and the good one beside it is NOT saved', r.status_code == 400 and st.get('max_open') != '4')
GOOD = {'max_open': '4', 'max_daily_loss_pct': '2.5', 'max_weekly_loss_pct': '5', 'max_losing_streak': '0', 'streak_cooldown_h': '6', 'burst_ceiling': '10', 'burst_big_score': '3',
        'min_confluence': '3', 'multi_min_score': '4', 'auto_disable_min_trades': '30', 'auto_markets_max': '3', 'max_trades_day': '0', 'news_lock': '0', 'symbols': 'XAUUSD,BTCUSD'}
r = C.post('/api/admin/settings', json=GOOD, headers=A)
T('good values are saved and come back', r.status_code == 200 and all(r.json[k] == v for k, v in GOOD.items()))
T('a normal user cannot change them', C.post('/api/admin/settings', json={'max_open': '2'}, headers=U).status_code == 403)
T('the older Auto numbers are still checked (risk_pct 9 refused)', C.post('/api/admin/settings', json={'risk_pct': '9'}, headers=A).status_code == 400)

# ---- page: structure ----
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the S4 code is in the page exactly once', html.count('/*S4S-start*/') == 1 and html.count('/*S4S-end*/') == 1)
i_main, i_adv, i_big, i_str, i_res, i_end, i_pay = [html.find(x) for x in ('id="s4Main"', 'id="sxAdv"', '>Big stake on strong setups</h3>', 'id="aStr"', 'id="aStrT"', '</details><h3 style="margin:8px 0 0">Payments log', '>Payments log</h3>')]
T('Main settings come first, before Test price', 0 < i_main < html.find('>Test price</h3>'))
T('Advanced is closed by default (no open attribute)', 'id="sxAdv"' in html and not re.search(r'<details id="sxAdv"[^>]*\bopen\b', html))
T('Big stake, Strategies and Results now sit inside Advanced', 0 < i_adv < i_big < i_str < i_res < i_end and i_end + 12 == i_pay - len('<h3 style="margin:8px 0 0">') + 0 or 0 < i_adv < i_big < i_str < i_res < i_end)
T('nothing was removed: Test price, Packages, Auto settings, Subscribers still there', all(x in html for x in ('>Test price</h3>', '>Packages</h3>', '>Auto settings</h3>', '>Subscribers</h3>', 'id="auSave"', 'id="skSave"')))
bad = []
for n, x in enumerate(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)):
    p = os.path.join(tempfile.gettempdir(), 'sxb_s4_%d.js' % n); open(p, 'w', encoding='utf-8').write(x)
    if shutil.which('node') and subprocess.run(['node', '--check', p], capture_output=True).returncode: bad.append(n)
T('every script in the page still parses', not bad)

# ---- page code in node ----
m = re.search(r'/\*S4S-start\*/(.*?)/\*S4S-end\*/', html, re.S); CODE = m.group(1) if m else ''
HARNESS = r'''
const code = process.argv[2], OUT = [];
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tick = () => new Promise(r => setTimeout(r, 5));
function run(server) {
  const els = {}, calls = [], toasts = [];
  const el = () => ({innerHTML: '', value: '', checked: false, disabled: false, textContent: '', onclick: null});
  const $ = s => els[s] || (els[s] = el());
  const SXA = {api: (u, o) => { calls.push({u, body: o && o.body}); return server(u, o); }};
  const wrap = new Function('$', 'esc', 'tst', 'SXA', code);
  wrap($, esc, t => toasts.push(t), SXA);
  // after the code ran, the rows were written into #s4Main / #s4Adv: create the input elements it will look up
  return {els, calls, toasts, $};
}
const S = {bot_enabled: '1', risk_pct: '1.0', symbols: 'XAUUSD', max_open: '3', news_lock: '1', rr: '2.0', max_stop_atr: '3.5', burst_enabled: '1', burst_ceiling: '15', burst_big_score: '3',
  min_confluence: '2', regime_switch: '0', auto_disable: '0', auto_markets: '0', max_trades_day: '0', symbols_pool: '', max_daily_loss_pct: '3.0', max_weekly_loss_pct: '6.0', max_losing_streak: '3', streak_cooldown_h: '4', multi_min_score: '3', auto_disable_min_trades: '20', auto_markets_max: '2'};
(async () => {
  const srv = (u, o) => u === '/api/admin/settings' ? Promise.resolve(Object.assign({}, S, (o && o.body) || {})) : Promise.resolve({ok: true});
  let p = run(srv); await tick();
  const M = p.els['#s4Main'].innerHTML, A = p.els['#s4Adv'].innerHTML;
  OUT.push(['main card has every top setting', ['s4_risk_pct', 's4_symbols', 's4_max_open', 's4_max_daily_loss_pct', 's4_max_weekly_loss_pct', 's4_max_losing_streak', 's4_news_lock', 's4_rr', 's4_max_stop_atr', 's4_burst_enabled', 's4_burst_ceiling', 's4_burst_big_score', 's4Bot'].every(x => M.includes('id="' + x + '"'))]);
  OUT.push(['advanced holds the hidden ones and NOT the top ones', ['s4_min_confluence', 's4_multi_min_score', 's4_regime_switch', 's4_auto_disable', 's4_auto_markets', 's4_auto_markets_max', 's4_symbols_pool', 's4_max_trades_day'].every(x => A.includes('id="' + x + '"')) && !A.includes('s4_risk_pct') && !M.includes('s4_min_confluence')]);
  OUT.push(['asks the server for the current values once', p.calls.length === 1 && p.calls[0].u === '/api/admin/settings']);
  OUT.push(['fields are filled from the server', p.$('#s4_risk_pct').value === '1.0' && p.$('#s4_news_lock').checked === true && p.$('#s4_regime_switch').checked === false && p.$('#s4Bot').checked === true]);
  // save main with a bad number: nothing is sent
  p.$('#s4_risk_pct').value = '9'; const n0 = p.calls.length; p.$('#s4Save').onclick.call(p.$('#s4Save')); await tick();
  OUT.push(['a number out of range is stopped in the page (nothing sent)', p.calls.length === n0 && /Risk per trade/.test(p.$('#s4Msg').textContent)]);
  // good save
  p.$('#s4_risk_pct').value = '0.5'; p.$('#s4_symbols').value = 'xauusd, btcusd'; p.$('#s4_news_lock').checked = false; p.$('#s4Bot').checked = false;
  p.$('#s4Save').onclick.call(p.$('#s4Save')); await tick(); await tick();
  const sent = p.calls.filter(c => c.u === '/api/admin/settings' && c.body && c.body.risk_pct)[0];
  OUT.push(['main save sends the numbers as text and the switches as 1/0', sent && sent.body.risk_pct === '0.5' && sent.body.news_lock === '0' && sent.body.burst_enabled === '1']);
  OUT.push(['symbols are cleaned to upper case without spaces', sent && sent.body.symbols === 'XAUUSD,BTCUSD']);
  OUT.push(['main save does not send the advanced fields', sent && !('min_confluence' in sent.body) && !('regime_switch' in sent.body)]);
  OUT.push(['Bot on is sent through /api/bot when it changed', p.calls.some(c => c.u === '/api/bot' && c.body && c.body.on === false)]);
  OUT.push(['it says Saved', p.$('#s4Msg').textContent === 'Saved.' && p.toasts.includes('Saved')]);
  // advanced save
  p.$('#s4_min_confluence').value = '3'; p.$('#s4_regime_switch').checked = true;
  p.$('#s4Save2').onclick.call(p.$('#s4Save2')); await tick(); await tick();
  const adv = p.calls.filter(c => c.body && 'min_confluence' in c.body)[0];
  OUT.push(['advanced save sends its own fields', adv && adv.body.min_confluence === '3' && adv.body.regime_switch === '1' && !('risk_pct' in adv.body)]);
  // a server refusal shows its words and re-enables the button
  const srv2 = (u, o) => (o && o.body && o.body.max_open) ? Promise.reject(new Error('max_open must be between 1 and 10')) : srv(u, o);
  p = run(srv2); await tick(); p.$('#s4_max_open').value = '5'; const b = p.$('#s4Save'); b.onclick.call(b); await tick(); await tick();
  OUT.push(['a server refusal is shown and the button works again', p.$('#s4Msg').textContent.includes('max_open') && b.disabled === false]);
  console.log(JSON.stringify(OUT));
})();
'''
if shutil.which('node') and CODE:
    # the harness needs the inputs to exist: the page code writes HTML, so here every "#s4_*" lookup creates a fake input on demand (see $ above)
    hp = os.path.join(tempfile.gettempdir(), 'sxb_s4_h.js'); open(hp, 'w', encoding='utf-8').write(HARNESS)
    r = subprocess.run(['node', hp, CODE], capture_output=True, text=True)
    try:
        for n, ok in json.loads(r.stdout.strip().splitlines()[-1]): T('page: ' + n, ok)
    except Exception: T('page code ran in node: ' + (r.stderr or r.stdout)[:300], False)
else: print('SKIP node part (node missing or no S4 code)')

for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
