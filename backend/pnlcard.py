"""Section 9A: the Profit and loss card on Home. GET /api/pnl returns, for the signed-in person only, the profit of their CLOSED trades:
today, the last 7 days and all time (amount + number of trades), the win rate, and the profit curve (running total after each closed trade, oldest first).
Nothing is invented: every number comes from the same closed-trade rows as the Journal (backend/journal.py), same scope (a person = their own uid;
the owner = their own EA '' scope + their own Deriv trades) and the same ?broker= picker (Deriv / MT5, default all).
Not the broker's equity history: we only store the profit of each closed trade, so the curve is "profit since the first trade", not the account balance.
ASSUMPTIONS (tunable): "today" = since 00:00 UTC (the same day the Live card uses); "week" = the last 7 days (rolling), not Monday to Sunday;
MAXP = most curve points sent to the app (a long history is thinned, the first and the last point always stay)."""
import time
from . import journal as jn

MAXP = 80
WEEK = 7 * 86400


def _thin(pts, maxp=MAXP):
    n = len(pts)
    if n <= maxp: return pts
    idx = sorted({round(i * (n - 1) / (maxp - 1)) for i in range(maxp)})
    return [pts[i] for i in idx]


def _part(rows, since):
    x = [r for r in rows if r['t'] >= since]
    return {'pnl': round(sum(r['pnl'] for r in x), 2), 'n': len(x)}


def snapshot(uid, admin=False, broker='', now=None):
    now = int(now or time.time())
    allr = jn._closed(uid, admin)
    brokers = sorted({r['broker'] for r in allr}, key=lambda b: (b not in jn.KNOWN, b))
    want = jn._canon(broker) or (str(broker or '').strip()[:20] if broker else '')
    rows = [r for r in allr if r['broker'] == want] if want else allr          # newest first
    num = jn.numbers(rows); run = 0.0; pts = []
    for r in reversed(rows):                                                   # oldest first
        run += r['pnl']; pts.append({'t': r['t'], 'v': round(run, 2), 'id': r['id']})
    return {'today': _part(rows, now - now % 86400), 'week': _part(rows, now - WEEK),
            'total': {'pnl': pts[-1]['v'] if pts else 0.0, 'n': len(rows)},
            'stats': {k: num[k] for k in ('trades', 'wins', 'losses', 'win_rate', 'max_drawdown', 'best', 'worst')},
            'curve': _thin(pts), 'curve_n': len(pts), 'brokers': brokers, 'broker': want, 'ts': now}
