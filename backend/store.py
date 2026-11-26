"""Storage. DATABASE_URL set -> Supabase Postgres. Not set -> local SQLite (tests, offline dev).
Same API either way: q() reads, x() writes, get/put key-values."""
import os, time, sqlite3, threading, json
from contextlib import closing, contextmanager
URL = os.getenv('DATABASE_URL', '').strip()
PG = bool(URL)
if PG:          # IMP3: load the driver once, now, before any background thread exists
    import psycopg2, psycopg2.extras, psycopg2.pool, psycopg2.extensions
DB = os.getenv('DB_PATH', 'data/spacex.db')
_lock = threading.Lock()
if not PG: os.makedirs(os.path.dirname(DB) or '.', exist_ok=True)

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY,email TEXT,name TEXT,plan_until INTEGER DEFAULT 0,fcm TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY AUTOINCREMENT,symbol TEXT,side TEXT,entry REAL,sl REAL,tp REAL,risk_pct REAL,
  strategy TEXT,score INTEGER,status TEXT,created INTEGER,ticket TEXT,lots REAL,fill REAL,pnl REAL,closed INTEGER,note TEXT);
CREATE TABLE IF NOT EXISTS payments(ref TEXT PRIMARY KEY,uid TEXT,provider TEXT,plan TEXT,amount REAL,currency TEXT,status TEXT,created INTEGER,extra TEXT);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT);
CREATE TABLE IF NOT EXISTS links(uid TEXT PRIMARY KEY,key_hash TEXT,mode TEXT DEFAULT 'demo',bot INTEGER DEFAULT 0,risk REAL,acct TEXT,seen INTEGER DEFAULT 0,created INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS ux_links_key ON links(key_hash);
CREATE TABLE IF NOT EXISTS broker_links(uid TEXT,broker TEXT,kind TEXT,secret_enc TEXT,label TEXT,mode TEXT DEFAULT 'demo',status TEXT DEFAULT 'saved',created INTEGER,updated INTEGER,PRIMARY KEY(uid,broker));
CREATE TABLE IF NOT EXISTS push_tokens(token TEXT PRIMARY KEY,uid TEXT,platform TEXT,created INTEGER,seen INTEGER);
CREATE INDEX IF NOT EXISTS ix_push_tokens_uid ON push_tokens(uid);
CREATE TABLE IF NOT EXISTS push_log(uid TEXT,kind INTEGER,k TEXT,ts INTEGER);
CREATE INDEX IF NOT EXISTS ix_push_log_uid ON push_log(uid,ts);
CREATE UNIQUE INDEX IF NOT EXISTS ux_push_log_key ON push_log(uid,k) WHERE k IS NOT NULL;
CREATE TABLE IF NOT EXISTS brain_events(id INTEGER PRIMARY KEY AUTOINCREMENT,uid TEXT,kind TEXT,strategy TEXT,symbol TEXT,side TEXT,pnl REAL,data TEXT,ts INTEGER);
CREATE INDEX IF NOT EXISTS ix_brain_kind ON brain_events(kind,ts);
"""
PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY,email TEXT,name TEXT,plan_until BIGINT DEFAULT 0,created BIGINT,
  username TEXT,phone TEXT,country TEXT,bio TEXT,exp_level TEXT,goal TEXT,risk_pref TEXT,av INTEGER,notif TEXT,dob TEXT,gender TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_username ON users(username) WHERE username IS NOT NULL;
CREATE TABLE IF NOT EXISTS signals(id BIGSERIAL PRIMARY KEY,symbol TEXT,side TEXT,entry DOUBLE PRECISION,sl DOUBLE PRECISION,tp DOUBLE PRECISION,
  risk_pct DOUBLE PRECISION,strategy TEXT,score INTEGER,status TEXT,created BIGINT,ticket TEXT,lots DOUBLE PRECISION,fill DOUBLE PRECISION,
  pnl DOUBLE PRECISION,closed BIGINT,note TEXT);
CREATE TABLE IF NOT EXISTS payments(ref TEXT PRIMARY KEY,uid TEXT,provider TEXT,plan TEXT,amount DOUBLE PRECISION,currency TEXT,status TEXT,
  created BIGINT,extra TEXT,phone TEXT,checkout_id TEXT,receipt TEXT,paid_at BIGINT,last_check BIGINT);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT);
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarded INTEGER;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE kv ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS uid TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS broker TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS grp BIGINT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS reason TEXT;
CREATE INDEX IF NOT EXISTS ix_signals_uid ON signals(uid);
CREATE TABLE IF NOT EXISTS links(uid TEXT PRIMARY KEY,key_hash TEXT,mode TEXT DEFAULT 'demo',bot INTEGER DEFAULT 0,risk DOUBLE PRECISION,acct TEXT,seen BIGINT DEFAULT 0,created BIGINT);
CREATE UNIQUE INDEX IF NOT EXISTS ux_links_key ON links(key_hash);
ALTER TABLE links ENABLE ROW LEVEL SECURITY;
CREATE TABLE IF NOT EXISTS broker_links(uid TEXT,broker TEXT,kind TEXT,secret_enc TEXT,label TEXT,mode TEXT DEFAULT 'demo',status TEXT DEFAULT 'saved',created BIGINT,updated BIGINT,PRIMARY KEY(uid,broker));
ALTER TABLE broker_links ENABLE ROW LEVEL SECURITY;
CREATE TABLE IF NOT EXISTS push_tokens(token TEXT PRIMARY KEY,uid TEXT,platform TEXT,created BIGINT,seen BIGINT);
CREATE INDEX IF NOT EXISTS ix_push_tokens_uid ON push_tokens(uid);
CREATE TABLE IF NOT EXISTS push_log(uid TEXT,kind BIGINT,k TEXT,ts BIGINT);
CREATE INDEX IF NOT EXISTS ix_push_log_uid ON push_log(uid,ts);
CREATE UNIQUE INDEX IF NOT EXISTS ux_push_log_key ON push_log(uid,k) WHERE k IS NOT NULL;
ALTER TABLE push_tokens ENABLE ROW LEVEL SECURITY;
CREATE TABLE IF NOT EXISTS brain_events(id BIGSERIAL PRIMARY KEY,uid TEXT,kind TEXT,strategy TEXT,symbol TEXT,side TEXT,pnl DOUBLE PRECISION,data TEXT,ts BIGINT);
CREATE INDEX IF NOT EXISTS ix_brain_kind ON brain_events(kind,ts);
ALTER TABLE brain_events ENABLE ROW LEVEL SECURITY;
"""

# ---------------- Postgres plumbing (only used when DATABASE_URL is set) ----------------
_pool = None
def _pg():
    global _pool
    if _pool is None:
        from psycopg2.pool import ThreadedConnectionPool
        import psycopg2.extensions as ext
        ext.register_type(ext.new_type(ext.DECIMAL.values, 'NUM2FLOAT', lambda v, c: float(v) if v is not None else None))
        _pool = ThreadedConnectionPool(1, int(os.getenv('DB_POOL', '5')), URL, connect_timeout=10, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
    return _pool
@contextmanager
def _pgc():
    p = _pg(); c = p.getconn()
    try: yield c
    except Exception:
        try: c.rollback()
        except Exception: pass
        raise
    finally: p.putconn(c)
def _ph(sql): return sql.replace('?', '%s')

def _c():
    c = sqlite3.connect(DB, timeout=15); c.row_factory = sqlite3.Row; return c

def init():
    if PG:
        with _pgc() as c, c.cursor() as cur: cur.execute(PG_SCHEMA); c.commit()
        return
    with closing(_c()) as c:
        c.executescript(SQLITE_SCHEMA)
        for col in ('phone TEXT', 'checkout_id TEXT', 'receipt TEXT', 'paid_at INTEGER', 'last_check INTEGER'):   # migrate older DBs
            try: c.execute('ALTER TABLE payments ADD COLUMN ' + col)
            except sqlite3.OperationalError: pass
        for col in ('username TEXT', 'phone TEXT', 'country TEXT', 'bio TEXT', 'exp_level TEXT', 'goal TEXT', 'risk_pref TEXT', 'av INTEGER', 'notif TEXT', 'dob TEXT', 'gender TEXT', 'onboarded INTEGER'):
            try: c.execute('ALTER TABLE users ADD COLUMN ' + col)
            except sqlite3.OperationalError: pass
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_users_username ON users(username) WHERE username IS NOT NULL')
        for col in ('uid TEXT', 'broker TEXT', 'grp INTEGER', 'reason TEXT'):      # broker = which connection traded it ('Deriv' / 'MT5'); older rows are empty and journal.broker_of() works it out
            try: c.execute('ALTER TABLE signals ADD COLUMN ' + col)
            except sqlite3.OperationalError: pass
        c.execute('CREATE INDEX IF NOT EXISTS ix_signals_uid ON signals(uid)')
        c.commit()

def q(sql, a=(), one=False):
    if PG:
        from psycopg2.extras import RealDictCursor
        with _pgc() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_ph(sql), tuple(a) or None); rows = [dict(r) for r in cur.fetchall()]; c.commit()
    else:
        with closing(_c()) as c: rows = [dict(r) for r in c.execute(sql, a).fetchall()]
    return (rows[0] if rows else None) if one else rows

def x(sql, a=(), count=False):
    """Write. Returns the new row id for a signals insert, or rows changed when count=True (conditional, idempotent updates)."""
    if PG:
        import psycopg2
        s = _ph(sql); ins = s.lstrip().upper().startswith('INSERT INTO SIGNALS')
        if ins: s += ' RETURNING id'
        with _pgc() as c, c.cursor() as cur:
            try: cur.execute(s, tuple(a) or None)
            except psycopg2.IntegrityError as e: raise sqlite3.IntegrityError(str(e))     # one exception type for callers (e.g. username taken)
            rc = cur.rowcount; rid = cur.fetchone()[0] if ins else None; c.commit()
        return rc if count else rid
    with _lock, closing(_c()) as c:
        cur = c.execute(sql, a); c.commit(); return cur.rowcount if count else cur.lastrowid

DEFAULTS = {'bot_enabled': '0', 'risk_pct': os.getenv('RISK_PCT', '1.0'), 'max_open': os.getenv('MAX_OPEN', '3'), 'max_open_ceiling': os.getenv('MAX_OPEN_CEILING', '6'), 'no_open_cap': os.getenv('NO_OPEN_CAP', '1'), 'manual_close': os.getenv('MANUAL_CLOSE', '0'),
    'max_trades_day': os.getenv('MAX_TRADES_DAY', '0'), 'screen_on': '0', 'max_daily_loss_pct': os.getenv('MAX_DAILY_LOSS_PCT', '0'),
    'min_confluence': os.getenv('MIN_CONFLUENCE', '2'), 'rr': os.getenv('RR', '2.0'), 'cooldown_min': os.getenv('COOLDOWN_MIN', '0'),
    'symbols': os.getenv('SYMBOLS', 'XAUUSD,EURUSD,GBPUSD,USDJPY'),
    'max_weekly_loss_pct': os.getenv('MAX_WEEKLY_LOSS_PCT', '0'), 'max_losing_streak': os.getenv('MAX_LOSING_STREAK', '0'),
    'streak_cooldown_h': os.getenv('STREAK_COOLDOWN_H', '0'), 'max_ccy_exposure': os.getenv('MAX_CCY_EXPOSURE', '0'),
    'news_lock': os.getenv('NEWS_LOCK', '0'), 'news_before_min': os.getenv('NEWS_BEFORE_MIN', '30'), 'news_after_min': os.getenv('NEWS_AFTER_MIN', '30'),
    'auto_markets': '0', 'symbols_pool': os.getenv('SYMBOLS_POOL', ''), 'auto_markets_max': '2', 'multi_entries': os.getenv('MULTI_ENTRIES', '1'), 'multi_min_score': os.getenv('MULTI_MIN_SCORE', '3'),
    'stake_on': os.getenv('STAKE_ON', '1'), 'stake_very_pct': os.getenv('STAKE_VERY_PCT', '40'), 'stake_strong_pct': os.getenv('STAKE_STRONG_PCT', '15'), 'stake_max_risk_pct': os.getenv('STAKE_MAX_RISK_PCT', '10'), 'feed_on': os.getenv('FEED_ON', '0'), 'auto_mode': os.getenv('AUTO_MODE', '0'), 'max_stop_atr': os.getenv('MAX_STOP_ATR', '3.5'), 'auto_positions': os.getenv('AUTO_POSITIONS', '1'), 'strategies_off': os.getenv('STRATEGIES_OFF', ''), 'strategies_solo': '', 'auto_disable': '0', 'auto_disable_min_trades': '20', 'regime_switch': os.getenv('REGIME_SWITCH', '0'), 'regime_min_trades': os.getenv('REGIME_MIN_TRADES', '10'), 'burst_enabled': os.getenv('BURST_ENABLED', '1'), 'burst_ceiling': os.getenv('BURST_CEILING', '15'), 'burst_big_score': os.getenv('BURST_BIG_SCORE', '3'), 'burst_free_per_hour': os.getenv('BURST_FREE_PER_HOUR', '2'), 'burst_minute_per_hour': os.getenv('BURST_MINUTE_PER_HOUR', '30'), 'auto_target_usd': os.getenv('AUTO_TARGET_USD', '0'), 'btc_sunday_bounce': '0', 'btc_short_pullback': '0', 'orb_session': '0', 'practice_trades_needed': '5', 'plans': ''}
def get(k):
    r = q('SELECT v FROM kv WHERE k=?', (k,), True); return r['v'] if r else DEFAULTS.get(k)
def put(k, v): x('INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', (k, str(v)))
def fget(k): return float(get(k))
def nolimits_once():
    """NL1: ONE time, switch the owner's stopping limits off in the saved settings too (a value saved earlier beats the new defaults). Later changes in the admin page stay."""
    if get('nolimits_v1') == '1': return
    for k, v in (('max_daily_loss_pct', '0'), ('max_weekly_loss_pct', '0'), ('max_losing_streak', '0'), ('streak_cooldown_h', '0'), ('max_ccy_exposure', '0'),
                 ('cooldown_min', '0'), ('news_lock', '0'), ('max_trades_day', '0'), ('no_open_cap', '1')): put(k, v)
    put('nolimits_v1', '1')
def acct(uid=''):
    """The EA account snapshot. uid '' = the owner's own EA; otherwise that subscriber's link."""
    if uid:
        r = q('SELECT acct FROM links WHERE uid=?', (uid,), True)
        try: a = json.loads(r['acct']) if r and r['acct'] else {}
        except ValueError: a = {}
        if a: return a
        r = q('SELECT v FROM kv WHERE k=?', ('acct:' + uid,), True)          # R7: a Deriv-only person has no MT5 link row, so the snapshot is kept in kv
        try: return json.loads(r['v']) if r else {}
        except ValueError: return {}
    r = q("SELECT v FROM kv WHERE k='acct'", one=True); return json.loads(r['v']) if r else {}
def set_acct(a, uid=''):
    a['seen'] = int(time.time())
    if uid:
        if not x('UPDATE links SET acct=?,seen=? WHERE uid=?', (json.dumps(a), a['seen'], uid), True): put('acct:' + uid, json.dumps(a))          # R7: no link row = keep it in kv
    else: put('acct', json.dumps(a))
def day_start(): t = time.time(); return int(t - t % 86400)

def _drop_pool():
    """Throw every saved connection away. After the free server sleeps they are dead; the next call opens fresh ones."""
    global _pool
    p = _pool; _pool = None
    for c in list(getattr(p, '_pool', None) or []):
        try: c.close()
        except Exception: pass

def _retry(f):
    def w(*a, **k):
        if not PG: return f(*a, **k)
        import psycopg2
        for i in range(3):
            try: return f(*a, **k)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if i == 2: raise
                print('db: connection lost, reconnecting', i + 1, repr(e)[:100]); _drop_pool(); time.sleep(0.4 * i)
    w.__name__ = f.__name__; return w
q = _retry(q); x = _retry(x)
