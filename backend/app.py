import os, time, json, hmac, threading, functools
from flask import Flask, request, jsonify, send_from_directory, Response, redirect
from . import store as st, notifart, bars, brain, risk, sbauth, news, stats, accounts, push, payments as pay

app = Flask(__name__, static_folder='../static', static_url_path='/static'); app.json.compact = True
st.init()
EA_KEY = os.getenv('EA_KEY', ''); ADMINS = {e.strip().lower() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()}
_last_scan = {}

def _same(a, b): return hmac.compare_digest(str(a).encode('utf-8'), str(b).encode('utf-8'))     # str compare_digest crashes on non-ASCII
def _j(force=False):
    """The JSON body as a dict. Anything else (a list, a number, no body) becomes {} so a bad request cannot crash a route."""
    j = request.get_json(force=force, silent=True)
    return j if isinstance(j, dict) else {}
def _ea_ok(): return bool(EA_KEY) and _same(request.headers.get('X-EA-Key', ''), EA_KEY)

def user():
    h = request.headers.get('Authorization', '')
    u = sbauth.verify(h[7:]) if h.startswith('Bearer ') else None
    if not u: return None
    if not st.q('SELECT 1 FROM users WHERE uid=?', (u['uid'],), True):
        st.x('INSERT INTO users(uid,email,name,created,onboarded) VALUES(?,?,?,?,0) ON CONFLICT(uid) DO NOTHING', (u['uid'], u['email'], u['name'], int(time.time())))
    u['admin'] = bool(u.get('verified')) and u['email'].lower() in ADMINS      # an unverified email can never be admin
    row = st.q('SELECT plan_until FROM users WHERE uid=?', (u['uid'],), True); u['plan_until'] = row['plan_until'] or 0
    u['active'] = u['admin'] or u['plan_until'] > time.time()
    return u

def need(admin=False, active=False, verified=False):
    def deco(f):
        @functools.wraps(f)
        def w(*a, **k):
            u = user()
            if not u: return jsonify(error='sign in required'), 401
            if (verified or admin) and not u.get('verified'): return jsonify(error='verify your email first'), 403
            if admin and not u['admin']: return jsonify(error='admin only'), 403
            if active and not u['active']: return jsonify(error='subscription required'), 402
            return f(u, *a, **k)
        return w
    return deco

# ---------------- static / config ----------------
@app.get('/')
def home(): return send_from_directory('../static', 'index.html')

@app.get('/favicon.ico')
def favicon(): return send_from_directory('../static/brand', 'favicon.ico')
@app.get('/healthz')
def hz(): return 'ok'
@app.get('/config.js')
def cfgjs():
    return Response(f'window.SXB={{sb:{json.dumps(sbauth.public_config())},gid:{json.dumps(os.getenv("GOOGLE_WEB_CLIENT_ID", ""))},plans:{json.dumps(pay.plans())}}};', mimetype='application/javascript')

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
    sid = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created) VALUES(?,?,?,?,?,?,?,?,?,?)',
         (sym, s['side'], s['entry'], s['sl'], s['tp'], st.fget('risk_pct'), s['strategy'], s['score'], 'pending', int(time.time())))
    sbauth.notify(f"{s['side'].upper()} {sym}", f"Entry {s['entry']}  SL {s['sl']}  TP {s['tp']}  ({s['strategy']})", key=f'sig{sid}-new')

@app.post('/api/ea/sync')
def ea_sync():
    if not _ea_ok(): return jsonify(error='bad key'), 401
    d = _j(True); bz = d.get('bars') if isinstance(d.get('bars'), dict) else {}
    st.set_acct(d.get('account') if isinstance(d.get('account'), dict) else {})
    for sym, tfs in bz.items():
        for tf, rows in (tfs.items() if isinstance(tfs, dict) else ()):
            try: bars.merge(sym, tf, rows)
            except (TypeError, ValueError, IndexError) as e: print('bad bars from EA', sym, tf, e)
    for sym in bz: _scan(sym)
    now = int(time.time())
    st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent') AND created<?", (now - 180,))
    s = st.q("SELECT id,symbol,side,sl,tp,risk_pct FROM signals WHERE status='pending' ORDER BY id LIMIT 1", one=True)
    if s: st.x("UPDATE signals SET status='sent' WHERE id=?", (s['id'],))
    return jsonify(signal=s, bot=st.get('bot_enabled') == '1', symbols=st.get('symbols'))

@app.post('/api/ea/report')
def ea_report():
    if not _ea_ok(): return jsonify(error='bad key'), 401
    d = _j(True); sid = d.get('id'); stt = d.get('status')
    if stt == 'open': st.x("UPDATE signals SET status='open',ticket=?,lots=?,fill=? WHERE id=?", (str(d.get('ticket')), d.get('lots'), d.get('price'), sid))
    elif stt == 'rejected': st.x("UPDATE signals SET status='rejected',note=? WHERE id=?", (str(d.get('reason'))[:120], sid))
    elif stt == 'closed': st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=?", (d.get('pnl'), int(time.time()), sid))
    if stt in ('open', 'closed'):
        s = st.q('SELECT * FROM signals WHERE id=?', (sid,), True)
        if s:
            title = f"{s['symbol']} {'opened' if stt == 'open' else 'closed'}"
            body = f"{s['side'].upper()} lots {s['lots']}" if stt == 'open' else f"P/L {s['pnl']}"
            sbauth.notify(title, body, key=f'sig{sid}-{stt}')
            if stt == 'open': push.notify(1, f'sig{sid}-open', sym=s['symbol'], side=s['side'], entry=s['fill'] or s['entry'], sl=s['sl'], tp=s['tp'], risk=s['risk_pct'])
            else: push.notify({'tp': 2, 'sl': 3}.get(str(d.get('reason')), 4), f'sig{sid}-closed', sym=s['symbol'], pnl=s['pnl'])
    if stt == 'rejected': push.notify(8, f'sig{sid}-skipped', sym=(st.q('SELECT symbol FROM signals WHERE id=?', (sid,), True) or {}).get('symbol', ''), reason=str(d.get('reason') or '')[:80])
    return jsonify(ok=True)

# ---------------- phone notifications ----------------
@app.get('/notif/<name>.png')
def notif_png(name):
    b = notifart.png(name)
    return Response(b, mimetype='image/png', headers={'Cache-Control': 'public, max-age=86400'}) if b else ('', 404)


@app.post('/api/push/token')
@need()
def push_token(u):
    j = _j()
    try: push.save_token(u['uid'], j.get('token'), j.get('platform') or 'android')
    except ValueError as e: return jsonify(error=str(e)), 400
    return jsonify(ok=True)

@app.post('/api/push/unregister')
@need()
def push_unreg(u):
    t = str(_j().get('token') or '')
    if t and st.q('SELECT 1 FROM push_tokens WHERE token=? AND uid=?', (t, u['uid']), True): push.drop_token(t)
    return jsonify(ok=True)

@app.post('/api/admin/push/test')
@need(admin=True)
def push_test(u):
    if not push.configured(): return jsonify(error='FCM_SERVICE_ACCOUNT is not set on the server'), 400
    n, why = push.send(u['uid'], 1, 'Test notification. If you can read this, phone alerts work.', title='spaceXBot test', force=True)
    return jsonify(sent=n, reason=why, devices=len(push.tokens(u['uid']))) if n else (jsonify(error=why or 'not sent', devices=len(push.tokens(u['uid']))), 400)

# ---------------- app API ----------------
@app.get('/api/me')
@need()
def me(u):
    a = st.acct(); online = time.time() - a.get('seen', 0) < 120
    out = {'uid': u['uid'], 'email': u['email'], 'verified': bool(u.get('verified')), 'admin': u['admin'], 'active': u['active'], 'plan_until': u['plan_until'], **accounts.view(u['uid'])}
    out['name'] = out['name'] or u.get('name') or u['email'].split('@')[0]
    if u['active']:
        since = st.day_start()
        out.update(bot=st.get('bot_enabled') == '1', ea_online=online, account=a if u['admin'] else {'demo': a.get('demo')},
                   today=st.q("SELECT COUNT(*) n, COALESCE(SUM(pnl),0) pnl FROM signals WHERE created>=?", (since,), True))
        if u['admin']: out['settings'] = {k: st.get(k) for k in st.DEFAULTS}
    return jsonify(out)

@app.post('/api/me/profile')
@need()
def me_profile(u):
    try: accounts.update(u['uid'], _j())
    except ValueError as e: return jsonify(error=str(e)), 400
    return jsonify(ok=True)

@app.delete('/api/me')
@need()
def me_delete(u):
    if u['admin']: return jsonify(error='Admin accounts cannot be deleted here.'), 400
    accounts.erase(u['uid']); sbauth.delete_user(u['uid']); return jsonify(ok=True)

@app.post('/api/me/signout-others')
@need()
def me_signout(u): return jsonify(ok=sbauth.revoke(u['uid']))

@app.get('/api/signals')
@need(active=True)
def signals(u): return jsonify(st.q('SELECT id,symbol,side,entry,sl,tp,strategy,score,status,created,pnl FROM signals ORDER BY id DESC LIMIT 50'))

@app.post('/api/admin/settings')
@need(admin=True)
def admin_set(u):
    for k, v in _j().items():
        if k in st.DEFAULTS and k != 'plans': st.put(k, v)          # plans have their own checked route (/api/admin/plans)
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
    try: return jsonify(pay.set_plans(_j().get('plans') or []))
    except (ValueError, TypeError, KeyError, AttributeError): return jsonify(error='bad plans'), 400

@app.post('/api/admin/grant')
@need(admin=True)
def admin_grant(u):
    j = _j(); em = str(j.get('email', '')).strip().lower()
    try: days = int(j.get('days', 0))
    except (TypeError, ValueError): days = 0
    r = st.q('SELECT uid FROM users WHERE lower(email)=?', (em,), True)
    if not r or not (0 < days <= 3650): return jsonify(error='user not found (they must sign in once) or bad days'), 400
    pay.activate(r['uid'], None, days); return jsonify(ok=True)

@app.get('/api/admin/subscribers')
@need(admin=True)
def admin_subs(u):
    names = {p['id']: p['name'] for p in pay.plans()}
    rows = st.q("SELECT u.email,u.name,u.plan_until,u.created,(SELECT p.plan FROM payments p WHERE p.uid=u.uid AND p.status='paid' ORDER BY p.created DESC LIMIT 1) AS plan "
                "FROM users u ORDER BY u.plan_until DESC, u.created DESC LIMIT 200")
    return jsonify([{'email': r['email'] or '', 'name': r['name'] or '', 'plan_until': int(r['plan_until'] or 0), 'created': int(r['created'] or 0),
                     'plan': names.get(r['plan'], r['plan'] or '')} for r in rows])

@app.post('/api/admin/revoke')
@need(admin=True)
def admin_revoke(u):
    em = str(_j().get('email', '')).strip().lower()
    n = st.x('UPDATE users SET plan_until=0 WHERE lower(email)=?', (em,), True)
    return jsonify(ok=True) if n else (jsonify(error='user not found'), 400)

# ---------------- payments ----------------
@app.get('/api/admin/health')
@need(admin=True)
def admin_health(u): return jsonify(pay.health())

@app.get('/api/plans')
def plans(): return jsonify(pay.plans())

@app.post('/api/pay/mpesa')
@need(verified=True)
def p_mpesa(u):
    j = _j()
    try: return jsonify(ref=pay.stk_push(u['uid'], j.get('plan'), j.get('phone')), msg='Check your phone for the M-Pesa prompt')
    except ValueError as e: return jsonify(error=str(e)), 400
    except PermissionError as e: return jsonify(error=str(e)), 429
    except RuntimeError as e: return jsonify(error=str(e)), 502

@app.post('/api/webhooks/payhero')
@app.post('/api/pay/payhero/callback')
def p_cb():
    sec = pay.cb_secret()
    if not sec or not _same(request.args.get('s', ''), sec): return 'no', 403
    cb = pay.parse_webhook(request.get_json(force=True, silent=True) or {})
    print('finoq webhook:', cb['ref'] or '(no ref)', cb['status'] or '?', 'amount', cb['amount'] or '?')
    if not cb['ref']: return jsonify(ok=True)
    try: return jsonify(ok=True, result=pay.settle_deposit(cb))
    except Exception as e: print('settle failed', cb['ref'], e); return jsonify(ok=False, error='retry'), 500     # non-2xx makes the gateway retry

@app.post('/api/pay/paypal')
@need(verified=True)
def p_pp(u):
    try: ref, url = pay.paypal_create(u['uid'], _j().get('plan'), 'card' if _j().get('mode') == 'card' else 'paypal'); return jsonify(ref=ref, url=url)
    except ValueError as e: return jsonify(error=str(e)), 400
    except RuntimeError as e: return jsonify(error=str(e)), 503
    except Exception as e: print('paypal create failed', e); return jsonify(error='PayPal is unavailable right now'), 502

@app.get('/api/pay/paypal/return')
def p_pp_ret():
    try: p = pay.paypal_capture(request.args.get('token', ''))
    except Exception as e: print('paypal return failed', e); p = None
    s = p['status'] if p else ''
    return redirect('/?paid=' + ('ok' if s == 'paid' else 'wait' if s == 'pending' else 'fail') + ('&ref=' + p['ref'] if p else ''))

@app.get('/api/pay/status')
@need()
def p_status(u):
    p = st.q('SELECT * FROM payments WHERE ref=? AND uid=?', (request.args.get('ref'), u['uid']), True)
    if not p: return jsonify(status='unknown')
    # webhook missed or slow? ask the gateway at most every 15s
    if p['status'] == 'pending' and p['checkout_id'] and time.time() - (p['last_check'] or 0) > 15 and time.time() - p['created'] > 10:
        try: (pay.check_status if p['provider'] == 'finoq' else pay.paypal_recover)(p)
        except Exception as e: print('status check failed', e)
        p = st.q('SELECT * FROM payments WHERE ref=?', (p['ref'],), True)
    return jsonify(status=p['status'], plan=p['plan'], amount=p['amount'], currency=p['currency'], receipt=p['receipt'], reason=p['extra'] if p['status'] == 'failed' else None)

def _reconciler():
    while True:
        time.sleep(120)
        try: pay.reconcile()
        except Exception as e: print('reconcile loop', e)
threading.Thread(target=_reconciler, daemon=True).start()

try:
    from . import live; live.start()
except Exception as e: print('[live] not started', e)
