import os, sys
p = 'requirements.txt'; s = open(p).read()
if 'tzdata' in s: print('skip (already there):', p); sys.exit(0)
tmp = p + '.new'; open(tmp, 'w').write(s.rstrip('\n') + '\ntzdata>=2024.1\n'); os.replace(tmp, p); print('edited', p)
d = 'docs/HANDOFF.md'; h = open(d).read()
note = '\n## Time zones (Nov 22)\n- requirements.txt now has tzdata. market_alerts.py (Tokyo/London/New York session alerts) uses zoneinfo, which needs a time zone database; Termux (and possibly Render) has none, so the job failed with "No time zone found with key Asia/Tokyo". tzdata is a free pip package that brings its own database. On Termux run: pip install tzdata\n'
if 'Time zones (Nov 22)' not in h:
    t = d + '.new'; open(t, 'w').write(h.rstrip('\n') + '\n' + note); os.replace(t, d); print('edited', d)
