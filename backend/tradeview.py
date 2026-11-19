"""Section 9B: the chart pop-up for ONE closed trade. GET /api/trade/<id> returns, for the signed-in person only, what the server really stored:
the prices (planned entry, fill, stop loss, take profit), the lots, both times, the profit, and the candles the server still holds around the trade.
Nothing is invented:
- The EA and the Deriv loop store only the PROFIT and the CLOSE TIME of a closed trade (backend/app.py ea_report, backend/deriv.py). There is no exit price and no
  reason it closed (stop loss, take profit or by hand), so "exit" is always {recorded: False} here and the page says so. The time it closed IS stored, so the
  page can mark that moment, but never a price.
- Candles live in server memory only (backend/bars.py, newest ~600 per market and timeframe, lost on a restart), so an old trade may have none. Then the
  answer says so and the page draws just the stored price levels.
Scope = the same as the Journal (backend/journal.py): a person sees only their own trades; the owner sees their own EA ('' scope) and their own Deriv trades.
ASSUMPTIONS (tunable): the chart uses M15 candles, PRE bars before the trade opened and POST bars after it closed; more than MAXC candles are merged into
bigger ones (open of the first, high, low, close of the last) so the picture stays small; fewer than MINC candles counts as no candles."""
import math, time
from . import store as st, bars, journal as jn, strategy_info as si

TF = 'M15'; TFS = 900
PRE = 24; POST = 8; MAXC = 90; MINC = 5
OPEN_NOTE = 'This trade is still open. The numbers and the chart update when you open it again.'
PRICE_NOTE = 'The exit price is not recorded: when a trade closes your broker reports only its profit. The line on the chart marks the time it closed, not a price.'
EXIT_NOTE = ('The exit price and the reason this trade closed (stop loss, take profit or closed by hand) are not recorded: when a trade closes your broker '
             'reports only its profit. The line on the chart marks the time it closed, not a price.')


def _px(v):
    x = jn._num(v)
    return round(x, 6) if x is not None and x > 0 else None


def _dec(prices):
    d = 2
    for p in prices:
        s = ('%.6f' % p).rstrip('0'); d = max(d, len(s.split('.')[1]) if '.' in s else 0)
    return min(d, 6)


def _ok(r):
    try: return all(math.isfinite(float(r[k])) and float(r[k]) > 0 for k in ('o', 'h', 'l', 'c')) and int(r['t']) > 0
    except (KeyError, TypeError, ValueError): return False


def _merge(rows, k):
    out = []
    for i in range(0, len(rows), k):
        g = rows[i:i + k]
        out.append([g[0]['t'], g[0]['o'], max(x['h'] for x in g), min(x['l'] for x in g), g[-1]['c']])
    return out


def _candles(scopes, symbol, t0, t1):
    """The candles the server still holds around the trade, from the scope that has the most of them."""
    best = []
    for who in dict.fromkeys(scopes):
        sel = [r for r in bars.get(symbol, TF, who) if _ok(r) and t0 - PRE * TFS <= r['t'] <= t1 + POST * TFS]
        if len(sel) > len(best): best = sel
    if len(best) < MINC: return {'tf': TF, 'secs': TFS, 'rows': [], 'covers_open': False, 'covers_close': False, 'merged': 1}
    k = -(-len(best) // MAXC)
    secs = TFS * k
    rows = _merge(best, k) if k > 1 else [[r['t'], r['o'], r['h'], r['l'], r['c']] for r in best]
    lo, hi = rows[0][0], rows[-1][0] + secs
    return {'tf': TF, 'secs': secs, 'rows': rows, 'covers_open': lo <= t0 < hi, 'covers_close': lo <= t1 < hi, 'merged': k}


def detail(uid, admin, tid):
    """One trade of this person (closed, or still open), or None (not theirs, no real profit figure on a closed one, or no such trade)."""
    try: tid = int(tid)
    except (TypeError, ValueError): return None
    a, b = jn.scope(uid, admin)
    r = st.q("SELECT id,symbol,side,strategy,entry,sl,tp,fill,lots,pnl,closed,created,note,broker,status FROM signals "
             "WHERE id=? AND status IN ('open','closed') AND COALESCE(uid,'') IN (?,?)", (tid, a, b), True)
    if not r: return None
    is_open = r.get('status') == 'open'
    p = jn._num(r.get('pnl'))
    if p is None and not is_open: return None
    opened = int(r.get('created') or 0); closed = None if is_open else int(r.get('closed') or r.get('created') or 0)
    why = None if is_open else (st.get('closedby:%d' % r['id']) or None)
    lv = {'entry': _px(r.get('entry')), 'fill': _px(r.get('fill')), 'sl': _px(r.get('sl')), 'tp': _px(r.get('tp'))}
    lots = jn._num(r.get('lots'))
    return {'id': r['id'], 'symbol': r['symbol'], 'side': str(r['side'] or '').lower(), 'strategy': r['strategy'], 'strategy_name': si.label(r['strategy']),
            'broker': jn.broker_of(r), 'lots': lots if lots and lots > 0 else None, 'pnl': round(p, 2) if p is not None else None, 'result': None if p is None else 'win' if p > 0 else 'loss',
            'status': 'open' if is_open else 'closed', 'opened_by': 'bot', 'closed_by': why,
            'opened': opened, 'closed': closed, 'levels': lv, 'dec': _dec([x for x in lv.values() if x]),
            'exit': {'recorded': False, 'price': None, 'reason': why, 'note': OPEN_NOTE if is_open else PRICE_NOTE if why else EXIT_NOTE},
            'candles': _candles((a, b), r['symbol'], opened, closed or int(time.time()))}
