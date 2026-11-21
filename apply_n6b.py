import os, sys
def edit(path, old, new, marker):
    s = open(path).read()
    if marker in s: print('skip (already there):', path, marker); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path); sys.exit(1)
    tmp = path + '.new'; open(tmp, 'w').write(s.replace(old, new)); os.replace(tmp, path); print('edited', path)
# check every anchor first, so nothing changes if one does not fit
need = [('backend/push.py', 'BYPASS_KINDS = {27} '), ('backend/system_alerts.py', 'def register():'), ('backend/app.py', "    return _link_edit(u, lambda: links.set_mode(u['uid'], m))"),
        ('backend/app.py', "    bk.set_mode(u['uid'], n, m); bk.set_why(u['uid'], n, 'bot off')"), ('backend/app.py', "    return _assist_do(u, lambda: assist.save(u['uid'], on, j.get('balance'), j.get('risk')))")]
done = all(m in open(p).read() for p, m in [('backend/push.py', '{27, 30, 31}'), ('backend/system_alerts.py', 'def switched('), ('backend/app.py', 'system_alerts.monitor(')])
if not done:
    for p, a in need:
        if open(p).read().count(a) != 1: print('STOP: cannot find exactly once in', p, a); sys.exit(1)
edit('backend/push.py', 'BYPASS_KINDS = {27} ', 'BYPASS_KINDS = {27, 30, 31} ', '{27, 30, 31}')
edit('backend/system_alerts.py', 'def register():', '''def switched(uid, old, new):
    """31: the person switched Demo <-> Real. Goes to that person only. It confirms their own tap, so quiet hours do not hold it (push.BYPASS_KINDS)."""
    old = old or 'demo'
    if new in ('demo', 'real') and new != old: push.notify_user(uid, 31, 'a31-%s-%d' % (uid, int(time.time() * 1000)), acct=new.capitalize())

def monitor(uid, on):
    """30: the person turned Phone (monitor) mode on or off. Goes to that person only; also confirms their own tap."""
    push.notify_user(uid, 30, 'm30-%s-%d' % (uid, int(time.time() * 1000)), on=bool(on))

def register():''', 'def switched(')
edit('backend/app.py', "    return _link_edit(u, lambda: links.set_mode(u['uid'], m))",
     "    was = links.view(u['uid']).get('mode'); r = _link_edit(u, lambda: links.set_mode(u['uid'], m))\n    if not isinstance(r, tuple): system_alerts.switched(u['uid'], was, m)          # N6b: kind 31\n    return r", 'system_alerts.switched(u')
edit('backend/app.py', "    bk.set_mode(u['uid'], n, m); bk.set_why(u['uid'], n, 'bot off')",
     "    was = bk.mode(u['uid'], n); bk.set_mode(u['uid'], n, m); bk.set_why(u['uid'], n, 'bot off'); system_alerts.switched(u['uid'], was, m)          # N6b: kind 31", 'was = bk.mode(')
edit('backend/app.py', "    return _assist_do(u, lambda: assist.save(u['uid'], on, j.get('balance'), j.get('risk')))",
     "    was = assist.is_on(u['uid']); r = _assist_do(u, lambda: assist.save(u['uid'], on, j.get('balance'), j.get('risk')))\n    if on is not None and on != was and not isinstance(r, tuple): system_alerts.monitor(u['uid'], on)          # N6b: kind 30\n    return r", 'system_alerts.monitor(')
NOTE = '''
## Section N6b (monitor mode and account type, kinds 30-31) DONE (Nov 22)
- backend/system_alerts.py got switched(uid, old, new) = 31 and monitor(uid, on) = 30; app.py calls them AFTER the change succeeded: /api/link/mode (MT5 Demo/Real), /api/brokers/<name>/mode (Deriv Demo/Real) and /api/assist/settings (Phone mode on/off). The gates and the save functions were NOT edited.
- 'Monitor mode' = Phone mode (the bot finds signals and waits for the person). Only a real change sends (on to on, or demo to demo, says nothing). Goes to that person only. push.BYPASS_KINDS is now {27, 30, 31}: they confirm the person's own tap, so quiet hours and the daily cap do not hold them; the person's own System switch still does.
- tests/test_n6b.py (fake FCM, the real routes). NOT tested: a real phone.
- Next: N6c (reports 32-37), N6d (nudges 45-49), N6e (security 50).
'''
p = 'docs/HANDOFF.md'; s = open(p).read()
if 'Section N6b (monitor' in s: print('skip (already there):', p)
else:
    tmp = p + '.new'; open(tmp, 'w').write(s.rstrip('\n') + '\n' + NOTE); os.replace(tmp, p); print('edited', p)
