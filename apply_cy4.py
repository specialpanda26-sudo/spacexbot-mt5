"""CY4 patch (MT5): wire backend/mt5_cycle.py into the EA routes in backend/app.py and add the HANDOFF section. Each old text must appear exactly once or NOTHING is
changed. Safe to run twice. Run from the repo root: python apply_cy4.py"""
import sys
F, H = 'backend/app.py', 'docs/HANDOFF.md'
A1 = "    st.set_acct(a, who)\n"
N1 = A1 + ("    try:          # CY4: a next group that had to wait for the account snapshot to catch up is tried again now\n"
           "        from . import mt5_cycle; mt5_cycle.retry(who)\n"
           "    except Exception as e: print('cycle retry failed', str(e)[:120])\n")
A2 = "        else: push.notify(9, f'sig{sid}-pending-{str(d.get(\"state\") or \"\")[:20]}', sym=sy, state=str(d.get('state') or '')[:20], **aud)\n"
N2 = A2 + ("    if stt == 'closed' and str(d.get('reason')) == 'basket':          # CY4: the last entry of a group the EA closed at its target may start the next group\n"
           "        try:\n"
           "            from . import mt5_cycle; mt5_cycle.after_close(who, sid, d.get('price'))\n"
           "        except Exception as e: print('cycle failed', str(e)[:120])\n")
W = 'backend/deriv_group.py'; w = open(W, encoding='utf-8').read()
if "'no price from Deriv'" in w:
    if w.count("'no price from Deriv'") != 1: sys.exit('STOP: wording found %d times in %s' % (w.count("'no price from Deriv'"), W))
    open(W, 'w', encoding='utf-8').write(w.replace("'no price from Deriv'", "'no current price'")); print('patched', W)
s = open(F, encoding='utf-8').read(); do1 = 'mt5_cycle.retry(who)' not in s; do2 = 'mt5_cycle.after_close(who' not in s
if do1 and s.count(A1) != 1: sys.exit('STOP: set_acct line found %d times in %s' % (s.count(A1), F))
if do2 and s.count(A2) != 1: sys.exit('STOP: pending push line found %d times in %s' % (s.count(A2), F))
if do1: s = s.replace(A1, N1)
if do2: s = s.replace(A2, N2)
if do1 or do2: open(F, 'w', encoding='utf-8').write(s); print('patched', F)
else: print(F, 'already patched')
MARK = '## Section CY4 (auto-cycle on MT5)'; h = open(H, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has CY4')
else:
    open(H, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 22)
- backend/mt5_cycle.py + two small calls in app.py. NO change to ea/SpaceXBridge.mq5: the EA already closes a group at its target and reports each entry as closed with reason 'basket', its closing price and gpnl. /api/ea/report: for a 'basket' close, after_close() checks it was the last open entry of a 'multi' group with a group target, the entries total a profit, the cycle is on and MT5 is the chosen platform; then deriv_group.reopen() queues the next group (same rules and gates as Deriv: same size, symbol, side, stop/target distances around the closing price, daily limit). kv cyc_done:<grp> (atomic insert) means one group starts one successor, even if two reports arrive together.
- /api/ea/sync calls retry(): the snapshot the EA sent last may still show the old positions open, so 'max open positions' / 'not enough room' is tried again on the next polls for up to 90 s (kv cyc_retry:<uid>); any other refusal ends it. The new group goes out as a normal basket in that same poll.
- A loss-limit close has a negative total, a stop loss or manual close reports another reason: neither starts the next group.
- Needs an EA that sends the closing price (Section 4). Without it the note says 'no current price' (deriv_group wording made generic by this patch).
- NOT built: Binance. backend/binance_bot.py has no groups at all (single spot trades), so there is no group to close or repeat. Needs a decision from the owner first: should the Binance bot open several entries as one group?
- Not tried with a real MT5. Run on a DEMO account first: a group with 2-3 entries and a small group target, watch the Journal.
- Tests: tests/test_cy4.py.
''')
    print('HANDOFF updated')
