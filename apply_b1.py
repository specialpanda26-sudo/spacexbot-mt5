#!/usr/bin/env python3
"""B1: broker vault + working Connect buttons. Run from the repo root. Safe to run twice. Adds only; removes nothing."""
import os, sys, subprocess
if not os.path.isfile('backend/app.py'): sys.exit('STOP: run this from the repo folder (spacexbot-mt5.)')
def rd(p): return open(p, encoding='utf-8', newline='').read()
def wr(p, s): open(p, 'w', encoding='utf-8', newline='').write(s)
BROKERS = r'''"""Broker vault: each subscriber's broker keys, encrypted at rest. No route ever sends a secret back to the app.
The lock key is BROKER_KEY (a Render env var). Without it nothing secret is saved, so a key is never stored in plain text.
Each saved value also carries its owner and broker inside the lock, so a copied row cannot be opened as someone else's."""
import os, re, time, json, base64, hashlib
from . import store as st

CATALOG = {'FBS': 'mt5', 'Exness': 'mt5', 'HFM': 'mt5', 'XM': 'mt5', 'IC Markets': 'mt5', 'Pepperstone': 'mt5',
           'Deriv': 'token', 'Binance': 'keypair'}          # mt5 = only the server name is kept; the MT5 password stays inside MT5
MAX_PER_USER = 10
_TOK = re.compile(r'^[A-Za-z0-9_.\-]{8,128}$'); _BKEY = re.compile(r'^[A-Za-z0-9]{16,128}$'); _SRV = re.compile(r'^[A-Za-z0-9 _.\-]{2,60}$')

def canon(name):
    n = str(name or '').strip().lower()
    return next((k for k in CATALOG if k.lower() == n), None)
def catalog(): return [{'name': k, 'kind': v} for k, v in CATALOG.items()]
def _lock():
    k = os.getenv('BROKER_KEY', '').strip()
    if len(k) < 16: return None
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(k.encode('utf-8')).digest()))
def ready(): return _lock() is not None

def save(uid, name, f):
    """Validate and store one broker connection (replaces any older one for that broker). Raises ValueError (bad input) or RuntimeError (vault not switched on)."""
    n = canon(name); f = f if isinstance(f, dict) else {}
    if not n: raise ValueError('Unknown broker')
    kind = CATALOG[n]; s = lambda k: str(f.get(k) or '').strip()
    if kind == 'mt5':
        if not _SRV.match(s('server')): raise ValueError('Type your MT5 server name, for example ' + n + '-Demo.')
        label, enc = s('server'), None
    else:
        lock = _lock()
        if not lock: print('BROKER_KEY is not set: refusing to save a broker key'); raise RuntimeError('Broker linking is not switched on yet. Please try again soon.')
        if kind == 'token':
            if not _TOK.match(s('token')): raise ValueError('That token does not look right. Copy the whole token.')
            vals, label = {'token': s('token')}, '...' + s('token')[-4:]
        else:
            if not (_BKEY.match(s('key')) and _BKEY.match(s('secret'))): raise ValueError('That key or secret does not look right. Copy each one whole.')
            vals, label = {'key': s('key'), 'secret': s('secret')}, '...' + s('key')[-4:]
        enc = lock.encrypt(json.dumps({'u': uid, 'b': n, 'v': vals}).encode('utf-8')).decode('ascii')
    mine = {r['broker'] for r in st.q('SELECT broker FROM broker_links WHERE uid=?', (uid,))}
    if n not in mine and len(mine) >= MAX_PER_USER: raise ValueError('Too many connections. Remove one first.')
    now = int(time.time())
    st.x("INSERT INTO broker_links(uid,broker,kind,secret_enc,label,mode,status,created,updated) VALUES(?,?,?,?,?,'demo','saved',?,?) "
         "ON CONFLICT(uid,broker) DO UPDATE SET kind=excluded.kind,secret_enc=excluded.secret_enc,label=excluded.label,mode='demo',status='saved',updated=excluded.updated",
         (uid, n, kind, enc, label, now, now))         # new keys always start in demo mode

def view(uid):
    """What the app may see: name, kind, a short tail of the key, mode, status. Never the secret."""
    return [{'name': r['broker'], 'kind': r['kind'], 'label': r['label'], 'mode': r['mode'] or 'demo', 'status': r['status'] or 'saved'}
            for r in st.q('SELECT broker,kind,label,mode,status FROM broker_links WHERE uid=? ORDER BY created', (uid,))]
def drop(uid, name): return st.x('DELETE FROM broker_links WHERE uid=? AND broker=?', (uid, name), True)

def secret(uid, name):
    """For the trading code only (Sections 2 and 3). The decrypted values, or None if missing, tampered, or the lock key changed."""
    n = canon(name); r = st.q('SELECT secret_enc FROM broker_links WHERE uid=? AND broker=?', (uid, n), True) if n else None
    lock = _lock()
    if not (r and r['secret_enc'] and lock): return None
    try: d = json.loads(lock.decrypt(r['secret_enc'].encode('ascii')).decode('utf-8'))
    except Exception: return None
    return d.get('v') if d.get('u') == uid and d.get('b') == n else None
'''
TESTS = r'''"""Section 1 tests (broker vault + routes). Run: python tests/test_brokers.py"""
import os, sys, tempfile, sqlite3
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(tempfile.gettempdir(), 'sxb_brk.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app import app
from backend import store as st, brokers as bk
c = app.test_client(); H = lambda e: {'Authorization': 'Bearer dev:' + e}
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
def pay(e): c.get('/api/me', headers=H(e)); st.x('UPDATE users SET plan_until=? WHERE uid=?', (4102444800, 'dev-' + e))
TOK = 'abcDEF1234567890'; KEY = 'A' * 20 + 'k3y9'; SEC = 'S' * 24 + 'z9z9'

T('no sign-in -> 401', c.get('/api/brokers').status_code == 401 and c.post('/api/brokers/Deriv', json={'token': TOK}).status_code == 401)
c.get('/api/me', headers=H('free@x.com'))
T('no plan cannot connect -> 402', c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('free@x.com')).status_code == 402)
pay('amy@x.com')
j = c.get('/api/brokers', headers=H('amy@x.com')).json
T('list starts empty, catalog has 8 brokers, vault ready', j['brokers'] == [] and len(j['catalog']) == 8 and j['ready'] is True)
r = c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
T('Deriv token saved, shown only as a short tail', r.status_code == 200 and r.json['brokers'][0]['label'] == '...7890' and TOK not in r.get_data(as_text=True))
T('new connection starts in demo mode', r.json['brokers'][0]['mode'] == 'demo' and r.json['brokers'][0]['status'] == 'saved')
raw = sqlite3.connect(os.environ['DB_PATH']).execute('SELECT secret_enc FROM broker_links').fetchone()[0]
T('stored value is encrypted, token not in the database', raw and TOK not in raw)
T('decrypts for the trading code', bk.secret('dev-amy@x.com', 'deriv') == {'token': TOK})
T('another user cannot read it', bk.secret('dev-bob@x.com', 'Deriv') is None)
st.x("INSERT INTO broker_links(uid,broker,kind,secret_enc,label,mode,status,created,updated) SELECT 'dev-bob@x.com',broker,kind,secret_enc,label,mode,status,created,updated FROM broker_links WHERE uid='dev-amy@x.com'")
T('a copied row does not open for someone else', bk.secret('dev-bob@x.com', 'Deriv') is None)
st.x("DELETE FROM broker_links WHERE uid='dev-bob@x.com'")
r = c.post('/api/brokers/Binance', json={'key': KEY, 'secret': SEC}, headers=H('amy@x.com'))
T('Binance key + secret saved, neither returned', r.status_code == 200 and KEY not in r.get_data(as_text=True) and SEC not in r.get_data(as_text=True) and bk.secret('dev-amy@x.com', 'Binance') == {'key': KEY, 'secret': SEC})
T('bad token / bad key rejected', c.post('/api/brokers/Deriv', json={'token': 'short'}, headers=H('amy@x.com')).status_code == 400 and c.post('/api/brokers/Binance', json={'key': KEY}, headers=H('amy@x.com')).status_code == 400 and c.post('/api/brokers/Deriv', json={'token': 'bad token with spaces!!'}, headers=H('amy@x.com')).status_code == 400)
T('unknown broker rejected', c.post('/api/brokers/Nope', json={'token': TOK}, headers=H('amy@x.com')).status_code == 400)
T('junk body does not crash', c.post('/api/brokers/Deriv', data='[1]', content_type='application/json', headers=H('amy@x.com')).status_code == 400)
r = c.post('/api/brokers/IC%20Markets', json={'server': 'ICMarketsSC-Demo'}, headers=H('amy@x.com'))
T('MT5 broker keeps only the server name', r.status_code == 200 and sqlite3.connect(os.environ['DB_PATH']).execute("SELECT secret_enc FROM broker_links WHERE broker='IC Markets'").fetchone()[0] is None)
T('MT5 broker needs a sane server name', c.post('/api/brokers/FBS', json={'server': '<script>'}, headers=H('amy@x.com')).status_code == 400)
c.post('/api/brokers/Deriv', json={'token': 'zzzzYYYY99998888'}, headers=H('amy@x.com'))
T('saving again replaces, no duplicate', len([b for b in c.get('/api/brokers', headers=H('amy@x.com')).json['brokers'] if b['name'] == 'Deriv']) == 1 and bk.secret('dev-amy@x.com', 'Deriv') == {'token': 'zzzzYYYY99998888'})
pay('bob@x.com')
T('users only see their own list', c.get('/api/brokers', headers=H('bob@x.com')).json['brokers'] == [])
T('remove works, and only your own', c.delete('/api/brokers/Deriv', headers=H('bob@x.com')).status_code == 200 and bk.secret('dev-amy@x.com', 'Deriv') is not None and c.delete('/api/brokers/Deriv', headers=H('amy@x.com')).status_code == 200 and bk.secret('dev-amy@x.com', 'Deriv') is None)
T('expired plan can still remove a connection', (st.x('UPDATE users SET plan_until=0 WHERE uid=?', ('dev-amy@x.com',)), c.delete('/api/brokers/Binance', headers=H('amy@x.com')).status_code)[1] == 200)
os.environ['BROKER_KEY'] = ''
pay('amy@x.com')
r = c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
T('no BROKER_KEY: refuses to save a secret (503), nothing stored', r.status_code == 503 and bk.secret('dev-amy@x.com', 'Deriv') is None and not [b for b in bk.view('dev-amy@x.com') if b['name'] == 'Deriv'])
os.environ['BROKER_KEY'] = 'unit-test-lock-key-0123456789'
c.post('/api/brokers/Deriv', json={'token': TOK}, headers=H('amy@x.com'))
os.environ['BROKER_KEY'] = 'a-different-lock-key-9876543210'
T('wrong lock key cannot open saved values', bk.secret('dev-amy@x.com', 'Deriv') is None)
os.environ['BROKER_KEY'] = 'unit-test-lock-key-0123456789'
T('deleting the account erases broker keys', (c.delete('/api/me', headers=H('amy@x.com')).status_code, st.q('SELECT 1 FROM broker_links WHERE uid=?', ('dev-amy@x.com',)))[1] == [])
n = sum(1 for _, ok in R if ok); print('\n%d/%d passed' % (n, len(R))); sys.exit(0 if n == len(R) else 1)
'''
def edit(path, pairs):
    s = rd(path)
    for old, new, marker in pairs:
        if marker in s: continue            # already applied
        if s.count(old) != 1: sys.exit('STOP: %s: expected 1 match, found %d for: %s' % (path, s.count(old), old[:70]))
        s = s.replace(old, new)
    wr(path, s)
wr('backend/brokers.py', BROKERS); wr('tests/test_brokers.py', TESTS)
SQ_OLD = 'CREATE TABLE IF NOT EXISTS push_tokens(token TEXT PRIMARY KEY,uid TEXT,platform TEXT,created INTEGER,seen INTEGER);'
SQ_NEW = 'CREATE TABLE IF NOT EXISTS broker_links(uid TEXT,broker TEXT,kind TEXT,secret_enc TEXT,label TEXT,mode TEXT DEFAULT \'demo\',status TEXT DEFAULT \'saved\',created INTEGER,updated INTEGER,PRIMARY KEY(uid,broker));\n' + SQ_OLD
PG_OLD = 'CREATE TABLE IF NOT EXISTS push_tokens(token TEXT PRIMARY KEY,uid TEXT,platform TEXT,created BIGINT,seen BIGINT);'
PG_NEW = 'CREATE TABLE IF NOT EXISTS broker_links(uid TEXT,broker TEXT,kind TEXT,secret_enc TEXT,label TEXT,mode TEXT DEFAULT \'demo\',status TEXT DEFAULT \'saved\',created BIGINT,updated BIGINT,PRIMARY KEY(uid,broker));\nALTER TABLE broker_links ENABLE ROW LEVEL SECURITY;\n' + PG_OLD
edit('backend/store.py', [(SQ_OLD, SQ_NEW, 'broker_links(uid TEXT,broker TEXT,kind TEXT,secret_enc TEXT,label TEXT,mode TEXT DEFAULT \'demo\',status TEXT DEFAULT \'saved\',created INTEGER'),
                          (PG_OLD, PG_NEW, 'created BIGINT,updated BIGINT,PRIMARY KEY(uid,broker))')])
edit('backend/accounts.py', [("st.x('DELETE FROM links WHERE uid=?', (uid,));", "st.x('DELETE FROM broker_links WHERE uid=?', (uid,)); st.x('DELETE FROM links WHERE uid=?', (uid,));", 'DELETE FROM broker_links')])
ROUTES = r'''
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

@app.delete('/api/brokers/<name>')
@need(verified=True)
def brokers_del(u, name):
    n = bk.canon(name)
    if not n: return jsonify(error='Unknown broker'), 400
    bk.drop(u['uid'], n); return jsonify(brokers=bk.view(u['uid']))
'''
LD_OLD = "    if not u['admin']: links.drop(u['uid'])\n    return jsonify(ok=True)\n"
edit('backend/app.py', [('feed, alerts\n', 'feed, alerts, brokers as bk\n', 'brokers as bk'), (LD_OLD, LD_OLD + ROUTES, "def brokers_get(u)")])
P = 'static/index.html'; s = rd(P)
if 'ldB()' not in s:
    for old, new in [('CN=LS("sxb_conn")||{}', 'CN={}'), ('(CN[p[0]]?"Saved · waiting for server":p[1])', '(CN[p[0]]?(CN[p[0]].kind==="mt5"?"Saved":"Connected"):p[1])'), ('Tap a platform to link it. Live links need the back end, so for now this saves your choice on this device.', 'Tap a platform to link it. Keys are stored encrypted and are never shown again. Start on a demo or virtual account.'), ('vc.insertBefore(pc,vc.firstChild);plR();', 'vc.insertBefore(pc,vc.firstChild);plR();function ldB(){if(!window.SXA)return;window.SXA.api("/api/brokers").then(function(j){CN={};(j.brokers||[]).forEach(function(b){CN[b.name]=b});plR()}).catch(function(){})}ldB();setTimeout(ldB,3000);')]:
        if s.count(old) != 1: sys.exit('STOP: index.html: expected 1 match, found %d for: %s' % (s.count(old), old[:70]))
        s = s.replace(old, new)
    H_START = '$("#plat").onclick=function(e){'; H_END = '\n\n/* ---- email verification, plans'
    NEWH = r'''$("#plat").onclick=function(e){var b=e.target.closest("[data-p]");if(!b)return;ldB();var n=b.dataset.p,m=PL.filter(function(p){return p[0]===n})[0][1],mt=m==="MT5 bridge",bn=n==="Binance",cur=CN[n];
  var f1=mt?"MT5 server name":bn?"API key":"API token",tx=mt?"Tell us your broker's server name. Your MT5 password stays inside MT5, never type it here. Then make your key in the Connect MT5 card.":n==="Deriv"?"Create a token in your Deriv account settings with Read and Trade scopes. Start on a virtual account.":"Create an API key with trading only. Never enable withdrawals.";
  ov(XB+'<h2>Connect '+n+'</h2><p class="muted">'+tx+'</p><div class="field"><label for="pF">'+f1+'</label><input class="inp" id="pF" '+(mt?'':'type="password" ')+'autocomplete="off" spellcheck="false" placeholder="'+(cur&&!mt?"Saved. Paste again to replace":mt?n+"-Demo":"Paste "+(bn?"key":"token"))+'"></div>'+(bn?'<div class="field"><label for="pS">API secret</label><input class="inp" id="pS" type="password" autocomplete="off" spellcheck="false" placeholder="Paste secret"></div>':'')+'<p class="err" id="pE"></p><button class="btn primary block" id="pG">'+(cur?"Update":"Save connection")+'</button>'+(cur?'<button class="btn block" id="pD">Remove</button>':''));
  var go=$("#pG");
  go.onclick=function(){var v=$("#pF").value.trim(),sv=bn?$("#pS").value.trim():"",er=$("#pE");if(!v||(bn&&!sv))return er.textContent="This field is needed.";if(!window.SXA)return er.textContent="Sign in first.";
    go.disabled=true;er.textContent="";window.SXA.api("/api/brokers/"+encodeURIComponent(n),{method:"POST",body:mt?{server:v}:bn?{key:v,secret:sv}:{token:v}}).then(function(){closeOv();tst(n+" connected");ldB()}).catch(function(x){go.disabled=false;er.textContent=x.status===402?"A plan is needed to connect a broker.":x.status===401?"Sign in first.":x.message||"Could not save. Try again."})};
  var dl=$("#pD");if(dl)dl.onclick=function(){if(!window.SXA)return;dl.disabled=true;window.SXA.api("/api/brokers/"+encodeURIComponent(n),{method:"DELETE"}).then(function(){closeOv();ldB()}).catch(function(){dl.disabled=false;$("#pE").textContent="Could not remove. Try again."})}}}'''
    if s.count(H_START) != 1: sys.exit('STOP: index.html: connect handler not found once')
    i = s.index(H_START); j = s.index(H_END, i)
    if not s[i:j].endswith('closeOv()}}}'): sys.exit('STOP: index.html: connect handler ends differently than expected')
    s = s[:i] + NEWH + s[j:]
    wr(P, s)
print('patched OK')
sys.exit(subprocess.call([sys.executable, 'tests/test_brokers.py']))
