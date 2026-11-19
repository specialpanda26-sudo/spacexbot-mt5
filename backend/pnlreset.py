"""Section 6 (next): the Reset today button. The person taps it and the "today" number on their Profit and loss card and Live card starts again from zero.
It only moves where "today" starts FOR THAT PERSON (one kv row, pnlreset:<uid>, holding the time of the reset). Nothing is deleted or edited:
the Journal, Stats, the 7-day and all-time numbers, the profit curve, the broker's own balance and the risk limits (daily loss limit, loss streak) all
keep reading the real trades. A reset from an earlier day is ignored, so it ends by itself at 00:00 UTC (the same day start the rest of the app uses).
Undo puts the day back. ASSUMPTION: the reset time is stored 1 second ahead, so a trade that closed in the very second of the tap stays in the old count."""
import time
from . import store as st


def _key(uid): return 'pnlreset:%s' % uid


def get(uid, base=None):
    """Seconds (UTC) of the person's reset today, or 0 if they did not reset today. base = start of today (default: the server's day start)."""
    base = st.day_start() if base is None else int(base)
    try: t = int(float(st.get(_key(uid)) or 0))
    except (TypeError, ValueError): t = 0
    return t if t >= base else 0


def since(uid, base=None):
    """Where today's count starts for this person: the day start, or the reset if they tapped Reset today."""
    base = st.day_start() if base is None else int(base)
    return max(base, get(uid, base))


def reset(uid, now=None):
    t = int(now or time.time()) + 1
    st.put(_key(uid), t); return t


def clear(uid):
    st.x('DELETE FROM kv WHERE k=?', (_key(uid),))
