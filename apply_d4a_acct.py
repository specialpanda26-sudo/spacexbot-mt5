"""D4a: account tag (FBS / Deriv MT5) saved when a signal is taken. Run from the repo folder: python apply_d4a_acct.py
Safe to run twice. If an old text is not found exactly once, NOTHING is changed."""
import os, sys, subprocess
A, B = 'backend/assist.py', 'backend/app.py'
IDX = "    st.x('CREATE INDEX IF NOT EXISTS ix_assist_log_uid ON assist_log(uid,ts)')\n"
E = [
 (A, IDX, IDX + "    try: st.x('ALTER TABLE assist_log ADD COLUMN ' + ('IF NOT EXISTS ' if st.PG else '') + 'acct TEXT')\n    except Exception: pass     # the column is already there\n", 'ADD COLUMN'),
 (A, "def take(uid, sid, now=None):\n", "ACCTS = {'fbs': 'FBS', 'deriv mt5': 'Deriv MT5'}      # which MT5 account it was taken on (a label only)\n\ndef take(uid, sid, now=None, acct=None):\n    acct = ACCTS.get(str(acct or '').strip().lower())\n", 'ACCTS = {'),
 (A, "\"UPDATE assist_log SET action='taken',ts=?,lots=? WHERE uid=? AND sid=?\", (int(now), z.get('lots'), uid, sg['id'])",
     "\"UPDATE assist_log SET action='taken',ts=?,lots=?,acct=? WHERE uid=? AND sid=?\", (int(now), z.get('lots'), acct, uid, sg['id'])", 'lots=?,acct=?'),
 (A, "\"INSERT INTO assist_log(uid,sid,action,ts,lots) VALUES(?,?,'taken',?,?) ON CONFLICT(uid,sid) DO NOTHING\", (uid, sg['id'], int(now), z.get('lots'))",
     "\"INSERT INTO assist_log(uid,sid,action,ts,lots,acct) VALUES(?,?,'taken',?,?,?) ON CONFLICT(uid,sid) DO NOTHING\", (uid, sg['id'], int(now), z.get('lots'), acct)", 'ts,lots,acct)'),
 (A, "l.lots AS lots,s.symbol", "l.lots AS lots,l.acct AS acct,s.symbol", 'l.acct AS acct'),
 (A, "'since': r['ts'],", "'acct': r['acct'], 'since': r['ts'],", "'acct': r['acct']"),
 (B, "assist.take(u['uid'], _j().get('id'))", "assist.take(u['uid'], _j().get('id'), acct=_j().get('acct'))", "acct=_j().get('acct')"),
]
files, bad = {}, []
for p, old, new, mk in E:
    t = files.get(p)
    if t is None: t = files[p] = open(p, encoding='utf-8').read()
    if mk in t: print('skip (already there):', p, mk); continue
    if t.count(old) != 1: bad.append((p, old[:50], t.count(old))); continue
    files[p] = t.replace(old, new, 1); print('edited:', p, mk)
if bad:
    for b in bad: print('STOP: old text found %d times in %s -> %s' % (b[2], b[0], b[1]))
    print('Nothing was changed.'); sys.exit(1)
for p, t in files.items():
    open(p + '.new', 'w', encoding='utf-8').write(t); os.replace(p + '.new', p)
print('edits done. Running the assist-related tests...')
fl = ['tests/' + f for f in sorted(os.listdir('tests')) if f.startswith('test_') and f.endswith('.py') and 'assist' in open('tests/' + f, encoding='utf-8').read()]
fl += [x for x in ('tests/test_d3.py', 'tests/test_d3b.py', 'tests/test_d4.py') if x not in fl]
fails = []
for f in fl:
    ok = lambda: subprocess.run([sys.executable, f], capture_output=True, text=True, timeout=300).returncode == 0
    if not ok() and not ok(): fails.append(f); print('FAIL', f)
print('RESULT:', 'ALL RELATED TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
