"""Phone mode ("assist"): for subscribers who only have a phone. The owner's bot finds a signal; the server tells each phone-mode
person (push + the app), with a lot size worked out for THEIR balance and risk. They take it or skip it by hand in their MT5 phone
app, then log how it ended. Nothing here places a trade, and nothing here needs a PC on the subscriber's side.

Needs the owner's own signal feed to be running (the owner's EA or desktop app online). No feed = no signals to hand out.
Data: assist (one row per person: on/off, balance, risk) and assist_log (one row per person per signal: taken or skipped, result)."""
import math, os, time, threading
from . import store as st, links, strategy_info as si, risk

WINDOW = 15 * 60                 # a signal can be taken for 15 minutes after it was found; later the price has probably moved
FEED_AGE = 24 * 3600             # the app lists the owner's signals from the last 24 hours (so results can still be logged)
FEED_MAX = 20
RISK_MIN, RISK_MAX = 0.1, 2.0    # same limits as the MT5 link
BAL_MIN, BAL_MAX = 10.0, 10_000_000.0
LOT_STEP, LOT_MIN, LOT_MAX = 0.01, 0.01, 50.0

# value of a 1.00 price move for 1 standard lot, in USD (USD account assumed). Pairs not listed here get no size (honest, not a guess).
_CONTRACT = {'XAUUSD': 100.0, 'XAGUSD': 5000.0}
_FX = 100000.0

def btc_contract():
    """BTC per 1.00 lot. Many brokers use 1; check your own (MT5: symbol Specification > Contract size). Setting btc_contract, else env BTC_CONTRACT, else 1."""
    try: x = float(st.get('btc_contract') or os.getenv('BTC_CONTRACT') or 1.0)
    except (TypeError, ValueError): return 1.0
    return x if math.isfinite(x) and 0 < x <= 1000 else 1.0

def init():
    """Create the two tables. Same SQL on SQLite and Postgres; safe to run on every boot."""
    st.x('CREATE TABLE IF NOT EXISTS assist(uid TEXT PRIMARY KEY,enabled INTEGER DEFAULT 0,balance DOUBLE PRECISION,risk DOUBLE PRECISION,updated BIGINT)')
    st.x('CREATE TABLE IF NOT EXISTS assist_log(uid TEXT,sid BIGINT,action TEXT,ts BIGINT,lots DOUBLE PRECISION,outcome TEXT,pnl DOUBLE PRECISION,done BIGINT,PRIMARY KEY(uid,sid))')
    st.x('CREATE INDEX IF NOT EXISTS ix_assist_log_uid ON assist_log(uid,ts)')
    if st.PG:
        st.x('ALTER TABLE assist ENABLE ROW LEVEL SECURITY'); st.x('ALTER TABLE assist_log ENABLE ROW LEVEL SECURITY')   # nobody reads these through Supabase's public API

# ---------- lot size ----------
def per_lot_loss(sym, entry, sl):
    """USD lost by 1.00 lot if price travels from entry to sl, or None when the symbol's contract is not known."""
    s = str(sym or '').upper(); d = abs(float(entry) - float(sl))
    if s in _CONTRACT: return d * _CONTRACT[s]
    if risk.is_crypto(s): return d * btc_contract()                 # BTCUSD, BTCUSDm, BTCUSD.a: NOT a forex pair
    if len(s) == 6 and s.isalpha():
        if s[3:] == 'USD': return d * _FX                           # EURUSD, GBPUSD, AUDUSD: quote currency is USD
        if s[:3] == 'USD' and float(entry) > 0: return d * _FX / float(entry)       # USDJPY, USDCHF, USDCAD: loss is in the quote currency
    return None

def _floor_lots(x):
    """Round DOWN to a 0.01 step. The 1e-9 stops 0.29 (= 28.999999999999996 steps) from losing a whole step to float error."""
    return round(math.floor(x / LOT_STEP + 1e-9) * LOT_STEP, 2)

def size(sym, entry, sl, tp, balance, risk_pct):
    """What to show next to a signal. {'lots','risk_usd','win_usd'} ; lots None = cannot size it; 'why' says in plain words."""
    try: entry, sl, tp, balance, risk_pct = float(entry), float(sl), float(tp), float(balance), float(risk_pct)
    except (TypeError, ValueError): return {'lots': None, 'why': 'No balance set yet.'}
    if not all(map(math.isfinite, (entry, sl, tp, balance, risk_pct))) or balance <= 0 or risk_pct <= 0: return {'lots': None, 'why': 'Set your balance and risk first.'}
    one = per_lot_loss(sym, entry, sl)
    if one is None or one <= 0: return {'lots': None, 'why': 'No size for %s: check your broker\'s contract size.' % sym}
    want = balance * risk_pct / 100.0; lots = _floor_lots(min(want / one, LOT_MAX))
    if lots < LOT_MIN - 1e-12:
        return {'lots': None, 'why': 'Too small: even 0.01 lot would risk about $%.2f (%.1f%% of your balance). Skip it, or raise your risk.' % (one * LOT_MIN, one * LOT_MIN / balance * 100),
                'min_risk_usd': round(one * LOT_MIN, 2)}
    risk_usd = lots * one; win = lots * (abs(tp - entry) / abs(entry - sl)) * one if entry != sl else 0.0
    return {'lots': lots, 'risk_usd': round(risk_usd, 2), 'win_usd': round(win, 2)}

# ---------- settings ----------
def get(uid):
    r = st.q('SELECT enabled,balance,risk FROM assist WHERE uid=?', (uid,), True) or {}
    risk = r.get('risk') if r.get('risk') is not None else 1.0          # default: 1 percent per trade
    return {'on': bool(r.get('enabled')), 'balance': r.get('balance'), 'risk': max(RISK_MIN, min(RISK_MAX, float(risk)))}

def is_on(uid): return get(uid)['on']

def save(uid, on=None, balance=None, risk=None):
    """Only the fields that are given change. Raises ValueError(plain words)."""
    cur = get(uid); b, r = cur['balance'], cur['risk']
    if balance is not None:
        try: b = float(balance)
        except (TypeError, ValueError): raise ValueError('Balance must be a number.')
        if not (BAL_MIN <= b <= BAL_MAX) or not math.isfinite(b): raise ValueError('Balance must be between %d and %d.' % (BAL_MIN, BAL_MAX))
        b = round(b, 2)
    if risk is not None:
        try: r = float(risk)
        except (TypeError, ValueError): raise ValueError('Risk must be a number.')
        if not (RISK_MIN <= r <= RISK_MAX): raise ValueError('Risk must be between %s and %s percent.' % (RISK_MIN, RISK_MAX))
        r = round(r, 2)
    if on is True:
        if links.bot_on(uid): raise ValueError('Stop your MT5 bot first, so the same signal is not traded twice.')
        if b is None: raise ValueError('Enter your account balance first, so the lot sizes fit you.')
    en = cur['on'] if on is None else bool(on)
    st.x('INSERT INTO assist(uid,enabled,balance,risk,updated) VALUES(?,?,?,?,?) ON CONFLICT(uid) DO UPDATE SET enabled=excluded.enabled,balance=excluded.balance,risk=excluded.risk,updated=excluded.updated',
         (uid, 1 if en else 0, b, r, int(time.time())))
    return get(uid)

def drop(uid): st.x('DELETE FROM assist WHERE uid=?', (uid,)); st.x('DELETE FROM assist_log WHERE uid=?', (uid,))

# ---------- the feed ----------
def _owner_outcome(pnl):
    if pnl is None: return None
    return 'win' if pnl > 0 else 'loss' if pnl < 0 else 'even'

def feed(uid, now=None):
    """The owner's recent signals as this person sees them, newest first. state: new (can be taken), late (window passed), taken, skipped, done."""
    now = now or time.time(); s = get(uid)
    rows = st.q("SELECT id,symbol,side,entry,sl,tp,strategy,score,status,created,pnl FROM signals WHERE COALESCE(uid,'')='' AND created>=? AND status<>'rejected' ORDER BY id DESC LIMIT ?",
                (int(now - FEED_AGE), FEED_MAX))
    logs = {r['sid']: r for r in st.q('SELECT sid,action,lots,outcome,pnl FROM assist_log WHERE uid=?', (uid,))} if rows else {}
    out = []
    for r in rows:
        lg = logs.get(r['id']); until = r['created'] + WINDOW
        state = ('done' if lg['outcome'] else lg['action']) if lg else ('new' if now < until else 'late')
        sz = size(r['symbol'], r['entry'], r['sl'], r['tp'], s['balance'], s['risk']) if s['balance'] else {'lots': None, 'why': 'Enter your balance to see a lot size.'}
        out.append({'id': r['id'], 'symbol': r['symbol'], 'side': r['side'], 'entry': r['entry'], 'sl': r['sl'], 'tp': r['tp'], 'strategy': r['strategy'], 'strategy_name': si.label(r['strategy']), 'score': r['score'],
                    'created': r['created'], 'valid_until': until, 'state': state, 'size': sz, 'owner': _owner_outcome(r['pnl']),
                    'mine': {'lots': lg['lots'], 'outcome': lg['outcome'], 'pnl': lg['pnl']} if lg else None})
    return out

def stats(uid):
    r = st.q('SELECT action,outcome,pnl FROM assist_log WHERE uid=?', (uid,)); taken = [x for x in r if x['action'] == 'taken']
    w = sum(1 for x in taken if x['outcome'] == 'win'); l = sum(1 for x in taken if x['outcome'] == 'loss'); e = sum(1 for x in taken if x['outcome'] == 'even')
    return {'taken': len(taken), 'skipped': sum(1 for x in r if x['action'] == 'skipped'), 'won': w, 'lost': l, 'even': e, 'waiting': sum(1 for x in taken if not x['outcome']),
            'pnl': round(sum(x['pnl'] for x in taken if x['pnl'] is not None), 2), 'win_rate': round(w / (w + l) * 100, 1) if (w + l) else None}

# ---------- take / skip / result ----------
def _signal(sid):
    try: sid = int(sid)
    except (TypeError, ValueError): raise ValueError('Unknown signal.')
    r = st.q("SELECT id,symbol,side,entry,sl,tp,created FROM signals WHERE id=? AND COALESCE(uid,'')='' AND status<>'rejected'", (sid,), True)
    if not r: raise ValueError('Unknown signal.')
    return r

def _log(uid, sid): return st.q('SELECT * FROM assist_log WHERE uid=? AND sid=?', (uid, sid), True)

def take(uid, sid, now=None):
    now = now or time.time(); sg = _signal(sid); lg = _log(uid, sg['id'])
    if lg and lg['action'] == 'taken': return {'ok': True, 'repeat': True}
    if now > sg['created'] + WINDOW: raise ValueError('Too late: this signal is over %d minutes old and the price has probably moved.' % (WINDOW // 60))
    s = get(uid); z = size(sg['symbol'], sg['entry'], sg['sl'], sg['tp'], s['balance'], s['risk']) if s['balance'] else {'lots': None}
    if lg: st.x("UPDATE assist_log SET action='taken',ts=?,lots=? WHERE uid=? AND sid=?", (int(now), z.get('lots'), uid, sg['id']))      # changed their mind after skipping
    else: st.x("INSERT INTO assist_log(uid,sid,action,ts,lots) VALUES(?,?,'taken',?,?) ON CONFLICT(uid,sid) DO NOTHING", (uid, sg['id'], int(now), z.get('lots')))
    return {'ok': True, 'lots': z.get('lots')}

def skip(uid, sid, now=None):
    now = now or time.time(); sg = _signal(sid); lg = _log(uid, sg['id'])
    if lg and lg['action'] == 'taken': raise ValueError('You already took this one. Log how it ended instead.')
    if not lg: st.x("INSERT INTO assist_log(uid,sid,action,ts) VALUES(?,?,'skipped',?) ON CONFLICT(uid,sid) DO NOTHING", (uid, sg['id'], int(now)))
    return {'ok': True}

def result(uid, sid, outcome, pnl=None, now=None):
    """Log how a taken signal ended. pnl is optional money in their account currency; its sign is forced to match the outcome."""
    now = now or time.time(); sg = _signal(sid); lg = _log(uid, sg['id'])
    if not lg or lg['action'] != 'taken': raise ValueError('Take the signal first, then log how it ended.')
    if outcome not in ('win', 'loss', 'even'): raise ValueError('Outcome must be win, loss or even.')
    p = None
    if pnl not in (None, ''):
        try: p = float(pnl)
        except (TypeError, ValueError): raise ValueError('Profit or loss must be a number.')
        if not math.isfinite(p) or abs(p) > 1e9: raise ValueError('Profit or loss must be a normal number.')
        p = round(abs(p) if outcome == 'win' else -abs(p) if outcome == 'loss' else 0.0, 2)
    elif outcome == 'even': p = 0.0
    st.x('UPDATE assist_log SET outcome=?,pnl=?,done=? WHERE uid=? AND sid=?', (outcome, p, int(now), uid, sg['id']))
    return {'ok': True}

# ---------- telling phones ----------
def _admins(): return {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}

def audience(now=None):
    """Phone-mode people who should hear about a new owner signal: switched on, plan active, not the owner, not running their own MT5 bot."""
    now = now or time.time(); ad = _admins(); out = []
    for r in st.q('SELECT a.uid AS uid,a.balance AS balance,a.risk AS risk,u.email AS email,u.plan_until AS pu FROM assist a JOIN users u ON u.uid=a.uid WHERE a.enabled=1'):
        if (r['pu'] or 0) > now and (r['email'] or '').lower() not in ad and not links.bot_on(r['uid']): out.append(r)
    return out

def announce_now(sid, now=None):
    """Send the 'signal found' push (kind 7) to every phone-mode person, each with their own lot size. Returns how many were sent."""
    from . import push; from .pushcopy import compose
    sg = st.q("SELECT id,symbol,side,entry,sl,tp,strategy FROM signals WHERE id=? AND COALESCE(uid,'')=''", (sid,), True)
    if not sg or not push.configured(): return 0
    n = 0
    for p in audience(now):
        z = size(sg['symbol'], sg['entry'], sg['sl'], sg['tp'], p['balance'], p['risk']) if p['balance'] else {'lots': None}
        t, b, i = compose(7, sym=sg['symbol'], side=sg['side'], entry=sg['entry'], sl=sg['sl'], tp=sg['tp'], strategy=sg['strategy'], lots=z.get('lots'), mins=WINDOW // 60)
        try: sent, _ = push.send(p['uid'], 7, b, t, 'sig%s-assist' % sid, img=i); n += 1 if sent else 0
        except Exception as e: print('[assist] push failed', str(e)[:120])
    return n

def announce(sid):
    """Background version for the scan: a slow phone push must never delay the EA's sync."""
    def run():
        try: announce_now(sid)
        except Exception as e: print('[assist] announce failed', str(e)[:120])
    threading.Thread(target=run, daemon=True).start()
