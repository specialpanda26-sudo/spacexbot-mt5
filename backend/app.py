import os, time, json, hmac, threading, functools
from flask import Flask, request, jsonify, send_from_directory, Response, redirect
from . import store as st, bars, brain, risk, fb, news, stats, payments as pay

app = Flask(__name__, static_folder='../static', static_url_path='/static'); app.json.compact = True
st.init()
EA_KEY = os.getenv('EA_KEY', ''); ADMINS = {e.strip().lower() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()}
_last_scan = {}

def _ea_ok(): return bool(EA_KEY) and hmac.compare_digest(request.headers.get('X-EA-Key', ''), EA_KEY)

def sub_tokens():
    now = int(time.time())
    return [r['fcm'] for r in st.q('SELECT fcm,email,plan_until FROM users WHERE fcm IS NOT NULL')
            if (r['plan_until'] or 0) > now or (r['email'] or '').lower() in ADMINS]

def user():
    h = request.headers.get('Authorization', '')
    u = fb.verify(h[7:]) if h.startswith('Bearer ') else None
    if not u: return None
    if not st.q('SELECT 1 FROM users WHERE uid=?', (u['uid'],), True):
        st.x('INSERT INTO users(uid,email,name,created) VALUES(?,?,?,?)', (u['uid'], u['email'], u['name'], int(time.time())))
    u['admin'] = u['email'].lower() in ADMINS
    row = st.q('SELECT plan_until FROM users WHERE uid=?', (u['uid'],), True); u['plan_until'] = row['plan_until'] or 0
    u['active'] = u['admin'] or u['plan_until'] > time.time()
    return u

def need(admin=False, active=False):
    def deco(f):
        @functools.wraps(f)
        def w(*a, **k):
            u = user()
            if not u: return jsonify(error='sign in required'), 401
            if admin and not u['admin']: return jsonify(error='admin only'), 403
            if active and not u['active']: return jsonify(error='subscription required'), 402
            return f(u, *a, **k)
        return w
    return deco

# ---------------- static / config ----------------
@app.get('/')
def home(): return send_from_directory('../static', 'index.html')
@app.get('/healthz')
def hz(): return 'ok'
@app.get('/config.js')
def cfgjs():
    c = os.getenv('FIREBASE_WEB_CONFIG', '{}'); v = os.getenv('FIREBASE_VAPID_KEY', '')
    return Response(f'window.SXB={{fb:{c},vapid:{json.dumps(v)},plans:{json.dumps(pay.plans())}}};', mimetype='application/javascript')
@app.get('/firebase-messaging-sw.js')
def sw():
    c = os.getenv('FIREBASE_WEB_CONFIG', '{}')
    js = ("importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js','https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js');"
          f"firebase.initializeApp({c});const m=firebase.messaging();"
          "m.onBackgroundMessage(p=>self.registration.showNotification(p.notification.title,{body:p.notification.body}));")
    return Response(js, mimetype='application/javascript')

# ---------------- EA bridge ----------------
def _scan(sym):
    if time.time() - _last_scan.get(sym, 0) < 20: return
    _last_scan[sym] = time.time()
    m15 = bars.get(sym, 'M15'); h1 = bars.get(sym, 'H1')
    if not m15: return
    key = f'lastbar:{sym}'
    if st.get(key) == str(m15[-1]['t']): return          # already evaluated this candle
    st.put(key, m15[-1]['t'])
    ok, why = risk.global_gate()
    if not ok: return
    off = {x for x in (st.get('strategies_off') or '').split(',') if x}
    if st.get('auto_disable') == '1': off |= stats.losers(int(st.fget('auto_disable_min_trades')))
    s = brain.evaluate(m15, h1, int(st.fget('min_confluence')), st.fget('rr'), off)
    if not s: return
    ok, why = risk.symbol_gate(sym, s['side'])
    if not ok: print('skip', sym, s['side'], why); return
    st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
         (sym, s['side'], s['entry'], s['sl'], s['tp'], st.fget('risk_pct'), s['strategy'], s['score'], 'pending', int(time.time())))
    fb.push(sub_tokens(), f"{s['side'].upper()} {sym}", f"Entry {s['entry']}  SL {s['sl']}  TP {s['tp']}  ({s['strategy']})")

@app.post('/api/ea/sync')
def ea_sync():
    if not _ea_ok(): return jsonify(error='bad key'), 401
    d = request.get_json(force=True, silent=True) or {}
    st.set_acct(d.get('account') or {})
    for sym, tfs in (d.get('bars') or {}).items():
        for tf, rows in tfs.items(): bars.merge(sym, tf, rows)
    for sym in (d.get('bars') or {}): _scan(sym)
    now = int(time.time())
    st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent') AND created<?", (now - 180,))
    s = st.q("SELECT id,symbol,side,sl,tp,risk_pct FROM signals WHERE status='pending' ORDER BY id LIMIT 1", one=True)
    if s: st.x("UPDATE signals SET status='sent' WHERE id=?", (s['id'],))
    return jsonify(signal=s, bot=st.get('bot_enabled') == '1', symbols=st.get('symbols'))

@app.post('/api/ea/report')
def ea_report():
    if not _ea_ok(): return jsonify(error='bad key'), 401
    d = request.get_json(force=True, silent=True) or {}; sid = d.get('id'); stt = d.get('status')
    if stt == 'open': st.x("UPDATE signals SET status='open',ticket=?,lots=?,fill=? WHERE id=?", (str(d.get('ticket')), d.get('lots'), d.get('price'), sid))
    elif stt == 'rejected': st.x("UPDATE signals SET status='rejected',note=? WHERE id=?", (str(d.get('reason'))[:120], sid))
    elif stt == 'closed': st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=?", (d.get('pnl'), int(time.time()), sid))
    if stt in ('open', 'closed'):
        s = st.q('SELECT * FROM signals WHERE id=?', (sid,), True)
        if s:
            title = f"{s['symbol']} {'opened' if stt == 'open' else 'closed'}"
            body = f"{s['side'].upper()} lots {s['lots']}" if stt == 'open' else f"P/L {s['pnl']}"
            fb.push(sub_tokens(), title, body)
    return jsonify(ok=True)

# ---------------- app API ----------------
@app.get('/api/me')
@need()
def me(u):
    a = st.acct(); online = time.time() - a.get('seen', 0) < 120
    out = {'email': u['email'], 'admin': u['admin'], 'active': u['active'], 'plan_until': u['plan_until']}
    if u['active']:
        since = st.day_start()
        out.update(bot=st.get('bot_enabled') == '1', ea_online=online, account=a if u['admin'] else {'demo': a.get('demo')},
                   today=st.q("SELECT COUNT(*) n, COALESCE(SUM(pnl),0) pnl FROM signals WHERE created>=?", (since,), True))
        if u['admin']: out['settings'] = {k: st.get(k) for k in st.DEFAULTS}
    return jsonify(out)

@app.post('/api/me/fcm')
@need()
def set_fcm(u):
    st.x('UPDATE users SET fcm=? WHERE uid=?', ((request.json or {}).get('token'), u['uid'])); return jsonify(ok=True)

@app.get('/api/signals')
@need(active=True)
def signals(u): return jsonify(st.q('SELECT id,symbol,side,entry,sl,tp,strategy,score,status,created,pnl FROM signals ORDER BY id DESC LIMIT 50'))

@app.post('/api/admin/settings')
@need(admin=True)
def admin_set(u):
    for k, v in (request.json or {}).items():
        if k in st.DEFAULTS: st.put(k, v)
    return jsonify({k: st.get(k) for k in st.DEFAULTS})

@app.get('/api/status')
@need(active=True)
def status(u):
    """Everything the Bot tab's gates card shows, from the real gate code."""
    a = st.acct(); now = time.time(); bal = float(a.get('balance') or 0); since = st.day_start()
    dpnl = st.q("SELECT COALESCE(SUM(pnl),0) p FROM signals WHERE closed>=?", (since,), True)['p']
    ok, why = risk.global_gate()
    nh = news.next_high(now)
    return jsonify(bot=st.get('bot_enabled') == '1', ea_online=now - a.get('seen', 0) < 120, can_trade=ok, why=why,
                   day_loss_pct=round(max(0, -dpnl) / bal * 100, 2) if bal else 0, day_loss_limit=st.fget('max_daily_loss_pct'),
                   open=int(a.get('open', 0)), max_open=int(st.fget('max_open')), news_next=nh, news_loaded=news.loaded(),
                   news_lock=st.get('news_lock') == '1', exposure=risk.exposure(), demo=a.get('demo'),
                   strategies=[f.__name__ for f in __import__('backend.strategies', fromlist=['ALL']).ALL], off=[x for x in (st.get('strategies_off') or '').split(',') if x])

@app.get('/api/stats')
@need(active=True)
def stats_api(u): return jsonify(summary=stats.summary(), by_strategy=stats.by_strategy())

@app.post('/api/admin/plans')
@need(admin=True)
def admin_plans(u):
    try: return jsonify(pay.set_plans((request.json or {}).get('plans') or []))
    except (ValueError, TypeError, KeyError): return jsonify(error='bad plans'), 400

@app.post('/api/admin/grant')
@need(admin=True)
def admin_grant(u):
    j = request.json or {}; em = str(j.get('email', '')).strip().lower(); days = int(j.get('days', 0))
    r = st.q('SELECT uid FROM users WHERE lower(email)=?', (em,), True)
    if not r or not (0 < days <= 3650): return jsonify(error='user not found (they must sign in once) or bad days'), 400
    pay.activate(r['uid'], None, days); return jsonify(ok=True)

# ---------------- payments ----------------
@app.get('/api/plans')
def plans(): return jsonify(pay.plans())

@app.post('/api/pay/mpesa')
@need()
def p_mpesa(u):
    j = request.json or {}
    try: return jsonify(ref=pay.stk_push(u['uid'], j.get('plan'), j.get('phone')), msg='Check your phone for the M-Pesa prompt')
    except ValueError as e: return jsonify(error=str(e)), 400
    except PermissionError as e: return jsonify(error=str(e)), 429
    except RuntimeError as e: return jsonify(error=str(e)), 502

@app.post('/api/webhooks/payhero')
@app.post('/api/pay/payhero/callback')
def p_cb():
    sec = pay.cb_secret()
    if not sec or not hmac.compare_digest(request.args.get('s', ''), sec): return 'no', 403
    cb = pay.parse_webhook(request.get_json(force=True, silent=True) or {})
    print('finoq webhook:', cb['ref'] or '(no ref)', cb['status'] or '?', 'amount', cb['amount'] or '?')
    if not cb['ref']: return jsonify(ok=True)
    try: return jsonify(ok=True, result=pay.settle_deposit(cb))
    except Exception as e: print('settle failed', cb['ref'], e); return jsonify(ok=False, error='retry'), 500     # non-2xx makes the gateway retry

@app.post('/api/pay/paypal')
@need()
def p_pp(u):
    try: ref, url = pay.paypal_create(u['uid'], (request.json or {}).get('plan')); return jsonify(ref=ref, url=url)
    except ValueError as e: return jsonify(error=str(e)), 400
    except Exception as e: print('paypal create failed', e); return jsonify(error='PayPal is unavailable right now'), 502

@app.get('/api/pay/paypal/return')
def p_pp_ret():
    p = pay.paypal_capture(request.args.get('token', ''))
    return redirect('/?paid=' + ('ok' if p and p['status'] == 'paid' else 'fail'))

@app.get('/api/pay/status')
@need()
def p_status(u):
    p = st.q('SELECT * FROM payments WHERE ref=? AND uid=?', (request.args.get('ref'), u['uid']), True)
    if not p: return jsonify(status='unknown')
    # webhook missed or slow? ask the gateway at most every 15s
    if p['status'] == 'pending' and p['provider'] == 'finoq' and p['checkout_id'] and time.time() - (p['last_check'] or 0) > 15 and time.time() - p['created'] > 10:
        try: pay.check_status(p)
        except Exception as e: print('status check failed', e)
        p = st.q('SELECT * FROM payments WHERE ref=?', (p['ref'],), True)
    return jsonify(status=p['status'], plan=p['plan'], amount=p['amount'], currency=p['currency'], receipt=p['receipt'], reason=p['extra'] if p['status'] == 'failed' else None)

def _reconciler():
    while True:
        time.sleep(120)
        try: pay.reconcile()
        except Exception as e: print('reconcile loop', e)
threading.Thread(target=_reconciler, daemon=True).start()
