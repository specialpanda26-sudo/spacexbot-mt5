import os, sys
def edit(path, old, new, marker):
    s = open(path).read()
    if marker in s: print('skip (already there):', path, marker); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path); sys.exit(1)
    tmp = path + '.new'; open(tmp, 'w').write(s.replace(old, new)); os.replace(tmp, path); print('edited', path)
E = [('backend/push.py', 'BYPASS_KINDS = {27, 30, 31}', 'BYPASS_KINDS = {27, 30, 31, 50}', '{27, 30, 31, 50}'),
 ('backend/app.py', 'from . import risk_alerts, system_alerts, report_alerts, nudge_alerts, lag,', 'from . import risk_alerts, system_alerts, report_alerts, nudge_alerts, security_alerts, lag,', 'nudge_alerts, security_alerts'),
 ('backend/app.py', "    if not u: return None\n    if not st.q('SELECT 1 FROM users WHERE uid=?', (u['uid'],), True):", "    if not u: return None\n    security_alerts.signin(u['uid'], u.get('last_sign_in'))          # N6e: kind 50\n    if not st.q('SELECT 1 FROM users WHERE uid=?', (u['uid'],), True):", 'security_alerts.signin('),
 ('backend/app.py', "def me_signout(u): return jsonify(ok=sbauth.revoke(u['uid']))", "def me_signout(u):\n    ok = sbauth.revoke(u['uid'])\n    if ok: security_alerts.notice(u['uid'], 'Your other devices were signed out')          # N6e\n    return jsonify(ok=ok)", "'Your other devices were signed out'"),
 ('backend/app.py', "    key = links.new_key(u['uid']); return jsonify(key=key, **links.view(u['uid']))      # the only time the key is shown", "    had = bool(links.get(u['uid'])); key = links.new_key(u['uid'])\n    security_alerts.notice(u['uid'], 'Your MT5 key was replaced' if had else 'An MT5 key was created')          # N6e (the notice never carries the key)\n    return jsonify(key=key, **links.view(u['uid']))      # the only time the key is shown", "'Your MT5 key was replaced'"),
 ('backend/app.py', "    if not u['admin']: links.drop(u['uid'])\n    return jsonify(ok=True)", "    if not u['admin']:\n        had = bool(links.get(u['uid'])); links.drop(u['uid'])\n        if had: security_alerts.notice(u['uid'], 'Your MT5 link was removed')          # N6e\n    return jsonify(ok=True)", "'Your MT5 link was removed'"),
 ('backend/app.py', "    except RuntimeError as e: return jsonify(error=str(e)), 503\n    return jsonify(brokers=bk.view(u['uid']))", "    except RuntimeError as e: return jsonify(error=str(e)), 503\n    security_alerts.notice(u['uid'], '%s was connected' % bk.canon(name))          # N6e\n    return jsonify(brokers=bk.view(u['uid']))", "was connected' % bk.canon"),
 ('backend/app.py', "    bk.drop(u['uid'], n); return jsonify(brokers=bk.view(u['uid']))", "    if bk.drop(u['uid'], n): security_alerts.notice(u['uid'], '%s was disconnected' % n)          # N6e\n    return jsonify(brokers=bk.view(u['uid']))", "was disconnected' % n"),
 ('backend/sbauth.py', "'verified': bool(d.get('email_confirmed_at') or d.get('confirmed_at'))}", "'verified': bool(d.get('email_confirmed_at') or d.get('confirmed_at')), 'last_sign_in': d.get('last_sign_in_at') or ''}", "'last_sign_in'"),
 ('tests/test_sbauth.py', "'name': 'Amy W', 'verified': True}", "'name': 'Amy W', 'verified': True, 'last_sign_in': ''}", "'last_sign_in': ''}"),
 ('tests/test_n6a.py', 'from backend import store as st, push, alerts, system_alerts as sa\n', 'from backend import store as st, push, alerts, system_alerts as sa\nalerts.stop()          # stop the background alert loop so it cannot race this test\n', 'alerts.stop()'),
 ('tests/test_n6b.py', 'from backend import store as st, push\n', 'from backend import store as st, push, alerts\nalerts.stop()          # stop the background alert loop so it cannot race this test\n', 'alerts.stop()'),
 ('tests/test_n6c.py', 'from backend import store as st, push, alerts, report_alerts as ra\n', 'from backend import store as st, push, alerts, report_alerts as ra\nalerts.stop()          # stop the background alert loop so it cannot race this test\n', 'alerts.stop()'),
 ('tests/test_n6d.py', 'from backend import store as st, push, alerts, nudge_alerts as na\n', 'from backend import store as st, push, alerts, nudge_alerts as na\nalerts.stop()          # stop the background alert loop so it cannot race this test\n', 'alerts.stop()')]
if not all(m in open(p).read() for p, o, n, m in E):
    for p, o, n, m in E:                       # check every anchor first: if one does not fit, nothing changes
        if m not in open(p).read() and open(p).read().count(o) != 1: print('STOP: cannot find exactly once in', p, '->', o[:70]); sys.exit(1)
for p, o, n, m in E: edit(p, o, n, m)
NOTE = '''
## Section N6e (security notice, kind 50) DONE (Nov 22)
- New backend/security_alerts.py + tests/test_n6e.py. No loop job: app.py calls security_alerts.notice() AFTER the thing succeeded. Goes to all of the person's OWN phones, only about their own account, never with a key or secret in it. Category 'system'; push.BYPASS_KINDS is now {27, 30, 31, 50}, so quiet hours and the daily cap do not hold it. The person's own System switch still silences it (their choice; to make security notices unsilenceable, change push.allowed).
- Sent for: MT5 key created or replaced (/api/link/key), MT5 link removed (DELETE /api/link, only if one existed), broker connected (POST /api/brokers/<name>) or disconnected (DELETE, only if one existed), 'sign out other devices', and a NEW SIGN-IN (sbauth.verify now returns last_sign_in from Supabase's last_sign_in_at; app.py user() passes it to signin(); the first stamp ever seen is only remembered; at most one sign-in notice per person per 6 h).
- NOT detectable: password change and email change. Supabase does them in the browser and does not tell this server. A real fix needs a Supabase Auth hook or webhook (free), not built.
- tests/test_sbauth.py compared verify() to an exact dict; it now expects the new last_sign_in field. The four earlier N6 tests (n6a-n6d) now call alerts.stop() after importing the app: the app starts its alert loop at import and its first pass runs every job on the real clock, which could rarely race a test (seen once as 23/25 and once as a failed n6c). Any NEW test that imports the app should do the same.
- NOT tested: real Supabase. The new-sign-in rule assumes last_sign_in_at changes on a sign-in and NOT on a token refresh. If people get a 'New sign-in' notice about once an hour, tell the next session: that assumption is wrong (the 6 h gap limits the damage).
- Next: kind 35 once decided. After N6, the alerts list is complete except 35.
'''
p = 'docs/HANDOFF.md'; s = open(p).read()
if 'Section N6e (security' in s: print('skip (already there):', p)
else:
    tmp = p + '.new'; open(tmp, 'w').write(s.rstrip('\n') + '\n' + NOTE); os.replace(tmp, p); print('edited', p)
