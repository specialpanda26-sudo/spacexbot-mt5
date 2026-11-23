"""Presets S4: GET/POST /api/presets (per person; the owner is refused) + a stricter tier check + 'demo' in the status.
Each old text must appear exactly once or NOTHING more is changed. Safe to run twice. Run from the repo folder."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')

P = 'backend/presets.py'; A = 'backend/app.py'; T = 'tests/test_presets.py'

# 1) presets.py: 20.5, True and the like are refused; the status says if the person is on demo
edit(P, "def _tier(n):\n    try: n = int(n)\n    except (TypeError, ValueError): n = 0\n",
     "def _tier(n):\n    \"\"\"10, 20 or 30 (a whole number, or the same number as text). Anything else, True and 20.5 included, is refused.\"\"\"\n    if isinstance(n, bool) or not isinstance(n, (int, float, str)): n = 0\n    try: f = float(n); n = int(f) if f == int(f) else 0\n    except (TypeError, ValueError, OverflowError): n = 0\n", 'def _tier(n):\n    """10, 20 or 30')
edit(P, "'not_included': NOT_INCLUDED, 'owner': bool(not uid or limits._owner(uid)),\n",
     "'not_included': NOT_INCLUDED, 'owner': bool(not uid or limits._owner(uid)),\n            'demo': bool(uid) and links.mode(uid) != 'real' and bk.mode(uid, 'Deriv') != 'real',\n", "'demo': bool(uid) and links.mode(uid)")

# 2) app.py: the two routes (same pattern as /api/prefs and /api/groupcap)
ROUTES = r'''@app.get('/api/presets')
@need(verified=True)
def presets_get(u): return jsonify(presets.status(_mine(u)))          # the owner gets owner=True and no tap (backend/presets.py)

@app.post('/api/presets')
@need(verified=True)
def presets_set(u):
    j = _j(); sc = _mine(u)
    if not isinstance(j, dict): return jsonify(error='Send the choice as an object'), 400
    try: out = presets.undo(sc) if j.get('undo') is True else presets.apply(sc, j.get('tier'))
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, 'preset': 'undo' if j.get('undo') is True else out['active']})
    return jsonify(out)

'''
edit(A, "@app.get('/api/live/why')", ROUTES + "@app.get('/api/live/why')", 'def presets_get')

# 3) tests
TESTS = r'''
# ---- S4: the routes ----
EA_, BO = H('amy@x.com'), H('boss@x.com')
sync(1000, GOLD); pre = raw(A); glb = {k: st.get(k) for k in ('max_trades_day', 'max_losing_streak', 'max_open', 'risk_pct', 'max_daily_loss_pct', 'max_open_ceiling')}
T('GET /api/presets needs sign-in', c.get('/api/presets').status_code == 401 and c.post('/api/presets', json={'tier': 10}).status_code == 401)
g = c.get('/api/presets', headers=EA_).get_json()
T('GET: the three tiers, nothing active, no undo, demo yes, owner no', set(g['tiers']) == {'10', '20', '30'} and g['active'] is None and g['can_undo'] is False and g['demo'] is True and g['owner'] is False and 'Drawdown stop' in g['not_included'])
T('GET: the worst-case dollars for each tier are there before anyone confirms', g['minlot']['20']['known'] and g['minlot']['20']['rows'][0]['worst_usd'] > 0)
r = c.post('/api/presets', json={'tier': 20}, headers=EA_); j = r.get_json()
T('POST tier 20: 200, active 20, undo possible', r.status_code == 200 and j['active'] == 20 and j['can_undo'] is True)
T('POST wrote through the real saves (entries 1, 3 strategies, burst off, one position)', prefs.get(A)['entries'] == 1 and len(prefs.get(A)['strategies']) == 3 and burst.get(A)['on'] is False and limits.max_open(A) == 1)
for bad in (15, 'x', True, 20.5, None, [20], {}, float('nan')):
    body = {'tier': bad} if bad != {} else {}
    rr = c.post('/api/presets', data=json.dumps(body, allow_nan=True), content_type='application/json', headers=EA_)
    T('bad tier refused (400) and still on 20: %r' % (bad,), rr.status_code == 400 and 'error' in rr.get_json() and presets.status(A)['active'] == 20)
T('a body that is not an object is refused', c.post('/api/presets', json=[20], headers=EA_).status_code == 400)
T('"30" as text works (same number)', c.post('/api/presets', json={'tier': '30'}, headers=EA_).get_json()['active'] == 30)
r = c.post('/api/presets', json={'undo': True}, headers=EA_)
T('POST undo: 200 and the exact old values are back', r.status_code == 200 and r.get_json()['active'] is None and raw(A) == pre)
T('undo again: 400 plain message', c.post('/api/presets', json={'undo': True}, headers=EA_).status_code == 400)
T('someone who never tapped (B) is untouched by all of this', raw(B) == before_b and presets._snap(B) is None)
ob = c.get('/api/presets', headers=BO).get_json()
T('owner GET: owner true, nothing to tap, no min-lot rows', ob['owner'] is True and ob['minlot'] == {} and ob['demo'] is False)
ro = c.post('/api/presets', json={'tier': 10}, headers=BO)
T('owner POST refused and no global setting moved', ro.status_code == 400 and glb == {k: st.get(k) for k in glb} and presets._snap('') is None)
st.x("UPDATE links SET mode='real' WHERE uid=?", (A,))
rr = c.post('/api/presets', json={'tier': 10}, headers=EA_)
T('Real mode: 400 "try demo first", nothing changes, GET says demo false', rr.status_code == 400 and 'demo' in rr.get_json()['error'].lower() and raw(A) == pre and c.get('/api/presets', headers=EA_).get_json()['demo'] is False)
st.x("UPDATE links SET mode='demo' WHERE uid=?", (A,))
sync(50, GOLD); rr = c.post('/api/presets', json={'tier': 10}, headers=EA_)
T('too-small balance: 400 with the plain balance message', rr.status_code == 400 and rr.get_json()['error'] == presets.WORDS and raw(A) == pre)
'''
edit(T, "\nn = len(R); bad = [x for x, ok in R if not ok]", TESTS + "\nn = len(R); bad = [x for x, ok in R if not ok]", 'S4: the routes')
