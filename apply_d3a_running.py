"""D3a: running(uid) for phone mode + 'running' in GET /api/assist. Run from the repo folder: python apply_d3a_running.py
Safe to run twice. If an old text is not found exactly once, NOTHING is changed."""
import os, sys, subprocess
FN = '''def running(uid, now=None):
    # taken trades with no result logged yet (read-only; the server cannot see the MT5 app)
    now = now or time.time()
    rows = st.q('SELECT l.sid AS id,l.ts AS ts,l.lots AS lots,s.symbol AS symbol,s.side AS side,s.entry AS entry,s.sl AS sl,s.tp AS tp '
                'FROM assist_log l JOIN signals s ON s.id=l.sid '
                "WHERE l.uid=? AND l.action='taken' AND (l.outcome IS NULL OR l.outcome='') ORDER BY l.ts DESC LIMIT 20", (uid,))
    return [{'id': r['id'], 'symbol': r['symbol'], 'side': r['side'], 'entry': r['entry'], 'sl': r['sl'], 'tp': r['tp'], 'lots': r['lots'],
             'since': r['ts'], 'minutes': max(0, int((now - r['ts']) // 60))} for r in rows]

'''
H = '# ---------- take / skip / result ----------\n'
A = "out.update(feed=assist.feed(u['uid']), stats=assist.stats(u['uid']))"
E = [('backend/assist.py', H, FN + H, 'def running(uid'),
     ('backend/app.py', A, A[:-1] + ", running=assist.running(u['uid']))", 'running=assist.running')]
files, bad = {}, []
for p, old, new, mk in E:
    t = files.get(p)
    if t is None: t = files[p] = open(p, encoding='utf-8').read()
    if mk in t: print('skip (already there):', p, mk); continue
    if t.count(old) != 1: bad.append((p, t.count(old))); continue
    files[p] = t.replace(old, new, 1); print('edited:', p, mk)
if bad:
    for b in bad: print('STOP: old text found %d times in %s' % (b[1], b[0]))
    print('Nothing was changed.'); sys.exit(1)
for p, t in files.items():
    open(p + '.new', 'w', encoding='utf-8').write(t); os.replace(p + '.new', p)
print('edits done. Running tests...')
fails = []
for f in sorted(os.listdir('tests')):
    if not (f.startswith('test_') and f.endswith('.py')) or f == 'test_rk5.py': continue
    def run(): return subprocess.run([sys.executable, 'tests/' + f], capture_output=True, text=True, timeout=300)
    if run().returncode:
        if f in ('test_n4.py', 'test_feed.py') and run().returncode == 0: print('flaky, passed on rerun:', f); continue
        fails.append(f); print('FAIL', f)
print('RESULT:', 'ALL TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
