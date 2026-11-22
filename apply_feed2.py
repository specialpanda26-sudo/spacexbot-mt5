"""Section 2 (BTC plan): BTC candles + a feed line for every default market, and the feed rests where the bot rests.
 - backend/feed.py: default FEED_MAP now XAUUSD:GC=F, EURUSD:EURUSD=X, GBPUSD:GBPUSD=X, USDJPY:USDJPY=X, BTCUSD:BTC-USD (a market is still fetched only when it is in the Symbols setting).
 - While a BTC market is listed (risk.crypto_open()), the feed does not download a market the bot is resting (gold/forex at the weekend, BTC on weekdays in 'weekends only' mode); the admin card shows 'rest' instead of a red error. With no BTC listed nothing changes.
Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
F = 'backend/feed.py'
edit(F, "from . import store as st, bars\n", "from . import store as st, bars, risk\n", "bars, risk")
edit(F, "H1_EVERY = 600 ", "DEFAULT_MAP = 'XAUUSD:GC=F,EURUSD:EURUSD=X,GBPUSD:GBPUSD=X,USDJPY:USDJPY=X,BTCUSD:BTC-USD'   # Yahoo names; BTC-USD is the 24/7 crypto price (a few dollars off a broker's BTCUSD)\nH1_EVERY = 600 ", "DEFAULT_MAP =")
edit(F, "os.getenv('FEED_MAP', 'XAUUSD:GC=F')", "os.getenv('FEED_MAP', DEFAULT_MAP)", "os.getenv('FEED_MAP', DEFAULT_MAP)")
edit(F, "def symbols():", '''def rest_reason(sym, now=None):
    """'' = download it; else why the bot is resting this market (only while a BTC market is listed, like the weekend rule in risk.py)."""
    if not risk.crypto_open(): return ''
    if risk.weekend_skip(sym, now): return 'weekend'
    if risk.weekday_skip(sym, now): return 'weekdays'
    return ''

def symbols():''', "def rest_reason")
edit(F, "    for sym in symbols():\n        try:\n            m15 = fetch(", '''    for sym in symbols():
        why = rest_reason(sym, now)
        if why:
            with _lock: STATUS['sym'].setdefault(sym, {}).update(err='', rest=why)
            continue
        try:
            m15 = fetch(''', "why = rest_reason")
