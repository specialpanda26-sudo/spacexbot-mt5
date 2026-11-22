"""Section B1 checks (owner, Nov 22): the Bitcoin switch. It puts BTCUSD in the Symbols setting, turns the weekend exemption on, and in 'weekends only' mode
Bitcoin rests on weekdays. Gold and forex are untouched. Run: python tests/test_btc1.py"""
import os, sys, glob, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'btc1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend import app as APPM
from backend.app import app
from backend import store as st, risk, links, bars, btc_switch
APP = open(os.path.join(ROOT, 'backend', 'app.py'), encoding='utf-8').read()
RSK = open(os.path.join(ROOT, 'backend', 'risk.py'), encoding='utf-8').read()
HTML = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def at(y, m, d, h, mi=0): return dt.datetime(y, m, d, h, mi, tzinfo=dt.timezone.utc).timestamp()
WED = at(2026, 11, 18, 12); SAT = at(2026, 11, 21, 12); SUN = at(2026, 11, 22, 9); MON0 = at(2026, 11, 23, 0); FRI19 = at(2026, 11, 20, 19, 59); FRI20 = at(2026, 11, 20, 20)
def syms(v): st.put('symbols', v)
def lst(): return [x for x in (st.get('symbols') or '').split(',') if x]
DEF = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY']
syms(','.join(DEF))
s = btc_switch.status()
T('default: Bitcoin is off, nothing listed', s['on'] is False and s['listed'] == [])
r = btc_switch.set_on(True)
T('switch on: BTCUSD is added after the existing markets', lst() == DEF + ['BTCUSD'] and r['on'] is True and r['listed'] == ['BTCUSD'])
T('switch on: the weekend exemption is on and the mode is weekends only', st.get('crypto_weekend') == '1' and st.get('btc_mode') == 'weekend' and r['mode'] == 'weekend')
btc_switch.set_on(True)
T('switch on twice: still exactly one BTCUSD', lst().count('BTCUSD') == 1 and len(lst()) == 5)
r = btc_switch.set_on(True, weekend_only=False)
T('every-day mode: btc_mode is always', st.get('btc_mode') == 'always' and r['mode'] == 'always')
syms('XAUUSD,BTCUSDm'); btc_switch.set_on(True)
T("a broker spelling already listed is kept and no second BTC is added", lst() == ['XAUUSD', 'BTCUSDm'])
syms(','.join(DEF + ['BTCUSD', 'BTCUSDm'])); r = btc_switch.set_on(False)
T('switch off: every Bitcoin spelling is removed, the other markets stay', lst() == DEF and r['on'] is False and r['listed'] == [])
syms('BTCUSD'); btc_switch.set_on(False)
T('switch off with only Bitcoin listed: the list is never left empty', lst() and not any(risk.is_crypto(x) for x in lst()))
syms(','.join(DEF)); st.put('crypto_weekend', '0'); btc_switch.set_on(True)
T('switch on turns a switched-off weekend exemption back on', st.get('crypto_weekend') == '1')
# weekday_skip: Bitcoin rests on weekdays in weekends-only mode
syms(','.join(DEF)); btc_switch.set_on(True)
T('weekends-only: BTCUSD and BTCUSDm are skipped on a Wednesday and Monday 00:00', all(risk.weekday_skip(x, t) for x in ('BTCUSD', 'BTCUSDm') for t in (WED, MON0)))
T('weekends-only: Friday 19:59 is still skipped, Friday 20:00 is not', risk.weekday_skip('BTCUSD', FRI19) and not risk.weekday_skip('BTCUSD', FRI20))
T('weekends-only: Saturday and Sunday are not skipped', not risk.weekday_skip('BTCUSD', SAT) and not risk.weekday_skip('BTCUSD', SUN))
T('weekends-only: gold and forex are never skipped by this rule', not any(risk.weekday_skip(x, t) for x in ('XAUUSD', 'EURUSD', 'GBPJPY') for t in (WED, SAT, FRI20)))
btc_switch.set_on(True, weekend_only=False)
T('every-day mode: Bitcoin is not skipped on a Wednesday', not risk.weekday_skip('BTCUSD', WED))
btc_switch.set_on(True); st.put('crypto_weekend', '0')
T('exemption off (crypto_weekend 0): the weekday rule does nothing', not risk.weekday_skip('BTCUSD', WED))
st.put('crypto_weekend', '1')
# the gate: Saturday is open with the switch on, shut with it off
st.put('bot_enabled', 1); links.bot_on = lambda uid='': True
st.acct = lambda uid='': {'seen': 4e9, 'balance': 1000, 'open': 0, 'demo': True}
syms(','.join(DEF)); btc_switch.set_on(True)
T('switch on: the Saturday gate lets the bot look', risk.global_gate(SAT) == (True, 'ok'))
btc_switch.set_on(False)
T('switch off: the Saturday gate is shut again', risk.global_gate(SAT) == (False, 'weekend/Friday-night risk'))
# the real scan: Bitcoin is not looked at on a weekday in weekends-only mode, and is looked at on a Saturday
rows = [[1700000000 + i * 900, 1.0, 2.0, 0.5, 1.5, 1] for i in range(3)]
bars.merge('BTCUSD', 'M15', rows); bars.merge('BTCUSD', 'H1', rows)
seen = []; APPM.risk_alerts.watch = lambda uid='': seen.append(uid)
def scan(shut):
    seen.clear(); st.x("DELETE FROM kv WHERE k LIKE 'lastbar:%'"); APPM._last_scan.clear()
    risk.weekend_shut = lambda now=None: shut
    try: APPM._scan_tf('BTCUSD', '', 'M15', 'H1')
    except Exception as e: pass
    return len(seen)
syms(','.join(DEF)); btc_switch.set_on(True)
T('scan on a weekday, weekends-only: Bitcoin is not analysed', scan(False) == 0)
T('scan on a Saturday, weekends-only: Bitcoin is analysed', scan(True) == 1)
btc_switch.set_on(True, weekend_only=False)
T('scan on a weekday, every-day mode: Bitcoin is analysed', scan(False) == 1)
# the admin route
C = app.test_client(); AH = {'Authorization': 'Bearer dev:boss@x.com'}; UH = {'Authorization': 'Bearer dev:joe@x.com'}
C.get('/api/me', headers=UH); C.get('/api/me', headers=AH)
syms(','.join(DEF)); st.put('btc_mode', 'always')
T('route: a normal user is refused (GET and POST)', C.get('/api/admin/btc', headers=UH).status_code == 403 and C.post('/api/admin/btc', json={'on': True}, headers=UH).status_code == 403)
r = C.get('/api/admin/btc', headers=AH).get_json()
T('route: GET shows the status', r['on'] is False and r['listed'] == [])
r = C.post('/api/admin/btc', json={'on': True, 'weekend_only': True}, headers=AH).get_json()
T('route: POST on adds BTCUSD and reports weekends only', r['on'] is True and r['mode'] == 'weekend' and 'BTCUSD' in lst())
T('route: a wrong type is refused and changes nothing', C.post('/api/admin/btc', json={'on': 'yes'}, headers=AH).status_code == 400 and C.post('/api/admin/btc', json={'on': True, 'weekend_only': 'x'}, headers=AH).status_code == 400 and lst().count('BTCUSD') == 1)
r = C.post('/api/admin/btc', json={'on': False}, headers=AH).get_json()
T('route: POST off removes it', r['on'] is False and 'BTCUSD' not in lst())
# wiring in the real files
T('app.py: the normal scan rests Bitcoin on weekdays (once)', APP.count('if ok and risk.weekday_skip(sym): return') == 1)
T('app.py: the burst scan rests it too (once)', APP.count('    if risk.weekday_skip(sym): return') == 1)
T('app.py: the route exists (GET and POST)', "@app.get('/api/admin/btc')" in APP and "@app.post('/api/admin/btc')" in APP and 'from . import btc_switch' in APP)
T('risk.py: weekday_skip exists and reads btc_mode', 'def weekday_skip(' in RSK and "st.get('btc_mode') == 'weekend'" in RSK)
T('index.html: the admin card, its four controls and the script block exist once', all(HTML.count(x) == 1 for x in ('id="btOn"', 'id="btOff"', 'id="btWk"', 'id="btMsg"', '/*B1-start*/', '/*B1-end*/')))
T('index.html: the card talks to the route and says demo first', HTML.count('"/api/admin/btc"') == 2 and 'not tested on Bitcoin, so use a demo account first' in HTML)
for f in glob.glob(DB + '*'): os.remove(f)
print('\n%d/%d passed' % (sum(1 for _, o in R if o), len(R))); sys.exit(0 if all(o for _, o in R) else 1)
