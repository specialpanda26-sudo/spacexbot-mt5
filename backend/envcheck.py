"""Setup check (Section 10b): looks at the Render environment and says, per feature, what is missing, still a placeholder from .env.example, or risky.
NEVER returns a value, only variable NAMES and plain sentences. report(env) takes a dict so tests need no real environment."""
import os, json, base64
from urllib.parse import urlparse

PLACEHOLDERS = ('change-me', 'yourdomain', 'your-service', 'you@gmail.com', 'another-long-random', 'xxxx', 'your-password', 'region.pooler')

def _g(env, k): return str(env.get(k, '') or '').strip().strip('"\'')
def _ph(v): v = v.lower(); return any(p in v for p in PLACEHOLDERS)
def _host(u):
    try: return urlparse(u).netloc.lower()
    except Exception: return ''
def _fcm(raw):
    try: a = json.loads(raw if raw.startswith('{') else base64.b64decode(raw).decode('utf-8'))
    except Exception: return None
    return a if isinstance(a, dict) else None

def report(env=None):
    e = os.environ if env is None else env
    out = []
    def add(group, key, level, msg): out.append({'group': group, 'key': key, 'level': level, 'msg': msg})
    def need(group, key, msg_missing, level='bad', check=None, msg_bad=None, bad_level='bad'):
        v = _g(e, key)
        if not v: return add(group, key, level, msg_missing)
        if _ph(v): return add(group, key, 'bad', 'Still the example text from .env.example. Put your real value.')
        if check and not check(v): return add(group, key, bad_level, msg_bad or 'The value looks wrong.')
        add(group, key, 'ok', 'Set.')

    G = 'Core'
    need(G, 'DATABASE_URL', 'Not set. Users, payments and plans are wiped on every redeploy.')
    need(G, 'BASE_URL', 'Not set.', check=lambda v: v.startswith('https://'), msg_bad='Must start with https:// (your Render address).')
    need(G, 'EA_KEY', 'Not set. The MT5 EA cannot connect.', check=lambda v: len(v) >= 16, msg_bad='Shorter than 16 characters. Use a long random key.', bad_level='warn')
    need(G, 'ADMIN_EMAILS', 'Not set. No signed-in admin exists (the admin pass can still open the panel).', level='warn')
    ap = _g(e, 'ADMIN_PASS')
    if not ap: add(G, 'ADMIN_PASS', 'ok', 'Empty: the admin pass is off. Admin works only through ADMIN_EMAILS.')
    elif _ph(ap): add(G, 'ADMIN_PASS', 'bad', 'Still the example text. Anyone who reads the repo can open admin.')
    elif len(ap) < 8: add(G, 'ADMIN_PASS', 'warn', 'Shorter than 8 characters.')
    else: add(G, 'ADMIN_PASS', 'ok', 'Set.')
    if _g(e, 'DEV_AUTH') == '1': add(G, 'DEV_AUTH', 'bad', 'On. Anyone can sign in as anyone. Remove it.')

    G = 'Sign-in'
    if _g(e, 'SUPABASE_URL') and _g(e, 'SUPABASE_ANON_KEY') and not _ph(_g(e, 'SUPABASE_URL')): add(G, 'SUPABASE_URL / SUPABASE_ANON_KEY', 'ok', 'Set.')
    else: add(G, 'SUPABASE_URL / SUPABASE_ANON_KEY', 'bad', 'Missing or example text. Nobody can sign in.')
    need(G, 'SUPABASE_SERVICE_KEY', 'Not set. Deleting an account will not remove its login.', level='warn')
    prov = (_g(e, 'AUTH_MAIL_PROVIDER') or 'auto').lower()
    have = bool(_g(e, 'RESEND_API_KEY') and _g(e, 'MAIL_FROM') and _g(e, 'SUPABASE_SERVICE_KEY'))
    if prov == 'resend' and not have: add(G, 'AUTH_MAIL_PROVIDER', 'bad', 'Set to resend but RESEND_API_KEY, MAIL_FROM or SUPABASE_SERVICE_KEY is missing. Sign-up codes cannot be sent.')
    elif prov == 'supabase': add(G, 'AUTH_MAIL_PROVIDER', 'warn', 'Supabase sends the codes, so its own SMTP must be set up there. This check cannot see that.')
    else: add(G, 'AUTH_MAIL_PROVIDER', 'ok', 'Codes are sent through Resend.' if have else 'Auto, and Resend is not complete, so Supabase sends the codes.')
    need(G, 'GOOGLE_WEB_CLIENT_ID', 'Not set. Google sign-in is off.', level='warn')

    G = 'Emails'
    k = _g(e, 'RESEND_API_KEY')
    if not k: add(G, 'RESEND_API_KEY', 'warn', 'Not set. Receipts and trade alert emails are off.')
    elif _ph(k) or not k.startswith('re_'): add(G, 'RESEND_API_KEY', 'bad', 'Does not look like a Resend key (starts with re_).')
    else: add(G, 'RESEND_API_KEY', 'ok', 'Set.')
    need(G, 'MAIL_FROM', 'Not set. Emails cannot be sent.', level='warn', check=lambda v: '@' in v, msg_bad='Needs an address like spaceXBot <alerts@yourdomain.com>.')

    G = 'Payments'
    need(G, 'PAYHERO_API_KEY', 'Not set. M-Pesa is off.')
    need(G, 'PAYHERO_API_SECRET', 'Not set. M-Pesa is off.')
    need(G, 'PAYHERO_CHANNEL_ID', 'Not set. M-Pesa is off.', check=lambda v: v.isdigit(), msg_bad='Must be a number.')
    need(G, 'PAYHERO_CALLBACK_SECRET', 'Not set. M-Pesa confirmations would be refused.')
    pp = _g(e, 'PAYHERO_PROVIDER').lower()
    if pp not in ('', 'm-pesa', 'sasapay', 'm-pesa-direct', 'mpesa-direct'): add(G, 'PAYHERO_PROVIDER', 'bad', 'Unknown provider. Use sasapay or m-pesa-direct.')
    cu = _g(e, 'CALLBACK_URL') or _g(e, 'PAYHERO_CALLBACK_URL'); base = _g(e, 'BASE_URL')
    if cu and base and _host(cu) != _host(base): add(G, 'CALLBACK_URL', 'bad', 'Points to a different site than BASE_URL. Delete CALLBACK_URL.')
    if _g(e, 'PAYPAL_CLIENT_ID') and _g(e, 'PAYPAL_SECRET'):
        add(G, 'PAYPAL_CLIENT_ID / PAYPAL_SECRET', 'ok', 'Set.')
        if (_g(e, 'PAYPAL_ENV') or 'live').lower() != 'live': add(G, 'PAYPAL_ENV', 'warn', 'Not live: PayPal takes no real money.')
    else: add(G, 'PAYPAL_CLIENT_ID / PAYPAL_SECRET', 'warn', 'Not set. PayPal is off.')

    G = 'Phone alerts'
    raw = _g(e, 'FCM_SERVICE_ACCOUNT')
    if not raw: add(G, 'FCM_SERVICE_ACCOUNT', 'warn', 'Not set. Phone alerts are off.')
    else:
        a = _fcm(raw)
        if a is None: add(G, 'FCM_SERVICE_ACCOUNT', 'bad', 'Cannot be read. Paste the whole JSON on ONE line, or its base64.')
        elif not (a.get('private_key') and a.get('client_email') and a.get('project_id')): add(G, 'FCM_SERVICE_ACCOUNT', 'bad', 'Readable but missing private_key, client_email or project_id. Use the Firebase service-account key.')
        else: add(G, 'FCM_SERVICE_ACCOUNT', 'ok', 'Set.')
    pu = _g(e, 'PUBLIC_URL')
    if not pu: add(G, 'PUBLIC_URL', 'warn', 'Not set. Alert pictures load from a built-in address that may not be yours.')
    elif _ph(pu) or not pu.startswith('https://'): add(G, 'PUBLIC_URL', 'bad', 'Must be your https Render address.')
    elif base and _host(pu) != _host(base): add(G, 'PUBLIC_URL', 'warn', 'Differs from BASE_URL. Alert pictures load from here.')
    else: add(G, 'PUBLIC_URL', 'ok', 'Set.')

    G = 'Deriv bot'
    need(G, 'BROKER_KEY', 'Not set. Nobody can link a Deriv or Binance key.', check=lambda v: len(v) >= 16, msg_bad='Shorter than 16 characters.')
    if _g(e, 'DERIV_CLIENT_ID') and not _g(e, 'DERIV_APP_ID'): add(G, 'DERIV_CLIENT_ID', 'ok', 'Set. Used for Log in with Deriv and the Deriv bot.')
    else: need(G, 'DERIV_APP_ID', 'Not set. The Deriv bot cannot trade for anyone.')
    if _g(e, 'DERIV_REAL') == '1': add(G, 'DERIV_REAL', 'warn', 'REAL Deriv accounts are allowed. Keep 0 until demo results are proven.')
    return out

def summary(rows):
    return {'bad': sum(r['level'] == 'bad' for r in rows), 'warn': sum(r['level'] == 'warn' for r in rows), 'ok': sum(r['level'] == 'ok' for r in rows)}
