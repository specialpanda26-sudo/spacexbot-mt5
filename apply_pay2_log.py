"""Pay fix 2: a payments log for the owner. Every attempt keeps the gateway's own words (refusal code and text, callback status and code,
provider and network used) in kv 'paylog:<ref>' and the owner reads them at /api/admin/payments. The customer-facing 'reason' is untouched.
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
import os, sys, subprocess

P = 'backend/payments.py'; A = 'backend/app.py'
EDITS = [
 (P, "def _new(uid, provider, pid, amount, cur, phone=''):\n",
     "def note(ref, text):\n"
     "    \"\"\"Owner-only detail for one attempt (never shown to the customer).\"\"\"\n"
     "    try: st.put('paylog:' + ref, str(text)[:400])\n"
     "    except Exception as e: print('paylog failed', e)\n\n"
     "def _new(uid, provider, pid, amount, cur, phone=''):\n"),
 (P, "        _mark(ref, 'failed', 'not_sent'); raise RuntimeError('Could not reach the payment gateway') from e\n",
     "        note(ref, 'no answer from gateway: %s | provider=%s network=%s' % (str(e)[:150], prov, body.get('network_code', '-')))\n"
     "        _mark(ref, 'failed', 'not_sent'); raise RuntimeError('Could not reach the payment gateway') from e\n"),
 (P, "        print('finoq refused', r.status_code, str(j)[:300]); _mark(ref, 'failed', 'not_sent'); raise RuntimeError('Could not send the M-Pesa prompt. Try again.')\n",
     "        print('finoq refused', r.status_code, str(j)[:300])\n"
     "        note(ref, 'gateway refused %s: %s | provider=%s network=%s' % (r.status_code, str(j)[:220], prov, body.get('network_code', '-')))\n"
     "        _mark(ref, 'failed', 'not_sent'); raise RuntimeError('Could not send the M-Pesa prompt. Try again.')\n"),
 (P, "    if prov_ref: st.x(\"UPDATE payments SET checkout_id=? WHERE ref=? AND status='pending'\", (prov_ref, ref))\n    return ref\n",
     "    if prov_ref: st.x(\"UPDATE payments SET checkout_id=? WHERE ref=? AND status='pending'\", (prov_ref, ref))\n"
     "    note(ref, 'prompt accepted by gateway | provider=%s network=%s' % (prov, body.get('network_code', '-')))\n    return ref\n"),
 (P, "            st.x(\"UPDATE payments SET status='underpaid',receipt=? WHERE ref=? AND status IN('pending','expired')\", (cb['receipt'] or None, p['ref'])); return 'underpaid'\n",
     "            note(p['ref'], 'underpaid: gateway says %s, price is %s' % (cb['amount'], p['amount']))\n"
     "            st.x(\"UPDATE payments SET status='underpaid',receipt=? WHERE ref=? AND status IN('pending','expired')\", (cb['receipt'] or None, p['ref'])); return 'underpaid'\n"),
 (P, "        _mark(p['ref'], 'failed', FAIL_REASON.get(cb['code'], 'other')); return 'failed'\n",
     "        note(p['ref'], 'callback: status=%s code=%s' % (cb['status'], cb['code'])); _mark(p['ref'], 'failed', FAIL_REASON.get(cb['code'], 'other')); return 'failed'\n"),
 (A, "@app.get('/api/plans')\ndef plans(): return jsonify(pay.plans())\n",
     "@app.get('/api/admin/payments')\n@need(admin=True)\ndef admin_payments(u):\n"
     "    \"\"\"Owner: the last 50 payment attempts with status and the gateway's own words, so a failing number can be explained.\"\"\"\n"
     "    mask = lambda s: (s[:4] + '***' + s[-2:]) if s and len(s) > 6 else (s or '')\n"
     "    rows = st.q('SELECT ref,uid,provider,plan,amount,status,created,extra,phone FROM payments ORDER BY created DESC LIMIT 50')\n"
     "    return jsonify(payments=[{'ref': r['ref'], 'uid': r['uid'], 'provider': r['provider'], 'plan': r['plan'], 'amount': r['amount'], 'status': r['status'],\n"
     "                              'created': r['created'], 'reason': r['extra'], 'phone': mask(r.get('phone') or ''), 'detail': st.get('paylog:' + r['ref']) or ''} for r in rows])\n\n"
     "@app.get('/api/plans')\ndef plans(): return jsonify(pay.plans())\n"),
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
    r = subprocess.run([sys.executable, 'tests/test_all.py'], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    print('\n'.join(l for l in out if l.startswith('FAIL')) or '(no failing test)')
    print(out[-1] if out else 'no test output'); print('RESULT:', 'OK' if r.returncode == 0 else 'TESTS FAILED')
    return r.returncode

sys.exit(main())
