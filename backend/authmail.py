"""Sign-in emails (sign-up code, password-reset code) sent through Resend by this server, called by Supabase's 'Send Email' auth hook.
The hook request is signed (Standard Webhooks: webhook-id, webhook-timestamp, webhook-signature = v1,base64(HMAC-SHA256(secret, id.timestamp.body))). An unsigned or old request is refused,
so nobody can use this route to send mail. Supabase makes and checks the 6-digit code itself; we only deliver it. A failed send answers 500 with a message, so the app shows its normal
'We could not send the email' instead of pretending it worked. Not counted against the alert/receipt caps (a person waiting for a code must never be blocked by alerts)."""
import os, hmac, hashlib, base64, time, threading, html as _h
import requests
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


# ---------- Resend-only mode: this server asks Supabase for the code (no email sent by Supabase), then emails it through Resend ----------
def _url(): return os.getenv('SUPABASE_URL', '').rstrip('/')
def _svc(): return os.getenv('SUPABASE_SERVICE_KEY', '').strip()

def mode():
    """'resend' = this server emails every sign-up / reset code through Resend. 'supabase' = Supabase sends them (old way).
    AUTH_MAIL_PROVIDER=resend | supabase | auto (default). auto = resend when RESEND_API_KEY, MAIL_FROM and SUPABASE_SERVICE_KEY are all set."""
    v = os.getenv('AUTH_MAIL_PROVIDER', 'auto').strip().lower()
    if v == 'supabase': return 'supabase'
    ready = bool(_url() and _svc() and mailer.configured())
    return 'resend' if ready else 'supabase'

def _admin(method, path, body):
    h = {'Authorization': 'Bearer ' + _svc(), 'apikey': _svc(), 'Content-Type': 'application/json'}
    return requests.request(method, _url() + '/auth/v1/admin' + path, json=body, headers=h, timeout=10)

def make_code(email, kind):
    """Ask Supabase for a one-time code WITHOUT sending any email. -> (code, why). kind: signup | recovery."""
    try:
        r = _admin('POST', '/generate_link', {'type': 'recovery' if kind == 'recovery' else 'magiclink', 'email': email})
        try: j = r.json()
        except ValueError: j = {}
        if r.status_code < 300 and j.get('email_otp'): return str(j['email_otp']), ''
        if r.status_code in (404, 422): return '', 'no such user'
        return '', 'Supabase said %s' % r.status_code
    except Exception as e: return '', 'Could not reach Supabase (%s).' % type(e).__name__

_last = {}; _ll = threading.Lock()
def _slow(key, gap=45):
    """True when the same key already asked in the last `gap` seconds."""
    now = time.time()
    with _ll:
        if len(_last) > 5000: _last.clear()
        if now - _last.get(key, 0) < gap: return True
        _last[key] = now; return False

def deliver(email, kind, ip=''):
    """-> (http status, message). Never says whether the email has an account (a reset for a stranger answers ok too)."""
    email = (email or '').strip().lower()
    if '@' not in email or len(email) > 200: return 400, 'Enter a valid email address.'
    if _slow('e:' + kind + ':' + email) or (ip and _slow('i:' + ip, 3)): return 429, 'Please wait a minute before asking for another code.'
    code, why = make_code(email, kind)
    if not code:
        if why == 'no such user': return 200, 'ok'
        print('auth code failed:', why); return 502, 'We could not send the email. Try again in a minute.'
    ok, info = send({'user': {'email': email}, 'email_data': {'token': code, 'email_action_type': 'recovery' if kind == 'recovery' else 'signup'}})
    if ok: return 200, 'ok'
    print('auth email failed:', info); return 502, 'We could not send the email. Try again in a minute.'

def create_user(name, email, password, dob=None, gender=None):
    """Make the account unconfirmed (no email from Supabase). -> (ok, message)."""
    email = (email or '').strip().lower()
    meta = {'full_name': (name or '')[:80]}
    if dob: meta['dob'] = dob
    if gender: meta['gender'] = gender
    try:
        r = _admin('POST', '/users', {'email': email, 'password': password, 'email_confirm': False, 'user_metadata': meta})
        try: j = r.json()
        except ValueError: j = {}
        if r.status_code < 300: return True, 'ok'
        c = str(j.get('error_code') or j.get('code') or ''); m = str(j.get('msg') or j.get('message') or '')
        if c == 'email_exists' or 'already' in m.lower(): return False, 'exists'
        if c == 'weak_password' or 'password' in m.lower(): return False, 'Choose a stronger password (at least 6 characters).'
        return False, 'We could not create the account. Try again.'
    except Exception as e: print('create_user failed', e); return False, 'We could not create the account. Try again.'
