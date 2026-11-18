"""Server price feed: the bot gets its own candles from the internet, so signals can reach a phone-only owner with NO PC, EA or Windows app.
Off by default. Switch it on in the admin panel (Price feed card) or with the Render variable FEED_ON=1.
What it does, once a minute while on: download closed 15-minute and 1-hour candles, put them in the same candle store the EA uses (owner's slot),
mark the owner's account as a DEMO feed, and run the same signal scan. A signal then goes to phone-mode people (notification + lot size). Nothing here places a trade.
Honest limits:
 - Source is Yahoo's free chart feed. Gold is the futures price (GC=F), not FBS's spot price: it usually differs by a few dollars, and the series has small
   jumps when the futures contract rolls. Use the levels as a guide and check them against your MT5 chart before you place anything.
 - Yahoo is unofficial and may refuse a server (rate limit or block). The admin card shows the exact reason; the feed just tries again a minute later.
 - It stays out of the way when your own EA is online (an EA that reported in the last 2 minutes): two sources would mix two different price scales.
 - Render's free plan sleeps without visitors: keep an uptime monitor pinging /healthz every 10 minutes while you want signals.
Env: FEED_ON (0/1), FEED_MAP (default XAUUSD:GC=F ; add e.g. ,EURUSD:EURUSD=X), FEED_EVERY (seconds, default 60)."""
import os, time, threading
import requests
from . import store as st, bars

STEP = {'M15': 900, 'H1': 3600}
_RANGE = {'M15': ('15m', '10d'), 'H1': ('60m', '60d')}
H1_EVERY = 600                                   # the hour chart changes slowly: fetch it every 10 minutes only
EA_LIVE = 120                                    # an EA that reported this recently owns the candle store
URL = 'https://query1.finance.yahoo.com/v8/finance/chart/%s'
UA = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36'}

class FeedError(Exception): pass

def parse_map(s=None):
    """'XAUUSD:GC=F,EURUSD:EURUSD=X' -> {'XAUUSD': 'GC=F', ...}. Junk entries are ignored."""
    s = os.getenv('FEED_MAP', 'XAUUSD:GC=F') if s is None else s; out = {}
    for part in str(s).split(','):
        if ':' not in part: continue
        a, b = part.split(':', 1); a, b = a.strip().upper(), b.strip()
        if a and b: out[a] = b
    return out

def parse_yahoo(js, tf, now=None):
    """Yahoo chart JSON -> [(t,o,h,l,c,v)] of CLOSED candles, oldest first. Raises FeedError with a plain reason."""
    now = now or time.time(); step = STEP[tf]
    try: ch = js['chart']
    except (TypeError, KeyError): raise FeedError('unexpected reply')
    if ch.get('error'): raise FeedError('Yahoo: ' + str((ch['error'] or {}).get('description') or ch['error'])[:80])
    try:
        r = ch['result'][0]; ts = r['timestamp']; q = r['indicators']['quote'][0]
        O, H, L, C, V = q['open'], q['high'], q['low'], q['close'], q.get('volume') or [0] * len(ts)
    except (TypeError, KeyError, IndexError): raise FeedError('no candles in the reply')
    rows = []
    for i, t in enumerate(ts):
        try: o, h, l, c = float(O[i]), float(H[i]), float(L[i]), float(C[i])
        except (TypeError, ValueError, IndexError): continue                 # Yahoo leaves holes (None) when the market is closed
        if min(o, h, l, c) <= 0 or t + step > now: continue                  # bad price, or the candle is still forming
        rows.append((int(t), o, max(h, o, c), min(l, o, c), c, V[i] if i < len(V) and V[i] else 0))
    rows.sort()
    if not rows: raise FeedError('no closed candles (market closed?)')
    return rows

def fetch(sym, tf, now=None, mp=None):
    tk = (mp or parse_map()).get(sym)
    if not tk: raise FeedError('no feed symbol for ' + sym)
    iv, rg = _RANGE[tf]
    try: r = requests.get(URL % tk, params={'interval': iv, 'range': rg}, headers=UA, timeout=12)
    except requests.RequestException as e: raise FeedError('network: ' + type(e).__name__)
    if r.status_code != 200: raise FeedError('Yahoo HTTP %d' % r.status_code)
    try: js = r.json()
    except ValueError: raise FeedError('Yahoo sent something that is not JSON')
    return parse_yahoo(js, tf, now)

_lock = threading.Lock()
STATUS = {'on': False, 'ok': 0, 'err': '', 'err_at': 0, 'sym': {}, 'note': ''}
_h1 = {}

def status():
    with _lock: s = dict(STATUS, sym={k: dict(v) for k, v in STATUS['sym'].items()})
    s['on'] = st.get('feed_on') == '1'; s['map'] = parse_map(); return s

def symbols():
    have = {x.strip().upper() for x in (st.get('symbols') or '').split(',') if x.strip()}
    return [s for s in parse_map() if s in have]

def check(now=None):
    """Try one download WITHOUT storing anything. -> {'ok': bool, 'msg': str}. Lets the admin test Yahoo from the server before switching on."""
    syms = list(parse_map())
    if not syms: return {'ok': False, 'msg': 'FEED_MAP has no symbols'}
    try: rows = fetch(syms[0], 'M15', now)
    except FeedError as e: return {'ok': False, 'msg': str(e)}
    return {'ok': True, 'msg': '%s: %d closed candles, last close %s at %s UTC' % (syms[0], len(rows), rows[-1][4], time.strftime('%Y-%m-%d %H:%M', time.gmtime(rows[-1][0])))}

def tick(scan, now=None):
    """One round. scan(sym, '') is the app's signal scan. Returns the status dict."""
    now = now or time.time()
    if st.get('feed_on') != '1': return status()
    a = st.acct('')
    if now - a.get('seen', 0) <= EA_LIVE and not a.get('feed'):
        with _lock: STATUS['note'] = 'paused: your own MT5 EA is online and supplies the candles'
        return status()
    done = []; errs = []
    for sym in symbols():
        try:
            m15 = fetch(sym, 'M15', now); bars.merge(sym, 'M15', m15, uid='')
            if now - _h1.get(sym, 0) >= H1_EVERY:
                bars.merge(sym, 'H1', fetch(sym, 'H1', now), uid=''); _h1[sym] = now
            done.append(sym)
            with _lock: STATUS['sym'][sym] = {'last': m15[-1][0], 'close': m15[-1][4], 'at': int(now), 'err': ''}
        except FeedError as e:
            errs.append('%s: %s' % (sym, e))
            with _lock: STATUS['sym'].setdefault(sym, {})['err'] = str(e)
    with _lock:
        STATUS['note'] = ''
        if errs: STATUS['err'], STATUS['err_at'] = '; '.join(errs)[:200], int(now)
        if done: STATUS['ok'] = int(now)
        if done and not errs: STATUS['err'] = ''
    if done:
        st.set_acct({'demo': True, 'feed': 'server'}, '')          # the scan wants a fresh, demo account snapshot
        for sym in done:
            try: scan(sym, '')
            except Exception as e: print('[feed] scan failed', sym, str(e)[:120])
    return status()

_started = False
def start(scan):
    global _started
    if _started: return
    _started = True
    def loop():
        while True:
            time.sleep(max(20, int(os.getenv('FEED_EVERY', '60'))))
            try: tick(scan)
            except Exception as e: print('[feed] round failed', repr(e)[:120])
    threading.Thread(target=loop, daemon=True).start()
