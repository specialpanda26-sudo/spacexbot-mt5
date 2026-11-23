"""DS1 tests: Deriv symbol naming for crypto vs forex/gold. No network. Run: python tests/test_ds1.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))

from backend import deriv_sym as ds

R = []
def T(n, ok):
    R.append((n, bool(ok)))
    print('PASS' if ok else 'FAIL', n)

T('BTCUSD -> cryBTCUSD', ds.name('BTCUSD') == 'cryBTCUSD')
T('ETHUSD -> cryETHUSD', ds.name('ETHUSD') == 'cryETHUSD')
T('BTCUSDm suffix stripped -> cryBTCUSD', ds.name('BTCUSDm') == 'cryBTCUSD')
T('BTCUSD.a suffix & spaces -> cryBTCUSD', ds.name('  btcusd.a ') == 'cryBTCUSD')
T('XAUUSD -> frxXAUUSD', ds.name('XAUUSD') == 'frxXAUUSD')
T('EURUSD -> frxEURUSD', ds.name('EURUSD') == 'frxEURUSD')
T('base() keeps plain pair', ds.base('BTCUSDm') == 'BTCUSD' and ds.base('XAUUSD') == 'XAUUSD')

f = sum(1 for _, ok in R if not ok)
print('%d/%d passed' % (len(R) - f, len(R)))
sys.exit(1 if f else 0)
