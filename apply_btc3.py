"""Section 3 (BTC plan): BTC lot size for Phone mode.
Finding: stops are already BTC-sized. brain.evaluate checks the stop in ATR (0.5 to max_stop_atr x the 15-minute ATR), so it scales with price
by itself. The EA sizes lots from the broker's own tick value, so it is right for any market. The one real bug: assist.per_lot_loss treated a
6-letter name ending in USD as a forex pair (100,000 units), so BTCUSD showed a lot size about 100,000 times too small / 'Too small' for everyone.
 - backend/assist.py: a crypto market (BTCUSD, BTCUSDm, BTCUSD.a ...) uses a contract size in BTC per 1.00 lot: setting btc_contract, else Render variable BTC_CONTRACT, else 1.0.
   Brokers differ (many use 1 lot = 1 BTC): the owner must check it in MT5 (right-click the symbol > Specification > Contract size). Bad value = 1.0.
Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
A = 'backend/assist.py'
edit(A, "from . import store as st, links, strategy_info as si\n", "from . import store as st, links, strategy_info as si, risk\n", "si, risk")
edit(A, "_FX = 100000.0\n", '''_FX = 100000.0

def btc_contract():
    """BTC per 1.00 lot. Many brokers use 1; check your own (MT5: symbol Specification > Contract size). Setting btc_contract, else env BTC_CONTRACT, else 1."""
    try: x = float(st.get('btc_contract') or os.getenv('BTC_CONTRACT') or 1.0)
    except (TypeError, ValueError): return 1.0
    return x if math.isfinite(x) and 0 < x <= 1000 else 1.0
''', "def btc_contract")
edit(A, "    if s in _CONTRACT: return d * _CONTRACT[s]\n", "    if s in _CONTRACT: return d * _CONTRACT[s]\n    if risk.is_crypto(s): return d * btc_contract()                 # BTCUSD, BTCUSDm, BTCUSD.a: NOT a forex pair\n", "btc_contract()                 #")
