"""Section N5: market alerts, push kinds 19 to 24 (kind 25, spread too wide, is sent from the EA report route in app.py).
One small job per alert, all run by the single loop in backend/alerts.py (register() below). Facts only, never advice.
Every job takes `now` so a test can fix the clock. Each alert has a key, so one person never gets the same alert twice (push_log).
Tunables are assumptions, change them here:"""
import time, datetime as dt
from zoneinfo import ZoneInfo
from . import store as st, news, bars, push, risk

NEWS_AHEAD_MIN = 60            # 19: tell people when a high-impact release is this close or closer
LOCK_END_WINDOW_MIN = 15       # 21: only say "lock ended" within this many minutes after it ended (not hours later)
OPEN_WINDOW_MIN = 10           # 22: only say "session opening" within this many minutes after the open
SESSIONS = (('Tokyo', 'Asia/Tokyo', 9), ('London', 'Europe/London', 8), ('New York', 'America/New_York', 8))   # local opening hour, weekdays, daylight saving handled by zoneinfo
MOVE_SYM = 'XAUUSD'
MOVE_PCT = 0.6                 # 23: gold moved at least this many percent ...
MOVE_MINS = 60                 # ... within this many minutes
MOVE_GAP = 2 * 3600            # 23: at most one alert per direction per 2 hours
CLOSED_WINDOW_H = 3            # 24: only say "market closed" in the 3 hours after the Friday 20:00 UTC cutoff
RETRY_SEC = 600                # a key that could not be sent (quiet hours, no phone) is tried again at most every 10 minutes
_tried = {}

def _fire(kind, key, now, **facts):
    """Send once per key. Everyone who should get market alerts (every subscriber and the admins). Quiet hours and the daily cap still apply inside push."""
    if now - _tried.get(key, 0) < RETRY_SEC: return False
    _tried[key] = now
    for k in [k for k, t in _tried.items() if now - t > 86400]: _tried.pop(k, None)
    push.notify(kind, key, **facts); return True

def _mine():
    """Currencies of the markets the bot trades (the Symbols setting), so a Japanese holiday does not wake a gold trader."""
    c = set()
    for s in (st.get('symbols') or '').split(','):
        if s.strip(): c |= news.currencies(s.strip().upper())
    return c

def _slug(e): return '%s-%d-%s' % (e['ccy'], int(e['t']), ''.join(ch for ch in str(e['title']).lower() if ch.isalnum())[:20])

def news_job(now=None):
    """19 high-impact news soon, 20 news lock started, 21 news lock ended. Follows the same minutes the trade gate uses (news_before_min / news_after_min)."""
    now = now or time.time(); mine = _mine(); lock_on = st.get('news_lock') == '1'
    before = st.fget('news_before_min') * 60; after = st.fget('news_after_min') * 60
    for e in news.events(now):
        if e['ccy'] not in mine: continue
        until = e['t'] - now; base = _slug(e)
        if 0 < until <= NEWS_AHEAD_MIN * 60: _fire(19, 'n19-' + base, now, event=e['title'], ccy=e['ccy'], mins=max(1, int(until / 60)))
        if lock_on and 0 <= until <= before: _fire(20, 'n20-' + base, now, event=e['title'])
        if lock_on and 0 <= now - (e['t'] + after) <= LOCK_END_WINDOW_MIN * 60: _fire(21, 'n21-' + base, now)

def session_job(now=None):
    """22 a session is opening (Tokyo, London, New York), weekdays only."""
    now = now or time.time()
    for name, zone, hour in SESSIONS:
        loc = dt.datetime.fromtimestamp(now, ZoneInfo(zone))
        if loc.weekday() >= 5: continue
        since = (loc.hour * 60 + loc.minute) - hour * 60
        if 0 <= since < OPEN_WINDOW_MIN: _fire(22, 's22-%s-%s' % (name, loc.date().isoformat()), now, session=name)

def move_job(now=None):
    """23 a large gold move: from the open of the oldest candle in the last MOVE_MINS minutes to the newest close (owner's price candles)."""
    now = now or time.time()
    if MOVE_SYM not in [s.strip().upper() for s in (st.get('symbols') or '').split(',')]: return
    rows = [r for r in bars.get(MOVE_SYM, 'M15', '') if r['t'] >= now - MOVE_MINS * 60 and r['t'] <= now]
    if len(rows) < 2 or now - rows[-1]['t'] > 1800 or not rows[0]['o']: return          # no fresh candles = no alert
    pct = (rows[-1]['c'] - rows[0]['o']) / rows[0]['o'] * 100
    if abs(pct) >= MOVE_PCT:
        _fire(23, 'm23-%s-%d' % ('up' if pct > 0 else 'down', int(now // MOVE_GAP)), now, pct='%+.2f' % pct, mins=MOVE_MINS, price=rows[-1]['c'])

def closed_job(now=None):
    """24 the weekend rule has started (Friday 20:00 UTC). Not sent while a crypto market keeps the bot looking."""
    now = now or time.time(); d = dt.datetime.utcfromtimestamp(now)
    if d.weekday() == 4 and 20 <= d.hour < 20 + CLOSED_WINDOW_H and risk.weekend_shut(now) and not risk.crypto_open():
        _fire(24, 'c24-%s' % d.date().isoformat(), now)

def register():
    """Put the four jobs on the alerts loop. Safe to call twice."""
    from . import alerts
    for name, fn in (('news_alerts', news_job), ('session_alerts', session_job), ('move_alerts', move_job), ('closed_alerts', closed_job)):
        alerts.register_job(name, 60, fn)
