"""Weekend rule per market (owner, Nov 21): gold and forex stay blocked on Saturday, Sunday and Friday after 20:00 UTC, but a BTC market is let through
(crypto trades 24/7). Every other gate (bot on, EA online, loss limits, max open, news, cooldown, exposure, Real mode) still applies to BTC.
 - backend/risk.py: weekend_shut(), is_crypto(), crypto_open(), weekend_skip(); global_gate asks crypto_open() instead of always shutting at the weekend.
 - backend/app.py: the normal scan and the burst scan skip a non-crypto market at the weekend (the gate alone no longer does that when a BTC market is listed). The extra check runs only when crypto_open() is true, so with no BTC market listed nothing changes.
Setting crypto_weekend = 0 puts the old rule back for everything. Only markets listed in the Symbols setting count. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
R = 'backend/risk.py'; A = 'backend/app.py'
FUNCS = '''CRYPTO = ('BTCUSD',)          # markets that never close (prefix match, so BTCUSDm, BTCUSD.a, BTCUSDT count too)

def weekend_shut(now=None):
    """Saturday, Sunday, or Friday from 20:00 UTC: gold and forex are closed or too risky."""
    d = dt.datetime.utcfromtimestamp(now or time.time()); return d.weekday() >= 5 or (d.weekday() == 4 and d.hour >= 20)

def is_crypto(sym): return str(sym or '').strip().upper().startswith(CRYPTO)

def crypto_open():
    """Weekend exemption: on unless the owner sets crypto_weekend to 0, and only while a crypto market is in the Symbols setting."""
    return st.get('crypto_weekend') != '0' and any(is_crypto(x) for x in (st.get('symbols') or '').split(','))

def weekend_skip(sym, now=None):
    """True = do not trade this market now because of the weekend rule (every market except crypto when the exemption is on)."""
    return weekend_shut(now) and not (st.get('crypto_weekend') != '0' and is_crypto(sym))

def global_gate(now=None, uid='', burst=False):
'''
edit(R, "def global_gate(now=None, uid='', burst=False):\n", FUNCS, 'def weekend_shut(')
edit(R, "    if d.weekday() >= 5 or (d.weekday() == 4 and d.hour >= 20): return False, 'weekend/Friday-night risk'\n",
        "    if weekend_shut(now) and not crypto_open(): return False, 'weekend/Friday-night risk'          # a BTC market in Symbols keeps the bot looking; other markets are skipped per market (weekend_skip)\n",
        'weekend_shut(now) and not crypto_open()')
edit(A, "    ok, why = risk.global_gate(uid=uid)\n    if not ok: botstate.note(uid, sym, 'gate', why); return\n",
        "    ok, why = risk.global_gate(uid=uid)\n    if ok and risk.crypto_open() and risk.weekend_skip(sym): ok, why = False, 'weekend/Friday-night risk'          # the gate passed only because a BTC market is listed: gold and forex still wait\n    if not ok: botstate.note(uid, sym, 'gate', why); return\n",
        'if ok and risk.crypto_open() and risk.weekend_skip(sym)')
edit(A, "    ok, why = burst.look(uid)\n    if not ok: return\n",
        "    ok, why = burst.look(uid)\n    if not ok or (risk.crypto_open() and risk.weekend_skip(sym)): return\n",
        'if not ok or (risk.crypto_open() and risk.weekend_skip(sym))')
