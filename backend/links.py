"""Per-user MT5 link. Each subscriber gets a personal EA key (shown once, only its hash is kept). Their candles, signals, limits and
Demo/Real mode are kept apart from everyone else's. uid '' means the owner's own EA (the global EA_KEY)."""
import hashlib, secrets, time, json, sqlite3
from . import store as st

RISK_MIN, RISK_MAX = 0.1, 2.0
def _h(k): return hashlib.sha256(str(k).encode('utf-8')).hexdigest()
def get(uid): return st.q('SELECT * FROM links WHERE uid=?', (uid,), True) if uid else None

def new_key(uid):
    """Make (or replace) the personal key. A new key starts in Demo mode with the bot off, and the old key stops working at once."""
    key = 'sxb_' + secrets.token_urlsafe(24); sql = "UPDATE links SET key_hash=?,mode='demo',bot=0,acct=NULL,seen=0 WHERE uid=?"
    if not st.x(sql, (_h(key), uid), True):
        try: st.x("INSERT INTO links(uid,key_hash,mode,bot,seen,created) VALUES(?,?,'demo',0,0,?)", (uid, _h(key), int(time.time())))
        except sqlite3.IntegrityError: st.x(sql, (_h(key), uid), True)
    return key

def by_key(key):
    key = str(key or '')
    if not key.startswith('sxb_') or len(key) > 80: return None
    r = st.q('SELECT uid FROM links WHERE key_hash=?', (_h(key),), True); return r['uid'] if r else None

def bot_on(uid):
    if not uid: return st.get('bot_enabled') == '1'
    l = get(uid); return bool(l and l['bot'])
def mode(uid): return ((get(uid) or {}).get('mode')) or 'demo'
def risk(uid):
    try: v = float((get(uid) or {}).get('risk'))
    except (TypeError, ValueError): v = st.fget('risk_pct')
    return max(RISK_MIN, min(RISK_MAX, v))
def set_mode(uid, m):
    if m not in ('demo', 'real'): raise ValueError('mode must be demo or real')
    st.x('UPDATE links SET mode=?,bot=0 WHERE uid=?', (m, uid))       # any switch stops the bot: the person starts it again on purpose
def set_bot(uid, on):
    st.x('UPDATE links SET bot=? WHERE uid=?', (1 if on else 0, uid))
    try:
        from . import activity
        activity.log(uid, 'Bot switched %s on MT5.' % ('ON' if on else 'OFF'), 'bot')          # AC1
    except Exception as e: print('activity note failed', str(e)[:80])
def set_risk(uid, v):
    try: v = float(v)
    except (TypeError, ValueError): raise ValueError('risk must be a number')
    if not (RISK_MIN <= v <= RISK_MAX): raise ValueError('risk must be between %s and %s percent' % (RISK_MIN, RISK_MAX))
    st.x('UPDATE links SET risk=? WHERE uid=?', (round(v, 2), uid))
def drop(uid): st.x('DELETE FROM links WHERE uid=?', (uid,))

def view(uid, now=None):
    """What the app may show: no key, no broker login number."""
    l = get(uid)
    if not l: return {'linked': False}
    a = st.acct(uid); now = now or time.time()
    return {'linked': True, 'mode': l['mode'] or 'demo', 'bot': bool(l['bot']), 'risk': risk(uid), 'online': now - (l['seen'] or 0) < 120,
            'demo': a.get('demo'), 'balance': a.get('balance'), 'equity': a.get('equity'), 'open': a.get('open')}
