"""Broker vault: each subscriber's broker keys, encrypted at rest. No route ever sends a secret back to the app.
The lock key is BROKER_KEY (a Render env var). Without it nothing secret is saved, so a key is never stored in plain text.
Each saved value also carries its owner and broker inside the lock, so a copied row cannot be opened as someone else's."""
import os, re, time, json, base64, hashlib
from . import store as st

CATALOG = {'FBS': 'mt5', 'Exness': 'mt5', 'HFM': 'mt5', 'XM': 'mt5', 'IC Markets': 'mt5', 'Pepperstone': 'mt5',
           'Deriv': 'token', 'Deriv MT5': 'mt5', 'Binance': 'keypair'}          # mt5 = only the server name is kept; the MT5 password stays inside MT5
MAX_PER_USER = 10
HINT = {'Deriv MT5': 'Type your Deriv MT5 server name. Copy it exactly from MT5 when you log in.'}
_TOK = re.compile(r'^[A-Za-z0-9_.\-]{8,128}$'); _BKEY = re.compile(r'^[A-Za-z0-9]{16,128}$'); _SRV = re.compile(r'^[A-Za-z0-9 _.\-]{2,60}$')

def canon(name):
    n = str(name or '').strip().lower()
    return next((k for k in CATALOG if k.lower() == n), None)
# What each broker really does today, in plain words (shown on its tile and in its Connect card). Change these when the code changes.
ABOUT = {
    'mt5': {'tile': 'Signals to your MT5 app', 'works': 'Sends you each signal with your lot size. You tap Take it and place it in your MT5 phone app. No EA and no key needed.', 'not': 'It does not place the trade inside MT5 for you, and this site does not read your MT5 balance. A PC with the EA is only an advanced option.'},
    'Deriv MT5': {'tile': 'Signals to your MT5 app', 'works': 'Sends you each signal with your lot size. You tap Take it and place it in your Deriv MT5 phone app. No EA and no key needed.', 'not': 'It does not place the trade inside MT5 for you. Deriv may name markets differently, so check the symbol on your MT5 chart. For fully automatic trading use the Deriv tile.'},
    'Deriv': {'tile': 'Check, balance, demo bot', 'works': 'Token check, balance read, and the bot trading on your demo (virtual) account.', 'not': 'Real-money trading stays off unless the owner allows it and you switch to Real.'},
    'Binance': {'tile': 'Testnet demo bot', 'works': 'Key check, test balance read, and a demo bot that buys and sells Spot crypto on the Binance TESTNET (fake money). Long-only: it buys, then sells.', 'not': 'Real-money Binance trading is not available yet. Use a testnet key from testnet.binance.vision, never your real Binance key.'},
}
def about(name): return ABOUT.get(name) or ABOUT.get('mt5' if CATALOG.get(name) == 'mt5' else '', {})
def catalog(): return [dict({'name': k, 'kind': v}, **about(k)) for k, v in CATALOG.items()]
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
        if not _SRV.match(s('server')): raise ValueError(HINT.get(n) or 'Type your MT5 server name, for example ' + n + '-Demo.')
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
    st.x('DELETE FROM kv WHERE k=?', ('bal:%s:%s' % (uid, n),))          # a new key may be a different account: forget the old balance
    for pre in ('bot', 'why', 'mode', 'note'): st.x('DELETE FROM kv WHERE k=?', ('%s:%s:%s' % (pre, uid, n),))          # a new key starts with the bot off again (switch forgotten)
    mine = {r['broker'] for r in st.q('SELECT broker FROM broker_links WHERE uid=?', (uid,))}
    if n not in mine and len(mine) >= MAX_PER_USER: raise ValueError('Too many connections. Remove one first.')
    now = int(time.time())
    st.x("INSERT INTO broker_links(uid,broker,kind,secret_enc,label,mode,status,created,updated) VALUES(?,?,?,?,?,'demo','saved',?,?) "
         "ON CONFLICT(uid,broker) DO UPDATE SET kind=excluded.kind,secret_enc=excluded.secret_enc,label=excluded.label,mode='demo',status='saved',updated=excluded.updated",
         (uid, n, kind, enc, label, now, now))         # new keys always start in demo mode

def set_bal(uid, name, bal, cur='USD', demo=True, now=None):
    """Remember the last balance we saw for this broker connection (shown on its tile). Only the owner ever sees it."""
    cur = str(cur or 'USD').upper(); cur = cur if re.match(r'^[A-Z]{2,6}$', cur) else 'USD'
    st.put('bal:%s:%s' % (uid, name), json.dumps({'balance': round(float(bal), 2), 'currency': cur, 'demo': bool(demo), 't': int(now or time.time())}))
def _bals(uid):
    out, pre = {}, 'bal:%s:' % uid
    for r in st.q("SELECT k,v FROM kv WHERE k LIKE ?", (pre + '%',)):
        if r['k'].startswith(pre):
            try: out[r['k'][len(pre):]] = json.loads(r['v'])
            except ValueError: pass
    return out

# ---- S1: the bot switch and the "why is it not trading" note live per broker connection (kv rows, so no schema change) ----
REASONS = {
    'ok': 'Running. Last check went fine.',
    'off': 'Deriv trading is not switched on on the server yet. The owner must set DERIV_APP_ID on Render.',
    'plan ended': 'Your plan has ended. Renew it to trade.',
    'bot off': 'The bot is off. Tap Start bot.',
    'other platform': 'You chose another platform to trade on, so this one is paused. Change it on the Bot tab.',
    'real not ready': 'Real-money Binance trading is not available yet. Switch to the testnet (demo).',
    'no key': 'No Binance key is saved. Save your testnet key and secret again.',
    'no crypto symbols': 'No crypto market is set to trade. The owner must add one (for example BTCUSD) to the symbols list.',
    'cannot trade': 'This Binance key cannot trade. Make a testnet key with trading allowed.',
    'not verified': 'Your token is not checked yet. Save it again to check it.',
    'no token': 'No token saved. Save your Deriv token again.',
    'no real account': 'Real mode is on but this token has no real account.',
    'login ended': 'Your Deriv login ended. Tap Log in with Deriv on the Connect tab, then Start bot.',
    'no demo account': 'This token has no virtual (demo) account.',
    'no balance': 'Deriv did not give the balance. It will try again soon.',
    'no symbols': 'No markets are set to trade. The owner must set the symbols list.',
    'error': 'Something failed on the last round. It will try again soon.',
}
def bot_flag(uid, name):
    """True / False once the person has used the switch, None if never used (then the old MT5 link switch decides)."""
    v = st.get('bot:%s:%s' % (uid, name)); return None if v is None else v == '1'
def set_bot(uid, name, on):
    st.put('bot:%s:%s' % (uid, name), '1' if on else '0')
    try:
        from . import activity
        activity.log(uid, 'Bot switched %s on %s.' % ('ON' if on else 'OFF', name), 'bot')          # AC1
    except Exception as e: print('activity note failed', str(e)[:80])
def set_why(uid, name, reason, now=None):
    st.put('why:%s:%s' % (uid, name), json.dumps({'r': str(reason)[:30], 't': int(now or time.time())}))
    try:
        from . import activity
        activity.log(uid, '%s: %s' % (name, 'Connected and watching.' if reason == 'ok' else REASONS.get(reason, 'Not trading: %s' % reason)), 'check' if reason == 'ok' else 'wait', now)          # AC1
    except Exception as e: print('activity note failed', str(e)[:80])
def _why(uid, name):
    try: j = json.loads(st.get('why:%s:%s' % (uid, name)) or '')
    except ValueError: return {}
    return {'why': REASONS.get(j.get('r'), 'Not trading: %s' % j.get('r')), 'why_code': j.get('r'), 'why_t': j.get('t')} if isinstance(j, dict) else {}

def set_note(uid, name, text): st.put('note:%s:%s' % (uid, name), str(text)[:300])
def note(uid, name): return st.get('note:%s:%s' % (uid, name)) or ''

def mode_flag(uid, name):
    """'demo' / 'real' once the person has used the switch on that broker's card, None if never used."""
    v = st.get('mode:%s:%s' % (uid, name)); return v if v in ('demo', 'real') else None
def mode(uid, name, dflt='demo'):
    """Demo or real for one broker connection. The switch wins once used; for Deriv, until then the old MT5-link mode still counts (nothing that worked before changes)."""
    f = mode_flag(uid, name)
    if f: return f
    if name == 'Deriv':
        from . import links
        return links.mode(uid)
    return dflt or 'demo'
def set_mode(uid, name, m):
    """Any switch stops that broker's bot and forgets the old balance (it belonged to the other account type)."""
    if m not in ('demo', 'real'): raise ValueError('mode must be demo or real')
    st.put('mode:%s:%s' % (uid, name), m); set_bot(uid, name, False)
    st.x('DELETE FROM kv WHERE k=?', ('bal:%s:%s' % (uid, name),))

def view(uid):
    """What the app may see: name, kind, a short tail of the key, mode, status. Never the secret."""
    b = _bals(uid)
    return [dict({'name': r['broker'], 'kind': r['kind'], 'label': r['label'], 'mode': mode(uid, r['broker'], r['mode']), 'status': r['status'] or 'saved', 'bot': bot_flag(uid, r['broker']) is True, 'note': note(uid, r['broker']), 'trades': True, **_why(uid, r['broker'])},
                 **({'balance': b[r['broker']].get('balance'), 'currency': b[r['broker']].get('currency'), 'acct_demo': b[r['broker']].get('demo'), 'bal_t': b[r['broker']].get('t')} if r['broker'] in b else {}))
            for r in st.q('SELECT broker,kind,label,mode,status FROM broker_links WHERE uid=? ORDER BY created', (uid,))]
def drop(uid, name):
    for pre in ('bal', 'bot', 'why', 'mode', 'note'): st.x('DELETE FROM kv WHERE k=?', ('%s:%s:%s' % (pre, uid, name),))
    return st.x('DELETE FROM broker_links WHERE uid=? AND broker=?', (uid, name), True)

def secret(uid, name):
    """For the trading code only (Sections 2 and 3). The decrypted values, or None if missing, tampered, or the lock key changed."""
    n = canon(name); r = st.q('SELECT secret_enc FROM broker_links WHERE uid=? AND broker=?', (uid, n), True) if n else None
    lock = _lock()
    if not (r and r['secret_enc'] and lock): return None
    try: d = json.loads(lock.decrypt(r['secret_enc'].encode('ascii')).decode('utf-8'))
    except Exception: return None
    return d.get('v') if d.get('u') == uid and d.get('b') == n else None
