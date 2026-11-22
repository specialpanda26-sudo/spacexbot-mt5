"""GL1 patch: the group LOSS limit now works on Deriv. Until now groupcap's loss_pct was saved with every group but only the MT5 bridge used it,
so on Deriv a losing group just waited for each entry's own stop loss.
  - deriv.py: when the first entry of a group really opens, the account balance from just BEFORE the buy is saved with the group (kv 'bg:<grp>', 'bal0').
  - deriv_group.py: each round, if (profit already booked + live profit of the open entries) is at or below minus (loss_pct x bal0 / 100), every open entry is sold at market
    (closedby 'basket', one alert 'group stopped at its loss limit'). A loss never starts the next group. A group with no recorded balance is left alone (nothing is guessed).
  - static/index.html: the group card now says who closes the group on each platform.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo root: python apply_gl1_deriv_loss.py"""
import sys
G, V, H, D = 'backend/deriv_group.py', 'backend/deriv.py', 'static/index.html', 'docs/HANDOFF.md'
HELP = '''def note_open_balance(grp, bal):
    """GL1: save the account balance from just BEFORE this group's first entry was bought (kv 'bg:<grp>', 'bal0'). The group loss limit is a percent of it. Saved once.
    -> True when saved, False when the group is unknown, the balance is not a positive number, or it was saved before."""
    m = _meta(grp); b = _f(bal)
    if not m or not b or b <= 0 or _f(m.get('bal0')): return False
    m['bal0'] = round(b, 2); st.put('bg:%d' % int(grp), json.dumps(m)); return True


def loss_limit(m):
    """GL1: the group loss in USD at which the group is stopped (loss percent x the saved balance / 100), or 0 when there is no limit or no saved balance."""
    lp = _f((m or {}).get('loss')) or 0; b0 = _f((m or {}).get('bal0')) or 0
    return round(b0 * lp / 100.0, 2) if lp > 0 and b0 > 0 else 0.0


def check(sess, uid, acct, now=None):'''
GR = [
 ("def check(sess, uid, acct, now=None):", HELP),
 ("  2. total >= target  ->  sell every open member at market (closedby 'basket'), one alert for the whole group.",
  "  2. total >= target  ->  sell every open member at market (closedby 'basket'), one alert for the whole group.\n  2b. GL1: total <= minus the group loss limit (loss percent of the balance saved when the group opened)  ->  the same sale; a loss never starts the next group."),
 ("        if tgt <= 0: continue\n", "        lim = loss_limit(m)\n        if tgt <= 0 and lim <= 0: continue\n"),
 ("        if round(booked + live, 2) < tgt: continue\n",
  "        tot = round(booked + live, 2); hit_t = tgt > 0 and tot >= tgt; hit_l = lim > 0 and tot <= -lim\n        if not (hit_t or hit_l): continue\n"),
 ("sbauth.notify('%s group closed' % opn[0]['symbol'], 'Total P/L %s' % total, key='grp%d-closed' % g, only=uid or None)",
  "sbauth.notify('%s group %s' % (opn[0]['symbol'], 'stopped at its loss limit' if hit_l and not hit_t else 'closed'), 'Total P/L %s' % total, key='grp%d-closed' % g, only=uid or None)"),
 ("if not fail and total > 0 and (m or {}).get('k') == 'multi': nxt =", "if not fail and total > 0 and not (hit_l and not hit_t) and (m or {}).get('k') == 'multi': nxt ="),
]
DV = [("        _report(uid, s['id'], 'open')\n    else:",
       "        _report(uid, s['id'], 'open')\n        try:          # GL1: the group loss limit is a percent of the balance from before this group's first buy\n            if s['grp']:\n                from . import deriv_group; deriv_group.note_open_balance(s['grp'], bal)\n        except Exception as e: print('[deriv] group balance note failed', repr(e)[:80])\n    else:")]
UI = [("The MT5 bridge closes the group; phone-only mode only sends signals.",
       "On MT5 the bridge closes the group. On Deriv the server closes the group (the loss limit is measured against the balance from before the first entry of the group was bought; a group opened before this update has none saved, so its loss limit is not applied). Phone-only mode only sends signals.")]
def patch(path, pairs, mark):
    s = open(path, encoding='utf-8').read()
    if mark in s: print(path, 'already patched'); return
    for o, n in pairs:
        if s.count(o) != 1: sys.exit('STOP: anchor found %d times in %s: %s' % (s.count(o), path, o[:70]))
    for o, n in pairs: s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s); print('patched', path)
patch(G, GR, 'def note_open_balance')
patch(V, DV, 'note_open_balance(s')
patch(H, UI, 'On Deriv the server closes the group')
MARK = '## Section GL1 (group loss limit on Deriv)'; h = open(D, encoding='utf-8').read()
if MARK in h: print('HANDOFF already has GL1')
else:
    open(D, 'a', encoding='utf-8').write('\n\n' + MARK + ''' DONE (Nov 24)
- Was open: groupcap loss_pct was MT5-only. Now Deriv too. deriv._trade_one saves the balance from BEFORE the first buy of a group (bg:<grp> bal0, once). deriv_group.check sells every open entry at market (closedby basket, alert "group stopped at its loss limit") when booked + live profit <= minus (loss_pct x bal0 / 100). A loss never starts the next group (cycle). Profit target unchanged; both may be set.
- A group with no saved balance (opened before this update, or not through Deriv) is left alone: the limit is not guessed. Deriv multiplier contracts keep their own stop loss as before.
- Card text on the Bot tab now says who closes the group on each platform. Binance still has no group close.
- Nothing was tried against the real Deriv API (sell message and the profit fields are the same assumptions as CY2): run tools/deriv_probe.py first. Tests: tests/test_gl1.py.
''')
    print('HANDOFF updated')
