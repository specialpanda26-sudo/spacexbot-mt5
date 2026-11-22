"""Section 5A checks: trade on ONE platform at a time (MT5 / Deriv / Binance). No network. Run: python tests/test_tp5a.py"""
import os, sys, time, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, '_tp5a_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', SYMBOLS='XAUUSD', DERIV_APP_ID='1', BROKER_KEY='x' * 32)
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, brokers as bk, deriv, tradeon, alerts
try: alerts.stop()
except Exception: pass
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, O = 'dev-amy@x.com', 'dev-boss@x.com'
st.x('UPDATE users SET plan_until=? WHERE uid=?', (int(time.time()) + 86400 * 30, A))
AK = links.new_key(A)
def deriv_row(uid):
    st.x("INSERT OR REPLACE INTO broker_links(uid,broker,kind,secret_enc,label,mode,status,created,updated) VALUES(?,'Deriv','token',NULL,'...abcd','demo','verified',1,1)", (uid,))
deriv_row(A); deriv_row(O)
def poll(who_key): return c.post('/api/ea/sync', json={'account': {'demo': True}}, headers={'X-EA-Key': who_key}).get_json()
def pending(uid):
    st.x("DELETE FROM signals WHERE COALESCE(uid,'')=?", (uid,))
    st.x("INSERT INTO signals(symbol,side,sl,tp,status,created,uid,risk_pct,strategy,entry) VALUES('XAUUSD','buy',1990,2020,'pending',?,?,1.0,'t',2000)", (int(time.time()), uid))

# ---- default: nothing chosen, nothing changes ----
T('nothing chosen: get is None, all allowed', tradeon.get(A) is None and tradeon.allows(A, 'MT5') and tradeon.allows(A, 'Deriv') and tradeon.allows(A, 'Binance'))
j = c.get('/api/trade-on', headers=H('amy@x.com')).get_json()
T('GET /api/trade-on says nothing chosen', j['trade_on'] is None and [p['name'] for p in j['platforms']] == ['MT5', 'Deriv', 'Binance'])
links.set_bot(A, True); pending(A)
T('default: the MT5 bridge still gets the signal', (poll(AK).get('signal') or {}).get('symbol') == 'XAUUSD')
T('default: the Deriv bot flag still follows the MT5 link switch', deriv._bot(A) is True)

# ---- choose Deriv: MT5 stops, EA gets nothing ----
r = c.post('/api/trade-on', json={'platform': 'Deriv'}, headers=H('amy@x.com')); j = r.get_json()
T('choosing Deriv works and is reported', r.status_code == 200 and j['trade_on'] == 'Deriv' and tradeon.get(A) == 'Deriv')
T('choosing Deriv switches the MT5 bot off', links.bot_on(A) is False)
links.set_bot(A, True); pending(A)
x = poll(AK)
T('Deriv chosen: even with the MT5 flag forced on, the EA gets no signal and bot=false', x.get('signal') is None and x.get('basket') is None and x.get('bot') is False)
r = c.post('/api/link/bot', json={'on': True}, headers=H('amy@x.com'))
T('Deriv chosen: starting the MT5 bot is refused with plain words', r.status_code == 400 and 'Deriv' in r.get_json()['error'])
links.set_bot(A, False)
bk.set_bot(A, 'Deriv', True)
T('Deriv chosen: Deriv may trade (bot flag on)', deriv._bot(A) is True)
r = c.post('/api/brokers/Deriv/bot', json={'on': True}, headers=H('amy@x.com'))
T('Deriv chosen: the Deriv tile Start is allowed', r.status_code == 200)

# ---- choose MT5: Deriv stops ----
time.sleep(1.5)      # let the background Deriv round from the Start tap finish, it writes the 'why' note
bk.set_bot(A, 'Deriv', True)
c.post('/api/trade-on', json={'platform': 'MT5'}, headers=H('amy@x.com'))
T('choosing MT5 switches the Deriv bot off and says why', bk.bot_flag(A, 'Deriv') is False and bk.view(A)[0]['why_code'] == 'other platform')
T('MT5 chosen: deriv._bot is False even if the flag is forced on', (bk.set_bot(A, 'Deriv', True), deriv._bot(A))[1] is False)
T('MT5 chosen: a Deriv round says other platform and does nothing', deriv.run_once(A, lambda *a: None, lambda u: True) == 'other platform')
r = c.post('/api/brokers/Deriv/bot', json={'on': True}, headers=H('amy@x.com'))
T('MT5 chosen: the Deriv tile Start is refused', r.status_code == 400 and 'MT5' in r.get_json()['error'])
bk.set_bot(A, 'Deriv', False)
r = c.post('/api/bot', json={'on': True}, headers=H('amy@x.com'))
T('MT5 chosen: Bot tab Start turns on MT5 only', r.status_code == 200 and links.bot_on(A) is True and bk.bot_flag(A, 'Deriv') is not True)
pending(A); T('MT5 chosen: the EA gets the signal', (poll(AK).get('signal') or {}).get('symbol') == 'XAUUSD')
r = c.post('/api/bot', json={'on': False}, headers=H('amy@x.com'))
T('Stop always stops everything', r.status_code == 200 and links.bot_on(A) is False and bk.bot_flag(A, 'Deriv') is not True)

# ---- choose Binance: nothing trades ----
links.set_bot(A, True); bk.set_bot(A, 'Deriv', True)
c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('amy@x.com'))
T('choosing Binance stops MT5 and Deriv', links.bot_on(A) is False and bk.bot_flag(A, 'Deriv') is False)
r = c.post('/api/bot', json={'on': True}, headers=H('amy@x.com'))
T('Binance chosen, no Binance key saved: Start asks for the key and MT5 stays off (5B-2b)', r.status_code == 400 and 'Binance' in r.get_json()['error'] and not links.bot_on(A))
pending(A); links.set_bot(A, True); T('Binance chosen: the EA gets nothing', poll(AK).get('signal') is None); links.set_bot(A, False)
j = c.get('/api/trade-on', headers=H('amy@x.com')).get_json()
T('Binance chosen: the note says nothing will trade', 'Only Binance trades' in j['note'])

# ---- validation and isolation ----
for bad in ('Kraken', '', None, 5):
    r = c.post('/api/trade-on', json={'platform': bad}, headers=H('amy@x.com'))
    T('refused: %r' % (bad,), r.status_code == 400 and tradeon.get(A) == 'Binance')
r = c.post('/api/trade-on', json={'platform': 'deriv'}, headers=H('amy@x.com'))
T('name is case-insensitive', r.status_code == 200 and tradeon.get(A) == 'Deriv')
T('one person\'s choice does not touch another', tradeon.get(O) is None and tradeon.get('') is None)
T('signed out is refused', c.post('/api/trade-on', json={'platform': 'MT5'}).status_code in (401, 403))

# ---- the owner: the owner's EA has no uid, the choice is kept for it too ----
st.put('bot_enabled', '1'); pending(''); T('owner default: the owner EA gets its signal', (poll('k').get('signal') or {}).get('symbol') == 'XAUUSD')
c.post('/api/trade-on', json={'platform': 'Deriv'}, headers=H('boss@x.com'))
T('owner choosing Deriv: owner EA switched off (bot_enabled 0) and scope "" remembers it', st.get('bot_enabled') == '0' and tradeon.get('') == 'Deriv')
st.put('bot_enabled', '1'); pending('')
x = poll('k'); T('owner Deriv: the owner EA gets no signal even if bot_enabled is forced on', x.get('signal') is None and x.get('bot') is False)
st.put('bot_enabled', '0'); bk.set_bot(O, 'Deriv', False)
r = c.post('/api/bot', json={'on': True}, headers=H('boss@x.com'))
T('owner Bot tab Start with Deriv chosen leaves the owner EA off, Deriv on', r.status_code == 200 and st.get('bot_enabled') == '0' and bk.bot_flag(O, 'Deriv') is True)
c.post('/api/trade-on', json={'platform': 'MT5'}, headers=H('boss@x.com'))
c.post('/api/bot', json={'on': True}, headers=H('boss@x.com')); pending('')
T('owner MT5: Start turns the owner EA on and it gets the signal', st.get('bot_enabled') == '1' and (poll('k').get('signal') or {}).get('symbol') == 'XAUUSD')
T('owner MT5: Deriv is off', bk.bot_flag(O, 'Deriv') is False)

bad = [n for n, ok in R if not ok]
print('%d checks, %d failed' % (len(R), len(bad)))
for f in glob.glob(DB + '*'): os.remove(f)
sys.exit(1 if bad else 0)
