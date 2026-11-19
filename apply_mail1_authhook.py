"""Sign-up codes and password-reset codes are now sent by OUR server through Resend, not by Supabase.
How: Supabase's 'Send Email' auth hook calls POST /api/auth/send-email with the code; this app checks the hook's signature, builds the email from
emails/verify-email.html or emails/reset-password.html, and sends it with the Resend API. Supabase still creates and checks the code; it just no longer sends the email.
Adds backend/authmail.py, the route, the import, an .env.example line and a README section. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import os
MOD = r'''"""Sign-in emails (sign-up code, password-reset code) sent through Resend by this server, called by Supabase's 'Send Email' auth hook.
The hook request is signed (Standard Webhooks: webhook-id, webhook-timestamp, webhook-signature = v1,base64(HMAC-SHA256(secret, id.timestamp.body))). An unsigned or old request is refused,
so nobody can use this route to send mail. Supabase makes and checks the 6-digit code itself; we only deliver it. A failed send answers 500 with a message, so the app shows its normal
'We could not send the email' instead of pretending it worked. Not counted against the alert/receipt caps (a person waiting for a code must never be blocked by alerts)."""
import os, hmac, hashlib, base64, time, html as _h
from . import mailer

TOL = 300                                         # seconds a signed request stays valid
_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'emails')

def secret(): return os.getenv('SEND_EMAIL_HOOK_SECRET', '').strip()
def configured(): return bool(secret() and mailer.configured())

def _key():
    s = secret()
    for p in ('v1,whsec_', 'whsec_'):
        if s.startswith(p): s = s[len(p):]; break
    try: return base64.b64decode(s)
    except Exception: return b''

def verify(headers, raw, now=None):
    """True only for a request signed with our hook secret, not older than TOL seconds."""
    k = _key()
    if not k: return False
    mid = headers.get('webhook-id', ''); ts = headers.get('webhook-timestamp', ''); sig = headers.get('webhook-signature', '')
    try: t = int(ts)
    except (TypeError, ValueError): return False
    if abs((now or time.time()) - t) > TOL: return False
    exp = base64.b64encode(hmac.new(k, ('%s.%s.' % (mid, ts)).encode() + raw, hashlib.sha256).digest()).decode()
    for part in str(sig).split():
        v, _, s = part.partition(',')
        if v == 'v1' and hmac.compare_digest(s, exp): return True
    return False

def _file(name, token, email):
    with open(os.path.join(_DIR, name), encoding='utf-8') as f: h = f.read()
    return h.replace('{{ .Token }}', _h.escape(token)).replace('{{ .Email }}', _h.escape(email))

def _simple(heading, token):
    e = _h.escape
    return ('<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;color:#111827"><h2 style="margin:0 0 12px">%s</h2>'
            '<p style="font-size:15px">Type this code in the app:</p><p style="font-size:32px;font-weight:700;letter-spacing:8px;margin:12px 0">%s</p>'
            '<p style="font-size:12px;color:#6b7280">It works for a short time and only once. If you did not ask for it, ignore this email.</p></div>') % (e(heading), e(token))

def build(payload):
    """-> (to, subject, html, text) or None when this kind of email is not supported."""
    u = payload.get('user') if isinstance(payload.get('user'), dict) else {}
    d = payload.get('email_data') if isinstance(payload.get('email_data'), dict) else {}
    to = str(u.get('email') or '').strip(); tok = str(d.get('token') or '').strip(); typ = str(d.get('email_action_type') or '')
    if not to or not tok: return None
    if typ == 'signup': sub, body, head = 'Your spaceXBot verification code', _file('verify-email.html', tok, to), 'Verify your email'
    elif typ == 'recovery': sub, body, head = 'Your spaceXBot password reset code', _file('reset-password.html', tok, to), 'Reset your password'
    elif typ in ('magiclink', 'reauthentication'): sub, head = 'Your spaceXBot sign-in code', 'Your sign-in code'; body = _simple(head, tok)
    else: return None
    return to, sub, body, '%s: %s. It works for a short time and only once. If you did not ask for it, ignore this email.' % (head, tok)

def send(payload, idem=None):
    """-> (ok, why). idem = the hook's webhook-id, so a retry by Supabase never sends the email twice."""
    b = build(payload if isinstance(payload, dict) else {})
    if not b: return False, 'This kind of email is not supported.'
    to, sub, body, text = b
    return mailer.send(to, sub, body, text, idem=('auth-' + idem) if idem else None, kind='test')
'''
ROUTE = '''@app.post('/api/auth/send-email')
def auth_send_email():
    """Supabase 'Send Email' auth hook: delivers the sign-up / password-reset code through Resend. Refuses anything not signed with SEND_EMAIL_HOOK_SECRET."""
    raw = request.get_data()
    if not authmail.verify(request.headers, raw): return jsonify(error={'http_code': 401, 'message': 'bad signature'}), 401
    try: p = json.loads(raw or b'{}')
    except ValueError: p = {}
    ok, why = authmail.send(p, request.headers.get('webhook-id', ''))
    if ok: return jsonify({}), 200
    print('auth email failed:', why)
    return jsonify(error={'http_code': 500, 'message': 'We could not send the email'}), 500

'''
README = '''## Sign-in emails sent by this app through Resend (instead of Supabase SMTP)
Supabase still makes and checks the 6-digit code. Its **Send Email hook** hands the code to this app, which emails it with Resend using `emails/verify-email.html` and `emails/reset-password.html`.
1. **Resend:** domain verified, `RESEND_API_KEY` and `MAIL_FROM` set in Render (same as the receipts above).
2. **Supabase > Auth > Hooks > Send Email:** turn on, type *HTTPS*, URL = `BASE_URL/api/auth/send-email`, then *Generate secret* and copy it (it looks like `v1,whsec_...`).
3. **Render:** add `SEND_EMAIL_HOOK_SECRET` = that secret. Redeploy.
4. **Test:** sign up with a new address and ask for a reset code. Both emails now come from `MAIL_FROM`. A wrong secret gives 401 in the Supabase hook log; a Resend problem shows as "We could not send the email" (check the Render log line "auth email failed").
The Supabase SMTP settings and email templates are not used while the hook is on. Sign-in codes are not counted in `MAIL_ALERT_CAP` / `MAIL_HARD_CAP`.

'''
if os.path.exists('backend/authmail.py'):
    print('already applied'); raise SystemExit
EDITS = [('backend/app.py', 'from . import lag, multi, automarkets, prefs, scale, burst, groupcap\n', 'from . import lag, multi, automarkets, prefs, scale, burst, groupcap, authmail\n'),
         ('backend/app.py', "@app.post('/api/webhooks/payhero')\n@app.post('/api/pay/payhero/callback')\n", ROUTE + "@app.post('/api/webhooks/payhero')\n@app.post('/api/pay/payhero/callback')\n"),
         ('.env.example', 'PAYHERO_CALLBACK_SECRET=another-long-random\n', 'PAYHERO_CALLBACK_SECRET=another-long-random\n# Supabase > Auth > Hooks > Send Email (HTTPS) secret, looks like v1,whsec_xxxx. With it, sign-up and reset codes are emailed by this app through Resend\nSEND_EMAIL_HOOK_SECRET=\n'),
         ('README.md', '## Email alerts and receipts (Resend API)\n', README + '## Email alerts and receipts (Resend API)\n')]
files = {}
for f, a, b in EDITS:
    files.setdefault(f, open(f, encoding='utf-8').read())
    assert files[f].count(a) == 1, 'not found exactly once in %s: %s' % (f, a[:50])
for f, a, b in EDITS: files[f] = files[f].replace(a, b)
for f, t in files.items(): open(f, 'w', encoding='utf-8').write(t)
open('backend/authmail.py', 'w', encoding='utf-8').write(MOD)
print('done')
