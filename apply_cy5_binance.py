"""CY5 patch (Binance testnet): wire backend/binance_group.py into backend/binance_bot.py (group close + group loss limit + auto-cycle) and add the HANDOFF section.
Needs backend/binance_group.py to be in place first. Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_cy5_binance.py"""
import sys, os
F, H = 'backend/binance_bot.py', 'docs/HANDOFF.md'
if not os.path.exists('backend/binance_group.py'): sys.exit('STOP: backend/binance_group.py is missing; create it first')
A1 = "_track(uid, key, secret, http, now)          # always, even if the bot is off\n"
N1 = A1 + ("    try:          # CY5: close a whole group at its profit target or loss limit; after a profit (cycle on, bot allowed to trade) queue the next group\n"
           "        from . import binance_group\n"
           "        binance_group.check(uid, key, secret, http, now, bool(paid(uid)) and tradeon.get(uid) == 'Binance' and _bot(uid) and bk.mode(uid, 'Binance') != 'real')\n"
           "    except Exception as e: print('[binance_bot] group failed', type(e).__name__)\n")
A2 = "        _report(uid, s['id'], 'open')\n    elif 'may or may not' in str(out.get('msg')):"
N2 = ("        _report(uid, s['id'], 'open')\n"
      "        try:          # CY5: the group loss limit is a percent of the balance from before this group's first buy\n"
      "            if s['grp']:\n"
      "                from . import deriv_group; deriv_group.note_open_balance(s['grp'], bal)\n"
      "        except Exception as e: print('[binance_bot] group balance note failed', type(e).__name__)\n"
      "    elif 'may or may not' in str(out.get('msg')):")
s = open(F, encoding='utf-8').read(); do1 = 'binance_group.check' not in s; do2 = 'note_open_balance' not in s
if do1 and s.count(A1) != 1: sys.exit('STOP: _track call found %d times in %s' % (s.count(A1), F))
if do2 and s.count(A2) != 1: sys.exit('STOP: open-report line found %d times in %s' % (s.count(A2), F))
if do1: s = s.replace(A1, N1)
if do2: s = s.replace(A2, N2)
if do1 or do2: open(F, 'w', encoding='utf-8').write(s); print('patched', F)
else: print(F, 'already patched')
MARK = '## Section CY5 (group close, loss limit and auto-cycle on Binance)'; h = open(H, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has CY5')
else:
    open(H, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 23)
- backend/binance_group.py + two small hooks in backend/binance_bot.py. Binance spot (testnet, long-only) has no basket, so like Deriv the bot adds the legs of a group up itself: booked profit + live profit of the open legs (qty x price, minus an estimated 0.1% selling fee, minus cost). At the group target, or at the group loss limit (percent of the balance saved when the first leg was bought, kv bg:<grp> bal0), every open leg is sold at market and marked closedby 'basket'.
- Only after a PROFIT close, with the cycle on, a multi group and every leg sold, deriv_group.reopen() queues the next group (same size, same gates, same daily limit), and only when the bot may trade (plan active, Binance chosen, bot switch on, testnet). A loss-limit close or a failed sell never starts the next group.
- Waits instead of guessing: a group with a pending, 'sent' or 'closing' leg, or a leg whose price cannot be read, is skipped this round. A leg that cannot be sold stays open and is counted again next round. Each leg still has its own stop loss and take profit.
- Spot has no stop built in and the bot looks about once a minute, so a fast move can pass the target or the limit.
- Not tried against the real Binance testnet. Run it there first: a group of 2-3 entries and a small group target, watch the Journal.
- Tests: tests/test_cy5.py.
''')
    print('HANDOFF updated')
