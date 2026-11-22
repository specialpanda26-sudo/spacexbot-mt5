"""CY2 patch: wire backend/deriv_group.py into the Deriv round and add the HANDOFF section. Idempotent. STOPS if the text is not found exactly once.
Run from the repo root: python apply_cy2.py"""
import sys
P = 'backend/deriv.py'
OLD = "        except Exception as e: print('[deriv] track failed', repr(e)[:100])\n"
NEW = OLD + ("        try:          # CY2: close a whole group at its profit target, then (cycle on) queue the next group; the trade step below opens it\n"
             "            from . import deriv_group\n"
             "            if deriv_group.check(sess, uid, acct, now): _resnap(sess, uid, acct)\n"
             "        except ConnectionError: raise\n"
             "        except Exception as e: print('[deriv] group failed', repr(e)[:100])\n")
s = open(P).read()
if 'deriv_group.check(sess, uid, acct, now)' in s: print('deriv.py already patched')
else:
    if s.count(OLD) != 1: sys.exit('STOP: track line found %d times in %s' % (s.count(OLD), P))
    open(P, 'w').write(s.replace(OLD, NEW)); print('patched', P)
H = 'docs/HANDOFF.md'; MARK = '## Section CY2 (Deriv group close + auto-cycle engine)'
h = open(H).read()
if MARK in h: print('HANDOFF already has CY2')
else:
    open(H, 'a').write('''

''' + MARK + ''' DONE (Nov 22)
- backend/deriv_group.py + a 5-line call in deriv._run_once (after _track, before _trade). Each round: for every fully-open Deriv group with a group target (kv bg:<grp> 'tgt'), total = profit booked by members + live profit of open members (proposal_open_contract). total >= target -> sell every open member at market ({'sell': id, 'price': 0}), record each closed (closedby 'basket', pnl re-read from Deriv), one alert per group (key grp<id>-closed).
- Cycle: only when cycle.rules(uid, n) applies, the group is kind 'multi', every member sold and the final total > 0 -> queue the next group of the same size (same symbol, side, stop/target DISTANCES around current_spot), kv cyc_from:<new grp>. It must pass risk.global_gate, weekend_skip, weekday_skip, symbol_gate (cool=False: no cooldown, news lock + exposure still count) and have room for n entries. Max new groups a day = cycle.max_per_day (kv cyc:<uid>:<utc day>). Every refusal is saved in plain words: dg.why(uid) (kv cyc_why:<uid>), for the Bot tab card (CY3).
- Behaviour change: a Deriv group target now works even with the cycle OFF (before, groupcap was MT5-only and Deriv ignored it).
- Left alone on purpose: a pending/sent member makes the group wait; a member Deriv already sold is left to _track first; a refused sell leaves that entry open and never starts the next group; a burst group closes at its target but is never cycled.
- NOT done: group LOSS limit on Deriv (groupcap loss_pct is still MT5-only); the Bot tab card (CY3); MT5 EA and Binance (CY4). deriv._size still refuses stakes under 1 USD, so 0.1 USD entries are rejected on Deriv. Nothing was tried against the real Deriv API: the sell message and the fields profit / current_spot / is_sold are assumed from the code that already reads them; run tools/deriv_probe.py first.
- Tests: tests/test_cy2.py. Next: CY3 (card on the Bot tab: switch, new groups a day, why-not note from cycle.view + dg.why).
''')
    print('HANDOFF updated')
