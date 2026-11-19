"""Pay fix 5: ask FinoQ for an uncompressed answer and keep the gateway's own words when the answer is not JSON.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
import os, sys, subprocess

P = 'backend/payments.py'; T = 'tests/test_all.py'
EDITS = [
 (P, "    return {'Authorization': 'Basic ' + t, 'Content-Type': 'application/json'}\n",
     "    return {'Authorization': 'Basic ' + t, 'Content-Type': 'application/json', 'Accept-Encoding': 'identity'}\n"),
 (P, "def cb_secret(): return _env('PAYHERO_CALLBACK_SECRET', 'CALLBACK_SECRET')\n",
     "def cb_secret(): return _env('PAYHERO_CALLBACK_SECRET', 'CALLBACK_SECRET')\n"
     "def _post(url, body):\n"
     "    \"\"\"POST to FinoQ -> (response, dict). A non-JSON answer is kept as {'raw': first 150 chars} so the admin log shows it.\"\"\"\n"
     "    r = requests.post(url, json=body, headers=_head(), timeout=25)\n"
     "    try: j = r.json() if r.content else {}\n"
     "    except ValueError: j = {'raw': r.text[:150]}\n"
     "    return r, (j if isinstance(j, dict) else {'raw': str(j)[:150]})\n"),
 (P, "        r = requests.post(base() + '/api/v2/payments', json=body, headers=_head(), timeout=25)\n        j = r.json() if r.content else {}\n",
     "        r, j = _post(base() + '/api/v2/payments', body)\n"),
]

def main():
    files = {}
    for f, old, new in EDITS:
        if f not in files:
            if not os.path.exists(f): print('STOP: missing', f, '(run from the repo folder)'); return 1
            files[f] = open(f, encoding='utf-8').read()
    done = 0
    for i, (f, old, new) in enumerate(EDITS, 1):
        c = files[f].count(old)
        if files[f].count(new) >= 1 and (c == 0 or new.count(old) >= 1): pass
        elif c == 1: files[f] = files[f].replace(old, new); done += 1
        else: print('STOP: edit %d does not fit %s (found %d times). Nothing changed.' % (i, f, c)); return 1
    for f, txt in files.items():
        with open(f + '.new', 'w', encoding='utf-8') as h: h.write(txt)
    for f in files: os.replace(f + '.new', f)
    print('edits applied: %d of %d (the rest were already there)' % (done, len(EDITS)))
    r = subprocess.run([sys.executable, T], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print('\n'.join(l for l in out if l.startswith('FAIL')) or '(no failing test)')
    print(out[-1] if out else 'no test output'); print('RESULT:', 'OK' if r.returncode == 0 else 'TESTS FAILED')
    return r.returncode

sys.exit(main())
