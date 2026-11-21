"""Sign-up / password-reset codes: Render switch AUTH_MAIL_PROVIDER = resend | supabase | auto (default).
resend = this server emails the codes through Resend, Supabase sends nothing. Needs RESEND_API_KEY, MAIL_FROM, SUPABASE_URL, SUPABASE_SERVICE_KEY.
Run from the repo root. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import os, sys

TAIL = r'''

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
'''

FILES = {
  'backend/app.py': [
    (r'''    return Response(f'window.SXB={{sb:{json.dumps(sbauth.public_config())},gid:{json.dumps(os.getenv("GOOGLE_WEB_CLIENT_ID", ""))},plans:{json.dumps(pay.plans())}}};', mimetype='application/javascript')
''',
     r'''    return Response(f'window.SXB={{sb:{json.dumps(sbauth.public_config())},mail:{json.dumps(authmail.mode())},gid:{json.dumps(os.getenv("GOOGLE_WEB_CLIENT_ID", ""))},plans:{json.dumps(pay.plans())}}};', mimetype='application/javascript')
'''),
    (r'''
@app.post('/api/webhooks/payhero')
''',
     r'''
def _ip(): return request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '?'

@app.post('/api/auth/mail/code')
def auth_mail_code():
    """Resend mode: email a fresh sign-up or password-reset code. Open route, so it is slowed per email and per address."""
    if authmail.mode() != 'resend': return jsonify(error='Not enabled.'), 404
    j = _j(); kind = 'recovery' if j.get('type') == 'recovery' else 'signup'
    c, m = authmail.deliver(j.get('email'), kind, _ip())
    return (jsonify(ok=True), 200) if c == 200 else (jsonify(error=m), c)

@app.post('/api/auth/mail/signup')
def auth_mail_signup():
    """Resend mode: create the account unconfirmed, then email the 6-digit code through Resend (Supabase sends nothing)."""
    if authmail.mode() != 'resend': return jsonify(error='Not enabled.'), 404
    j = _j(); em = str(j.get('email') or '').strip().lower(); pw = str(j.get('password') or '')
    if '@' not in em or len(em) > 200: return jsonify(error='Enter a valid email address.'), 400
    if len(pw) < 6 or len(pw) > 200: return jsonify(error='Choose a stronger password (at least 6 characters).'), 400
    ok, m = authmail.create_user(j.get('name'), em, pw, j.get('dob'), j.get('gender'))
    if not ok: return jsonify(error='That email already has an account. Log in instead.' if m == 'exists' else m, code='user_already_exists' if m == 'exists' else None), (409 if m == 'exists' else 400)
    c, m = authmail.deliver(em, 'signup', _ip())
    return (jsonify(ok=True), 200) if c == 200 else (jsonify(error=m), c)

@app.post('/api/webhooks/payhero')
'''),
  ],
  'static/live.js': [
    (r'''  function tok() { return S ? S.auth.getSession().then(function (r) { return r.data && r.data.session ? r.data.session.access_token : null; }) : Promise.resolve(null); }
  function api(path, o) {
''',
     r'''  function tok() { return S ? S.auth.getSession().then(function (r) { return r.data && r.data.session ? r.data.session.access_token : null; }) : Promise.resolve(null); }
  function rm() { return !!(window.SXB && window.SXB.mail === "resend"); }   /* server emails the codes through Resend */
  function mailCode(email, type) { return fetch("/api/auth/mail/code", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: email, type: type }) }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) { var e = new Error(j.error || "We could not send the email. Try again in a minute."); e.status = r.status; throw e; } return j; }); }); }
  function api(path, o) {
'''),
    (r'''      var n = need(); if (n) return n;
      return S.auth.signUp({ email: email, password: pw, options: { data: { full_name: name, dob: extra && extra.dob, gender: extra && extra.gender } } }).then(chk).then(function (d) {
''',
     r'''      var n = need(); if (n) return n;
      if (rm()) return fetch("/api/auth/mail/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: name, email: email, password: pw, dob: extra && extra.dob, gender: extra && extra.gender }) }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok) { var e = new Error(j.error || "We could not create the account."); if (j.code) e.code = j.code; throw e; }
          PEND = { email: email, name: name, extra: extra || null }; return { pending: true, email: email, name: name };
        });
      });
      return S.auth.signUp({ email: email, password: pw, options: { data: { full_name: name, dob: extra && extra.dob, gender: extra && extra.gender } } }).then(chk).then(function (d) {
'''),
    (r'''            return S.auth.resend({ type: "signup", email: email }).then(function () { return { pending: true, email: email }; }, function () { return { pending: true, email: email }; });
''',
     r'''            var rs = rm() ? mailCode(email, "signup") : S.auth.resend({ type: "signup", email: email });
            return rs.then(function () { return { pending: true, email: email }; }, function () { return { pending: true, email: email }; });
'''),
    (r'''      return S.auth.verifyOtp({ email: email, token: code, type: "signup" }).then(chk).then(load).then(function (m) {
''',
     r'''      return S.auth.verifyOtp({ email: email, token: code, type: "signup" }).then(chk).catch(function (e) {
        /* a code made by the server may be typed "email" by Supabase: try that once before giving up */
        if (!rm()) throw e; return S.auth.verifyOtp({ email: email, token: code, type: "email" }).then(chk).catch(function () { throw e; });
      }).then(load).then(function (m) {
'''),
    (r'''    resendCode: function (email) { var n = need(); return n || S.auth.resend({ type: "signup", email: email }).then(chk); },
''',
     r'''    resendCode: function (email) { var n = need(); if (n) return n; return rm() ? mailCode(email, "signup") : S.auth.resend({ type: "signup", email: email }).then(chk); },
'''),
    (r'''    resetPassword: function (email) { var n = need(); return n || S.auth.resetPasswordForEmail(email).then(chk); },
''',
     r'''    resetPassword: function (email) { var n = need(); if (n) return n; return rm() ? mailCode(email, "recovery") : S.auth.resetPasswordForEmail(email).then(chk); },
'''),
  ],
  '.env.example': [
    (r'''#   Auth > URL Configuration: Site URL = your BASE_URL above; add it under Redirect URLs (needed for Google sign-in).
# --- Email alerts and receipts: Resend API. These DO go in Render (sign-in codes use Supabase SMTP instead, see above) ---
''',
     r'''#   Auth > URL Configuration: Site URL = your BASE_URL above; add it under Redirect URLs (needed for Google sign-in).
# --- SWITCH: who sends the sign-up and password-reset codes ---
# AUTH_MAIL_PROVIDER=resend   -> this server emails the codes through Resend. Supabase sends NOTHING. Needs RESEND_API_KEY + MAIL_FROM + SUPABASE_SERVICE_KEY (+ SUPABASE_URL). No dashboard hook or SMTP needed.
# AUTH_MAIL_PROVIDER=supabase -> old way: Supabase sends them (its SMTP / Send Email hook).
# AUTH_MAIL_PROVIDER=auto (default) -> resend when all of those keys are set, otherwise supabase.
AUTH_MAIL_PROVIDER=resend
# --- Email alerts and receipts: Resend API. These DO go in Render (sign-in codes use Supabase SMTP instead, see above) ---
'''),
  ],
  'backend/authmail.py': [
    (r'''import os, hmac, hashlib, base64, time, html as _h
from . import mailer
''',
     r'''import os, hmac, hashlib, base64, time, threading, html as _h
import requests
from . import mailer
'''),
  ],
}

def rd(p):
    with open(p, encoding='utf-8') as f: return f.read()
def main():
    if not os.path.isdir('backend'): sys.exit('Run this from the repo root (the folder that has backend/).')
    if 'def mode()' in rd('backend/authmail.py'): print('Already applied. Nothing to do.'); return
    out = {}
    for path, prs in FILES.items():
        s = rd(path)
        for old, new in prs:
            if s.count(old) != 1: sys.exit('STOP: expected text not found exactly once in %s. Nothing was changed.\n%s' % (path, old[:120]))
            s = s.replace(old, new)
        out[path] = s
    out['backend/authmail.py'] += TAIL
    for path, s in out.items():
        with open(path, 'w', encoding='utf-8', newline='') as f: f.write(s)
        print('wrote', path)
    print('Done. Now set AUTH_MAIL_PROVIDER=resend on Render')
main()
