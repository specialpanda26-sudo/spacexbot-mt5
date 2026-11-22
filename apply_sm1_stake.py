"""SM1 patch: Deriv small stakes, said in plain words. Deriv documents multipliers as starting from 1 USD, and the Burst card's 'Stake per entry' defaults to 0.5 USD.
Before: a normal entry whose stake worked out under 1 USD was dropped with the wrong reason ('no multiplier fits this balance and stop distance'), and a burst stake under 1
was sent to Deriv once per multiplier and refused with Deriv's own wording. Now the rejection names the real cause and the setting to change, and the Burst card label says
Deriv needs 1 or more. Nothing is blocked that worked before: a burst stake under 1 is still sent (Deriv decides), because the minimum can differ by market.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_sm1_stake.py"""
import sys
D, X, H = 'backend/deriv.py', 'static/index.html', 'docs/HANDOFF.md'
def edit(path, pairs, done):
    s = open(path, encoding='utf-8').read()
    if done in s: print(path, 'already patched'); return
    for a, _ in pairs:
        if s.count(a) != 1: sys.exit('STOP: text found %d times in %s: %r' % (s.count(a), path, a[:70]))
    for a, b in pairs: s = s.replace(a, b)
    open(path, 'w', encoding='utf-8').write(s); print('patched', path)

HELP = '''def _low_stake(sig, bal, want, m):
    """SM1: about what the stake would be, when that is under 1 USD (Deriv multipliers start at 1 USD). None when it is 1 or more or cannot be worked out."""
    try: entry, sl, bal, m = float(sig['entry']), float(sig['sl']), float(bal), float(m)
    except (TypeError, ValueError): return None
    if not entry or entry == sl or bal <= 0 or m <= 0: return None
    try: raw = bal * float(want) / 100.0 if want else bal * float(sig['risk_pct'] or 1) / 100.0 / (m * abs(entry - sl) / entry)
    except (TypeError, ValueError, ZeroDivisionError): return None
    return round(raw, 2) if 0 < raw < 1 else None

def _place(sess, sig, bal, cur):'''
edit(D, [
 ("def _place(sess, sig, bal, cur):", HELP),
 ("    return 'rejected', last\n",
  "    if last == 'no multiplier fits this balance and stop distance' and order:          # SM1: say the real cause when the stake was simply under Deriv's 1 USD minimum\n"
  "        low = _low_stake(sig, bal, want, min(order))\n"
  "        if low is not None: last = 'Stake would be about %s USD; Deriv multipliers need at least 1 USD. Raise the risk percent or add funds.' % low\n"
  "    elif bs and bs < 1 and any(w in last.lower() for w in ('stake', 'minimum', 'at least')): last = 'Burst stake %s USD is under the 1 USD Deriv multipliers need. Raise Stake per entry.' % bs\n"
  "    return 'rejected', last\n"),
], "_low_stake")
edit(X, [('<label for="bswStake">Stake per entry ($)</label>', '<label for="bswStake">Stake per entry ($, Deriv needs 1 or more)</label>')], 'Deriv needs 1 or more')
MARK = '## Section SM1 (Deriv small stakes)'; h = open(H, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has SM1')
else:
    open(H, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 23)
- Deriv's own pages say multipliers start from 1 USD (one Deriv blog says the minimum runs 0.35 to 1 USD by market). The Burst card's 'Stake per entry' DEFAULTS to 0.5 USD (burst.py DEF stake_usd), so burst entries on forex, gold and crypto are likely refused until the stake is 1 or more. NOT proven on the real API: tools/deriv_probe.py must run first.
- deriv._place: a normal entry whose stake would be under 1 USD is now rejected as 'Stake would be about X USD; Deriv multipliers need at least 1 USD. Raise the risk percent or add funds.' (was the wrong 'no multiplier fits ...'). A burst stake under 1 is still SENT (Deriv decides, minimum can differ by market); if Deriv refuses it for the stake, the note says 'Burst stake X USD is under the 1 USD Deriv multipliers need. Raise Stake per entry.'
- Burst card label: 'Stake per entry ($, Deriv needs 1 or more)'. The default is left at 0.5 on purpose (a saved setting must not change by itself): raise it to 1 on Deriv.
- MT5 is unaffected: risk percent sets the lot size there, and the burst Stake per entry is not used. Binance has its own sizing (binance_trade.plan_buy refuses an order under Binance's minimum with its own message).
- Tests: tests/test_sm1.py.
''')
    print('HANDOFF updated')
