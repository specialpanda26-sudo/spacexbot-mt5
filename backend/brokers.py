"""Broker vault: each subscriber's broker keys, encrypted at rest. No route ever sends a secret back to the app.
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
