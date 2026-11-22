"""Tests for Section 3 (BTC lot size in Phone mode, and proof that stops are already BTC-sized). Run: python tests/test_btc3.py"""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'btc3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
os.environ.pop('BTC_CONTRACT', None)
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, ROOT)
from backend import app as appmod, assist, store as st, brain, indicators
appmod.alerts.stop()
R = []
def T(name, ok): R.append((name, bool(ok)))

# ---- lot size ----
T('BTC is not a forex pair: 1 lot, $500 stop = $500 loss (contract 1 BTC)', abs(assist.per_lot_loss('BTCUSD', 60000, 59500) - 500) < 1e-6)
T('broker spellings count too (BTCUSDm, BTCUSD.a)', abs(assist.per_lot_loss('BTCUSDm', 60000, 59500) - 500) < 1e-6 and abs(assist.per_lot_loss('btcusd.a', 60000, 59500) - 500) < 1e-6)
r = assist.size('BTCUSD', 60000, 59500, 61000, 1000, 1.0)
T('$1,000 account, 1% risk, $500 stop: 0.02 lot, risk $10, win $20 at 2R', r['lots'] == 0.02 and r['risk_usd'] == 10.0 and r['win_usd'] == 20.0)
r = assist.size('BTCUSD', 60000, 58000, 62000, 1000, 1.0)
T('a wide stop on a small account says "too small" in plain words, not a wrong size', r['lots'] is None and 'Too small' in r['why'] and r['min_risk_usd'] == 20.0)
st.put('btc_contract', '0.1'); T('setting btc_contract changes the size (broker with 0.1 BTC per lot)', abs(assist.per_lot_loss('BTCUSD', 60000, 59500) - 50) < 1e-6)
st.put('btc_contract', 'junk'); T('a bad btc_contract falls back to 1', assist.btc_contract() == 1.0)
st.put('btc_contract', '-5'); T('a negative btc_contract falls back to 1', assist.btc_contract() == 1.0)
st.put('btc_contract', ''); os.environ['BTC_CONTRACT'] = '0.5'; T('empty setting: the Render variable BTC_CONTRACT is used', assist.btc_contract() == 0.5)
os.environ.pop('BTC_CONTRACT'); st.put('btc_contract', '1')
T('gold is untouched (100 per lot)', abs(assist.per_lot_loss('XAUUSD', 2650, 2645) - 500) < 1e-6)
T('EURUSD is untouched (100,000 per lot)', abs(assist.per_lot_loss('EURUSD', 1.1, 1.099) - 100) < 1e-6)
T('USDJPY is untouched', abs(assist.per_lot_loss('USDJPY', 150, 149) - 100000 / 150) < 1e-6)
T('an unknown name still gets no size', assist.per_lot_loss('FOOBAR', 1, 0.5) is None)

# ---- stops: the brain's stop check is in ATR, so it must treat gold-sized and BTC-sized candles the same ----
def candles(scale, n=200):
    random.seed(3); p = 100.0 * scale; out = []
    for i in range(n):
        o = p; p += random.gauss(0, 0.6) * scale; h = max(o, p) + 0.3 * scale; l = min(o, p) - 0.3 * scale; out.append({'t': i * 900, 'o': o, 'h': h, 'l': l, 'c': p, 'v': 1})
    return out
def verdict(scale, k, side='buy'):
    m = candles(scale); a = indicators.atr(m)[-1]; entry = m[-1]['c']; sl = entry - k * a if side == 'buy' else entry + k * a
    def fake(m15, h1): return {'name': 'fake_btc', 'side': side, 'sl': sl}
    fake.__name__ = 'fake_btc'
    old = brain.ALL; brain.ALL = [fake]; info = {}
    try: res = brain.evaluate(m, m, min_conf=1, info=info, adx_trend_min=0, adx_rev_max=1e9)
    finally: brain.ALL = old
    return res, info
for scale, label in ((1, 'gold-sized'), (600, 'BTC-sized')):
    ok, _ = verdict(scale, 2.0); T('%s candles: a 2 ATR stop is accepted' % label, ok is not None and ok['side'] == 'buy')
    no, info = verdict(scale, 4.5); T('%s candles: a 4.5 ATR stop is refused as too wide' % label, no is None and info.get('code') == 'stop')
    no, info = verdict(scale, 0.3); T('%s candles: a 0.3 ATR stop is refused as too tight' % label, no is None and info.get('code') == 'stop')
a, b = verdict(1, 2.0)[0], verdict(600, 2.0)[0]
T('same shape at 600x the price gives the same stop in ATR', a and b and a['why']['sl_atr'] == b['why']['sl_atr'])
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
