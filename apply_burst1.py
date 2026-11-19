"""Burst mode, Section 1 (server engine). backend/burst.py and tests/test_burst1.py are written just before this by the same command.
Wires: risk.global_gate(burst=True) and risk.symbol_gate(cool=False), the owner settings burst_enabled / burst_ceiling / burst_big_score,
and two routes (GET/POST /api/burst). Each old text must be found exactly once or NOTHING is changed. Safe to run twice."""
import sys, os

ROUTE = """@app.get('/api/burst')
@need(verified=True)
def burst_get(u): return jsonify(burst.view(_mine(u)))

@app.post('/api/burst')
@need(verified=True)
def burst_set(u):
    j = _j()
    try: out = burst.save(_mine(u), j)
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in burst.KEYS}})
    return jsonify(burst.view(_mine(u)))

"""
EDITS = [
 ('backend/risk.py', "def global_gate(now=None, uid=''):", "def global_gate(now=None, uid='', burst=False):", "uid='', burst=False"),
 ('backend/risk.py', "    if open_count(uid, a) >= limits.max_open(uid): return False, 'max open positions'",
  "    if not burst and open_count(uid, a) >= limits.max_open(uid): return False, 'max open positions'          # burst mode has its own ceiling (burst.py)", 'if not burst and open_count'),
 ('backend/risk.py', "def symbol_gate(sym, side, now=None, uid=''):", "def symbol_gate(sym, side, now=None, uid='', cool=True):", "uid='', cool=True"),
 ('backend/risk.py', "    if last and now - last['created'] < st.fget('cooldown_min') * 60: return False, 'symbol cooldown'",
  "    if cool and last and now - last['created'] < st.fget('cooldown_min') * 60: return False, 'symbol cooldown'", 'if cool and last'),
 ('backend/store.py', "'regime_min_trades': os.getenv('REGIME_MIN_TRADES', '10'), 'plans': ''}",
  "'regime_min_trades': os.getenv('REGIME_MIN_TRADES', '10'), 'burst_enabled': os.getenv('BURST_ENABLED', '1'), 'burst_ceiling': os.getenv('BURST_CEILING', '15'), 'burst_big_score': os.getenv('BURST_BIG_SCORE', '3'), 'plans': ''}", "'burst_enabled'"),
 ('backend/app.py', 'from . import lag, multi, automarkets, prefs, scale\n', 'from . import lag, multi, automarkets, prefs, scale, burst\n', 'prefs, scale, burst\n'),
 ('backend/app.py', "@app.post('/api/admin/testprice')", ROUTE + "@app.post('/api/admin/testprice')", 'def burst_get('),
]
if not os.path.isdir('backend') or not os.path.isdir('static'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
if not os.path.exists('backend/burst.py'): print('STOP: backend/burst.py is missing'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
