import os, sys
def edit(path, old, new, marker):
    s = open(path).read()
    if marker in s: print('skip (already there):', path, marker); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path); sys.exit(1)
    tmp = path + '.new'; open(tmp, 'w').write(s.replace(old, new)); os.replace(tmp, path); print('edited', path)
edit('backend/app.py', 'from . import risk_alerts, lag,', 'from . import risk_alerts, system_alerts, lag,', 'risk_alerts, system_alerts')
edit('backend/app.py', 'risk_alerts.register(); alerts.start()', 'risk_alerts.register(); system_alerts.register(); alerts.start()', 'system_alerts.register()')
NOTE = '''
## Section N6a (system alerts, kinds 26-29) DONE (Nov 22)
- New backend/system_alerts.py + tests/test_n6a.py (25 checks, fake FCM, mutation-checked). Two jobs on the ONE loop (system_alerts.register(), called in app.py before alerts.start()).
- 26 MT5 connected (first time an EA heartbeat is seen), 27 MT5 offline (no heartbeat for 5 min; bypasses quiet hours), 28 back online. State per person in kv ea26:<scope> ('up' or 'down:<last heartbeat>'). The owner EA goes to ADMIN phones only; a subscriber's own EA goes to that subscriber only. A Deriv snapshot (src deriv) is not MT5 and sends nothing.
- 29 server updated: needs RENDER_GIT_COMMIT (Render sets it) or BUILD_ID; admins only; the first start only remembers (kv boot29); a wake-up on the same version says nothing.
- Tunables at the top: FRESH 120 s, OFFLINE_MIN 5. NOTE: the first deploy sends 26 once to the owner and to each person who already linked an EA.
- NOT DONE here: 30 (monitor mode) and 31 (account type) fire from a button press, they are Section N6b. Then N6c (daily/weekly/monthly reports 32-37), N6d (nudges 45-49), N6e (security 50).
- NOT tested: a real phone, real FCM.
'''
p = 'docs/HANDOFF.md'; s = open(p).read()
if 'Section N6a' in s: print('skip (already there):', p)
else:
    tmp = p + '.new'; open(tmp, 'w').write(s.rstrip('\n') + '\n' + NOTE); os.replace(tmp, p); print('edited', p)
