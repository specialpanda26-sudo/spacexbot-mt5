"""M-Pesa prompt no longer needs a verified email. A signed-in customer who has not confirmed their email was refused with 'verify your email first' before the
prompt was even sent, which is why your own (verified) number worked and theirs did not. The payment is still tied to the signed-in account.
PayPal and everything else keep their rules. The old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
F = 'backend/app.py'
s = open(F, encoding='utf-8').read()
A = "@app.post('/api/pay/mpesa')\n@need(verified=True)\ndef p_mpesa(u):"
B = "@app.post('/api/pay/mpesa')\n@need()\ndef p_mpesa(u):"
if B in s:
    print('already applied'); raise SystemExit
assert s.count(A) == 1, 'anchor not found exactly once'
open(F, 'w', encoding='utf-8').write(s.replace(A, B))
print('done')
