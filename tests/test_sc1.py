"""SC1 checks: AI screen assistant, server side (fake AI, no network). Run: python tests/test_sc1.py"""
import os, sys, time, glob, json, base64, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_sc1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD', SCREEN_DAILY_CAP='60', SCREEN_LEARN_CAP='3')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, screenread as sr, bars, brain, alerts
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'bob@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, B = 'dev-amy@x.com', 'dev-bob@x.com'
st.x('UPDATE users SET plan_until=? WHERE uid=?', (int(time.time()) + 86400 * 30, A))
rows = [(1_700_000_000 + i * 900, 2000, 2001, 1999, 2000, 1) for i in range(130)]
bars.merge('XAUUSD', 'M15', rows); bars.merge('XAUUSD', 'H1', rows)
MARK = b'SECRET-PIXELS-9f3a'
IMG = base64.b64encode(b'\xff\xd8\xff\xe0' + MARK + b'\x00' * 50).decode()
GOOD = {'readable': True, 'symbol': 'XAU/USD', 'timeframe': 'M15', 'trend': 'up', 'bias': 'buy', 'patterns': ['pullback'], 'support': [1990], 'resistance': [2010],
        'last_price': 2000, 'strategies': ['ma_bounce', 'not_a_strategy'], 'note': 'Uptrend.'}
calls = []
def fake(reply):
    def f(b64): calls.append(b64); return reply if isinstance(reply, str) else json.dumps(reply)
    return f
SIG = {'side': 'buy', 'entry': 2000.0, 'sl': 1990.0, 'tp': 2020.0, 'strategy': 'ma_bounce', 'score': 2, 'adx': 25, 'why': {}}
real_eval = brain.evaluate
def bot_says(s, text='None of the strategies saw a setup.'):
    def ev(*a, **k):
        if k.get('info') is not None: k['info']['text'] = text
        return s
    brain.evaluate = ev
def post(who, image=IMG, ctx='trade', free=True, keep=False):
    if free: st.put('screen:last:dev-' + who, 0)
    if free and not keep: st.x('DELETE FROM screen_reads')
    return c.post('/api/screen/read', json={'image': image, 'context': ctx}, headers=H(who))
def nsig(): return st.q('SELECT COUNT(*) n FROM signals', (), True)['n']

T('switch defaults to off', st.get('screen_on') == '0')
sr.call_model = fake(GOOD); n0 = len(calls)
r = post('amy@x.com'); T('switched off: 403 and the AI is never asked', r.status_code == 403 and len(calls) == n0)
T('signed out: 401', c.post('/api/screen/read', json={'image': IMG}).status_code == 401)
T('admin switch rejects 2', c.post('/api/admin/settings', json={'screen_on': '2'}, headers=H('boss@x.com')).status_code == 400)
T('admin switch accepts 1', c.post('/api/admin/settings', json={'screen_on': '1'}, headers=H('boss@x.com')).status_code == 200 and sr.on())

r = post('bob@x.com'); T('trade without a plan: 402', r.status_code == 402)
r = post('amy@x.com', image='%%%'); T('not base64: 400', r.status_code == 400)
r = post('amy@x.com', image=base64.b64encode(b'GIF89a-not-a-jpeg').decode()); T('not a JPEG: 400', r.status_code == 400)
r = post('amy@x.com', image='A' * (sr.MAX_B64 + 4)); T('too big: 413', r.status_code == 413)
r = post('amy@x.com', ctx='x'); T('bad context: 400', r.status_code == 400)
T('none of those reached the AI', len(calls) == n0)

# ---- verdicts (the bot is asked, nothing is placed) ----
s0 = nsig()
bot_says(SIG); r = post('amy@x.com'); j = r.get_json()
T('read comes back checked, unknown strategy id dropped, symbol mapped', r.status_code == 200 and j['read']['strategies'] == ['ma_bounce'] and j['read']['symbol'] == 'XAU/USD')
T('trade context, bot switched off: blocked with plain words, no trade', j['bot']['code'] == 'blocked' and 'cannot work' in j['bot']['text'] and 'bot off' in j['bot']['text'])
T('the bot still shows its own stop and target, not the AI\'s', j['bot']['signal']['sl'] == 1990.0 and j['bot']['signal']['tp'] == 2020.0 and j['bot']['signal']['strategy_name'])
j = post('amy@x.com', ctx='learn').get_json()
T('learn context: the bot gates do not block the lesson, bot agrees', j['bot']['code'] == 'agree')
T('learn context: teaching list has plain descriptions', j['teach'] and j['teach'][0]['id'] == 'ma_bounce' and j['teach'][0]['desc'])
g = dict(GOOD, bias='sell'); sr.call_model = fake(g); j = post('amy@x.com', ctx='learn').get_json()
T('AI and bot disagree: says so, bot stays out', j['bot']['code'] == 'disagree' and 'stays out' in j['bot']['text'])
g = dict(GOOD, bias='none'); sr.call_model = fake(g); j = post('amy@x.com', ctx='learn').get_json()
T('AI sees nothing, bot sees a setup: bot_only', j['bot']['code'] == 'bot_only')
sr.call_model = fake(GOOD); bot_says(None, 'No setup on this candle.'); j = post('amy@x.com', ctx='learn').get_json()
T('bot sees no setup: no_setup with the bot reason, never a trade', j['bot']['code'] == 'no_setup' and 'would not trade' in j['bot']['text'] and 'No setup' in j['bot']['text'] and j['bot']['signal'] is None)
sr.call_model = fake(dict(GOOD, symbol='Volatility 75 Index')); j = post('amy@x.com', ctx='learn').get_json()
T('market the bot has no candles for: no_data, AI read still shown', j['bot']['code'] == 'no_data' and j['read']['readable'])
T('no signal row was ever created', nsig() == s0)
brain.evaluate = real_eval

# ---- bad AI answers ----
for name, reply in (('plain text', 'I think it goes up'), ('bad bias', dict(GOOD, bias='maybe')), ('bad price', dict(GOOD, last_price=-5)), ('support not a list', dict(GOOD, support='1990')), ('no readable flag', {'symbol': 'XAUUSD'})):
    sr.call_model = fake(reply); j = post('amy@x.com', ctx='learn').get_json()
    T('AI answer rejected (%s): unreadable, no bot verdict' % name, j['read']['readable'] is False and j['bot'] is None)
sr.call_model = fake({'readable': False, 'note': 'blurry'}); j = post('amy@x.com', ctx='learn').get_json()
T('AI says it cannot read: passed on in plain words', j['read'] == {'readable': False, 'note': 'blurry'} and j['bot'] is None)
sr.call_model = fake('```json\n' + json.dumps(GOOD) + '\n```'); bot_says(SIG)
T('JSON inside a code fence is accepted', post('amy@x.com', ctx='learn').get_json()['read']['readable'] is True); brain.evaluate = real_eval
def boom(b64): raise sr.ModelError('The AI reader did not answer (500). Try again in a moment.')
sr.call_model = boom; r = post('amy@x.com', ctx='learn')
T('AI service down: 502 with plain words', r.status_code == 502 and 'did not answer' in r.get_json()['error'])

# ---- limits ----
sr.call_model = fake(GOOD); bot_says(SIG)
st.x('DELETE FROM screen_reads'); st.put('screen:last:' + A, 0)
r1 = post('amy@x.com', free=False); r2 = post('amy@x.com', free=False)
T('two reads inside the gap: second is 429', r1.status_code == 200 and r2.status_code == 429 and 'wait' in r2.get_json()['error'])
st.x('DELETE FROM screen_reads')
codes = [post('amy@x.com', ctx='learn', keep=True).status_code for _ in range(4)]
T('learn cap 3: the 4th read is 429', codes == [200, 200, 200, 429])
T('trade reads are counted apart from learn reads', post('amy@x.com', ctx='trade', keep=True).status_code == 200)
j = c.get('/api/screen/status', headers=H('bob@x.com')).get_json()
T('status: bob may learn, may not trade, counts shown', j['on'] and j['learn']['allowed'] and not j['trade']['allowed'] and j['learn']['cap'] == 3)
brain.evaluate = real_eval

# ---- the picture is never kept ----
buf = io.StringIO(); sr.call_model = fake(GOOD); bot_says(SIG)
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf): post('amy@x.com', ctx='learn')
brain.evaluate = real_eval
import sqlite3
con = sqlite3.connect(DB); blob = ''
for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    for row in con.execute('SELECT * FROM "%s"' % t).fetchall(): blob += repr(row)
con.close()
T('the picture is in no table and not in the log', IMG not in blob and MARK.decode() not in blob and IMG not in buf.getvalue() and 'SECRET-PIXELS' not in buf.getvalue())
T('what is kept: short read, time, verdict', st.q("SELECT COUNT(*) n FROM screen_reads WHERE data LIKE '%symbol%' AND verdict!=''", (), True)['n'] > 0)
sr.call_model = sr._anthropic; os.environ.pop('ANTHROPIC_API_KEY', None)
st.put('screen:last:' + A, 0); st.x('DELETE FROM screen_reads')
r = c.post('/api/screen/read', json={'image': IMG, 'context': 'learn'}, headers=H('amy@x.com'))
T('no key set: 502 says the owner must add it', r.status_code == 502 and 'owner must add' in r.get_json()['error'])
for f in glob.glob(DB + '*'): os.remove(f)
p = sum(1 for _, o in R if o); print('%d/%d passed' % (p, len(R))); sys.exit(0 if p == len(R) else 1)
