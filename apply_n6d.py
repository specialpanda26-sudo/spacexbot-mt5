import os, sys
def edit(path, old, new, marker):
    s = open(path).read()
    if marker in s: print('skip (already there):', path, marker); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path); sys.exit(1)
    tmp = path + '.new'; open(tmp, 'w').write(s.replace(old, new)); os.replace(tmp, path); print('edited', path)
IMP = 'from . import risk_alerts, system_alerts, report_alerts, lag,'
HOOK = "    sc = _mine(u); a = st.acct(sc); online = time.time() - a.get('seen', 0) < 120\n    out = {'uid': u['uid']"
REG = 'report_alerts.register(); alerts.start()'
s = open('backend/app.py').read()
if 'nudge_alerts.register()' not in s:
    for a in (IMP, HOOK, REG):
        if s.count(a) != 1: print('STOP: cannot find exactly once in backend/app.py:', a[:60]); sys.exit(1)
edit('backend/app.py', IMP, 'from . import risk_alerts, system_alerts, report_alerts, nudge_alerts, lag,', 'report_alerts, nudge_alerts')
edit('backend/app.py', HOOK, "    nudge_alerts.seen(u['uid'], bool(u.get('verified')))          # N6d: kind 45\n" + HOOK, 'nudge_alerts.seen(')
edit('backend/app.py', REG, 'report_alerts.register(); nudge_alerts.register(); alerts.start()', 'nudge_alerts.register()')
NOTE = '''
## Section N6d (setup nudges, kinds 45-49) DONE (Nov 22)
- New backend/nudge_alerts.py + tests/test_n6d.py (37 checks, fake FCM, mutation-checked). One job on the ONE loop (nudge_alerts.register(), called in app.py before alerts.start()), every 30 min, only between 09:00 and 20:00 EAT. app.py /api/me also calls nudge_alerts.seen() (kind 45 only).
- ONCE EVER per person per step (push_log key n<kind>-<uid>); push.allowed already limits nudges to ONE a day, so a person with two open steps gets the second the next day. Admins get none. Category 'tips' (the person's Tips switch applies).
- 45 verify email: the server does NOT store 'verified' (it lives only in the sign-in token), so /api/me records people who are in the app unverified (in memory, lost on restart): unverified 2 h and seen in the app within the last hour. 46 connect broker: has a plan, 1 day after sign-up, no MT5 key, no saved broker (Deriv) and Phone mode off. 47 set risk: an MT5 key made 1+ day ago with no risk saved. 48 choose alerts: alerts never saved (notif empty) 2 days after the first phone registered. 49 finish profile: username, phone or country missing, 3 days after sign-up.
- Tunables are the constants at the top of nudge_alerts.py (assumptions). NOT tested: a real phone, real FCM.
- Next: N6e (security 50), 35 once decided.
'''
p = 'docs/HANDOFF.md'; s = open(p).read()
if 'Section N6d (setup' in s: print('skip (already there):', p)
else:
    tmp = p + '.new'; open(tmp, 'w').write(s.rstrip('\n') + '\n' + NOTE); os.replace(tmp, p); print('edited', p)
