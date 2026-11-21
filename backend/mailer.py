"""Email through the Resend API: trade alerts and payment receipts.
Nothing here raises. A failed email must never break a trade or a payment."""
import os, json, time, html, threading, datetime as dt
import requests
from . import store as st

API = 'https://api.resend.com/emails'
def _key(): return os.getenv('RESEND_API_KEY', '').strip()
def _from(): return os.getenv('MAIL_FROM', '').strip()
def configured(): return bool(_key() and _from())
def _cap(name, d):
    try: return int(os.getenv(name, d))
    except ValueError: return d

def _day_key(): return 'mail:' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')
def _reserve(kind):
    """Count this email against today's cap. Alerts stop at MAIL_ALERT_CAP; receipts may go on to MAIL_HARD_CAP, so alerts can never use up the room receipts and sign-in codes need."""
    k = _day_key()
    st.x('INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=CAST(CAST(kv.v AS INTEGER)+1 AS TEXT)', (k, '1'))
    ok = int(st.get(k) or 0) <= (_cap('MAIL_HARD_CAP', 90) if kind == 'receipt' else _cap('MAIL_ALERT_CAP', 60))
    if not ok: _refund()
    return ok
def _refund(): st.x('UPDATE kv SET v=CAST(CAST(v AS INTEGER)-1 AS TEXT) WHERE k=?', (_day_key(),))

def _reason(code, name, msg):
    if code == 401: return 'The Resend API key is wrong or missing (RESEND_API_KEY).'
    if code == 403: return 'Resend refused it: the sender domain is not verified, or the key is restricted (MAIL_FROM, RESEND_API_KEY).'
    if code == 422: return 'Resend rejected the email fields. Check MAIL_FROM looks like: spaceXBot <alerts@yourdomain.com>.'
    if code == 429: return 'Resend rate limit or daily quota reached.'
    if code >= 500: return 'Resend is having trouble. Try again later.'
    return 'Resend said: ' + (msg or name or str(code))[:160]

def send(to, subject, html_body, text, idem=None, kind='alert'):
    """-> (ok, email id or reason). kind: alert, receipt, or test (a test ignores the daily cap)."""
    try:
        if not configured(): return False, 'Email is not set up (RESEND_API_KEY and MAIL_FROM).'
        if not to or '@' not in to: return False, 'No email address.'
        if kind != 'test' and not _reserve(kind): return False, 'Daily email cap reached.'
        h = {'Authorization': 'Bearer ' + _key(), 'Content-Type': 'application/json'}
        if idem: h['Idempotency-Key'] = idem[:256]
        body = {'from': _from(), 'to': [to], 'subject': subject[:200], 'html': html_body, 'text': text}
        if os.getenv('MAIL_REPLY_TO', '').strip(): body['reply_to'] = os.getenv('MAIL_REPLY_TO').strip()
        try: r = requests.post(API, json=body, headers=h, timeout=10)
        except Exception as e:
            if kind != 'test': _refund()
            return False, 'Could not reach Resend (' + type(e).__name__ + ').'
        try: j = r.json()
        except ValueError: j = {}
        if kind != 'test' and not (r.status_code < 300 and j.get('id')): _refund()
        if r.status_code < 300 and j.get('id'): return True, j['id']
        if r.status_code == 409: return True, 'duplicate'          # same idempotency key: it was already sent
        return False, _reason(r.status_code, j.get('name', ''), j.get('message', ''))
    except Exception as e:
        print('mail error', e); return False, 'Email error.'

def _base(): return os.getenv('BASE_URL', '').strip().rstrip('/') or 'https://spacexbot-gn73.onrender.com'

def _page(heading, rows, foot, img=None):
    e = html.escape
    tr = ''.join('<tr><td style="padding:9px 14px 9px 0;color:#7b86a0;font-size:14px;border-bottom:1px solid #EEF1F8">%s</td><td style="padding:9px 0;font-weight:700;color:#1E2330;font-size:14px;border-bottom:1px solid #EEF1F8">%s</td></tr>' % (e(a), e(b)) for a, b in rows)
    pic = ('<tr><td align="center" style="padding:14px 20px 0"><img src="%s/static/email/%s.gif" width="480" alt="spaceXBot illustration" style="display:block;width:100%%;max-width:480px;height:auto;border:0;border-radius:18px;background:#10151E"></td></tr>' % (_base(), e(img))) if img else ''
    h = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light only"></head>'
         '<body style="margin:0;padding:0;background:#EEF1FB"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0" bgcolor="#EEF1FB"><tr><td align="center" style="padding:26px 12px">'
         '<table role="presentation" width="520" cellpadding="0" cellspacing="0" bgcolor="#FFFFFF" style="width:100%%;max-width:520px;background:#FFFFFF;border-radius:24px;border:1px solid #E1E6F4">'
         '<tr><td style="padding:22px 28px 0;font-family:Arial,Helvetica,sans-serif;font-size:20px;font-weight:800;color:#1E2330"><span style="color:#1B9A47">&#9679;</span>&nbsp;spaceXBot</td></tr>%s'
         '<tr><td style="padding:20px 28px 0;font-family:Arial,Helvetica,sans-serif;color:#1E2330;text-align:center"><h1 style="margin:0;font-size:23px;line-height:1.3;font-weight:800">%s</h1></td></tr>'
         '<tr><td style="padding:16px 32px 6px;font-family:Arial,Helvetica,sans-serif"><table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">%s</table></td></tr>'
         '<tr><td style="padding:16px 32px 26px;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.7;color:#94a0b8;text-align:center">%s</td></tr>'
         '</table></td></tr></table></body></html>') % (pic, e(heading), tr, e(foot))
    t = heading + '\n\n' + '\n'.join('%s: %s' % (a, b) for a, b in rows) + '\n\n' + foot
    return h, t

# ---------- trade alerts ----------
def _recipients():
    """Subscribers (and admins) who kept Trade alerts on. Default is on."""
    now = time.time(); admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}; out = []
    for r in st.q('SELECT uid,email,notif,plan_until FROM users'):
        em = (r['email'] or '').strip()
        if not em or not ((r['plan_until'] or 0) > now or em.lower() in admins): continue
        try: n = json.loads(r['notif'] or '{}')
        except ValueError: n = {}
        if n.get('trade', 1) in (0, False, '0'): continue
        out.append((r['uid'], em))
    return out

def _alerts(title, body, key=None, only=None):
    if not configured(): return 0
    h, t = _page(title, [('Details', body)], 'You get this because Trade alerts are on. Turn them off in Profile > Notifications. Not financial advice; trading can lose money.', img='alert')
    n = 0
    for uid, em in _recipients():
        if only and uid != only: continue
        ok, info = send(em, 'spaceXBot: ' + title, h, t, idem=(key + '/' + uid) if key else None, kind='alert')
        if ok: n += 1
        elif info.startswith('Daily email cap'): print('[mail] alert cap reached for today'); break
        else: print('[mail] alert not sent:', info)
    return n

def trade_alert(title, body, key=None, only=None):
    if configured(): threading.Thread(target=_alerts, args=(title, body, key, only), daemon=True).start()

# ---------- receipts ----------
def _receipt_now(ref):
    p = st.q('SELECT * FROM payments WHERE ref=?', (ref,), True)
    if not p or p['status'] != 'paid': return False
    u = st.q('SELECT email,name,plan_until FROM users WHERE uid=?', (p['uid'],), True)
    if not u or not u['email']: return False
    from . import payments as pay
    pl = pay.plan(p['plan']) or {}; cur = (p['currency'] or '').upper(); amt = float(p['amount'] or 0)
    until = dt.datetime.fromtimestamp(int(u['plan_until'] or 0), dt.timezone.utc).strftime('%d %b %Y')
    rows = [('Plan', pl.get('name') or p['plan'] or ''), ('Paid', ('%s %s' % (cur, format(amt, ',.0f' if cur == 'KES' else ',.2f'))).strip()),
            ('Method', 'M-Pesa' if p['provider'] == 'finoq' else 'PayPal')]
    if p.get('receipt'): rows.append(('Receipt', str(p['receipt'])))
    rows += [('Reference', p['ref']), ('Access until', until)]
    h, t = _page('Payment received. Thank you!', rows, 'Keep this email as your receipt. Questions? Reply to this email.', img='receipt')
    ok, info = send(u['email'], 'spaceXBot receipt', h, t, idem='receipt/' + ref, kind='receipt')
    if not ok: print('[mail] receipt not sent:', ref, info)
    return ok

def receipt(ref):
    if configured(): threading.Thread(target=_receipt_now, args=(ref,), daemon=True).start()
