"""BT9: the owner's burst card uses the owner's own uid when Deriv or Binance is chosen. Run from the repo folder: python apply_bt9.py   (add --test to also run the test)
Safe to run twice. If any old text is not found exactly once, NOTHING is changed."""
import sys, subprocess

def edit(path, old, new, done):
    s = open(path, encoding='utf-8').read()
    if done in s:
        print('skip (already done):', path, '-', done[:50]); return True
    if s.count(old) != 1:
        print('NOT FOUND exactly once:', path, '-', old[:60]); return False
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print('edited:', path); return True

A, H = 'backend/app.py', 'docs/HANDOFF.md'
ok = edit(A, "from . import btc_switch, tradeon, course,", "from . import burst_scope, btc_switch, tradeon, course,", "from . import burst_scope, btc_switch")
ok = edit(A, "def burst_get(u): return jsonify(burst.view(_mine(u)))", "def burst_get(u): return jsonify(burst.view(burst_scope.scope(u)))          # BT9", "burst.view(burst_scope.scope(u)))") and ok
ok = edit(A, "    try: out = burst.save(_mine(u), j)\n    except ValueError as e: return jsonify(error=str(e)), 400\n    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in burst.KEYS}})\n    return jsonify(burst.view(_mine(u)))",
              "    sc = burst_scope.scope(u)          # BT9\n    try: out = burst.save(sc, j)\n    except ValueError as e: return jsonify(error=str(e)), 400\n    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in burst.KEYS}})\n    return jsonify(burst.view(sc))",
              "sc = burst_scope.scope(u)          # BT9") and ok
SEC = """## Section BT9 (burst card for the owner on Deriv) DONE (Nov 23)
- Found (owner on a phone, Deriv chosen, burst never opened anything): the app saved the OWNER's burst settings under scope '' (the owner's PC EA has no uid) but the owner's Deriv bot scans under the owner's own uid, so burst was 'off' where the scan looks. The card also judged the bot by the EA switch ('The bot is stopped. Tap Start bot.') while Deriv was running, and live burst numbers were not shown. Non-owners were never affected.
- backend/burst_scope.py: scope(u) = the owner's own uid when Deriv or Binance is chosen on Trade on; '' for the owner on MT5 or with nothing chosen; the uid for everyone else. The first time, settings already saved under '' are copied once to the uid (never over settings already there). GET and POST /api/burst use it.
- After the deploy the owner sees the same switches as before (copied). Other owner cards (group target and loss, limits, strategies) still use scope '': NOT checked, not changed here.
- Tests: tests/test_bt9.py.

"""
ok = edit(H, "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", SEC + "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", "## Section BT9") and ok
if not ok: sys.exit(1)
if '--test' in sys.argv: sys.exit(subprocess.call([sys.executable, 'tests/test_bt9.py']))
