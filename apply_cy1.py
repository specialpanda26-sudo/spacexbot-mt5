"""CY1: Auto-cycle choices (server side). OFF by default. Adds GET/POST /api/cycle and a HANDOFF note. Removes nothing. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
P = 'backend/app.py'
edit(P, 'burst, groupcap, authmail', 'burst, groupcap, cycle, authmail', 'groupcap, cycle, authmail')
edit(P, "    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in groupcap.KEYS}})\n    return jsonify(groupcap.view(_mine(u)))\n",
        "    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in groupcap.KEYS}})\n    return jsonify(groupcap.view(_mine(u)))\n\n"
        "@app.get('/api/cycle')          # CY1: Auto-cycle choices\n@need(verified=True)\ndef cycle_get(u): return jsonify(cycle.view(_mine(u)))\n\n"
        "@app.post('/api/cycle')\n@need(verified=True)\ndef cycle_set(u):\n    j = _j()\n    try: cycle.save(_mine(u), j)\n    except ValueError as e: return jsonify(error=str(e)), 400\n"
        "    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in cycle.KEYS}})\n    return jsonify(cycle.view(_mine(u)))\n", "def cycle_get(u)")
H = 'docs/HANDOFF.md'
s = open(H, encoding='utf-8').read()
if '## Section CY1' in s: print(H, ': already ok')
else:
    open(H, 'a', encoding='utf-8').write("""

## Section CY1 (Auto-cycle choices, server side) DONE (Nov 22)
- Owner wish: when a group of entries (e.g. 6 positions) reaches a profit target for the WHOLE group (e.g. 0.70 USD), close them all and open the next group straight away, without waiting for a new signal. A switch, OFF by default. Deriv first, then MT5 and Binance.
- backend/cycle.py: kv 'cycle:<uid>' {on, max_per_day 1..100, default 10}; get/save/rules(uid, n)/why_not/view. Builds on groupcap (group target USD) and prefs 'entries'. Active only when cycle on + group target on and > 0 + 2 or more entries.
- GET/POST /api/cycle (signed in + verified). tests/test_cycle1.py (28 checks).
- DESIGN for CY2 (decided, not built): only a group that closed at its PROFIT target starts the next one (never a stop loss, a loss limit or a manual close). The new group uses the same symbol, side and stop/target distances at the current price (Deriv: proposal_open_contract current_spot), still passes every risk gate, and stops for the day after max_per_day new groups. Deriv has NO group close today (groupcap is MT5-only). CY2 adds it: in deriv._track add up the open profit of a group, sell all members when the total reaches the target, record each as closed (closedby 'basket'), then queue the next group.
- NOT built yet: Deriv engine (CY2), Bot tab card (CY3), MT5 EA and Binance (CY4). deriv._size refuses stakes under 1 USD, so '0.1 USD per entry' cannot open on Deriv as the code stands.
""")
    print(H, ': appended')
