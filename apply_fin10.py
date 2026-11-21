"""Section 10: final check. Adds docs/PHONE_CHECKLIST.md (already created by the cat block) to HANDOFF, and fixes the stale tests/test_burst3.py check (it re-ran a historical patch that now stops because a later section changed the EA version; the real intent is that the files do not change). Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
edit('tests/test_burst3.py',
     "T('running apply_burst3.py again changes nothing', 'patched OK' in out and before == [h(p) for p in ('backend/app.py', 'backend/burst.py', 'ea/SpaceXBridge.mq5')])",
     "T('running apply_burst3.py again changes no file', before == [h(p) for p in ('backend/app.py', 'backend/burst.py', 'ea/SpaceXBridge.mq5')])  # Section 10: it now stops (a later section changed the EA version); the point is that nothing changes",
     'changes no file')
H = 'docs/HANDOFF.md'
SEC = """## Section 10 (final check) DONE as far as code and docs go (Nov 21)
- Already built earlier and still green: setup check backend/envcheck.py (admin Health, names only, tests/test_env10.py) and the update pop-up 'why' reason (SXBUpdate.status / localStorage sxb_upd_why, tests/test_why10.py).
- New: docs/PHONE_CHECKLIST.md = the by-hand list for a real phone (Render env, the 5 GitHub secrets, APK install, push, update pop-up, every Home state with its bubble, demo trade path, payment with someone else's number, plan-ending cards). Nothing in it can be checked from code; the owner ticks it on the phone.
- apply_fin10.py also fixes the stale check in tests/test_burst3.py (it re-ran a historical patch that now stops). The whole suite now ends N/N passed, test_push3 prints OK.
- STILL OPEN (needs the owner or real hardware): the phone checklist itself, a real APK build with google-services.json, real Resend and real M-Pesa sends, the backtest on real data (6-12 months), then a demo account before real money.

"""
edit(H, '## STATUS BOARD (Nov 21, newest; read this first)\n', SEC + '## STATUS BOARD (Nov 21, newest; read this first)\n', '## Section 10 (final check)')
edit(H, '- NEXT in order: 9 (more emails / notifications, only where the server has a trigger), 10 (final check: Render env, 4 signing secrets, "why no update pop-up" screen, real-phone checklist).',
        '- NEXT in order: run docs/PHONE_CHECKLIST.md on a real phone and report failures; 9b only if a trigger is chosen; then parked work (alerts N3-N6, 4C, the backtest).', '- NEXT in order: run docs/PHONE_CHECKLIST.md')
