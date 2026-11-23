"""MC1: owner switch 'I close the profits myself'. Run from the repo folder: python apply_mc1.py   (add --test to also run the test)
Needs backend/manual_close.py (written first). Safe to run twice. If any old text is not found exactly once, NOTHING is changed."""
import sys, subprocess

def edit(path, old, new, done):
    s = open(path, encoding='utf-8').read()
    if done in s:
        print('skip (already done):', path, '-', done[:50]); return True
    if s.count(old) != 1:
        print('NOT FOUND exactly once:', path, '-', old[:60]); return False
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print('edited:', path); return True

S, A, D, G, U, H = 'backend/store.py', 'backend/app.py', 'backend/deriv.py', 'backend/deriv_group.py', 'static/index.html', 'docs/HANDOFF.md'
ok = edit(S, "'no_open_cap': os.getenv('NO_OPEN_CAP', '0'),", "'no_open_cap': os.getenv('NO_OPEN_CAP', '0'), 'manual_close': os.getenv('MANUAL_CLOSE', '0'),", "'manual_close'")
ok = edit(A, "from . import burst_scope, btc_switch,", "from . import manual_close, burst_scope, btc_switch,", "from . import manual_close, burst_scope") and ok
ok = edit(A, "    bk = burst.basket(s, who) if s else None          # a burst group goes out ALL AT ONCE as one basket (the old way would send one entry per poll)\n",
          "    bk = burst.basket(s, who) if s else None          # a burst group goes out ALL AT ONCE as one basket (the old way would send one entry per poll)\n    if bk and manual_close.on(who): bk.update(tgt=manual_close.FAR, gb=0, tp=manual_close.far_tp(bk['side'], bk['sl'], bk['tp']))          # MC1: the owner closes the profits\n", "bk.update(tgt=manual_close.FAR") and ok
ok = edit(A, "    if s: s = dict(s); s['stake_pct'] = stake.pct(s['id']); s['stake_max_risk_pct'] = stake.max_risk()",
          "    if s and manual_close.on(who): s = dict(s, tp=manual_close.far_tp(s['side'], s['sl'], s['tp']))          # MC1\n    if s: s = dict(s); s['stake_pct'] = stake.pct(s['id']); s['stake_max_risk_pct'] = stake.max_risk()", "if s and manual_close.on(who): s = dict(s, tp=") and ok
ok = edit(A, "'screen_on', 'no_open_cap'):", "'screen_on', 'no_open_cap', 'manual_close'):", "'no_open_cap', 'manual_close'") and ok
ok = edit(D, "    from . import stake as stk\n", "    from . import stake as stk, manual_close\n", "from . import stake as stk, manual_close") and ok
ok = edit(D, "'multiplier': m, 'limit_order': {'stop_loss': slm, 'take_profit': tpm}})", "'multiplier': m, 'limit_order': ({'stop_loss': slm} if manual_close.on_sig(sig) else {'stop_loss': slm, 'take_profit': tpm})})          # MC1: no take profit when the owner closes the profits", "manual_close.on_sig(sig)") and ok
ok = edit(G, "from . import store as st, cycle, groupcap, risk, multi, links, limits, learn, sbauth, push, burst_live", "from . import store as st, cycle, groupcap, risk, multi, links, limits, learn, sbauth, push, burst_live, manual_close", "burst_live, manual_close") and ok
ok = edit(G, "        if tgt <= 0 and lim <= 0: continue\n", "        manual = manual_close.on(uid)          # MC1: the owner closes the profits: no sale at the target, the live profit is still read\n        if manual: tgt = 0\n        if tgt <= 0 and lim <= 0 and not manual: continue\n", "manual = manual_close.on(uid)") and ok
ok = edit(U, '["no_open_cap","No limit on open trades (owner only; the 60% stop and loss limits still protect you)","c"],', '["no_open_cap","No limit on open trades (owner only; the 60% stop and loss limits still protect you)","c"],["manual_close","I close the profits myself (owner only; the bot never banks a profit. Switch OFF when you are away)","c"],', '"manual_close"') and ok
SEC = """## Section MC1 (owner closes the profits himself) DONE (Nov 23)
- Owner wish: an optional switch so that WINNING trades are closed only by him. Setting manual_close (0 or 1, default 0, admin page checkbox 'I close the profits myself'). Owner only (limits._owner): subscribers are never touched.
- When ON: MT5 single signals get a far take-profit (manual_close.far_tp, 20 x the stop-to-target distance beyond the target; the stored plan keeps the real target); an MT5 burst basket gets tgt 1e9 and give-back 0 (the EA closes a basket at its target or on give-back, so both are switched off WITHOUT a new EA build) and a far take-profit; the Deriv order has no take_profit; deriv_group.check does not sell a group at its target but still reads and saves its live profit.
- NOT touched (loss side): stop loss, the group loss limit, daily and weekly limits, streak stop. With the switch ON, nobody banks a profit except the owner: switch it OFF when away.
- Not built: a phone alert 'your group reached its old target, close it' (needs a new push kind); MT5 baskets already open when the switch is flipped keep the old target (their target lives in the EA).
- Tests: tests/test_mc1.py.

"""
ok = edit(H, "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", SEC + "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", "## Section MC1") and ok
if not ok: sys.exit(1)
if '--test' in sys.argv: sys.exit(subprocess.call([sys.executable, 'tests/test_mc1.py']))
