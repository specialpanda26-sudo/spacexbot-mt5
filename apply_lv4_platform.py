"""LV4 patch: the live numbers (Home card, Bot tab strip, 'Bot running' phone notification) now come from the ONE platform the bot is set to trade on
(tradeon: MT5 / Deriv / Binance), with that account's own balance (demo or real). Before, balance and equity were the SUM of every connected account, the open
trades and 'today' counted every platform, Binance was missing, and a Binance-only bot never counted as running.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_lv4_platform.py"""
import sys
L, V, H = 'backend/livestats.py', 'backend/live.py', 'docs/HANDOFF.md'
def edit(path, pairs, done):
    s = open(path, encoding='utf-8').read()
    if done in s: print(path, 'already patched'); return
    for a, _ in pairs:
        if s.count(a) != 1: sys.exit('STOP: text found %d times in %s: %r' % (s.count(a), path, a[:70]))
    for a, b in pairs: s = s.replace(a, b)
    open(path, 'w', encoding='utf-8').write(s); print('patched', path)

edit(L, [
 ("from . import store as st, links, brokers as bk, strategy_info as si, pnlreset as pr\n",
  "from . import store as st, links, brokers as bk, strategy_info as si, pnlreset as pr, tradeon\n"),
 ("def sources(uid, admin, now):\n    out = []\n    for b in bk.view(uid):\n        if b.get('name') != 'Deriv': continue\n",
  "def sources(uid, admin, now):\n    out = []\n    for b in bk.view(uid):\n        if b.get('name') not in ('Deriv', 'Binance'): continue          # LV4: Binance (testnet balance) is a source too\n"),
 ("        out.append({'id': 'Deriv', 'name': 'Deriv', 'mode'", "        out.append({'id': b['name'], 'name': b['name'], 'mode'"),
 ("def snapshot(uid, admin=False, now=None):\n    now = now or time.time(); src = sources(uid, admin, now); sc = ('' if admin else uid, uid)\n",
  "def _scope_sql(ch):\n    \"\"\"LV4: which signal rows belong to the chosen platform. MT5 rows are marked 'MT5' (older ones are empty); Deriv and Binance rows carry their own name.\"\"\"\n"
  "    if not ch: return ''\n    return \" AND (COALESCE(broker,'')='MT5' OR COALESCE(broker,'')='')\" if ch == 'MT5' else \" AND COALESCE(broker,'')='%s'\" % ch\n\n\n"
  "def snapshot(uid, admin=False, now=None):\n    now = now or time.time(); src = sources(uid, admin, now); sc = ('' if admin else uid, uid)\n"
  "    ch = tradeon.get(uid)          # LV4: the platform the bot is set to trade on; nothing chosen = the old behaviour (every connected account)\n"
  "    if ch: src = [s for s in src if s['id'] == ch]\n    bq = _scope_sql(ch)\n"),
 ("AND pnl IS NOT NULL AND COALESCE(uid,'') IN (?,?)\", (pr.since(uid)", "AND pnl IS NOT NULL AND COALESCE(uid,'') IN (?,?)\" + bq, (pr.since(uid)"),
 ("n_sig = (st.q(\"SELECT COUNT(*) n FROM signals WHERE status='open' AND COALESCE(uid,'') IN (?,?)\", sc, True)", "n_sig = (st.q(\"SELECT COUNT(*) n FROM signals WHERE status='open' AND COALESCE(uid,'') IN (?,?)\" + bq, sc, True)"),
 ("FROM signals WHERE status='open' AND COALESCE(uid,'') IN (?,?) ORDER BY id DESC LIMIT %d\" % MAX_TRADES, sc)", "FROM signals WHERE status='open' AND COALESCE(uid,'') IN (?,?)\" + bq + \" ORDER BY id DESC LIMIT %d\" % MAX_TRADES, sc)"),
 ("    return {'state': state, 'mode':", "    return {'platform': ch, 'state': state, 'mode':"),
], "LV4")
edit(V, [
 ("        if s['id'] == 'MT5' and links.bot_on('' if admin else uid): return True\n",
  "        if s['id'] == 'MT5' and links.bot_on('' if admin else uid): return True\n        if s['id'] == 'Binance':          # LV4\n            from . import binance_bot\n            if binance_bot._bot(uid): return True\n"),
 ("    a = {'balance': ls['balance'], 'equity': ls['equity'], 'open': ls['open']} if srcs else {}\n",
  "    a = {'balance': ls['balance'], 'equity': ls['equity'], 'open': ls['open'], 'label': ' (%s %s)' % (srcs[0]['id'], srcs[0]['mode']) if ls.get('platform') and len(srcs) == 1 else ''} if srcs else {}\n"),
 ("lines.append('Balance ' + _m(bal) + ('   Equity '", "lines.append('Balance ' + _m(bal) + (a.get('label') or '') + ('   Equity '"),
], "LV4: Binance")
MARK = '## Section LV4 (live numbers follow the chosen platform)'; h = open(H, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has LV4')
else:
    open(H, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 23)
- Found: livestats.snapshot() ADDED UP balance and equity of every connected account (Deriv + MT5), counted open trades and today's profit of every platform, had no Binance source, and live._running() never counted Binance. So the phone notification could show a mixed or stale number that matched no single account.
- Now: when a platform is chosen (tradeon), balance, equity, mode (demo/real), open trades, open count and today come from THAT platform only (signals.broker; MT5 rows may have an empty broker). The notification shows the label, e.g. 'Balance $1,000.50 (Deriv demo)'. Nothing chosen = the old behaviour. Binance balance = testnet free USDT + cost of open positions; no floating figure (equity = balance).
- Not changed: where MT5's numbers come from (the EA's last report, owner's scope ''). If the EA stopped, the card says stale after 2 minutes, but the notification is only sent while an account is online.
- Tests: tests/test_lv4.py.
''')
    print('HANDOFF updated')
