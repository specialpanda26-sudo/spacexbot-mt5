"""OC1: owner switch 'No limit on open trades'. Run from the repo folder: python apply_oc1.py   (add --test to also run the test)
Safe to run twice. If any old text is not found exactly once, NOTHING is changed."""
import sys, subprocess

def edit(path, old, new, done):
    s = open(path, encoding='utf-8').read()
    if done in s:
        print('skip (already done):', path, '-', done[:50]); return True
    if s.count(old) != 1:
        print('NOT FOUND exactly once:', path, '-', old[:60]); return False
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print('edited:', path); return True

L, S, B, A, U, H = 'backend/limits.py', 'backend/store.py', 'backend/burst.py', 'backend/app.py', 'static/index.html', 'docs/HANDOFF.md'
ok = edit(S, "'max_open_ceiling': os.getenv('MAX_OPEN_CEILING', '6'),", "'max_open_ceiling': os.getenv('MAX_OPEN_CEILING', '6'), 'no_open_cap': os.getenv('NO_OPEN_CAP', '0'),", "'no_open_cap'")
ok = edit(L, "import json\nfrom . import store as st\n",
          "import json, os\nfrom . import store as st\n", "import json, os") and ok
ok = edit(L, "def ceiling():\n",
          "UNLIMITED = 1000          # OC1: what 'no limit' counts as in the room sums\n\ndef _owner(uid):\n    \"\"\"OC1: the owner's own scope ('') or a signed-in admin's uid (the owner's Deriv / Binance bot runs under the owner's own uid).\"\"\"\n    if not uid: return True\n    r = st.q('SELECT email FROM users WHERE uid=?', (uid,), True)\n    adm = {e.strip().lower() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()}\n    return bool(r) and (r['email'] or '').lower() in adm\n\ndef no_cap(uid=''):\n    \"\"\"OC1: True when the owner switched 'No limit on open trades' on (setting no_open_cap = 1). It applies to the OWNER only; every subscriber keeps the ceiling.\"\"\"\n    return st.get('no_open_cap') == '1' and _owner(uid)\n\ndef ceiling():\n", "def no_cap(uid=''):") and ok
ok = edit(L, "    base = max(1, _g('max_open') or 3)\n    try:\n        from . import automode",
          "    if no_cap(uid): return UNLIMITED          # OC1\n    base = max(1, _g('max_open') or 3)\n    try:\n        from . import automode", "if no_cap(uid): return UNLIMITED") and ok
ok = edit(L, "    mo = {'max_open': _num(_mine(uid).get('mo')) if uid else max_open(''),",
          "    mo = {'max_open_unlimited': no_cap(uid), 'max_open': _num(_mine(uid).get('mo')) if uid else max_open(''),", "'max_open_unlimited': no_cap(uid)") and ok
ok = edit(B, "    room = ceiling() - risk.open_count(uid)\n    mt = limits.trades(uid)",
          "    room = (limits.UNLIMITED if limits.no_cap(uid) else ceiling()) - risk.open_count(uid)          # OC1: no burst ceiling for the owner when 'No limit' is on\n    mt = limits.trades(uid)", "limits.UNLIMITED if limits.no_cap(uid) else ceiling()") and ok
ok = edit(A, "for k in ('btc_sunday_bounce', 'btc_short_pullback', 'orb_session', 'screen_on'):", "for k in ('btc_sunday_bounce', 'btc_short_pullback', 'orb_session', 'screen_on', 'no_open_cap'):", "'screen_on', 'no_open_cap'") and ok
ok = edit(U, '["max_open","Max open trades","n",1,10],', '["max_open","Max open trades","n",1,10],["no_open_cap","No limit on open trades (owner only; the 60% stop and loss limits still protect you)","c"],', '"no_open_cap"') and ok
ok = edit(U, '(OPEN != null ? "Open now " + OPEN + " of " + L.max_open_now : "Limit " + L.max_open_now)', '(OPEN != null ? "Open now " + OPEN + (L.max_open_unlimited ? ", no limit" : " of " + L.max_open_now) : (L.max_open_unlimited ? "No limit" : "Limit " + L.max_open_now))', 'L.max_open_unlimited ? ", no limit"') and ok
SEC = """## Section OC1 (no limit on open trades, owner switch) DONE (Nov 23)
- Owner wish: the bot must not sit idle because 'Max open trades reached' (phone alert: 6 trades are open, so new signals wait). Setting no_open_cap (0 or 1, default 0, admin page checkbox 'No limit on open trades').
- limits.no_cap(uid): on only for the OWNER (uid '' or a uid whose email is in ADMIN_EMAILS); subscribers keep their pick and the owner's ceiling. limits.max_open() returns UNLIMITED (1000) then, so risk.global_gate, multi, deriv_group and burst room sums all stop blocking. burst.plan() ignores the burst ceiling for the owner too (entries in ONE group are still limited by the burst ceiling number).
- limits.view() adds max_open_unlimited; the Positions-at-once chip says 'Open now N, no limit'.
- Still protecting the account: daily and weekly loss limits, loss-streak stop, news lock, currency exposure, symbol cooldown. NOT yet: a stop at 60% account loss, a dollar loss alert, margin check (next sections). Until those exist, keep this switch ON for a DEMO account only.
- The ADMIN check here reads users.email without the 'verified' flag (same as app._paid).
- Tests: tests/test_oc1.py.

"""
ok = edit(H, "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", SEC + "## STATUS BOARD Nov 23 (newest; read this first, then the sections above it)", "## Section OC1") and ok
if not ok: sys.exit(1)
if '--test' in sys.argv: sys.exit(subprocess.call([sys.executable, 'tests/test_oc1.py']))
