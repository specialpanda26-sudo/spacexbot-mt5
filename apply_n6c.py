import os, sys
def edit(path, old, new, marker):
    s = open(path).read()
    if marker in s: print('skip (already there):', path, marker); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path); sys.exit(1)
    tmp = path + '.new'; open(tmp, 'w').write(s.replace(old, new)); os.replace(tmp, path); print('edited', path)
s = open('backend/app.py').read()
if 'report_alerts.register()' not in s:
    for a in ('from . import risk_alerts, system_alerts, lag,', 'system_alerts.register(); alerts.start()'):
        if s.count(a) != 1: print('STOP: cannot find exactly once in backend/app.py', a); sys.exit(1)
edit('backend/app.py', 'from . import risk_alerts, system_alerts, lag,', 'from . import risk_alerts, system_alerts, report_alerts, lag,', 'system_alerts, report_alerts')
edit('backend/app.py', 'system_alerts.register(); alerts.start()', 'system_alerts.register(); report_alerts.register(); alerts.start()', 'report_alerts.register()')
NOTE = '''
## Section N6c (report alerts, kinds 32, 33, 34, 36, 37) DONE (Nov 22)
- New backend/report_alerts.py + tests/test_n6c.py (29 checks, fake FCM, real closed trades, mutation-checked). Two jobs on the ONE loop (report_alerts.register(), called in app.py before alerts.start()). Numbers come from journal._closed (the same list the Journal uses); admins read the owner scope. Times are EAT.
- 32 daily summary: in the first hour from 21:00 EAT, only when the person closed 1+ trades that day. 37 review your trades: sent with it only on a day with 2+ losses AND a net loss. 33 weekly report: Sunday 21:00 EAT, last 7 days, only with trades. 34 monthly report: the 1st at 09:00 EAT for the month that ended, only with trades. 36 winning streak: exactly 3, 5 or 10 wins in a row, newest win less than 2 h old (job every 10 min). Audience: every person with a phone and a plan, plus admins. Category 'daily' (quiet hours, daily cap and the person's Daily switch apply).
- 35 (brain learned something) is NOT built: nothing in the code produces weekly lessons yet. Needs a decision on what to report.
- Tunables are the constants at the top of report_alerts.py (DAILY_HOUR, WEEKLY_WEEKDAY, MONTHLY_*, WINDOW_H, STREAKS, STREAK_FRESH, REVIEW_MIN_LOSSES). They are assumptions. The report only goes out if the server is awake in its one-hour window (free Render sleeps: ping /healthz).
- NOT tested: a real phone, real FCM.
- Next: N6d (nudges 45-49), N6e (security 50), 35 once decided.
'''
p = 'docs/HANDOFF.md'; s = open(p).read()
if 'Section N6c (report' in s: print('skip (already there):', p)
else:
    tmp = p + '.new'; open(tmp, 'w').write(s.rstrip('\n') + '\n' + NOTE); os.replace(tmp, p); print('edited', p)
