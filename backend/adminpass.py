"""Admin ACCESS PASS. The owner sets ADMIN_PASS (8+ characters) on the server. Whoever opens #admin and types it gets a signed 12-hour pass
(kept in the browser tab only) that unlocks the /api/admin/* routes, with no sign-in needed. Nothing else is unlocked by it.
Safety: the code is compared in constant time | 5 wrong tries from one address lock that address for 10 minutes | 30 wrong tries from anywhere
lock the pass for 10 minutes | changing ADMIN_PASS ends every pass already handed out | if ADMIN_PASS is not set (or shorter than 8) the feature is OFF."""
import os, time, hmac, hashlib, threading

TTL = 12 * 3600         # how long a pass lasts (seconds)
MIN_LEN = 8             # a shorter ADMIN_PASS is treated as not set
MAX_TRIES = 5           # wrong tries per address ...
GLOBAL_TRIES = 30       # ... and from everyone together ...
WINDOW = 600            # ... within this many seconds locks it for that long
_fails = {}; _all = []; _lk = threading.Lock()

def _pw(): return os.getenv('ADMIN_PASS', '')
def enabled(): return len(_pw()) >= MIN_LEN
def _key(): return hashlib.sha256(('sxa-adminpass|' + _pw()).encode('utf-8')).digest()
def _sig(exp): return hmac.new(_key(), str(int(exp)).encode(), hashlib.sha256).hexdigest()
def _same(a, b): return hmac.compare_digest(hashlib.sha256(str(a).encode('utf-8')).digest(), hashlib.sha256(str(b).encode('utf-8')).digest())

def issue(now=None):
    """A pass that ends TTL seconds from now: 'expiry.signature'."""
    exp = int((now if now is not None else time.time()) + TTL); return '%d.%s' % (exp, _sig(exp))

def valid(tok, now=None):
    """True only for a pass we signed, that has not expired, under the CURRENT ADMIN_PASS."""
    if not enabled() or not isinstance(tok, str) or '.' not in tok: return False
    e, s = tok.split('.', 1)
    try: exp = int(e)
    except ValueError: return False
    if exp <= (now if now is not None else time.time()): return False
    return _same(s, _sig(exp))

def _recent(lst, now): return [t for t in lst if now - t < WINDOW]

def attempt(code, ip, now=None):
    """-> (token, status, wait_seconds). status: 'ok' | 'wrong' | 'locked' | 'off'."""
    now = now if now is not None else time.time()
    if not enabled(): return None, 'off', 0
    with _lk:
        mine = _fails[ip] = _recent(_fails.get(ip, []), now); world = _all[:] = _recent(_all, now)
        if len(mine) >= MAX_TRIES: return None, 'locked', int(mine[0] + WINDOW - now) + 1
        if len(world) >= GLOBAL_TRIES: return None, 'locked', int(world[0] + WINDOW - now) + 1
        if _same(code, _pw()):
            _fails.pop(ip, None); return issue(now), 'ok', 0
        mine.append(now); _all.append(now)
        if len(_fails) > 5000: _fails.clear()
        return None, 'wrong', 0

def reset():
    """Forget all failed tries (used by the tests)."""
    with _lk: _fails.clear(); _all.clear()
