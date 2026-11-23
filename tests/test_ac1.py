"""AC1 tests: the Journal's live 'what the bot is doing' feed. No network. Run: python tests/test_ac1.py"""
import os, sys, time, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_ac1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, botstate, activity, burst_look, brokers as bk, links
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client(); OW = {'Authorization': 'Bearer dev:boss@x.com'}; PE = {'Authorization': 'Bearer dev:ann@x.com'}
c.get('/api/me', headers=OW); c.get('/api/me', headers=PE); OU = 'dev-boss@x.com'; PU = 'dev-ann@x.com'
now = int(time.time())
activity.log(PU, 'Checked XAUUSD: No good setup yet.', 'check', now - 300)
activity.log(PU, 'Checked XAUUSD: No good setup yet.', 'check', now - 280)
T('same sentence 20 s later is not written again (one row)', len(activity.items(PU, False)) == 1)
activity.log(PU, 'Checked XAUUSD: No good setup yet.', 'check', now)
it = activity.items(PU, False)
T('same sentence later refreshes the row: still one, newer time, a = first seen', len(it) == 1 and it[0]['t'] == now and it[0]['a'] == now - 300 and it[0]['n'] == 2)
activity.log(PU, 'EURUSD: waiting', 'wait', now + 1); activity.log(PU, 'Checked XAUUSD: No good setup yet.', 'check', now + 200)
T('a repeat that is not on top moves back to the top', [r['m'] for r in activity.items(PU, False)][0].startswith('Checked XAUUSD'))
for i in range(120): activity.log(PU, 'row %d' % i, 'check', now + i)
T('at most 80 rows are kept', len(activity.items(PU, False, 500)) == activity.MAX)
activity.log(PU, '', 'check'); T('empty text is ignored', all(r['m'] for r in activity.items(PU, False, 500)))
botstate.note(OU, 'XAUUSD', 'nosetup', 'Trend and RSI disagree.')
botstate.note(OU, 'EURUSD', 'gate', 'max open positions')
botstate.note(OU, 'GBPUSD', 'signal')
m = [r['m'] for r in activity.items(OU, False)]
T('botstate.note writes plain sentences', any(x == 'Checked XAUUSD: No good setup yet. Trend and RSI disagree.' for x in m) and any(x.startswith('EURUSD: It already has the most open trades') for x in m) and 'GBPUSD: Found a setup and sent it.' in m)
burst_look.note(OU, 'XAUUSD: no candles received yet.'); T('burst notes are in the feed', any(x == 'Burst: XAUUSD: no candles received yet.' for x in [r['m'] for r in activity.items(OU, False)]))
bk.set_why(OU, 'Deriv', 'login ended'); bk.set_bot(OU, 'Deriv', True)
m = [r['m'] for r in activity.items(OU, False)]
T('Deriv wait reason and bot switch are in the feed', 'Bot switched ON on Deriv.' in m and any(x.startswith('Deriv: Your Deriv login ended') for x in m))
j = c.get('/api/activity', headers=OW).get_json()
T('/api/activity: now, markets, items present', set(j) >= {'now', 'markets', 'items', 'ts'} and j['now']['headline'] and isinstance(j['items'], list))
T('markets lists each symbol once with words', {o['symbol'] for o in j['markets']} >= {'XAUUSD', 'EURUSD', 'GBPUSD'})
T('a signed-out caller gets 401', c.get('/api/activity').status_code == 401)
p = c.get('/api/activity', headers=PE).get_json()
T("a normal person never sees the owner's rows", not any('GBPUSD' in r['m'] for r in p['items']) and not p['markets'])
T('the owner sees the EA (empty scope) rows and their own', len(activity.items(OU, True)) >= len(activity.items(OU, False)))
st.put('scan:%s:OLD' % PU, json.dumps({'t': now - 90000, 'c': 'nosetup', 'w': ''})); T('a market not looked at for a day is left out', 'OLD' not in {o['symbol'] for o in activity.markets(PU, False)})
real = botstate.explain; botstate.explain = lambda *a, **k: 1 / 0
T('snapshot survives a failing state check', activity.snapshot(PU)['now']['state'] == 'stopped'); botstate.explain = real
html = open(os.path.join(HERE, '..', 'static', 'index.html'), encoding='utf-8').read()
T('page: AC1 block once, jNow card, poll url', html.count('/*AC1-start*/') == 1 and 'id="jNow"' in html and '"/api/activity"' in html)
T('page: jall falls back when the feed is not loaded', 'window.SXAC&&window.SXAC.state==="ok"' in html)
p_, f_ = sum(1 for _, ok in R if ok), sum(1 for _, ok in R if not ok)
print('%d passed, %d failed' % (p_, f_)); os.remove(os.environ['DB_PATH']); sys.exit(1 if f_ else 0)
