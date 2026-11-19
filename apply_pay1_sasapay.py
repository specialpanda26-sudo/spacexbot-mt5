"""Pay fix 1: (a) M-Pesa prompt always goes through SasaPay (the real prompt), never the plain 'm-pesa' channel that shows
another app's name; (b) a success whose payer-phone field differs from the typed number is still credited (ref + secret + amount are the proof).
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
import os, sys, subprocess

P = 'backend/payments.py'; E = '.env.example'; T = 'tests/test_all.py'
EDITS = [
 (P, "    prov = _env('PAYHERO_PROVIDER').lower(); prov = 'sasapay' if prov == 'sasapay' else 'm-pesa'\n",
     "    prov = _provider()\n"),
 (P, "def cb_secret(): return _env('PAYHERO_CALLBACK_SECRET', 'CALLBACK_SECRET')\n",
     "def cb_secret(): return _env('PAYHERO_CALLBACK_SECRET', 'CALLBACK_SECRET')\n"
     "def _provider():\n"
     "    \"\"\"SasaPay is the real prompt. Plain 'm-pesa' is used ONLY when PAYHERO_PROVIDER=m-pesa-direct (a channel that is a Paybill/Till).\"\"\"\n"
     "    return 'm-pesa' if _env('PAYHERO_PROVIDER').lower() in ('m-pesa-direct', 'mpesa-direct') else 'sasapay'\n"),
 (P, "        if cb['phone'] and p['phone'] and cb['phone'][-9:] != ''.join(c for c in p['phone'] if c.isdigit())[-9:]:\n"
     "            print('finoq: phone mismatch, not credited', p['ref']); return 'phone_mismatch'\n",
     "        if cb['phone'] and p['phone'] and cb['phone'][-9:] != ''.join(c for c in p['phone'] if c.isdigit())[-9:]:\n"
     "            print('finoq: callback phone differs from the typed one, crediting anyway', p['ref'])    # gateway field can be the merchant's\n"),
 (P, "(if it names a payer) the same phone, and a late", "(the payer phone is only logged) and a late"),
 (P, "not in ('', 'm-pesa', 'sasapay'): bad.append('PAYHERO_PROVIDER should be m-pesa or sasapay.')",
     "not in ('', 'm-pesa', 'sasapay', 'm-pesa-direct', 'mpesa-direct'): bad.append('PAYHERO_PROVIDER should be empty or sasapay.')"),
 (P, "'mpesa_provider': 'sasapay' if _env('PAYHERO_PROVIDER').lower() == 'sasapay' else 'm-pesa'}", "'mpesa_provider': _provider()}"),
 (E, "PAYHERO_PROVIDER=m-pesa      # or sasapay", "PAYHERO_PROVIDER=sasapay      # sasapay is the default and the real prompt. Leave it like this"),
 (T, "body['provider'] == 'm-pesa' and body['callback_url']", "body['provider'] == 'sasapay' and body['network_code'] == '63902' and body['callback_url']"),
 (T, "@T('pay: underpaid, missing amount, wrong phone are NOT credited')", "@T('pay: underpaid and missing amount are NOT credited')"),
 (T, "    r3 = newpay(); assert hook(r3, Phone='254799999999').json['result'] == 'phone_mismatch'\n    assert not active()\n",
     "    assert not active()\n    r3 = newpay(); assert hook(r3, Phone='254799999999').json['result'] == 'paid' and active()\n"),
 (T, "@T('pay: webhook needs the secret')",
     "@T('pay: provider is SasaPay unless m-pesa-direct is asked for')\n"
     "def _():\n"
     "    for v, want in (('', 'sasapay'), ('m-pesa', 'sasapay'), ('sasapay', 'sasapay'), ('m-pesa-direct', 'm-pesa')):\n"
     "        os.environ['PAYHERO_PROVIDER'] = v; SENT.clear(); n = str(['', 'm-pesa', 'sasapay', 'm-pesa-direct'].index(v)); assert C.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': '071100000' + n}, headers=U).status_code == 200; b = SENT[0][1]; assert b['provider'] == want and (('network_code' in b) == (want == 'sasapay')), v\n"
     "    os.environ.pop('PAYHERO_PROVIDER', None)\n"
     "@T('pay: webhook needs the secret')"),
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
