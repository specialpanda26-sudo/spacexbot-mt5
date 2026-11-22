"""LV4 tests: live numbers follow the platform the bot is set to trade on. No network. Run: python tests/test_lv4.py"""
import os, sys, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'lv4_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, brokers as bk, links, livestats as ls, live, tradeon
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
A = 'dev-amy@x.com'; c.get('/api/me', headers=H('amy@x.com')); NOW = time.time()
def sig(status, broker, sym, pnl=None, closed=None):
    st.x("INSERT INTO signals(symbol,side,entry,status,created,pnl,closed,strategy,fill,uid,broker) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (sym, 'buy', 100.0, status, int(NOW), pnl, closed, 'gold_scalp', 100.0, A, broker))
bk.save(A, 'Deriv', {'token': 'abcDEF1234567890'}); bk.set_bal(A, 'Deriv', 1000.0, 'USD', True)
bk.save(A, 'Binance', {'key': 'K' * 64, 'secret': 'S' * 64}); bk.set_bal(A, 'Binance', 250.0, 'USD', True)
st.set_acct({'balance': 42000.0, 'equity': 41980.0, 'open': 1, 'demo': True, 'seen': NOW}, A) if hasattr(st, 'set_acct') else None
links.get(A) or links.create(A) if hasattr(links, 'create') else None
sig('open', 'Deriv', 'EURUSD'); sig('open', 'Binance', 'BTCUSD'); sig('open', 'MT5', 'XAUUSD'); sig('open', None, 'USDJPY')
sig('closed', 'Deriv', 'EURUSD', 5.0, int(NOW)); sig('closed', 'Binance', 'BTCUSD', 2.0, int(NOW))
s = ls.snapshot(A, False, NOW)
T('nothing chosen: old behaviour, Deriv and Binance balances are both sources', {x['id'] for x in s['sources']} >= {'Deriv', 'Binance'} and s['platform'] is None and s['open'] >= 4)
tradeon.set_(A, False, 'Deriv'); s = ls.snapshot(A, False, NOW)
T('Deriv chosen: only the Deriv balance, equity, trades and today', s['balance'] == 1000.0 and s['equity'] == 1000.0 and [x['id'] for x in s['sources']] == ['Deriv'] and s['open'] == 1 and [t['symbol'] for t in s['trades']] == ['EURUSD'] and s['today'] == 5.0 and s['platform'] == 'Deriv')
bk.set_bal(A, 'Deriv', 1000.0, 'USD', False); T('the chosen account\'s real/demo mode is used', ls.snapshot(A, False, NOW)['mode'] == 'real'); bk.set_bal(A, 'Deriv', 1000.0, 'USD', True)
tradeon.set_(A, False, 'Binance'); s = ls.snapshot(A, False, NOW)
T('Binance chosen: its testnet balance, its own trades and today', s['balance'] == 250.0 and s['mode'] == 'demo' and [x['id'] for x in s['sources']] == ['Binance'] and [t['symbol'] for t in s['trades']] == ['BTCUSD'] and s['today'] == 2.0)
tradeon.set_(A, False, 'MT5'); s = ls.snapshot(A, False, NOW)
T('MT5 chosen: no Deriv or Binance money, and only MT5 or old unmarked trades', all(x['id'] == 'MT5' for x in s['sources']) and s['balance'] != 1250.0 and {t['symbol'] for t in s['trades']} == {'XAUUSD', 'USDJPY'} and s['today'] == 0)
tradeon.set_(A, False, 'Binance'); bk.set_bot(A, 'Binance', True)
T('a Binance-only bot counts as running when its balance is fresh', live.snapshot(NOW, A)['on'] is True)
bk.set_bot(A, 'Binance', False); T('...and not when its switch is off', live.snapshot(NOW, A)['on'] is False)
d = live.build(True, {'a': {'balance': 250.0, 'equity': 250.0, 'open': 1, 'label': ' (Binance demo)'}, 'open': [], 'today': 0, 'now': NOW})
T('the notification names the account it reads', 'Balance $250.00 (Binance demo)' in d['big'])
print('%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
