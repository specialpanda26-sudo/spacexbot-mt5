import os, time, sqlite3, threading, json
from contextlib import closing
DB = os.getenv('DB_PATH', 'data/spacex.db')
os.makedirs(os.path.dirname(DB) or '.', exist_ok=True)
_lock = threading.Lock()
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY,email TEXT,name TEXT,plan_until INTEGER DEFAULT 0,fcm TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY AUTOINCREMENT,symbol TEXT,side TEXT,entry REAL,sl REAL,tp REAL,risk_pct REAL,
  strategy TEXT,score INTEGER,status TEXT,created INTEGER,ticket TEXT,lots REAL,fill REAL,pnl REAL,closed INTEGER,note TEXT);
CREATE TABLE IF NOT EXISTS payments(ref TEXT PRIMARY KEY,uid TEXT,provider TEXT,plan TEXT,amount REAL,currency TEXT,status TEXT,created INTEGER,extra TEXT);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT);
"""
def _c():
    c = sqlite3.connect(DB, timeout=15); c.row_factory = sqlite3.Row; return c
def init():
    with closing(_c()) as c:
        c.executescript(SCHEMA)
        for col in ('phone TEXT', 'checkout_id TEXT', 'receipt TEXT', 'paid_at INTEGER', 'last_check INTEGER'):   # migrate older DBs
            try: c.execute('ALTER TABLE payments ADD COLUMN ' + col)
            except sqlite3.OperationalError: pass
        c.commit()
def q(sql, a=(), one=False):
    with closing(_c()) as c: rows = [dict(r) for r in c.execute(sql, a).fetchall()]
    return (rows[0] if rows else None) if one else rows
def x(sql, a=(), count=False):
    """Write. Returns lastrowid, or rows changed when count=True (used for conditional, idempotent updates)."""
    with _lock, closing(_c()) as c:
        cur = c.execute(sql, a); c.commit(); return cur.rowcount if count else cur.lastrowid
DEFAULTS = {'bot_enabled': '0', 'risk_pct': os.getenv('RISK_PCT', '1.0'), 'max_open': os.getenv('MAX_OPEN', '3'),
    'max_trades_day': os.getenv('MAX_TRADES_DAY', '6'), 'max_daily_loss_pct': os.getenv('MAX_DAILY_LOSS_PCT', '3.0'),
    'min_confluence': os.getenv('MIN_CONFLUENCE', '2'), 'rr': os.getenv('RR', '2.0'), 'cooldown_min': os.getenv('COOLDOWN_MIN', '60'),
    'symbols': os.getenv('SYMBOLS', 'XAUUSD,EURUSD,GBPUSD,USDJPY'),
    'max_weekly_loss_pct': os.getenv('MAX_WEEKLY_LOSS_PCT', '6.0'), 'max_losing_streak': os.getenv('MAX_LOSING_STREAK', '3'),
    'streak_cooldown_h': os.getenv('STREAK_COOLDOWN_H', '4'), 'max_ccy_exposure': os.getenv('MAX_CCY_EXPOSURE', '2'),
    'news_lock': os.getenv('NEWS_LOCK', '1'), 'news_before_min': os.getenv('NEWS_BEFORE_MIN', '30'), 'news_after_min': os.getenv('NEWS_AFTER_MIN', '30'),
    'strategies_off': '', 'auto_disable': '0', 'auto_disable_min_trades': '20', 'plans': ''}
def get(k):
    r = q('SELECT v FROM kv WHERE k=?', (k,), True); return r['v'] if r else DEFAULTS.get(k)
def put(k, v): x('INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', (k, str(v)))
def fget(k): return float(get(k))
def acct():
    r = q("SELECT v FROM kv WHERE k='acct'", one=True); return json.loads(r['v']) if r else {}
def set_acct(a): a['seen'] = int(time.time()); put('acct', json.dumps(a))
def day_start(): t = time.time(); return int(t - t % 86400)
