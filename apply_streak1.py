"""Losing-streak pause: request to continue + admin review. Patches backend/risk.py, backend/app.py, static/index.html.
New files (made separately): backend/streakreq.py, static/streak_ui.js. Each old text must appear exactly once or NOTHING more is changed. Safe to run twice. Run from the repo folder."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')

R = 'backend/risk.py'
edit(R, "def global_gate(now=None, uid='', burst=False):",
'''def streak_state(uid='', now=None):
    """None, or the losing-streak pause that is on now: {'k', 'until', 'pnls' (the k last setup results), 'since' (when the last loss closed)}.
    Only setups closed AFTER the admin's approval (kv 'streakok:<uid>', see streakreq.py) count, so an approval starts the count again."""
    now = now or time.time(); k = limits.streak(uid)
    if k <= 0: return None
    try: ok_at = int(float(st.get('streakok:' + uid) or 0))
    except (TypeError, ValueError): ok_at = 0
    last = _setups(st.q("SELECT pnl,closed,grp FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? AND closed>? ORDER BY closed DESC LIMIT ?", (uid, ok_at, k * 12)))[:k]
    until = last[0]['closed'] + st.fget('streak_cooldown_h') * 3600 if last else 0
    if len(last) == k and all(x['pnl'] < 0 for x in last) and now < until: return {'k': k, 'until': until, 'pnls': [x['pnl'] for x in last], 'since': last[0]['closed']}
    return None

def global_gate(now=None, uid='', burst=False):''', 'def streak_state')
edit(R, """    k = limits.streak(uid)
    last = _setups(st.q("SELECT pnl,closed,grp FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? ORDER BY closed DESC LIMIT ?", (uid, k * 12)))[:k]
    if k > 0 and len(last) == k and all(x['pnl'] < 0 for x in last) and now - last[0]['closed'] < st.fget('streak_cooldown_h') * 3600:
        return False, f'{k} losses in a row: cooling down'
""", """    s = streak_state(uid, now)          # streakreq.py: an admin approval restarts the count
    if s: return False, f"{s['k']} losses in a row: cooling down"
""", "s = streak_state(uid, now)")

A = 'backend/app.py'
edit(A, "stake, envcheck, presets", "stake, envcheck, presets, streakreq", "presets, streakreq")
edit(A, "@app.get('/api/live/why')          # LIVE2",
'''@app.get('/api/streak')
@need(verified=True)
def streak_get(u): return jsonify(streakreq.status(_mine(u)))          # the person's losing-streak pause and their request (backend/streakreq.py)

@app.post('/api/streak/request')
@need(verified=True)
def streak_ask(u):
    try: out = streakreq.request(_mine(u))
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path})
    return jsonify(out)

@app.get('/api/admin/streak')
@need(admin=True)
def streak_list(u): return jsonify(streakreq.listing())

@app.post('/api/admin/streak')
@need(admin=True)
def streak_decide(u):
    j = _j()
    if not isinstance(j.get('uid'), str) or not isinstance(j.get('approve'), bool): return jsonify(error='Send uid and approve (true or false)'), 400
    try: out = streakreq.decide(j['uid'], j['approve'], j.get('note', ''))
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'] or 'owner', 'setting', data={'path': request.path, 'approve': j['approve'], 'for': j['uid']})
    return jsonify(out)

@app.get('/api/live/why')          # LIVE2''', "def streak_get")

H = 'static/index.html'
edit(H, '<script src="/static/prefs_ui.js"></script>', '<script src="/static/prefs_ui.js"></script><script src="/static/streak_ui.js"></script>', 'streak_ui.js')
