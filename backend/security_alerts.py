"""Section N6e: security notice, push kind 50 ("<what happened>. If this was not you, change your password now.").
Goes to ALL of that person's own phones, only about THEIR OWN account, never with a key or a secret in it. Category 'system', and push.BYPASS_KINDS holds 50: quiet hours and the daily cap do not hold it; the person's own System switch still does.
No loop job: each notice is called from the place where the thing happens (app.py), AFTER it succeeded.
What the server can see, and what it cannot:
  SEEN: an MT5 key made or replaced, the MT5 link removed, a broker connected or disconnected, 'sign out other devices', a new sign-in (Supabase's last_sign_in_at).
  NOT SEEN: a password or email change. Supabase does that in the browser and does not tell this server.
Tunables (assumptions, change here):"""
import time
from . import store as st, push

SIGNIN_GAP = 6 * 3600       # at most one 'new sign-in' notice per person per this many seconds (a safety net if Supabase ever moves last_sign_in_at on a token refresh)
_last = {}; _noted = {}

def notice(uid, what):
    """Send one security notice. Never raises: a failed notice must not break the action itself."""
    try: push.notify_user(uid, 50, 'x50-%s-%d' % (uid, int(time.time() * 1000)), what=what)
    except Exception as e: print('security notice failed:', e)

def signin(uid, stamp, now=None):
    """Called on every signed-in request with Supabase's last_sign_in_at. A NEW stamp = a new sign-in. The first stamp ever seen is only remembered (no notice)."""
    try:
        if not stamp or _last.get(uid) == stamp: return
        if len(_last) > 5000: _last.clear()
        old = _last.get(uid) or st.get('sin:' + uid)
        _last[uid] = stamp
        if old == stamp: return
        st.put('sin:' + uid, stamp); now = now or time.time()
        if old and now - _noted.get(uid, 0) >= SIGNIN_GAP: _noted[uid] = now; notice(uid, 'New sign-in on your account')
    except Exception as e: print('sign-in check failed:', e)
