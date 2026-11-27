"""PL6: per-account market choice + switch. Run: python tests/test_mt5_markets.py   (last line: N checks, M failed)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_pl6_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t',
                  BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(HERE, '..'))
from backend import app as A
from backend import store as st, burst, mt5_markets as mk
c = A.app.test_client(); BOSS = {'Authorization': 'Bearer dev:boss@x.com'}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def bad(*a, **k):
    try: mk.switch(*a, **k); return False
    except ValueError: return True
SYM = {'XAUUSD': {'vol_min': 0.01, 'tick_value': 1.0, 'tick_size': 0.01}, 'EURUSD': {'vol_min': 0.01, 'tick_value': 1.0, 'tick_size': 0.00001},
       'US30': {'vol_min': 0.1, 'tick_value': 0.1, 'tick_size': 0.01}}
def ea(bars_for, sym=SYM):
    """One owner EA sync that sends candles for these markets; returns the markets the server scanned."""
    seen = []; old = A._scan; A._scan = lambda s, u='': seen.append((s, u))
    try:
        row = [[1800000000 + 900 * i, 1.0, 1.1, 0.9, 1.0, 1] for i in range(3)]
        r = c.post('/api/ea/sync', json={'account': {'balance': 1000, 'equity': 1000, 'login': 1, 'demo': True, 'sym': sym}, 'bars': {s: {'M15': row} for s in bars_for}}, headers={'X-EA-Key': 'k'})
        assert r.status_code == 200, r.status_code
    finally: A._scan = old
    return sorted(s for s, u in seen)

burst.save('', {'plan_usd': 0}); st.put('bot_enabled', '1')
T('default: nothing chosen = every market the EA sends is scanned', mk.get('') == [] and ea(['XAUUSD', 'EURUSD', 'US30']) == ['EURUSD', 'US30', 'XAUUSD'])
mk.switch('', 'EURUSD', 'only')
T('switch only EURUSD: just EURUSD is scanned', mk.get('') == ['EURUSD'] and ea(['XAUUSD', 'EURUSD', 'US30']) == ['EURUSD'])
T('lower case and spaces are fine', mk.switch('', ' xauusd ', 'add') == ['EURUSD', 'XAUUSD'] and ea(['XAUUSD', 'EURUSD', 'US30']) == ['EURUSD', 'XAUUSD'])
T('add of a market already chosen changes nothing', mk.switch('', 'EURUSD', 'add') == ['EURUSD', 'XAUUSD'])
T('remove one', mk.switch('', 'XAUUSD', 'remove') == ['EURUSD'])
T('cannot remove the last market', bad('', 'EURUSD', 'remove') and mk.get('') == ['EURUSD'])
T('all = back to every market', mk.switch('', '', 'all') == [] and ea(['XAUUSD', 'EURUSD']) == ['EURUSD', 'XAUUSD'])
T('remove with no choice starts from what the EA sends', mk.switch('', 'XAUUSD', 'remove') == ['EURUSD', 'US30'])
mk.switch('', '', 'all')
T('refuses a market the EA is not sending', bad('', 'GBPJPY', 'only') and mk.get('') == [])
T('refuses bad names and modes', bad('', 'EUR USD!', 'only') and bad('', '', 'only') and bad('', 'EURUSD', 'nope') and bad('', 'AB', 'only'))
T('add with nothing chosen = already every market (no change)', mk.switch('', 'EURUSD', 'add') == [])

# managed plan: a market whose broker minimum is above the plan lot is refused up front
burst.save('', {'plan_usd': 20})
T('$20 plan (0.02): switching to US30 (broker minimum 0.1) is refused', bad('', 'US30', 'only') and mk.get('') == [])
T('$20 plan: EURUSD is fine', mk.switch('', 'EURUSD', 'only') == ['EURUSD'])
ck = {m['sym']: m for m in mk.check('')['markets']}
T('check: EURUSD ok, US30 says why not', ck['EURUSD']['lot_ok'] is True and ck['US30']['lot_ok'] is False and 'refused' in ck['US30']['note'] and ck['EURUSD']['chosen'] and not ck['US30']['chosen'])
burst.save('', {'plan_usd': 0}); mk.switch('', '', 'all')
T('no plan: US30 can be switched to', mk.switch('', 'US30', 'only') == ['US30'])
mk.switch('', '', 'all')

# per-account: a subscriber's choice does not touch the owner's
st.put('mk:u1', json.dumps(['EURUSD']))
T('another account is separate', mk.allowed('u1', 'EURUSD') and not mk.allowed('u1', 'XAUUSD') and mk.allowed('', 'XAUUSD'))
T('junk in storage is ignored', (st.put('mk:u2', '{"x":1}') or True) and mk.get('u2') == [] and (st.put('mk:u3', 'not json') or True) and mk.get('u3') == [])

# routes
r = c.get('/api/markets', headers=BOSS); j = r.get_json()
T('GET route works for the owner', r.status_code == 200 and j['all'] is True and j['ea_known'] is True)
r = c.post('/api/markets', json={'mode': 'only', 'to': 'EURUSD'}, headers=BOSS)
T('POST route switches', r.status_code == 200 and r.get_json()['chosen'] == ['EURUSD'] and mk.get('') == ['EURUSD'])
r = c.post('/api/markets', json={'mode': 'only', 'to': 'GBPJPY'}, headers=BOSS)
T('POST route refuses with plain words', r.status_code == 400 and 'not sending' in r.get_json()['error'] and mk.get('') == ['EURUSD'])
T('POST route needs sign-in', c.post('/api/markets', json={'mode': 'all'}).status_code == 401)
mk.switch('', '', 'all')
try: os.remove(os.environ['DB_PATH'])
except OSError: pass
n = len(R); f = sum(1 for _, ok in R if not ok); print('%d checks, %d failed' % (n, f)); sys.exit(1 if f else 0)
