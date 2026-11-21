"""DB1: login / sign-up 'Something hiccuped' after the free server has been asleep.
(a) the database layer now throws away its saved connections and reconnects up to 3 times (it used to retry once on the next saved connection, which could be dead too),
(b) the error message now names the kind of error, e.g. 'Something hiccuped (OperationalError). Please try again.',
(c) /healthz now also wakes the database, so the free uptime ping keeps it warm, and it can never fail the health check,
(d) NEW /api/health/deep: open it in the phone browser, it says in plain words whether the database, sign-in (Supabase) and email (Resend) work.
Each old text must be found exactly once or NOTHING changes. Safe to run twice."""
import sys, os
EDITS = [
 ('backend/store.py',
  "def _retry(f):\n    def w(*a, **k):\n        if not PG: return f(*a, **k)\n        import psycopg2\n        try: return f(*a, **k)\n        except (psycopg2.OperationalError, psycopg2.InterfaceError): return f(*a, **k)\n    w.__name__ = f.__name__; return w\n",
  "def _drop_pool():\n    \"\"\"Throw every saved connection away. After the free server sleeps they are dead; the next call opens fresh ones.\"\"\"\n    global _pool\n    p = _pool; _pool = None\n    for c in list(getattr(p, '_pool', None) or []):\n        try: c.close()\n        except Exception: pass\n\ndef _retry(f):\n    def w(*a, **k):\n        if not PG: return f(*a, **k)\n        import psycopg2\n        for i in range(3):\n            try: return f(*a, **k)\n            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:\n                if i == 2: raise\n                print('db: connection lost, reconnecting', i + 1, repr(e)[:100]); _drop_pool(); time.sleep(0.4 * i)\n    w.__name__ = f.__name__; return w\n",
  'def _drop_pool'),
 ('backend/app.py',
  "return jsonify(error='Something hiccuped. Please try again.'), 500",
  "return jsonify(error='Something hiccuped (%s). Please try again.' % type(e).__name__), 500",
  "Something hiccuped (%s)"),
 ('backend/app.py',
  "@app.get('/healthz')\ndef hz(): return 'ok'\n",
  "@app.get('/healthz')\ndef hz():\n    try: st.q('SELECT 1')          # keeps the database connection warm; a failure here must never fail the health check\n    except Exception as e: print('healthz db:', repr(e)[:120])\n    return 'ok'\n\ndef _why(e):\n    \"\"\"A database error in plain words. Never the raw text (it can hold the database address or user).\"\"\"\n    s = str(e).lower()\n    for k, m in (('password authentication failed', 'the database password is wrong (DATABASE_URL)'), ('tenant or user not found', 'the database user or project was not found (DATABASE_URL), or the Supabase project is paused'),\n                 ('could not translate host', 'the database address is wrong (DATABASE_URL)'), ('timeout expired', 'the database did not answer in time (is the Supabase project paused?)'),\n                 ('timed out', 'the database did not answer in time (is the Supabase project paused?)'), ('ssl connection has been closed', 'the connection dropped while the server slept'),\n                 ('too many', 'too many database connections'), ('connection refused', 'the database refused the connection (is the Supabase project paused?)')):\n        if k in s: return m\n    return type(e).__name__\n\n@app.get('/api/health/deep')\ndef hz_deep():\n    \"\"\"Open this in the phone browser: it says in plain words which part is broken. No secrets, no names, only ok or a reason.\"\"\"\n    import requests\n    from . import mailer\n    out = {}\n    try: st.q('SELECT 1'); out['database'] = 'ok'\n    except Exception as e: out['database'] = _why(e)\n    if sbauth.configured():\n        try:\n            r = requests.get(sbauth._url() + '/auth/v1/health', headers={'apikey': sbauth._anon()}, timeout=6)\n            out['sign_in'] = 'ok' if r.status_code == 200 else 'Supabase answered %s (is the project paused?)' % r.status_code\n        except Exception as e: out['sign_in'] = 'cannot reach Supabase (%s)' % type(e).__name__\n    else: out['sign_in'] = 'not set up (SUPABASE_URL, SUPABASE_ANON_KEY)'\n    out['email'] = 'ok' if mailer.configured() else 'not set up (RESEND_API_KEY, MAIL_FROM)'\n    out['sign_up_mode'] = authmail.mode()\n    return jsonify(out)\n",
  'def hz_deep'),
]
if not os.path.isdir('backend') or not os.path.isdir('ea'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new[path] if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:70]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
