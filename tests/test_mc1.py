"""MC1 checks: owner switch 'I close the profits myself'. Fake Deriv session, no network. Run: python tests/test_mc1.py (last line: N checks, M failed)"""
import os, sys, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'mc1_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', SYMBOLS='XAUUSD', BROKER_KEY='unit-test-lock-key-0123456789', DERIV_APP_ID='123')
for f in glob.glob(DB + '*'): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import store as st, links, limits, burst, manual_close as mc, deriv_group as dg
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
for e in ('amy@x.com', 'boss@x.com'): c.get('/api/me', headers=H(e))
A, O = 'dev-amy@x.com', 'dev-boss@x.com'
NOW = int(time.time())

T('default: off', mc.on('') is False and mc.on(O) is False)
st.put('manual_close', '1')
T('on: the owner scope and the owner uid, not a subscriber', mc.on('') is True and mc.on(O) is True and mc.on(A) is False)
T('on_sig reads the uid of a signal row (dict without uid = owner)', mc.on_sig({'uid': O}) is True and mc.on_sig({'uid': A}) is False and mc.on_sig({'id': 1}) is True and mc.on_sig(None) is True)
T('far_tp buy: far above the old target, same side', mc.far_tp('buy', 3614.6, 3634.37) > 3634.37 + 300)
T('far_tp sell: far below the old target, still positive', 0 < mc.far_tp('sell', 3624.23, 3601.93) < 3601.93 - 300)
T('far_tp sell never goes to zero or below', mc.far_tp('sell', 100.0, 1.0) > 0)
T('far_tp bad numbers come back unchanged', mc.far_tp('buy', 'x', 5) == 5 and mc.far_tp('buy', 1, 1) == 1)

# ---- the MT5 poll: single signal and burst basket ----
st.put('bot_enabled', '1')
def poll(): return c.post('/api/ea/sync', headers={'X-EA-Key': 'k'}, json={'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'allow_live': True}).get_json()
def sig(side='buy', grp=None):
    return st.x("INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp) VALUES('XAUUSD',?,3620,?,?,1,'s',1,'pending',?,NULL,?)", (side, 3614.6 if side == 'buy' else 3624.2, 3634.4 if side == 'buy' else 3601.9, int(time.time()), grp))
sid = sig(); j = poll()
T('on: the EA gets a far take-profit on a single signal', j.get('signal') and j['signal']['tp'] > 3634.4 + 300)
T('on: the stored plan (journal) keeps the real target', st.q('SELECT tp FROM signals WHERE id=?', (sid,), True)['tp'] == 3634.4)
st.x('DELETE FROM signals'); st.put('manual_close', '0'); sid = sig(); j = poll()
T('off: the EA gets the real take-profit', j.get('signal') and j['signal']['tp'] == 3634.4)
st.x('DELETE FROM signals'); st.put('manual_close', '1')
g = sig('sell'); st.x('UPDATE signals SET grp=? WHERE id=?', (g, g)); g2 = sig('sell', g); g3 = sig('sell', g)
st.put('bg:%d' % g, json.dumps({'k': 'quick', 'n': 3, 'each': 0.5, 'gb': 40, 't': NOW, 'dtgt': 1.5}))
j = poll(); bk = j.get('basket') or {}
T('on: a burst basket gets an unreachable target, no give-back and a far take-profit', bk.get('tgt') == mc.FAR and bk.get('gb') == 0 and bk.get('tp') < 3601.9 - 300)
T('on: the basket keeps its loss limit field and its entries', 'loss' in bk and bk.get('ids') == '%d,%d,%d' % (g, g2, g3))
st.x('DELETE FROM signals'); st.put('manual_close', '0')
g = sig('sell'); st.x('UPDATE signals SET grp=? WHERE id=?', (g, g)); sig('sell', g)
st.put('bg:%d' % g, json.dumps({'k': 'quick', 'n': 2, 'each': 0.5, 'gb': 40, 't': NOW, 'dtgt': 1.0}))
bk = poll().get('basket') or {}
T('off: the basket keeps its own target and give-back', bk.get('tgt') != mc.FAR and bk.get('gb') == 40 and bk.get('tp') == 3601.9)
st.x('DELETE FROM signals')

# ---- Deriv group closer ----
class Fake:
    def __init__(s, prof): s.prof, s.log = dict(prof), []
    def ask(s, m):
        s.log.append(m)
        if 'proposal_open_contract' in m: return {'proposal_open_contract': {'is_sold': 0, 'profit': s.prof.get(m['contract_id'], 0), 'current_spot': 2000.0}}
        if 'sell' in m: return {'sell': {'sold_for': 1, 'contract_id': m['sell']}}
        return {'error': {'message': 'x'}}
def group(uid='', n=3, **meta):
    ids = []; sql = "INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason,ticket,broker,lots) VALUES('XAUUSD','buy',2000,1990,2020,0.33,'s',1,'open',?,?,?,'why',?,'Deriv',1.0)"
    for i in range(n): ids.append(st.x(sql, (NOW - 60, uid or None, ids[0] if ids else None, str(101 + i))))
    st.x('UPDATE signals SET grp=? WHERE id=?', (ids[0], ids[0]))
    st.put('bg:%d' % ids[0], json.dumps(dict({'k': 'quick', 'n': n, 'each': 1, 'gb': 0, 't': NOW - 60}, **meta))); return ids
def sold(f): return [m for m in f.log if 'sell' in m]
def wipe(): st.x('DELETE FROM signals'); st.x("DELETE FROM kv WHERE k LIKE 'bg:%' OR k LIKE 'glive:%'")

wipe(); st.put('manual_close', '0'); ids = group(dtgt=0.5); f = Fake({101: 0.3, 102: 0.3, 103: 0.1}); out = dg.check(f, '', {}, now=NOW)
T('off: the group is sold at its target (the old behaviour)', len(out) == 1 and len(sold(f)) == 3)
wipe(); st.put('manual_close', '1'); ids = group(dtgt=0.5); f = Fake({101: 0.3, 102: 0.3, 103: 0.1}); out = dg.check(f, '', {}, now=NOW)
T('on: the same group is NOT sold', out == [] and not sold(f))
T('on: its live profit is still read and saved', json.loads(st.get('glive:%d' % ids[0]))['live'] == 0.7)
wipe(); ids = group(dtgt=0.5, loss=10, bal0=100); f = Fake({101: -4, 102: -4, 103: -3}); out = dg.check(f, '', {}, now=NOW)
T('on: the group loss limit still sells a losing group', len(out) == 1 and len(sold(f)) == 3)
wipe(); ids = group(uid=A, dtgt=0.5); f = Fake({101: 0.3, 102: 0.3, 103: 0.1}); out = dg.check(f, A, {}, now=NOW)
T("on: a subscriber's group is still sold at its target", len(out) == 1 and len(sold(f)) == 3)

# ---- Deriv order: no take_profit on the contract ----
from backend import deriv
class Sess:
    def __init__(s): s.log = []
    def ask(s, m):
        s.log.append(m)
        if 'proposal' in m: return {'proposal': {'id': 'q1', 'ask_price': 1.0}}
        if 'buy' in m: return {'buy': {'contract_id': 777, 'buy_price': 1.0}}
        return {}
deriv._mult_ok.clear()
def place(uid):
    row = {'id': 1, 'uid': uid, 'symbol': 'XAUUSD', 'side': 'buy', 'entry': 2000, 'sl': 1990, 'tp': 2020, 'risk_pct': 1.0, 'grp': None}
    s = Sess(); deriv._place(s, row, 100.0, 'USD'); return [m for m in s.log if 'proposal' in m]
p = place(''); T('on: the Deriv order has a stop loss and NO take profit', p and 'stop_loss' in p[0]['limit_order'] and 'take_profit' not in p[0]['limit_order'])
p = place(A); T('on: a subscriber order keeps its take profit', p and 'take_profit' in p[0]['limit_order'])
st.put('manual_close', '0'); p = place(''); T('off: the owner order has its take profit again', p and 'take_profit' in p[0]['limit_order'])

# ---- admin switch ----
r = c.post('/api/admin/settings', headers=H('boss@x.com'), json={'manual_close': '2'}); T('admin save refuses 2', r.status_code == 400)
r = c.post('/api/admin/settings', headers=H('boss@x.com'), json={'manual_close': '1'}); T('admin save accepts 1', r.status_code == 200 and mc.on('') is True)
r = c.post('/api/admin/settings', headers=H('amy@x.com'), json={'manual_close': '0'}); T('a subscriber cannot flip it', r.status_code == 403 and mc.on('') is True)
st.put('manual_close', '0')
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page: the admin checkbox is there', '"manual_close"' in html)
for f in glob.glob(DB + '*'): os.remove(f)
bad = [n for n, ok in R if not ok]
print('%d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
