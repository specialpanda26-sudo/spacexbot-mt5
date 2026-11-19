import os, re, time, json, hmac, threading, functools
from flask import Flask, request, jsonify, send_from_directory, Response, redirect
from . import store as st, botstate, notifart, bars, brain, risk, sbauth, news, stats, accounts, push, links, assist, learn, payments as pay, adminpass as ap, strategy_info as si, feed, alerts, brokers as bk, deriv, livestats, limits, journal, bridge

app = Flask(__name__, static_folder='../static', static_url_path='/static'); app.json.compact = True
st.init(); assist.init()

@app.errorhandler(Exception)
def _boom(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException): return e
    print('500', request.path, repr(e)[:200]); return jsonify(error='Something hiccuped. Please try again.'), 500
EA_KEY = os.getenv('EA_KEY', ''); ADMINS = {e.strip().lower() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()}
_last_scan = {}

def _same(a, b): return hmac.compare_digest(str(a).encode('utf-8'), str(b).encode('utf-8'))     # str compare_digest crashes on non-ASCII
def _j(force=False):
    """The JSON body as a dict. Anything else (a list, a number, no body) becomes {} so a bad request cannot crash a route."""
    j = request.get_json(force=force, silent=True)
    return j if isinstance(j, dict) else {}
def _ea_who():
    """Who is calling the EA routes: '' = the owner's own EA (EA_KEY), a uid = that subscriber's personal key, None = refused."""
    k = request.headers.get('X-EA-Key', '')
    if EA_KEY and _same(k, EA_KEY): return ''
    return links.by_key(k) if k else None
def _paid(uid):
    r = st.q('SELECT email,plan_until FROM users WHERE uid=?', (uid,), True)
    return bool(r) and ((r['plan_until'] or 0) > time.time() or (r['email'] or '').lower() in ADMINS)

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

_OWNER = {'uid': '', 'email': '', 'name': 'Owner', 'verified': True, 'admin': True, 'active': True, 'plan_until': 0}     # who the admin access pass stands for
def need(admin=False, active=False, verified=False):
    def deco(f):
        @functools.wraps(f)
        def w(*a, **k):
            if admin and ap.valid(request.headers.get('X-Admin-Pass', '')): return f(_OWNER, *a, **k)     # admin access pass: admin routes only
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
def _scan(sym, uid=''):
    k = (uid, sym)
    if time.time() - _last_scan.get(k, 0) < 20: return
    _last_scan[k] = time.time()
    m15 = bars.get(sym, 'M15', uid); h1 = bars.get(sym, 'H1', uid)
    if not m15: return
    key = f'lastbar:{uid}:{sym}' if uid else f'lastbar:{sym}'
    if st.get(key) == str(m15[-1]['t']): return          # already evaluated this candle
    st.put(key, m15[-1]['t'])
    ok, why = risk.global_gate(uid=uid)
    if not ok: botstate.note(uid, sym, 'gate', why); return
    off = {x for x in (st.get('strategies_off') or '').split(',') if x}
    if st.get('auto_disable') == '1': off |= stats.losers(int(st.fget('auto_disable_min_trades')), uid)
    solo = {x for x in (st.get('strategies_solo') or '').split(',') if x}
    s = brain.evaluate(m15, h1, int(st.fget('min_confluence')), st.fget('rr'), off, solo=solo)
    if not s: botstate.note(uid, sym, 'nosetup'); return
    ok, why = risk.symbol_gate(sym, s['side'], uid=uid)
    if not ok: print('skip', sym, s['side'], why); botstate.note(uid, sym, 'skip', why); return
    sid = st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
         (sym, s['side'], s['entry'], s['sl'], s['tp'], links.risk(uid) if uid else st.fget('risk_pct'), s['strategy'], s['score'], 'pending', int(time.time()), uid or None))
    sbauth.notify(f"{s['side'].upper()} {sym}", si.alert_body(s['strategy'], s['entry'], s['sl'], s['tp']), key=f'sig{sid}-new', only=uid or None)
    botstate.note(uid, sym, 'signal')
    learn.log(uid, 'signal', s['strategy'], sym, s['side'], data={'score': s['score'], 'adx': s['adx'], 'entry': s['entry']})
    if not uid: assist.announce(sid)          # phone-mode people get the signal with their own lot size

@app.post('/api/ea/sync')
def ea_sync():
    who = _ea_who()
    if who is None: return jsonify(error='bad key'), 401
    d = _j(True); a = d.get('account') if isinstance(d.get('account'), dict) else {}; bz = d.get('bars') if isinstance(d.get('bars'), dict) else {}
    if who:
        if not _paid(who): return jsonify(signal=None, bot=False, expired=True, symbols=st.get('symbols'))          # plan ended: nothing is stored or traded
        a = {k: a[k] for k in ('balance', 'equity', 'open', 'demo', 'allow_live', 'login') if k in a}                   # only the fields we know
        ok = {x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()}
        bz = {s: v for s, v in list(bz.items())[:12] if s in ok}                                                        # only the owner's symbol list
    st.set_acct(a, who)
    for sym, tfs in bz.items():
        for tf, rows in (tfs.items() if isinstance(tfs, dict) else ()):
            if who and (tf not in ('M15', 'H1') or not isinstance(rows, list)): continue
            try: bars.merge(sym, tf, rows[:500] if who else rows, uid=who)
            except (TypeError, ValueError, IndexError) as e: print('bad bars from EA', sym, tf, e)
    for sym in bz:
        try: _scan(sym, who)
        except Exception as e: print('scan failed', sym, str(e)[:120])
    now = int(time.time())
    st.x("UPDATE signals SET status='expired' WHERE status IN('pending','sent') AND created<? AND COALESCE(uid,'')=?", (now - 180, who))
    s = st.q("SELECT id,symbol,side,sl,tp,risk_pct FROM signals WHERE status='pending' AND COALESCE(uid,'')=? ORDER BY id LIMIT 1", (who,), one=True)
    if s: st.x("UPDATE signals SET status='sent' WHERE id=?", (s['id'],))
    return jsonify(signal=s, bot=links.bot_on(who), symbols=st.get('symbols'))

@app.post('/api/ea/report')
def ea_report():
    who = _ea_who()
    if who is None: return jsonify(error='bad key'), 401
    d = _j(True); stt = d.get('status'); only = who or None
    aud = {'only': who} if who else {'admins': True}      # a subscriber's own EA: only that person. The OWNER's EA: only the admins' phones (subscribers get the signal alert, kind 7, and their own EA's results)
    try: sid = int(d.get('id'))
    except (TypeError, ValueError): return jsonify(ok=True)
    if not st.q("SELECT 1 FROM signals WHERE id=? AND COALESCE(uid,'')=?", (sid, who), True): return jsonify(ok=True)      # not this caller's trade: change nothing, reveal nothing
    if stt == 'open': st.x("UPDATE signals SET status='open',ticket=?,lots=?,fill=?,broker='MT5' WHERE id=?", (str(d.get('ticket')), d.get('lots'), d.get('price'), sid))
    elif stt == 'rejected': st.x("UPDATE signals SET status='rejected',note=? WHERE id=?", (str(d.get('reason'))[:120], sid))
    elif stt == 'closed': st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=?", (d.get('pnl'), int(time.time()), sid))
    if stt in ('open', 'closed'):
        s = st.q('SELECT * FROM signals WHERE id=?', (sid,), True)
        if s:
            if stt == 'closed': learn.log(who, 'closed', s['strategy'], s['symbol'], s['side'], s['pnl'], {'reason': str(d.get('reason') or '')})
            title = f"{s['symbol']} {'opened' if stt == 'open' else 'closed'}"
            body = f"{s['side'].upper()} lots {s['lots']}" if stt == 'open' else f"P/L {s['pnl']}"
            sbauth.notify(title, body, key=f'sig{sid}-{stt}', only=only)
            if stt == 'open': push.notify(1, f'sig{sid}-open', sym=s['symbol'], side=s['side'], entry=s['fill'] or s['entry'], sl=s['sl'], tp=s['tp'], risk=s['risk_pct'], strategy=s['strategy'], **aud)
            else: push.notify({'tp': 2, 'sl': 3}.get(str(d.get('reason')), 4), f'sig{sid}-closed', sym=s['symbol'], pnl=s['pnl'], **aud)
    if stt == 'rejected': push.notify(8, f'sig{sid}-skipped', sym=(st.q('SELECT symbol FROM signals WHERE id=?', (sid,), True) or {}).get('symbol', ''), reason=str(d.get('reason') or '')[:80], **aud)
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
    if not push.configured(): return jsonify(error=push.explain('FCM not configured'), devices=0), 400
    n, why = push.send(u['uid'], 1, 'Test notification. If you can read this, phone alerts work.', title='spaceXBot test', force=True)
    dev = len(push.tokens(u['uid']))
    return jsonify(sent=n, reason=why, devices=dev) if n else (jsonify(error=push.explain(why), devices=dev), 400)

# ---------------- app API ----------------
@app.get('/api/me')
@need()
def me(u):
    sc = _mine(u); a = st.acct(sc); online = time.time() - a.get('seen', 0) < 120
    out = {'uid': u['uid'], 'email': u['email'], 'verified': bool(u.get('verified')), 'admin': u['admin'], 'active': u['active'], 'plan_until': u['plan_until'], **accounts.view(u['uid'])}
    out['name'] = out['name'] or u.get('name') or u['email'].split('@')[0]
    if u['active']:
        since = st.day_start()
        out.update(bot=links.bot_on(sc), ea_online=online, account=a if u['admin'] else {'demo': a.get('demo')},
                   today=st.q("SELECT COUNT(*) n, COALESCE(SUM(pnl),0) pnl FROM signals WHERE created>=? AND COALESCE(uid,'')=?", (since, sc), True))
        if not u['admin']: out['link'] = links.view(u['uid'])
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
def signals(u):
    rows = st.q("SELECT id,symbol,side,entry,sl,tp,strategy,score,status,created,pnl FROM signals WHERE COALESCE(uid,'')=? ORDER BY id DESC LIMIT 50", (_mine(u),))
    for r in rows: r['strategy_name'] = si.label(r['strategy'])          # readable name for the app; 'strategy' keeps the raw id
    return jsonify(rows)

# ---------------- each subscriber's own MT5 link ----------------
def _mine(u):
    """The data scope of this person: '' (the owner's own EA) for admins, their own link for everyone else."""
    return '' if u['admin'] else u['uid']

@app.get('/api/link')
@need(verified=True)
def link_get(u):
    if u['admin']: return jsonify(linked=False, admin=True)
    return jsonify(links.view(u['uid']))

@app.post('/api/link/key')
@need(verified=True, active=True)
def link_key(u):
    if u['admin']: return jsonify(error='Admins use the main EA key (EA_KEY).'), 400
    key = links.new_key(u['uid']); return jsonify(key=key, **links.view(u['uid']))      # the only time the key is shown

def _link_edit(u, fn):
    if u['admin']: return jsonify(error='Admins use the main EA key (EA_KEY).'), 400
    if not links.get(u['uid']): return jsonify(error='Make your key first.'), 400
    try: fn()
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in _j().items() if k in ('mode', 'on', 'risk')}})
    return jsonify(links.view(u['uid']))

@app.post('/api/link/mode')
@need(verified=True)
def link_mode(u):
    j = _j(); m = j.get('mode')
    if m == 'real':
        if not u['active']: return jsonify(error='subscription required'), 402
        if j.get('confirm') != 'REAL': return jsonify(error='Type REAL to confirm. Real mode trades real money.'), 400
    return _link_edit(u, lambda: links.set_mode(u['uid'], m))

@app.post('/api/link/bot')
@need(verified=True)
def link_bot(u):
    on = _j().get('on') is True
    if on and not u['active']: return jsonify(error='subscription required'), 402
    if on and assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400
    return _link_edit(u, lambda: links.set_bot(u['uid'], on))

@app.post('/api/link/risk')
@need(verified=True)
def link_risk(u): return _link_edit(u, lambda: links.set_risk(u['uid'], _j().get('risk')))

@app.delete('/api/link')
@need(verified=True)
def link_del(u):
    if not u['admin']: links.drop(u['uid'])
    return jsonify(ok=True)

# ---------------- broker connections (Deriv, Binance, MT5 brokers). Keys are encrypted; nothing secret is ever returned ----------------
@app.get('/api/brokers')
@need(verified=True)
def brokers_get(u): return jsonify(brokers=bk.view(u['uid']), catalog=bk.catalog(), ready=bk.ready())

@app.post('/api/brokers/<name>')
@need(verified=True, active=True)
def brokers_put(u, name):
    try: bk.save(u['uid'], name, _j())
    except ValueError as e: return jsonify(error=str(e)), 400
    except RuntimeError as e: return jsonify(error=str(e)), 503
    return jsonify(brokers=bk.view(u['uid']))

@app.post('/api/brokers/<name>/verify')
@need(verified=True, active=True)
def brokers_verify(u, name):
    n = bk.canon(name)
    if n != 'Deriv': return jsonify(error='Checking this broker is not available yet.'), 400
    ok, msg = deriv.verify(u['uid'])
    return jsonify(ok=ok, message=msg, brokers=bk.view(u['uid']))

@app.post('/api/brokers/<name>/mode')
@need(verified=True)
def brokers_mode(u, name):
    """Demo / Real switch for ONE broker connection (Deriv). Real needs a plan and the word REAL. ANY switch stops that bot."""
    n = bk.canon(name)
    if n != 'Deriv': return jsonify(error='This broker trades through the MT5 app. Change its mode on the Connect MT5 card.'), 400
    j = _j(); m = j.get('mode')
    if m not in ('demo', 'real'): return jsonify(error='mode must be demo or real'), 400
    if not st.q("SELECT 1 FROM broker_links WHERE uid=? AND broker='Deriv'", (u['uid'],), True): return jsonify(error='Save your Deriv token first.'), 400
    if m == 'real':
        if not u['active']: return jsonify(error='subscription required'), 402
        if j.get('confirm') != 'REAL': return jsonify(error='Type REAL to confirm. Real mode trades real money.'), 400
    bk.set_mode(u['uid'], n, m); bk.set_why(u['uid'], n, 'bot off'); learn.log(u['uid'], 'setting', data={'path': request.path, 'mode': m})
    try: deriv.refresh(u['uid'])
    except Exception: pass
    return jsonify(brokers=bk.view(u['uid']))

@app.post('/api/brokers/<name>/bot')
@need(verified=True)
def brokers_bot(u, name):
    """Start / stop the bot for ONE broker connection. Deriv only for now (the MT5 brokers trade through the MT5 app). Works for admins too:
    it needs no MT5 key. Starting needs an active plan, a checked token, and Phone mode off (so a signal is never traded twice)."""
    n = bk.canon(name)
    if n != 'Deriv': return jsonify(error='This broker trades through the MT5 app. Use the Connect MT5 card.'), 400
    on = _j().get('on') is True; r = st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'", (u['uid'],), True)
    if on:
        if not r: return jsonify(error='Save your Deriv token first.'), 400
        if not u['active']: return jsonify(error='subscription required'), 402
        if r['status'] != 'verified': return jsonify(error='Your token is not checked yet. Save it again to check it.'), 400
        if assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400
    bk.set_bot(u['uid'], n, on); learn.log(u['uid'], 'setting', data={'path': request.path, 'on': on})
    if on: deriv.kick(u['uid'], _scan, _paid)
    else: bk.set_why(u['uid'], n, 'bot off')
    return jsonify(brokers=bk.view(u['uid']))

@app.delete('/api/brokers/<name>')
@need(verified=True)
def brokers_del(u, name):
    n = bk.canon(name)
    if not n: return jsonify(error='Unknown broker'), 400
    bk.drop(u['uid'], n); return jsonify(brokers=bk.view(u['uid']))

# ---------------- phone mode (assist): signals for people with only a phone ----------------
@app.get('/api/assist')
@need(verified=True)
def assist_get(u):
    if u['admin']: return jsonify(admin=True)
    s = assist.get(u['uid']); why = ''
    if not u['active']: why = 'Phone mode needs an active plan.'
    elif links.bot_on(u['uid']): why = 'Your MT5 bot is on. Stop it first to use phone mode.'
    out = {**s, 'active': u['active'], 'why': why}
    if u['active'] and s['on']: out.update(feed=assist.feed(u['uid']), stats=assist.stats(u['uid']))
    return jsonify(out)

def _assist_do(u, fn):
    if u['admin']: return jsonify(error='The owner uses the EA, not phone mode.'), 400
    try: return jsonify(fn())
    except ValueError as e: return jsonify(error=str(e)), 400

@app.post('/api/assist/settings')
@need(verified=True, active=True)
def assist_set(u):
    j = _j(); on = j.get('on') if isinstance(j.get('on'), bool) else None
    return _assist_do(u, lambda: assist.save(u['uid'], on, j.get('balance'), j.get('risk')))

@app.post('/api/assist/take')
@need(verified=True, active=True)
def assist_take(u):
    if not u['admin'] and not assist.is_on(u['uid']): return jsonify(error='Turn phone mode on first.'), 400
    return _assist_do(u, lambda: assist.take(u['uid'], _j().get('id')))

@app.post('/api/assist/skip')
@need(verified=True)
def assist_skip(u): return _assist_do(u, lambda: assist.skip(u['uid'], _j().get('id')))

@app.post('/api/assist/result')
@need(verified=True)
def assist_result(u):
    j = _j(); return _assist_do(u, lambda: assist.result(u['uid'], j.get('id'), j.get('outcome'), j.get('pnl')))

@app.post('/api/admin/pass')
def admin_pass():
    """Trade the admin access pass for a 12-hour signed pass (backend/adminpass.py). Wrong tries are limited."""
    ip = (request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '?')
    tok, why, wait = ap.attempt(str(_j().get('code', ''))[:200], ip)
    if why == 'ok': return jsonify(token=tok, ttl=ap.TTL)
    if why == 'off': return jsonify(error='The access pass is not set up on this server.'), 400
    if why == 'locked': return jsonify(error='Too many wrong tries. Try again in %d minutes.' % (wait // 60 + 1)), 429
    return jsonify(error='Wrong access pass.'), 401

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
    sc = _mine(u); a = st.acct(sc); now = time.time(); bal = float(a.get('balance') or 0); since = st.day_start()
    dpnl = st.q("SELECT COALESCE(SUM(pnl),0) p FROM signals WHERE closed>=? AND COALESCE(uid,'')=?", (since, sc), True)['p']
    ok, why = risk.global_gate(uid=sc)
    nh = news.next_high(now)
    return jsonify(bot=links.bot_on(sc), ea_online=now - a.get('seen', 0) < 120, can_trade=ok, why=why,
                   day_loss_pct=round(max(0, -dpnl) / bal * 100, 2) if bal else 0, day_loss_limit=st.fget('max_daily_loss_pct'),
                   open=int(a.get('open', 0)), max_open=int(st.fget('max_open')), news_next=nh, news_loaded=news.loaded(),
                   news_lock=st.get('news_lock') == '1', exposure=risk.exposure(sc), demo=a.get('demo'),
                   strategies=[f.__name__ for f in __import__('backend.strategies', fromlist=['ALL']).ALL], off=[x for x in (st.get('strategies_off') or '').split(',') if x])

@app.get('/api/bridge')
@need(verified=True)
def bridge_api(u):
    """Section 7: is the MT5 bridge reporting, which account, demo or real, and plain setup help (nothing made up)."""
    site = (os.getenv('BASE_URL') or '').strip().rstrip('/')
    if not site.startswith('http'): site = request.host_url.rstrip('/'); site = site.replace('http://', 'https://') if 'localhost' not in site and '127.0.0.1' not in site else site
    return jsonify(bridge.describe(u['uid'], bool(u['admin']), _paid(u['uid']), site))

@app.get('/api/botstate')
@need(verified=True)
def botstate_api(u):
    """Section 4: is the bot running, and if it is not trading, why (plain words, from the real gates)."""
    out = botstate.explain(u['uid'], bool(u['admin']), _paid(u['uid']))
    d = st.q("SELECT 1 FROM broker_links WHERE uid=? AND broker='Deriv'", (u['uid'],), True)
    if d:
        row = next((r for r in bk.view(u['uid']) if r['name'] == 'Deriv'), {})
        out['deriv'] = {'on': bool(bk.bot_flag(u['uid'], 'Deriv')), 'why': row.get('why')}
    return jsonify(out)

@app.post('/api/bot')
@need(verified=True)
def bot_switch(u):
    """Section 4: the Bot tab's Start / Stop. The owner switches the owner's EA; everyone else switches their own link (plan and Phone-mode rules as before)."""
    on = _j().get('on') is True
    if u['admin']:
        st.put('bot_enabled', '1' if on else '0'); learn.log(u['uid'], 'setting', data={'path': request.path, 'on': on})
        return jsonify(ok=True, **botstate.explain(u['uid'], True))
    if on and not u['active']: return jsonify(error='subscription required'), 402
    if on and assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400
    if not links.get(u['uid']): return jsonify(error='Make your MT5 key on the Connect tab first.'), 400
    links.set_bot(u['uid'], on); learn.log(u['uid'], 'setting', data={'path': request.path, 'on': on})
    return jsonify(ok=True, **botstate.explain(u['uid'], False, _paid(u['uid'])))

@app.get('/api/live')
@need(verified=True)
def live_api(u):
    """Section 3: the person's own live numbers (balance, equity, today, open trades). No secrets in the answer."""
    return jsonify(livestats.snapshot(u['uid'], bool(u['admin'])))

@app.get('/api/journal')
@need(verified=True)
def journal_api(u):
    """Section 6: the person's own closed trades + the numbers from them. ?broker=Deriv|MT5 (default all), ?result=win|loss (list only; the numbers always cover every trade)."""
    return jsonify(journal.snapshot(u['uid'], bool(u['admin']), request.args.get('broker', ''), request.args.get('result', 'all')))

@app.get('/api/stats')
@need(active=True)
def stats_api(u): return jsonify(summary=stats.summary(_mine(u)), by_strategy=stats.by_strategy(_mine(u)))

@app.get('/api/admin/brain')
@need(admin=True)
def admin_brain(u): return jsonify(summary=learn.summary(), by_strategy=learn.by_strategy())

@app.get('/api/admin/strategies')
@need(admin=True)
def admin_strategies(u):
    """Every strategy with a readable name, description, group, on/off, and the results of all users' closed trades."""
    from . import strategies as S
    off = {x for x in (st.get('strategies_off') or '').split(',') if x}
    solo = {x for x in (st.get('strategies_solo') or '').split(',') if x}
    return jsonify(si.listing([f.__name__ for f in S.ALL], S.TREND, S.REVERSION, off, learn.by_strategy(), solo))

@app.post('/api/admin/plans')
@need(admin=True)
def admin_plans(u):
    try: return jsonify(pay.set_plans(_j().get('plans') or []))
    except (ValueError, TypeError, KeyError, AttributeError): return jsonify(error='bad plans'), 400

@app.get('/api/admin/feed')
@need(admin=True)
def admin_feed_get(u): return jsonify(feed.status())

@app.post('/api/admin/feed')
@need(admin=True)
def admin_feed_set(u):
    j = _j()
    if j.get('check'): return jsonify(feed.check())
    if 'on' in j:
        if not isinstance(j['on'], bool): return jsonify(error='on must be true or false'), 400
        st.put('feed_on', '1' if j['on'] else '0')
        if j['on']: threading.Thread(target=lambda: feed.tick(_scan), daemon=True).start()       # first round now, not in a minute
    return jsonify(feed.status())

@app.get('/api/limits')
@need(verified=True)
def limits_get(u): return jsonify(limits.view(_mine(u)))

@app.post('/api/limits')
@need(verified=True)
def limits_set(u):
    j = _j()
    try: out = limits.save(_mine(u), j.get('max_trades'), j.get('streak'))
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in ('max_trades', 'streak')}})
    return jsonify(out)

@app.post('/api/admin/testprice')
@need(admin=True)
def admin_testprice(u):
    j = _j()
    try: return jsonify(pay.set_test_plan(j.get('kes'), j.get('usd'), 1 if j.get('days') is None else j.get('days'), bool(j.get('off'))))
    except (ValueError, TypeError, KeyError, AttributeError): return jsonify(error='Enter KES 1 or more, USD 0.01 or more, and days 1 to 3650'), 400

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
def admin_health(u):
    h = pay.health(); bad = list(h.get('problems') or [])
    if not bk.ready(): bad.append('BROKER_KEY is missing (16+ characters). Nobody can link a Deriv or Binance key.')
    if not deriv.APP(): bad.append('DERIV_APP_ID is missing. The Deriv bot cannot trade for anyone.')
    try: beat = int(st.get('deriv:beat') or 0)
    except ValueError: beat = 0
    return jsonify(dict(h, ok=not bad, problems=bad, deriv_loop_last=beat or None, deriv_loop_ago=int(time.time()) - beat if beat else None))

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

try: feed.start(_scan)
except Exception as e: print('[feed] not started', e)
try: deriv.start(_scan, _paid)
except Exception as e: print('deriv loop not started', e)
try:
    from . import live; alerts.start()
    live.start()
except Exception as e: print('[live] not started', e)
