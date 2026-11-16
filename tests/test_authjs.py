"""Checks the browser sign-in code (static/live.js) against a fake Supabase client. Needs node; skipped if node is missing.
Run: python tests/test_authjs.py"""
import os, sys, shutil, subprocess
if not shutil.which('node'): print('SKIP node not installed'); sys.exit(0)
JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'live.js')
HARNESS = r'''
const fs = require('fs'); const calls = []; let mode = {};
const ok = (d) => Promise.resolve({ data: d || {}, error: null });
const auth = {
  onAuthStateChange() {}, getSession: () => ok({ session: null }),
  signUp: (a) => { calls.push(['signUp', a]); return ok(mode.signUp || { user: { identities: [{}] }, session: null }); },
  signInWithPassword: (a) => { calls.push(['signIn', a]); return Promise.resolve(mode.signIn || { data: {}, error: { code: 'email_not_confirmed', message: 'Email not confirmed' } }); },
  resend: (a) => { calls.push(['resend', a]); return mode.resendFail ? Promise.resolve({ data: null, error: { code: 'over_email_send_rate_limit', message: 'x' } }) : ok(); },
  verifyOtp: (a) => { calls.push(['verifyOtp', a]); return Promise.resolve({ data: null, error: { code: 'otp_expired', message: 'Token has expired or is invalid' } }); },
  resetPasswordForEmail: (e) => { calls.push(['reset', e]); return ok(); },
  signOut: () => ok(),
};
global.window = { SXB: { sb: { url: 'https://x.supabase.co', key: 'k' } }, supabase: { createClient: () => ({ auth }) } };
global.location = { origin: 'http://t' };
eval(fs.readFileSync(process.argv[1], 'utf8'));
const X = window.SXA, out = {};
(async () => {
  out.signup = await X.signUp('Amy', 'a@b.com', 'pw12345678');
  mode.signUp = { user: { identities: [] }, session: null };
  out.dupe = await X.signUp('Amy', 'a@b.com', 'pw').catch(e => X.err(e));
  out.signin = await X.signIn('a@b.com', 'pw');
  mode.resendFail = true; out.signinLimited = await X.signIn('a@b.com', 'pw'); mode.resendFail = false;
  out.verify = await X.verifyCode('a@b.com', '123456').catch(e => X.err(e));
  await X.resendCode('a@b.com'); await X.resetPassword('a@b.com');
  out.resetVerify = await X.resetVerify('a@b.com', '123456').catch(e => X.err(e));
  out.calls = calls;
  const E = (code, message) => X.err({ code, message });
  out.err = [E('invalid_credentials', ''), E('over_email_send_rate_limit', 'For security purposes, you can only request this once every 45 seconds'),
    E('', 'Error sending confirmation email'), E('unexpected_failure', 'Error sending recovery email'), E('email_address_invalid', ''),
    E('email_address_not_authorized', ''), E('', 'Token has expired or is invalid'), E('', 'Failed to fetch'), E('', ''), E('signup_disabled', '')];
  console.log(JSON.stringify(out));
})();
'''
r = subprocess.run(['node', '-e', HARNESS, JS], capture_output=True, text=True, timeout=30)
if r.returncode: print(r.stderr); sys.exit(1)
import json; o = json.loads(r.stdout.strip().splitlines()[-1]); C = o['calls']
R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
def find(k): return [c[1] for c in C if c[0] == k]
T('sign-up asks for a code (pending, no session)', o['signup'] == {'pending': True, 'email': 'a@b.com', 'name': 'Amy'})
T('sign-up stores the name in metadata', find('signUp')[0]['options']['data'] == {'full_name': 'Amy'})
T('existing email is refused with a clear message', o['dupe'] == 'That email already has an account. Log in instead.')
T('unconfirmed log-in resends a signup code', o['signin'] == {'pending': True, 'email': 'a@b.com'} and find('resend')[0] == {'type': 'signup', 'email': 'a@b.com'})
T('rate-limited resend still opens the code screen', o['signinLimited'] == {'pending': True, 'email': 'a@b.com'})
T('sign-up code is checked as type signup', find('verifyOtp')[0] == {'email': 'a@b.com', 'token': '123456', 'type': 'signup'})
T('wrong code shows the friendly message', o['verify'] == "That code didn't match. Check it and try once more.")
T('resend button sends a signup code', {'type': 'signup', 'email': 'a@b.com'} in find('resend'))
T('forgot password asks Supabase for a recovery email', find('reset') == ['a@b.com'])
T('reset code is checked as type recovery', find('verifyOtp')[1]['type'] == 'recovery' and o['resetVerify'] == o['verify'])
e = o['err']
T('error: wrong password', e[0] == 'Wrong email or password.')
T('error: rate limit shows the seconds', e[1] == 'Your code is still good. Use the one we sent, or ask for a new one in 45 seconds.')
T('error: email could not be sent (SMTP/Resend problem)', e[2] == e[3] == 'We could not send the email. Try again in a minute.')
T('error: bad and unauthorised addresses', e[4] == 'Enter a valid email.' and 'cannot send email' in e[5])
T('error: expired token, offline, empty, sign-ups off', e[6].startswith('That code') and e[7] == 'No connection. Check your internet.' and e[8] == 'Something went wrong. Try again.' and e[9].startswith('New sign-ups'))
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
