"""Section N6c: report alerts, push kinds 32, 33, 34, 36, 37. (35 'brain learned' has no data behind it yet, so it is NOT sent.)
Real numbers only, from the same closed-trade list the Journal uses (journal._closed). Nobody gets a report for a period with no trades.
Two small jobs on the ONE loop in backend/alerts.py (register() below). Each takes `now` so a test can fix the clock. Times are East Africa Time (EAT).
Tunables (assumptions, change here):"""
import time, datetime as dt
from . import push, journal as jn

EAT = push.EAT
DAILY_HOUR = 21             # 32 daily summary goes out in the first hour from 21:00 EAT (before the 22:00 quiet hours start)
WEEKLY_WEEKDAY = 6          # 33 weekly report: Sunday (Monday is 0), same hour as the daily one, the last 7 days
MONTHLY_DAY = 1             # 34 monthly report: on the 1st of the month, for the month that just ended
MONTHLY_HOUR = 9
WINDOW_H = 1                # a report is only sent in the first WINDOW_H hour(s) from its time, never hours later
STREAKS = (3, 5, 10)        # 36 winning streak: said when the run of wins in a row reaches exactly one of these
STREAK_FRESH = 2 * 3600     # ... and only while the newest win closed less than this many seconds ago
REVIEW_MIN_LOSSES = 2       # 37 review your trades: sent with the daily summary on a day with this many losses or more AND a net loss
RETRY_SEC = 600             # a report that could not be sent (no phone, category off) is tried again at most every 10 minutes
CUR = 'USD'
_tried = {}

def _fire(uid, kind, key, now, **facts):
    if now - _tried.get(key, 0) < RETRY_SEC: return False
    _tried[key] = now
    for k in [k for k, t in _tried.items() if now - t > 86400]: _tried.pop(k, None)
    push.notify_user(uid, kind, key, cur=CUR, **facts); return True

def _people():
    """Everyone with a phone and a plan, plus the admins; the flag says whether the OWNER scope applies (admins read the owner's trades)."""
    admins = set(push.recipients(True)); return [(u, u in admins) for u in push.recipients()]

def _facts(rows):
    n = len(rows); w = sum(1 for r in rows if r['pnl'] > 0); best = max(rows, key=lambda r: r['pnl']) if rows else None
    return dict(n=n, pnl=round(sum(r['pnl'] for r in rows), 2), wr=round(w / n * 100) if n else None, best=best['symbol'] if best and best['pnl'] > 0 else '')

def _midnight(now): return dt.datetime.fromtimestamp(now, EAT).replace(hour=0, minute=0, second=0, microsecond=0)

def report_job(now=None):
    """32 daily summary (and 37 review on a bad day), 33 weekly report, 34 monthly report. Each only inside its own time window."""
    now = now or time.time(); loc = dt.datetime.fromtimestamp(now, EAT); d0 = _midnight(now); day = d0.date().isoformat()
    daily = DAILY_HOUR <= loc.hour < DAILY_HOUR + WINDOW_H; weekly = daily and loc.weekday() == WEEKLY_WEEKDAY
    monthly = loc.day == MONTHLY_DAY and MONTHLY_HOUR <= loc.hour < MONTHLY_HOUR + WINDOW_H
    if not (daily or monthly): return
    m1 = (d0.replace(day=1) - dt.timedelta(days=1)).replace(day=1)          # first day of the month that just ended
    for uid, admin in _people():
        rows = jn._closed(uid, admin)
        if daily:
            today = [r for r in rows if r['t'] >= d0.timestamp()]
            if today:
                f = _facts(today); _fire(uid, 32, 'r32-%s-%s' % (uid, day), now, **f)
                if f['pnl'] < 0 and sum(1 for r in today if r['pnl'] <= 0) >= REVIEW_MIN_LOSSES: _fire(uid, 37, 'r37-%s-%s' % (uid, day), now)
        if weekly:
            wk = [r for r in rows if r['t'] >= (d0 - dt.timedelta(days=6)).timestamp()]
            if wk: _fire(uid, 33, 'r33-%s-%s' % (uid, day), now, **_facts(wk))
        if monthly:
            mo = [r for r in rows if m1.timestamp() <= r['t'] < d0.timestamp()]
            if mo: _fire(uid, 34, 'r34-%s-%s' % (uid, m1.strftime('%Y-%m')), now, **_facts(mo))

def streak_job(now=None):
    """36 the run of wins in a row (newest first) reaches 3, 5 or 10 and the newest win is fresh. Once per person per milestone per newest trade."""
    now = now or time.time()
    for uid, admin in _people():
        rows = jn._closed(uid, admin); n = 0
        for r in rows:
            if r['pnl'] > 0: n += 1
            else: break
        if n in STREAKS and rows[0]['t'] >= now - STREAK_FRESH: _fire(uid, 36, 'r36-%s-%d-%s' % (uid, n, rows[0]['id']), now, n=n)

def register():
    """Put both jobs on the alerts loop. Safe to call twice."""
    from . import alerts
    alerts.register_job('report_alerts', 300, report_job); alerts.register_job('streak_alerts', 600, streak_job)
