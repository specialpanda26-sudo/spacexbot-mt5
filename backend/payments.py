"""M-Pesa via FinoQ (= PayHero v2) and PayPal Orders v2.
Hardened the way Comrade Connect does it: only a webhook (or a verified status check) marks a payment paid,
every state change is conditional so repeats are harmless, a success must name an amount >= the price and
(if it names a payer) the same phone, and a late success after 'expired' still credits."""
import os, time, json, base64, secrets, threading, datetime as dt, requests
from . import store as st

DEFAULT_PLANS = [{'id': 'p1', 'name': '1 Week', 'days': 7, 'kes': 500, 'usd': 4},
                 {'id': 'p2', 'name': '1 Month', 'days': 30, 'kes': 1500, 'usd': 12, 'pop': 1},
                 {'id': 'p3', 'name': '3 Months', 'days': 90, 'kes': 3900, 'usd': 30}]

def plans():
    try:
        p = json.loads(st.get('plans') or '[]')
        if isinstance(p, list) and p and all(isinstance(x, dict) and x.get('id') and x.get('name') and x.get('days') and x.get('kes') and x.get('usd') for x in p): return p
    except Exception: pass
    return DEFAULT_PLANS
def plan(pid): return next((p for p in plans() if p['id'] == pid), None)
def set_plans(rows):
    ok = [{'id': str(r['id'])[:20], 'name': str(r['name'])[:40], 'days': int(r['days']), 'kes': int(r['kes']), 'usd': float(r['usd']), **({'pop': 1} if r.get('pop') else {})}
          for r in rows if r.get('id') and r.get('name') and int(r.get('days', 0)) > 0 and int(r.get('kes', 0)) > 0 and float(r.get('usd', 0)) > 0]
    st.put('plans', json.dumps(ok)); return ok

def activate(uid, pid, days=None):
    d = days or (plan(pid) or {}).get('days')
    if not d: raise ValueError('unknown plan')
    u = st.q('SELECT plan_until FROM users WHERE uid=?', (uid,), True) or {'plan_until': 0}
    st.x('UPDATE users SET plan_until=? WHERE uid=?', (max(int(time.time()), int(u['plan_until'] or 0)) + int(d) * 86400, uid))

# ---------- FinoQ (PayHero v2) ----------
def _env(*names, d=''):
    for n in names:
        v = os.getenv(n, '').strip()
        if v: return v
    return d
def base(): return _env('PAYHERO_BASE_URL', d='https://api.finoq.africa').rstrip('/')
def _cb_url():
    """Where FinoQ posts the result. An explicit CALLBACK_URL wins; otherwise BASE_URL + the secret."""
    u = _env('CALLBACK_URL', 'PAYHERO_CALLBACK_URL').strip('"\'')
    if u: return u
    b = _env('BASE_URL').rstrip('/')
    return f"{b}/api/webhooks/payhero?s={cb_secret()}" if b and cb_secret() else ''
def ready(): return bool(_env('PAYHERO_API_KEY', 'PAYHERO_USER') and _env('PAYHERO_API_SECRET', 'PAYHERO_PASS') and _channel() and cb_secret() and _cb_url())
def _channel():
    try: n = int(_env('PAYHERO_CHANNEL_ID')); return n if n > 0 else 0
    except ValueError: return 0
def _head():
    t = base64.b64encode(f"{_env('PAYHERO_API_KEY', 'PAYHERO_USER')}:{_env('PAYHERO_API_SECRET', 'PAYHERO_PASS')}".encode()).decode()
    return {'Authorization': 'Basic ' + t, 'Content-Type': 'application/json'}
def cb_secret(): return _env('PAYHERO_CALLBACK_SECRET', 'CALLBACK_SECRET')

def norm_phone(p):
    """-> local '07XXXXXXXX' / '01XXXXXXXX' or None."""
    d = ''.join(c for c in str(p or '') if c.isdigit())
    if d.startswith('254'): d = d[3:]
    d = d[-9:] if len(d) >= 9 else ''
    return '0' + d if d[:1] in ('7', '1') and len(d) == 9 else None

_rl = threading.Lock()
def bump(key, limit):
    """Daily counter; False once `limit` is reached (stops STK spam at strangers)."""
    k = f'rl:{key}:{int(time.time() // 86400)}'
    with _rl:
        n = int(st.get(k) or 0)
        if n >= limit: return False
        st.put(k, n + 1); return True

def _new(uid, provider, pid, amount, cur, phone=''):
    ref = 'SXB-' + secrets.token_hex(5).upper()
    st.x('INSERT INTO payments(ref,uid,provider,plan,amount,currency,status,created,phone) VALUES(?,?,?,?,?,?,?,?,?)',
         (ref, uid, provider, pid, amount, cur, 'pending', int(time.time()), phone))
    return ref

def stk_push(uid, pid, phone_raw):
    """-> ref. Raises ValueError (bad input), PermissionError (rate limit), RuntimeError (gateway)."""
    p = plan(pid); ph = norm_phone(phone_raw)
    if not p or not ph: raise ValueError('Check the plan and phone number')
    if not ready(): raise RuntimeError('Payments are not set up yet')
    if not (bump('aid:' + uid, int(_env('STK_DAILY_PER_ACCOUNT', d='30'))) and bump('phone:' + ph, int(_env('STK_DAILY_PER_PHONE', d='10')))):
        raise PermissionError('Too many payment attempts today. Try again tomorrow.')
    ref = _new(uid, 'finoq', pid, p['kes'], 'KES', ph)
    prov = _env('PAYHERO_PROVIDER').lower(); prov = 'sasapay' if prov == 'sasapay' else 'm-pesa'
    body = {'amount': int(p['kes']), 'phone_number': ph, 'channel_id': _channel(), 'provider': prov, 'external_reference': ref}
    if prov == 'sasapay': body['network_code'] = '63902'
    acc = _env('PAYHERO_ACCOUNT_ID')
    if acc.isdigit(): body['account_id'] = int(acc)
    body['callback_url'] = _cb_url()
    try:
        r = requests.post(base() + '/api/v2/payments', json=body, headers=_head(), timeout=25)
        j = r.json() if r.content else {}
    except Exception as e:
        _mark(ref, 'failed', 'not_sent'); raise RuntimeError('Could not reach the payment gateway') from e
    if r.status_code >= 300:
        print('finoq refused', r.status_code, str(j)[:300]); _mark(ref, 'failed', 'not_sent'); raise RuntimeError('Could not send the M-Pesa prompt. Try again.')
    d = j.get('data') if isinstance(j.get('data'), dict) else j
    prov_ref = str(d.get('reference') or d.get('Reference') or d.get('CheckoutRequestID') or d.get('checkout_request_id') or '').strip()
    if prov_ref: st.x("UPDATE payments SET checkout_id=? WHERE ref=? AND status='pending'", (prov_ref, ref))
    return ref

def parse_webhook(body):
    """Reads nested {response:{...}} and flat snake_case callbacks."""
    b = body if isinstance(body, dict) else {}
    norm = lambda o: {str(k).lower().replace('_', ''): v for k, v in o.items()} if isinstance(o, dict) else {}
    nested = next((x for x in (b.get('response'), b.get('data'), b.get('transaction')) if isinstance(x, dict)), None)
    inner, outer = norm(nested), norm(b)
    def get(*keys):
        for src in (inner, outer):
            for k in keys:
                v = src.get(k)
                if v not in (None, '') and not isinstance(v, bool): return v
    status = str(get('status', 'transactionstatus', 'state') or '').strip().upper()
    def num(v):
        try: return float(v)
        except (TypeError, ValueError): return 0.0
    code = get('resultcode', 'failedcode')
    return {'status': status, 'ref': str(get('externalreference', 'externalref') or '').strip(), 'amount': num(get('amount', 'value')),
            'phone': ''.join(c for c in str(get('phonenumber', 'phone', 'msisdn', 'recipient') or '') if c.isdigit()),
            'receipt': str(get('providerreference', 'mpesareceiptnumber', 'mpesareceipt', 'transactionid', 'reference', 'receipt', 'checkoutrequestid') or '').strip().upper(),
            'code': int(num(code)) or None,
            'success': status in ('SUCCESS', 'COMPLETE', 'COMPLETED', 'PAID', 'CONFIRMED'),
            'failed': status in ('FAILED', 'FAILURE', 'CANCELED', 'CANCELLED', 'REJECTED', 'DECLINED', 'TIMEOUT')}

FAIL_REASON = {1: 'insufficient', 1032: 'cancelled', 1037: 'timeout', 2001: 'wrong_pin', 1001: 'busy', 1019: 'expired'}
def _mark(ref, status, reason=''):
    st.x("UPDATE payments SET status=?,extra=? WHERE ref=? AND status IN('pending','expired')", (status, reason, ref))

def _receipt(p):
    try:
        from . import mailer; mailer.receipt(p['ref'])
    except Exception as e: print('receipt failed', e)

def settle_deposit(cb):
    """-> result string. Idempotent: safe to call for every repeated callback."""
    p = st.q('SELECT * FROM payments WHERE ref=? AND provider=?', (cb['ref'], 'finoq'), True)
    if not p: print('finoq webhook: no payment matches', cb['ref']); return 'unknown'
    if cb['success']:
        if p['status'] not in ('pending', 'expired'): return 'duplicate'
        if not cb['amount'] > 0: print('finoq: success without amount, not credited', p['ref']); return 'no_amount'
        if cb['phone'] and p['phone'] and cb['phone'][-9:] != ''.join(c for c in p['phone'] if c.isdigit())[-9:]:
            print('finoq: phone mismatch, not credited', p['ref']); return 'phone_mismatch'
        if cb['amount'] < p['amount']:
            st.x("UPDATE payments SET status='underpaid',receipt=? WHERE ref=? AND status IN('pending','expired')", (cb['receipt'] or None, p['ref'])); return 'underpaid'
        n = st.x("UPDATE payments SET status='paid',receipt=?,paid_at=? WHERE ref=? AND status IN('pending','expired')", (cb['receipt'] or None, int(time.time()), p['ref']), count=True)
        if not n: return 'duplicate'
        try: activate(p['uid'], p['plan'])
        except Exception:                                  # paid but not delivered: reopen so a retry can deliver
            st.x("UPDATE payments SET status='expired' WHERE ref=? AND status='paid'", (p['ref'],)); raise
        _receipt(p)
        return 'paid'
    if cb['failed']:
        if p['status'] != 'pending': return 'duplicate'
        _mark(p['ref'], 'failed', FAIL_REASON.get(cb['code'], 'other')); return 'failed'
    return 'waiting'

def check_status(p):
    """Ask FinoQ about one payment whose webhook may have been missed. Unknown is never treated as failure."""
    if not p.get('checkout_id') or not ready(): return None
    st.x('UPDATE payments SET last_check=? WHERE ref=?', (int(time.time()), p['ref']))
    try:
        r = requests.post(base() + '/api/global/transaction-status', json={'request_id': p['checkout_id']}, headers=_head(), timeout=15)
        j = r.json() if r.status_code < 300 else None
    except Exception as e: print('finoq status check failed', e); return None
    if not j: return None
    cb = parse_webhook(j); cb['ref'] = p['ref']
    if cb['success']: cb['amount'] = cb['amount'] or p['amount']; cb['phone'] = ''
    return settle_deposit(cb) if (cb['success'] or cb['failed']) else 'waiting'

def reconcile():
    now = int(time.time())
    for p in st.q("SELECT * FROM payments WHERE provider='finoq' AND status IN('pending','expired') AND checkout_id IS NOT NULL AND created>=? AND created<=? ORDER BY created LIMIT 25", (now - 6 * 3600, now - 120)):
        try: check_status(p)
        except Exception as e: print('reconcile failed', p['ref'], e)
    st.x("UPDATE payments SET status='expired',extra='no_response' WHERE provider='finoq' AND status='pending' AND created<?", (now - 15 * 60,))
    for p in st.q("SELECT * FROM payments WHERE provider='paypal' AND status='pending' AND checkout_id IS NOT NULL AND created>=? AND created<=? ORDER BY created LIMIT 25", (now - 4 * 3600, now - 60)):
        try: paypal_recover(p)
        except Exception as e: print('paypal reconcile failed', p['ref'], e)
    st.x("UPDATE payments SET status='expired',extra='no_response' WHERE provider='paypal' AND status='pending' AND created<?", (now - 4 * 3600,))

# ---------- PayPal (Orders v2) ----------
def _pp_base(): return 'https://api-m.paypal.com' if (os.getenv('PAYPAL_ENV') or 'live').strip().lower() == 'live' else 'https://api-m.sandbox.paypal.com'
def paypal_ready(): return bool(_env('PAYPAL_CLIENT_ID') and _env('PAYPAL_SECRET') and _env('BASE_URL').startswith('http'))
def _pp_token():
    r = requests.post(_pp_base() + '/v1/oauth2/token', data={'grant_type': 'client_credentials'}, auth=(_env('PAYPAL_CLIENT_ID'), _env('PAYPAL_SECRET')), timeout=25)
    if r.status_code >= 300: print('paypal auth failed', r.status_code, r.text[:200])      # wrong keys, or live keys with PAYPAL_ENV=sandbox (or the reverse)
    r.raise_for_status(); return r.json()['access_token']
def _pp_get(order_id):
    r = requests.get(f'{_pp_base()}/v2/checkout/orders/{order_id}', headers={'Authorization': 'Bearer ' + _pp_token()}, timeout=25)
    return r.json() if r.status_code < 300 else None

def _pp_code(r):
    """Short reason from a PayPal error answer. Safe to show, never holds a key. e.g. http401-invalid_client, http422-CURRENCY_NOT_SUPPORTED."""
    try: j = r.json()
    except Exception: j = {}
    if not isinstance(j, dict): j = {}
    d = j.get('details'); why = ''
    if isinstance(d, list) and d and isinstance(d[0], dict): why = d[0].get('issue') or ''
    why = why or j.get('error') or j.get('name') or ''
    return ('http%s-%s' % (r.status_code, ''.join(c for c in str(why) if c.isalnum() or c in '_-')))[:60].rstrip('-')

def paypal_create(uid, pid):
    p = plan(pid)
    if not p: raise ValueError('bad plan')
    if not paypal_ready(): raise RuntimeError('PayPal is not set up yet')
    ref = _new(uid, 'paypal', pid, p['usd'], 'USD'); b = _env('BASE_URL').rstrip('/')
    body = {'intent': 'CAPTURE', 'purchase_units': [{'reference_id': ref, 'custom_id': ref, 'description': ('spaceXBot ' + str(p['name']) + ' (' + str(p['days']) + ' days)')[:120], 'soft_descriptor': 'SPACEXBOT',
                        'amount': {'currency_code': 'USD', 'value': f"{p['usd']:.2f}"}}],
            'application_context': {'brand_name': 'spaceXBot', 'shipping_preference': 'NO_SHIPPING', 'landing_page': 'GUEST_CHECKOUT', 'return_url': f'{b}/api/pay/paypal/return', 'cancel_url': f'{b}/?paid=cancel', 'user_action': 'PAY_NOW'}}
    code = 'unknown'
    try:
        r = requests.post(_pp_base() + '/v2/checkout/orders', json=body, headers={'Authorization': 'Bearer ' + _pp_token(), 'PayPal-Request-Id': ref}, timeout=25)
        if r.status_code >= 300: print('paypal refused the order', r.status_code, r.text[:300]); code = _pp_code(r); raise RuntimeError('refused')
        o = r.json(); code = 'no-approve-link'; link = next(l['href'] for l in o['links'] if l['rel'] in ('approve', 'payer-action'))
    except Exception as e:
        resp = getattr(e, 'response', None)
        if resp is not None and hasattr(resp, 'status_code'): code = _pp_code(resp)      # sign-in refused: wrong keys, or live keys with PAYPAL_ENV=sandbox
        elif code == 'unknown': code = 'net-' + type(e).__name__                         # no answer from PayPal at all
        print('paypal create failed:', code, '|', str(e)[:200])
        _mark(ref, 'failed', 'not_sent'); raise RuntimeError('PayPal is unavailable right now (' + code + ')') from e
    st.x('UPDATE payments SET checkout_id=? WHERE ref=?', (o['id'], ref))
    return ref, link

def _pp_state(p, j):
    """-> 'paid' | 'pending' | 'failed' | 'underpaid', read from a PayPal order. Anything unclear is 'pending', never 'failed'."""
    try: cap = j['purchase_units'][0]['payments']['captures'][0]
    except (KeyError, IndexError, TypeError): cap = None
    if not cap: return 'failed' if j.get('status') == 'VOIDED' else 'pending'
    cs = cap.get('status')
    if cs == 'COMPLETED':
        if j.get('status') != 'COMPLETED': return 'pending'
        try: good = cap['amount']['currency_code'] == 'USD' and float(cap['amount']['value']) >= float(p['amount'])
        except (KeyError, TypeError, ValueError): good = False
        return 'paid' if good else 'underpaid'          # underpaid = money captured but not the price: needs a human (refund or grant)
    if cs == 'PENDING': return 'pending'                # e.g. under review: PayPal may still complete it
    return 'failed'

def _pp_apply(p, state, j):
    """Move a pending PayPal payment to its new state once. Only the update that wins credits the plan; a repeat does nothing."""
    if state == 'pending': return
    try: cap_id = j['purchase_units'][0]['payments']['captures'][0].get('id') or ''
    except (KeyError, IndexError, TypeError, AttributeError): cap_id = ''
    n = st.x("UPDATE payments SET status=?,paid_at=?,receipt=? WHERE ref=? AND status='pending'",
             (state, int(time.time()) if state == 'paid' else None, (cap_id or p['checkout_id']) if state in ('paid', 'underpaid') else None, p['ref']), count=True)
    if state == 'paid' and n:
        try: activate(p['uid'], p['plan'])
        except Exception:                                # paid but not delivered: reopen so the next check delivers it
            st.x("UPDATE payments SET status='pending' WHERE ref=? AND status='paid'", (p['ref'],)); raise
        _receipt(p)

def _row(ref): return st.q('SELECT * FROM payments WHERE ref=?', (ref,), True)

def paypal_capture(order_id):
    """-> payment row or None. Credits only when PayPal says COMPLETED for at least the price in USD. A lost answer is re-checked with PayPal."""
    p = st.q("SELECT * FROM payments WHERE checkout_id=? AND provider='paypal'", (order_id,), True)
    if not p: return None
    if p['status'] != 'pending': return p
    st.x('UPDATE payments SET last_check=? WHERE ref=?', (int(time.time()), p['ref']))
    try:
        r = requests.post(f'{_pp_base()}/v2/checkout/orders/{order_id}/capture', headers={'Authorization': 'Bearer ' + _pp_token(), 'Content-Type': 'application/json', 'PayPal-Request-Id': p['ref'] + '-cap'}, timeout=25)
    except Exception as e: print('paypal capture error', e); return p            # stay pending, the status check retries
    if r.status_code >= 500: return p
    try: j = r.json()
    except Exception: j = {}
    if r.status_code >= 400:
        issues = ' '.join(str(d.get('issue', '')) for d in (j.get('details') or []) if isinstance(d, dict))
        if 'ORDER_ALREADY_CAPTURED' in issues:            # the first answer was lost: ask PayPal, do not guess
            try: j = _pp_get(order_id) or {}
            except Exception as e: print('paypal re-check failed', e); return p
            state = _pp_state(p, j) if j else 'pending'
        elif 'ORDER_NOT_APPROVED' in issues or 'PAYER_ACTION_REQUIRED' in issues: return p
        else: print('paypal capture refused', r.status_code, issues or str(j)[:200]); state = 'failed'
    else: state = _pp_state(p, j)
    try: _pp_apply(p, state, j)
    except Exception as e: print('paypal credit failed, will retry', p['ref'], e)
    return _row(p['ref'])

def paypal_recover(p):
    """The browser never came back from PayPal (tab closed, signal lost). Ask PayPal: capture if approved, credit if already captured."""
    if p['status'] != 'pending' or not p.get('checkout_id') or not paypal_ready(): return None
    st.x('UPDATE payments SET last_check=? WHERE ref=?', (int(time.time()), p['ref']))
    try: j = _pp_get(p['checkout_id'])
    except Exception as e: print('paypal status check failed', e); return None
    if not j: return None
    if j.get('status') == 'APPROVED': return paypal_capture(p['checkout_id'])
    try: _pp_apply(p, _pp_state(p, j), j)
    except Exception as e: print('paypal credit failed, will retry', p['ref'], e)
    return _row(p['ref'])

def health():
    """Setup check for the admin: which settings are wrong. Never returns a secret value."""
    from urllib.parse import urlparse
    from . import sbauth
    base = _env('BASE_URL'); bad = []
    if not st.PG: bad.append('DATABASE_URL is not set. Users, payments and plans are wiped on every redeploy.')
    if not base.startswith('https://'): bad.append('BASE_URL must be your https Render address.')
    if not sbauth.configured(): bad.append('SUPABASE_URL or SUPABASE_ANON_KEY is missing. Nobody can sign in.')
    if not os.getenv('SUPABASE_SERVICE_KEY'): bad.append('SUPABASE_SERVICE_KEY is missing. Deleting an account will not remove its login.')
    if not os.getenv('EA_KEY'): bad.append('EA_KEY is missing. The MT5 EA cannot connect.')
    if not (os.getenv('RESEND_API_KEY') and os.getenv('MAIL_FROM')): bad.append('RESEND_API_KEY or MAIL_FROM is missing. Receipts and trade alert emails are off.')
    if not _env('PAYHERO_API_KEY', 'PAYHERO_USER'): bad.append('PAYHERO_API_KEY is missing. M-Pesa is off.')
    if not _env('PAYHERO_API_SECRET', 'PAYHERO_PASS'): bad.append('PAYHERO_API_SECRET is missing. M-Pesa is off.')
    if not _channel(): bad.append('PAYHERO_CHANNEL_ID is missing or not a number. M-Pesa is off.')
    if not cb_secret(): bad.append('PAYHERO_CALLBACK_SECRET is missing. M-Pesa is off, because confirmations would be refused.')
    cu = _env('CALLBACK_URL', 'PAYHERO_CALLBACK_URL').strip('"\'')
    if cu and base and urlparse(cu).netloc != urlparse(base).netloc: bad.append('CALLBACK_URL points to a different site than BASE_URL, so payment confirmations would go there. Delete CALLBACK_URL.')
    if _env('PAYHERO_PROVIDER').lower() not in ('', 'm-pesa', 'sasapay'): bad.append('PAYHERO_PROVIDER should be m-pesa or sasapay.')
    if not (_env('PAYPAL_CLIENT_ID') and _env('PAYPAL_SECRET')): bad.append('PAYPAL_CLIENT_ID or PAYPAL_SECRET is missing. PayPal is off.')
    if os.getenv('DEV_AUTH') == '1': bad.append('DEV_AUTH is on. Anyone can sign in as anyone. Remove it.')
    return {'ok': not bad, 'problems': bad, 'database': 'postgres' if st.PG else 'temporary sqlite', 'mpesa_ready': ready(), 'paypal_ready': paypal_ready(),
            'paypal_env': (_env('PAYPAL_ENV') or 'live').lower(), 'mpesa_provider': 'sasapay' if _env('PAYHERO_PROVIDER').lower() == 'sasapay' else 'm-pesa'}
