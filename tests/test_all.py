"""Offline tests, no network. Run:  python tests/test_all.py   (exit code 1 on any failure)"""
import os, sys, json, time, math, random, tempfile, datetime as dt
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_test.db'), PAYHERO_API_KEY='a', PAYHERO_API_SECRET='b',
                  PAYHERO_CHANNEL_ID='7', PAYHERO_CALLBACK_SECRET='sec', BASE_URL='http://t', PAYPAL_ENV='sandbox')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, strategies as S, brain, risk, news, stats, payments as pay, indicators as ix

R = []
def T(name):
    def deco(f):
        try: f(); R.append((name, True, ''))
        except Exception as e: R.append((name, False, repr(e)[:160]))
        return f
    return deco

# ---------- candle fixtures ----------
def series(n, seed, start=1699920000):
    random.seed(seed); p = 2300.0; out = []; drift = 0.0
    for i in range(n):
        if i % 200 == 0: drift = random.choice([-0.35, -0.1, 0, 0.1, 0.35])
        o = p; p += drift + random.gauss(0, 1.4) + 2.2 * math.sin(i / 17)
        out.append({'t': start + i * 900, 'o': o, 'h': max(o, p) + abs(random.gauss(0, .6)), 'l': min(o, p) - abs(random.gauss(0, .6)), 'c': p, 'v': 100})
    return out
def h1(m):
    o = []
    for i in range(0, len(m) - 3, 4):
        g = m[i:i + 4]; o.append({'t': g[0]['t'], 'o': g[0]['o'], 'h': max(x['h'] for x in g), 'l': min(x['l'] for x in g), 'c': g[-1]['c'], 'v': 1})
    return o
MON = int(dt.datetime(2026, 11, 9, tzinfo=dt.timezone.utc).timestamp()); WED = MON + 2 * 86400 + 12 * 3600
def wob(t, base, amp=0.8):
    o = base + random.uniform(-amp, amp); c = base + random.uniform(-amp, amp)
    return {'t': t, 'o': o, 'h': max(o, c) + 0.3, 'l': min(o, c) - 0.3, 'c': c, 'v': 100}

# ---------- every strategy can fire ----------
FIRE = {'fvg_retrace': (1, 323), 'awesome_osc': (1, 488), 'heikin_flip': (1, 539), 'psar_flip': (1, 647), 'bb_reversion': (1, 917),
        'ema_pullback': (1, 977), 'macd_cross': (1, 2291), 'sr_retest': (2, 1184), 'star_reversal': (2, 2210)}
_cache = {}
for name, (seed, e) in FIRE.items():
    def mk(name=name, seed=seed, e=e):
        def f():
            m = _cache.setdefault(seed, series(2400, seed))[:e]; r = getattr(S, name)(m, h1(m))
            assert r and r['side'] in ('buy', 'sell') and r['name'] == name and r['sl'] > 0, r
        return f
    T('strategy fires: ' + name)(mk())

@T('strategy fires: london_breakout (crafted)')
def _():
    random.seed(7); m = [wob(MON + i * 900, 2300) for i in range(3 * 96)]; k = 2 * 96 + 30
    hi = max(x['h'] for x in m[2 * 96:2 * 96 + 28]); m = m[:k + 1]; m[k - 1]['c'] = hi - .2; m[k - 1]['h'] = max(m[k - 1]['h'], hi - .1)
    m[k] = {'t': MON + k * 900, 'o': hi - .2, 'h': hi + 2, 'l': hi - .3, 'c': hi + 1.8, 'v': 1}
    r = S.london_breakout(m, []); assert r and r['side'] == 'buy', r

@T('strategy fires: dual_thrust (crafted)')
def _():
    random.seed(3); m = [wob(MON + i * 900, 2300 + 10 * math.sin(i / 12) if i // 96 < 3 else 2300) for i in range(4 * 96)]
    d = 3 * 96; k = d + 36; m = m[:k + 1]; pr = m[96:288]
    rng = max(max(x['h'] for x in pr) - min(x['c'] for x in pr), max(x['c'] for x in pr) - min(x['l'] for x in pr)); up = m[d]['o'] + .5 * rng
    m[k - 1]['c'] = up - .5; m[k - 1]['h'] = up - .2; m[k] = {'t': MON + k * 900, 'o': up - .5, 'h': up + 2, 'l': up - .6, 'c': up + 1.5, 'v': 1}
    r = S.dual_thrust(m, []); assert r and r['side'] == 'buy', r

@T('strategies never crash on random data')
def _():
    m = series(400, 9)
    for fn in S.ALL: fn(m, h1(m))

# ---------- indicators / brain ----------
@T('adx: trend scores higher than chop')
def _():
    up = [{'t': i, 'o': 100 + i, 'h': 101 + i, 'l': 99.5 + i, 'c': 100.8 + i, 'v': 1} for i in range(80)]
    ch = [{'t': i, 'o': 100, 'h': 100.6 + (i % 2) * .2, 'l': 99.4 - (i % 2) * .2, 'c': 100 + (-1) ** i * .3, 'v': 1} for i in range(80)]
    a, b = ix.adx(up)[-1], ix.adx(ch)[-1]; assert a > 40 and b < 25 and a > b, (a, b)

@T('brain: strategies can be switched off; unmet confluence gives nothing')
def _():
    m = series(2400, 1)[:1000]; hh = h1(m)
    assert brain.evaluate(m, hh, 99) is None
    for fn in S.ALL: assert brain.evaluate(m, hh, 1, 2.0, {f.__name__ for f in S.ALL}) is None

# ---------- gates ----------
def acct(**k): a = {'balance': 1000, 'open': 0, 'demo': True, 'allow_live': False, **k}; st.put('acct', json.dumps({**a, 'seen': int(WED)}))
def reset(): st.x('DELETE FROM signals'); st.x('DELETE FROM kv')
@T('gate: bot off / weekend / EA offline')
def _():
    reset(); acct(); ok, w = risk.global_gate(WED); assert not ok and w == 'bot off'
    st.put('bot_enabled', 1); assert risk.global_gate(WED) == (True, 'ok')
    assert risk.global_gate(MON + 5 * 86400 + 3600)[1] in ('weekend/Friday-night risk', 'EA offline')
    assert risk.global_gate(WED + 600)[1] == 'EA offline'
@T('gate: daily loss, weekly loss, losing streak')
def _():
    reset(); st.put('bot_enabled', 1); acct()
    def close(pnl, ago=60): st.x("INSERT INTO signals(symbol,side,status,created,closed,pnl,strategy) VALUES('EURUSD','buy','closed',?,?,?,'x')", (int(WED) - ago, int(WED) - ago, pnl))
    for _ in range(3): close(-5, 120)
    ok, w = risk.global_gate(WED); assert not ok and 'losses in a row' in w, w
    reset(); st.put('bot_enabled', 1); acct(); close(-31, 60); ok, w = risk.global_gate(WED); assert not ok and w == 'daily loss limit hit', w
    reset(); st.put('bot_enabled', 1); acct(); close(-70, 86400 + 5); ok, w = risk.global_gate(WED); assert not ok and w == 'weekly loss limit hit', w
@T('gate: news lock blocks the right currency only')
def _():
    reset(); news.set_rows([{'title': 'FOMC', 'country': 'USD', 'date': dt.datetime.fromtimestamp(WED + 600, dt.timezone.utc).isoformat(), 'impact': 'High'},
                            {'title': 'Minor', 'country': 'EUR', 'date': dt.datetime.fromtimestamp(WED + 600, dt.timezone.utc).isoformat(), 'impact': 'Low'}])
    assert news.blocked('XAUUSD', WED)[0] and news.blocked('EURUSD', WED)[0] and not news.blocked('EURGBP', WED)[0]
    assert not news.blocked('EURUSD', WED + 3 * 3600)[0]
    assert risk.symbol_gate('XAUUSD', 'buy', WED)[1].startswith('news')
    news.set_rows([])
@T('gate: correlated trades are capped per currency')
def _():
    reset(); news.set_rows([]); st.put('cooldown_min', 0)
    for s in ('EURUSD', 'GBPUSD'): st.x("INSERT INTO signals(symbol,side,status,created) VALUES(?,?,?,?)", (s, 'buy', 'open', int(WED)))
    ok, w = risk.symbol_gate('AUDUSD', 'buy', WED); assert not ok and 'USD' in w, w         # third USD-short
    assert risk.symbol_gate('AUDUSD', 'sell', WED)[0]                                       # opposite side is fine
@T('stats: per-strategy results')
def _():
    reset()
    for p, s in ((10, 'a+b'), (-4, 'a'), (6, 'b')): st.x("INSERT INTO signals(symbol,side,status,created,closed,pnl,strategy) VALUES('X','buy','closed',1,2,?,?)", (p, s))
    b = stats.by_strategy(); assert b['a']['n'] == 2 and b['a']['pnl'] == 6 and b['b']['win_rate'] == 100.0 and stats.summary()['net'] == 12

# ---------- payments ----------
class Resp:
    def __init__(s, code=200, j=None): s.status_code = code; s._j = j or {}; s.content = b'x'
    def json(s): return s._j
SENT = []
import backend.payments as P
def fake_post(url, **kw):
    SENT.append((url, kw.get('json')))
    if 'payments' in url and 'v2' in url: return Resp(200, {'success': True, 'reference': 'PH-REF-1'})
    if 'transaction-status' in url: return Resp(200, {'status': 'SUCCESS', 'amount': 500})
    return Resp(404)
P.requests.post = fake_post
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
C.get('/api/me', headers=U)
def active(h=U): return C.get('/api/me', headers=h).json['active']
def newpay(plan='p1'):
    SENT.clear(); r = C.post('/api/pay/mpesa', json={'plan': plan, 'phone': '+254 712 345 678'}, headers=U); assert r.status_code == 200, r.json; return r.json['ref']
def hook(ref, **o):
    b = {'response': {'ExternalReference': ref, 'Status': 'Success', 'Amount': 500, 'Phone': '254712345678', 'MpesaReceiptNumber': 'abc123', **o}}
    return C.post('/api/webhooks/payhero?s=sec', json=b)

@T('pay: STK push body is right and phone is normalised')
def _():
    ref = newpay(); url, body = SENT[0]
    assert url.endswith('/api/v2/payments') and body['phone_number'] == '0712345678' and body['amount'] == 500 and body['channel_id'] == 7
    assert body['external_reference'] == ref and body['provider'] == 'm-pesa' and body['callback_url'].endswith('?s=sec')
    assert st.q('SELECT checkout_id FROM payments WHERE ref=?', (ref,), True)['checkout_id'] == 'PH-REF-1'
@T('pay: webhook needs the secret')
def _():
    ref = newpay(); assert C.post('/api/webhooks/payhero?s=bad', json={}).status_code == 403 and C.post('/api/webhooks/payhero', json={}).status_code == 403
@T('pay: success activates once, repeats are harmless')
def _():
    assert not active(); ref = newpay(); r = hook(ref); assert r.json['result'] == 'paid' and active()
    until = C.get('/api/me', headers=U).json['plan_until']; assert hook(ref).json['result'] == 'duplicate'
    assert C.get('/api/me', headers=U).json['plan_until'] == until
    assert C.get('/api/pay/status?ref=' + ref, headers=U).json['status'] == 'paid'
@T('pay: underpaid, missing amount, wrong phone are NOT credited')
def _():
    st.x('UPDATE users SET plan_until=0'); 
    r1 = newpay(); assert hook(r1, Amount=100).json['result'] == 'underpaid'
    r2 = newpay(); assert hook(r2, Amount=0).json['result'] == 'no_amount'
    r3 = newpay(); assert hook(r3, Phone='254799999999').json['result'] == 'phone_mismatch'
    assert not active()
@T('pay: failed callback marks failed; late success after expiry still credits')
def _():
    st.x('UPDATE users SET plan_until=0'); r = newpay(); assert hook(r, Status='Failed', ResultCode=1032).json['result'] == 'failed'
    s = C.get('/api/pay/status?ref=' + r, headers=U).json; assert s['status'] == 'failed' and s['reason'] == 'cancelled'
    r = newpay(); st.x("UPDATE payments SET status='expired' WHERE ref=?", (r,)); assert hook(r).json['result'] == 'paid' and active()
@T('pay: missed webhook is recovered by the status check')
def _():
    st.x('UPDATE users SET plan_until=0'); r = newpay(); st.x('UPDATE payments SET created=created-60,last_check=0 WHERE ref=?', (r,))
    assert C.get('/api/pay/status?ref=' + r, headers=U).json['status'] == 'paid' and active()
    assert any('transaction-status' in u for u, _ in SENT)
@T('pay: STK rate limit and bad input')
def _():
    assert C.post('/api/pay/mpesa', json={'plan': 'zzz', 'phone': '0712345678'}, headers=U).status_code == 400
    assert C.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': '123'}, headers=U).status_code == 400
    st.put('rl:phone:0700000001:%d' % (time.time() // 86400), 10)
    assert C.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': '0700000001'}, headers=U).status_code == 429
@T('pay: gateway refusal marks the payment failed')
def _():
    P.requests.post = lambda *a, **k: Resp(500, {'error': 'x'})
    r = C.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': '0712000000'}, headers=U); assert r.status_code == 502
    assert st.q("SELECT status FROM payments ORDER BY created DESC,rowid DESC LIMIT 1", one=True)['status'] == 'failed'; P.requests.post = fake_post
@T('paypal: amount/currency must match before crediting')
def _():
    st.x('UPDATE users SET plan_until=0')
    def run(val, cur):
        ref = P._new('dev-joe@x.com', 'paypal', 'p1', 4, 'USD'); oid = 'ORD' + ref; st.x('UPDATE payments SET checkout_id=? WHERE ref=?', (oid, ref))
        P._pp_token = lambda: 't'
        P.requests.post = lambda *a, **k: Resp(201, {'status': 'COMPLETED', 'purchase_units': [{'payments': {'captures': [{'status': 'COMPLETED', 'amount': {'value': val, 'currency_code': cur}}]}}]})
        return P.paypal_capture(oid)['status']
    assert run('1.00', 'USD') == 'underpaid' and not active()
    assert run('4.00', 'KES') == 'underpaid' and not active()
    assert run('4.00', 'USD') == 'paid' and active(); P.requests.post = fake_post

_REAL_GET = P.requests.get
def pp_order(status='COMPLETED', cap='COMPLETED', val='4.00', cur='USD'):
    return {'status': status, 'purchase_units': [{'payments': {'captures': [{'id': 'CAP1', 'status': cap, 'amount': {'value': val, 'currency_code': cur}}]}}]}
def pp_row():
    ref = P._new('dev-joe@x.com', 'paypal', 'p1', 4, 'USD'); oid = 'ORD' + ref; st.x('UPDATE payments SET checkout_id=? WHERE ref=?', (oid, ref)); return ref, oid
def pstatus(ref): return st.q('SELECT status FROM payments WHERE ref=?', (ref,), True)['status']
def prow(ref): return st.q('SELECT * FROM payments WHERE ref=?', (ref,), True)

@T('pay: M-Pesa stays off until the callback is fully set up')
def _():
    assert P.ready()
    sec = os.environ.pop('PAYHERO_CALLBACK_SECRET')
    try: assert not P.ready()
    finally: os.environ['PAYHERO_CALLBACK_SECRET'] = sec
    base = os.environ.pop('BASE_URL')
    try: assert not P.ready()
    finally: os.environ['BASE_URL'] = base
    os.environ['CALLBACK_URL'] = '"https://other.example/api/webhooks/payhero?s=x"'
    try:
        assert P._cb_url() == 'https://other.example/api/webhooks/payhero?s=x'
        assert any('CALLBACK_URL' in x for x in P.health()['problems'])
    finally: del os.environ['CALLBACK_URL']
@T('paypal: a lost first answer (already captured) is verified with PayPal, not marked failed')
def _():
    st.x('UPDATE users SET plan_until=0'); ref, oid = pp_row(); P._pp_token = lambda: 't'
    P.requests.post = lambda *a, **k: Resp(422, {'details': [{'issue': 'ORDER_ALREADY_CAPTURED'}]})
    P.requests.get = lambda *a, **k: Resp(200, pp_order())
    try: assert P.paypal_capture(oid)['status'] == 'paid' and active()
    finally: P.requests.post = fake_post; P.requests.get = _REAL_GET
@T('paypal: not approved yet or money still pending stays pending; a decline fails')
def _():
    ref, oid = pp_row(); P._pp_token = lambda: 't'
    try:
        P.requests.post = lambda *a, **k: Resp(422, {'details': [{'issue': 'ORDER_NOT_APPROVED'}]}); assert P.paypal_capture(oid)['status'] == 'pending'
        P.requests.post = lambda *a, **k: Resp(201, pp_order('COMPLETED', 'PENDING')); assert P.paypal_capture(oid)['status'] == 'pending'
        P.requests.post = lambda *a, **k: Resp(503, {}); assert P.paypal_capture(oid)['status'] == 'pending'
        P.requests.post = lambda *a, **k: Resp(422, {'details': [{'issue': 'INSTRUMENT_DECLINED'}]}); assert P.paypal_capture(oid)['status'] == 'failed'
    finally: P.requests.post = fake_post
@T('paypal: an approved order whose browser never came back is captured by the status check')
def _():
    st.x('UPDATE users SET plan_until=0'); os.environ.update(PAYPAL_CLIENT_ID='i', PAYPAL_SECRET='s'); P._pp_token = lambda: 't'
    try:
        ref, oid = pp_row()
        P.requests.get = lambda *a, **k: Resp(200, {'status': 'APPROVED'}); P.requests.post = lambda *a, **k: Resp(201, pp_order())
        P.paypal_recover(prow(ref)); assert pstatus(ref) == 'paid' and active()
        ref2, oid2 = pp_row(); P.requests.get = lambda *a, **k: Resp(200, {'status': 'CREATED'})
        P.paypal_recover(prow(ref2)); assert pstatus(ref2) == 'pending'
    finally:
        del os.environ['PAYPAL_CLIENT_ID'], os.environ['PAYPAL_SECRET']; P.requests.post = fake_post; P.requests.get = _REAL_GET
@T('paypal: reconcile expires orders nobody approved')
def _():
    ref, oid = pp_row(); st.x('UPDATE payments SET created=? WHERE ref=?', (int(time.time()) - 5 * 3600, ref))
    P.reconcile(); assert pstatus(ref) == 'expired'
@T('paypal: create says "not set up" when keys are missing, returns the link when set, marks a refused order failed')
def _():
    r = C.post('/api/pay/paypal', json={'plan': 'p1'}, headers=U); assert r.status_code == 503 and 'not set up' in r.json['error']
    os.environ.update(PAYPAL_CLIENT_ID='i', PAYPAL_SECRET='s'); P._pp_token = lambda: 't'
    try:
        P.requests.post = lambda *a, **k: Resp(201, {'id': 'O1', 'links': [{'rel': 'approve', 'href': 'https://pp/approve'}]})
        r = C.post('/api/pay/paypal', json={'plan': 'p1'}, headers=U); assert r.status_code == 200 and r.json['url'] == 'https://pp/approve'
        assert prow(r.json['ref'])['checkout_id'] == 'O1'
        P.requests.post = lambda *a, **k: Resp(400, {'name': 'INVALID_REQUEST'})
        r = C.post('/api/pay/paypal', json={'plan': 'p1'}, headers=U); assert r.status_code == 503
        assert st.q('SELECT status FROM payments ORDER BY created DESC,rowid DESC LIMIT 1', one=True)['status'] == 'failed'
    finally:
        del os.environ['PAYPAL_CLIENT_ID'], os.environ['PAYPAL_SECRET']; P.requests.post = fake_post
@T('paypal: when create fails the app says why with a short code, never a key')
def _():
    os.environ.update(PAYPAL_CLIENT_ID='i', PAYPAL_SECRET='SECRETVALUE'); keep = P._pp_token
    def go(): return C.post('/api/pay/paypal', json={'plan': 'p1'}, headers=U)
    def deny(): raise P.requests.HTTPError('401', response=Resp(401, {'error': 'invalid_client'}))
    def boom(*a, **k): raise P.requests.ConnectionError('x')
    bad = Resp(422, {'details': [{'issue': 'CURRENCY_NOT_SUPPORTED'}]}); bad.text = '{}'
    try:
        P._pp_token = deny; r = go(); assert r.status_code == 503 and 'http401-invalid_client' in r.json['error'] and 'SECRETVALUE' not in r.json['error']
        P._pp_token = lambda: 't'
        P.requests.post = lambda *a, **k: bad; assert 'http422-CURRENCY_NOT_SUPPORTED' in go().json['error']
        P.requests.post = boom; assert 'net-ConnectionError' in go().json['error']
        P.requests.post = lambda *a, **k: Resp(201, {'id': 'O9', 'links': []}); assert 'no-approve-link' in go().json['error']
    finally:
        del os.environ['PAYPAL_CLIENT_ID'], os.environ['PAYPAL_SECRET']; P._pp_token = keep; P.requests.post = fake_post
@T('paypal: the return page redirects with the real result and the payment ref')
def _():
    st.x('UPDATE users SET plan_until=0'); ref, oid = pp_row(); P._pp_token = lambda: 't'
    P.requests.post = lambda *a, **k: Resp(201, pp_order())
    try: loc = C.get('/api/pay/paypal/return?token=' + oid).headers['Location']; assert 'paid=ok' in loc and ref in loc
    finally: P.requests.post = fake_post
@T('admin health: admin only, lists problems, never shows a secret value')
def _():
    assert C.get('/api/admin/health', headers=U).status_code == 403
    os.environ['PAYHERO_API_SECRET'] = 'ZZSECRETVALUE9'
    try:
        r = C.get('/api/admin/health', headers=A); assert r.status_code == 200
        assert 'ZZSECRETVALUE9' not in json.dumps(r.json) and any('DATABASE_URL' in x for x in r.json['problems']) and r.json['mpesa_ready'] is True
    finally: os.environ['PAYHERO_API_SECRET'] = 'b'

# ---------- API ----------
@T('api: plans, admin edit, grant, gating')
def _():
    assert len(C.get('/api/plans').json) == 3
    st.x('UPDATE users SET plan_until=0'); assert C.get('/api/signals', headers=U).status_code == 402 and C.get('/api/status', headers=U).status_code == 402
    assert C.post('/api/admin/plans', json={'plans': [{'id': 'x', 'name': 'X', 'days': 3, 'kes': 100, 'usd': 1}]}, headers=U).status_code == 403
    assert C.post('/api/admin/plans', json={'plans': [{'id': 'x', 'name': 'X', 'days': 3, 'kes': 100, 'usd': 1}]}, headers=A).json[0]['id'] == 'x'
    assert C.post('/api/admin/grant', json={'email': 'joe@x.com', 'days': 5}, headers=A).status_code == 200 and active()
    assert C.get('/api/status', headers=U).status_code == 200 and 'summary' in C.get('/api/stats', headers=U).json
    st.put('plans', '')
@T('api: EA key, signal hand-off and report loop')
def _():
    reset(); H = {'X-EA-Key': 'k'}; assert C.post('/api/ea/sync', json={}, headers={'X-EA-Key': 'x'}).status_code == 401 and C.post('/api/ea/sync', json={}).status_code == 401
    st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created) VALUES('XAUUSD','buy',2300,2295,2310,1,'ema_pullback',2,'pending',?)", (int(time.time()),))
    r = C.post('/api/ea/sync', json={'account': {'balance': 1000, 'demo': True}}, headers=H).json; sig = r['signal']; assert sig and sig['symbol'] == 'XAUUSD'
    assert C.post('/api/ea/sync', json={'account': {'balance': 1000, 'demo': True}}, headers=H).json['signal'] is None      # handed out once
    assert C.post('/api/ea/report', json={'id': sig['id'], 'status': 'open', 'ticket': 5, 'lots': .1, 'price': 2300}, headers=H).json['ok']
    C.post('/api/ea/report', json={'id': sig['id'], 'status': 'closed', 'pnl': 12.5}, headers=H); assert stats.summary()['net'] == 12.5

w = max(len(n) for n, _, _ in R)
for n, ok, e in R: print(('PASS ' if ok else 'FAIL ') + n.ljust(w), '' if ok else ' <- ' + e)
bad = [n for n, ok, _ in R if not ok]; print(f'\n{len(R) - len(bad)}/{len(R)} passed'); sys.exit(1 if bad else 0)
