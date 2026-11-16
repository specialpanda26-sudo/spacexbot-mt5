"""High-impact news lock from the keyless ForexFactory weekly feed (same source trading_skills uses).
The feed rate-limits (HTTP 429 above ~1 request / 5 min), so it is cached for an hour and a stale copy is
reused if a refresh fails. If it has never loaded, the lock FAILS OPEN and /api/status says so."""
import time, threading, datetime as dt
import requests
URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json'
_lock = threading.Lock(); _rows = None; _at = 0.0; _try = 0.0

def _fetch():
    global _rows, _at, _try
    now = time.time()
    if _rows is not None and now - _at < 3600: return
    if now - _try < 300: return                       # never hammer the feed
    _try = now
    try:
        r = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}, timeout=8)
        d = r.json() if r.status_code == 200 else None
        if isinstance(d, list): _rows = d; _at = now
    except Exception as e: print('news fetch failed', e)

def set_rows(rows):                                   # tests / manual seeding
    global _rows, _at
    with _lock: _rows = rows; _at = time.time()

def events(now=None, impact=('high',)):
    with _lock: _fetch()
    out = []
    for r in (_rows or []):
        try: t = dt.datetime.fromisoformat(r['date']).timestamp()
        except Exception: continue
        if (r.get('impact') or '').lower() in impact: out.append({'t': t, 'ccy': r.get('country'), 'title': r.get('title')})
    return sorted(out, key=lambda e: e['t'])

def currencies(sym):
    s = sym.upper()
    if len(s) < 6: return {'USD'}
    c = {s[:3], s[3:6]}
    if 'XAU' in c or 'XAG' in c: c.add('USD')         # metals trade on USD data
    return c

def blocked(sym, now=None, before=30, after=30):
    """-> (is_blocked, reason). Blocks from `before` min ahead of a high-impact release to `after` min past it."""
    now = now or time.time(); ccy = currencies(sym)
    for e in events():
        if e['ccy'] in ccy and e['t'] - before * 60 <= now <= e['t'] + after * 60:
            return True, f"news: {e['ccy']} {e['title']}"
    return False, 'ok'

def next_high(now=None, ccy=None):
    now = now or time.time()
    for e in events():
        if e['t'] >= now and (not ccy or e['ccy'] in ccy): return {'in_min': int((e['t'] - now) / 60), 'ccy': e['ccy'], 'title': e['title']}
    return None

def loaded(): return _rows is not None
