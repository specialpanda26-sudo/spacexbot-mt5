"""Section N6a: system alerts, push kinds 26 to 29.
26 MT5 connected (first time the EA is seen), 27 MT5 offline (no heartbeat for OFFLINE_MIN minutes), 28 back online, 29 server updated.
Two small jobs on the ONE loop in backend/alerts.py (register() below). Each takes `now` so a test can fix the clock.
Kinds 30 (monitor mode) and 31 (account type) are NOT here: they fire from a button press, see Section N6b.
Tunables (assumptions, change here):"""
import os, time
from . import store as st, push

FRESH = 120            # the EA counts as online when its last heartbeat is newer than this many seconds (same as the rest of the app)
OFFLINE_MIN = 5        # 27: only say "offline" after this many minutes without a heartbeat, so a short blip is silent

def _scopes():
    """The owner's EA ('') and every subscriber who ever linked an MT5 key."""
    return [''] + [r['uid'] for r in st.q('SELECT uid FROM links WHERE seen>0') if r['uid']]

def _send(scope, kind, key, **facts):
    """The owner's EA goes to the admins' phones only (same rule as the owner's trades); a subscriber's EA goes to that subscriber only."""
    if scope: push.notify_user(scope, kind, key, **facts)
    else: push.notify(kind, key, admins=True, **facts)

def ea_job(now=None):
    """26 first seen online, 27 offline for OFFLINE_MIN minutes, 28 back. State per person in kv ea26:<scope> = 'up' or 'down:<last heartbeat>'."""
    now = now or time.time()
    for sc in _scopes():
        a = st.acct(sc) or {}; seen = int(a.get('seen') or 0)
        if not seen or a.get('src') == 'deriv': continue            # never seen, or a Deriv snapshot (that is not MT5)
        k = 'ea26:' + sc; s = st.get(k) or ''; up = now - seen < FRESH
        if not s:
            if up: st.put(k, 'up'); _send(sc, 26, 'e26-' + sc)
        elif s == 'up' and not up and now - seen >= OFFLINE_MIN * 60:
            st.put(k, 'down:%d' % seen); _send(sc, 27, 'e27-%s-%d' % (sc, seen), mins=int((now - seen) // 60))
        elif s.startswith('down:') and up:
            st.put(k, 'up'); _send(sc, 28, 'e28-%s-%s' % (sc, s[5:]))

_booted = False
def boot_job(now=None):
    """29 the server started with a NEW version (Render sets RENDER_GIT_COMMIT). Admins only; same version again (a wake-up) says nothing; the very first start only remembers."""
    global _booted
    if _booted: return
    _booted = True
    ver = (os.getenv('RENDER_GIT_COMMIT') or os.getenv('BUILD_ID') or '').strip()[:12]
    if not ver: return
    old = st.get('boot29'); st.put('boot29', ver)
    if old and old != ver: push.notify(29, 'u29-' + ver, admins=True)

def register():
    """Put both jobs on the alerts loop. Safe to call twice."""
    from . import alerts
    alerts.register_job('ea_alerts', 60, ea_job); alerts.register_job('boot_alerts', 60, boot_job)
