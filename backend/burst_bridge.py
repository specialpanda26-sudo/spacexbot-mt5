"""BT12: how long ago the MT5 bridge (the EA) last talked to the server. The burst card already says 'MT5 is not talking to the server' when the EA has been
silent for more than 2 minutes; this adds the missing fact, how long it has been, so 'waiting for MT5' can be told apart from 'burst has nothing to trade'.
Words only: nothing here places or closes a trade."""
import time
from . import store as st, burst_look


def since(uid='', now=None):
    """-> ' Last contact: 14 min ago.' (starts with a space), or ' The bridge has not connected yet.' when it never did."""
    now = now or time.time()
    try: seen = int((st.acct(uid) or {}).get('seen') or 0)
    except (TypeError, ValueError): seen = 0
    if seen <= 0: return ' The bridge has not connected yet.'
    return ' Last contact: %s.' % burst_look.ago(now - seen)
