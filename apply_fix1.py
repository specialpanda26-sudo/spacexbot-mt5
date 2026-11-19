"""Fix 1: (a) open-trades rows no longer squash the symbol into one letter per line, (b) the EA now reports trades YOU close by hand
(a hand close has magic 0, the old check threw it away, so wins closed on the phone never reached the app), (c) a M-Pesa success whose phone
comes masked (2547***123) is no longer refused as 'phone_mismatch'. Each old text must be found exactly once or NOTHING changes. Safe to run twice."""
import sys, os
EDITS = [
 ('static/index.html', '.row .t{font-weight:800;min-width:0;overflow-wrap:anywhere}', '.row .t{font-weight:800;min-width:0;overflow-wrap:break-word}', 'overflow-wrap:break-word}'),
 ('static/index.html', '.row .r2{grid-column:3;grid-row:2;text-align:right;font-size:13px;color:var(--muted)}', '.row .r2{grid-column:2/4;grid-row:2;text-align:right;font-size:13px;color:var(--muted)}', 'grid-column:2/4;grid-row:2'),
 ('ea/SpaceXBridge.mq5', '   if(HistoryDealGetInteger(t.deal, DEAL_MAGIC) != Magic) return;\n', '   // no magic check here: a trade closed by hand (phone or terminal) has magic 0. Our trades are found below by their SXB comment.\n', 'no magic check here'),
 ('backend/payments.py', "'phone': ''.join(c for c in str(get('phonenumber', 'phone', 'msisdn', 'recipient') or '') if c.isdigit()),", "'phone': _cbphone(get('phonenumber', 'phone', 'msisdn', 'recipient')),", '_cbphone('),
 ('backend/payments.py', 'def parse_webhook(body):', 'def _cbphone(v):\n    """Digits of the payer phone, or \'\' when the gateway masked it (2547***123) or sent too few digits: a masked number cannot be compared."""\n    s = str(v or \'\')\n    d = \'\'.join(c for c in s if c.isdigit())\n    return \'\' if any(c in s for c in \'*xX\\u2022\') or len(d) < 9 else d\n\ndef parse_webhook(body):', 'def _cbphone'),
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
