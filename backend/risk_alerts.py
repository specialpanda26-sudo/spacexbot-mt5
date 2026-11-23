"""Section N4: trade and risk alerts. Kinds 10 (trade open a long time), 11-13, 15-18 (the risk gates), 14 (trading resumed).
Kinds 5, 6 and 9 (breakeven, partial close, pending order) are sent from app.ea_report when the EA reports those statuses.
The gates in backend/risk.py only RETURN a reason; gate() below turns that reason into one alert, once per day (or per event), per person.
A person's own alerts go to that person; the owner's scope (uid '') goes to the admins' phones. Risk alerts ignore quiet hours and the cap (push.BYPASS_CATS).
Tunables are assumptions:"""
import time, datetime as dt
from . import store as st, push, limits, risk, lag

HALF = 0.5                    # 18: tell the person when this share of the daily loss limit is used
LONG_OPEN_H = 6               # 10: a trade open this many hours
RETRY_SEC = 3600              # an alert that could not be sent is tried again at most once an hour
EAT = dt.timezone(dt.timedelta(hours=3))
_tried = {}

def _aud(uid): return {'only': uid} if uid else {'admins': True}

def _fire(kind, key, uid, now, **facts):
    k = (uid, key)
    if now - _tried.get(k, 0) < RETRY_SEC: return False
    _tried[k] = now
    for x in [x for x, t in _tried.items() if now - t > 7 * 86400]: _tried.pop(x, None)
    push.notify(kind, key, **facts, **_aud(uid)); return True

def _num(x):
    x = float(x); return ('%d' % x) if x == int(x) else ('%.1f' % x)

def gate(uid, why, sym='', now=None):
    """Called where a scan was stopped by a gate. Returns the kind it tried to send, or None (a reason that is not a risk alert)."""
    now = now or time.time(); w = str(why or ''); day = dt.datetime.utcfromtimestamp(now).date().isoformat()
    if w == 'daily loss limit hit': _fire(11, 'r11-' + day, uid, now, limit=_num(st.fget('max_daily_loss_pct'))); return 11
    if w == 'weekly loss limit hit': _fire(12, 'r12-%d' % risk._week_start(now), uid, now, limit=_num(st.fget('max_weekly_loss_pct'))); return 12
    if w.endswith('losses in a row: cooling down'):
        try: n = int(w.split()[0])
        except ValueError: n = limits.streak(uid)
        last = (st.q("SELECT MAX(closed) c FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=?", (uid,), True) or {}).get('c') or now
        until = int(last + st.fget('streak_cooldown_h') * 3600)
        st.put('ra14:%s' % (uid or 'owner'), until)          # kind 14 goes out when this time has passed
        _fire(13, 'r13-%d' % until, uid, now, n=n, until=dt.datetime.fromtimestamp(until, EAT).strftime('%H:%M') + ' EAT'); return 13
    if w == 'max open positions': _fire(15, 'r15-' + day, uid, now, n=limits.max_open(uid)); return 15
    if w == 'max trades today': _fire(16, 'r16-' + day, uid, now, n=limits.trades(uid)); return 16
    if 'exposure already at limit' in w:
        ccy = w.split()[0]; _fire(17, 'r17-%s-%s' % (day, ccy), uid, now, ccy=ccy, sym=sym); return 17
    return None

def watch(uid, now=None):
    """18: half of the daily loss limit is used (called after the gates passed, so the limit itself is not hit yet)."""
    now = now or time.time(); bal = float((st.acct(uid) or {}).get('balance') or 0)
    if bal <= 0: return None
    lim = st.fget('max_daily_loss_pct'); loss = -risk._pnl_since(risk.day_since(uid, now), uid) / bal * 100
    if lim > 0 and HALF * lim <= loss < lim:
        _fire(18, 'r18-' + dt.datetime.utcfromtimestamp(now).date().isoformat(), uid, now, used=_num(round(loss, 1)), limit=_num(lim)); return 18
    return None

def resume_job(now=None):
    """14 trading resumed: the losing-streak pause (kind 13) is over."""
    now = now or time.time()
    for r in st.q("SELECT k,v FROM kv WHERE k LIKE 'ra14:%'"):
        try: until = float(r['v'])
        except (TypeError, ValueError): until = 0
        if now >= until:
            u = r['k'].split(':', 1)[1]; uid = '' if u == 'owner' else u
            st.x('DELETE FROM kv WHERE k=?', (r['k'],)); _fire(14, 'r14-%d' % until, uid, now)

def long_open_job(now=None):
    """10 a trade has been open a long time. One alert per trade. Needs the time the broker confirmed it (lag stamp 'opened')."""
    now = now or time.time()
    for s in st.q("SELECT id,symbol,uid FROM signals WHERE status='open'"):
        o = lag._read(s['id']).get('opened')
        if o and now - o >= LONG_OPEN_H * 3600:
            m = int((now - o) // 60); _fire(10, 'sig%d-long' % s['id'], s['uid'] or '', now, sym=s['symbol'], dur='%dh %02dm' % (m // 60, m % 60))

def register():
    from . import alerts
    alerts.register_job('resume_alerts', 60, resume_job); alerts.register_job('long_open_alerts', 300, long_open_job)
