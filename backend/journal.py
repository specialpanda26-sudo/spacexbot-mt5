"""Section 6: the real Journal and Stats. GET /api/journal returns, for the signed-in person only, their CLOSED trades and the numbers worked out from them.
Nothing here is invented: every row is a row of the signals table (status closed, with a profit figure), every number comes from those rows.
Scope: a normal person = their own uid. The owner (admin) = the owner's own EA ('' scope) + their own Deriv trades (their uid), the same scope as livestats.
Broker: signals.broker says which connection traded it ('Deriv' / 'MT5'). Older rows have no value: Deriv trades carry the note 'x<multiplier>', everything else came through MT5.
The numbers always cover every closed trade of the chosen broker (up to MAX_ROWS); the Wins/Losses filter and the row limit only change the list.
ASSUMPTIONS (tunable): LIMIT rows are sent to the app; MAX_ROWS rows are used for the numbers. Amounts are plain numbers, the app shows them with $ like the live card.
The EA reports only the profit of a closed trade, not why it closed, so there is no tp / sl / manual label here (it would be a guess)."""
import re, time, math
from . import store as st, strategy_info as si, reason as rsn

LIMIT = 300
MAX_ROWS = 5000
KNOWN = ('Deriv', 'MT5')


def scope(uid, admin):
    return ('', uid) if admin else (uid, uid)


def broker_of(row):
    b = str(row.get('broker') or '').strip()
    if b: return b
    return 'Deriv' if re.match(r'^x\d', str(row.get('note') or '')) else 'MT5'


def _canon(b):
    b = str(b or '').strip().lower()
    return next((k for k in KNOWN if k.lower() == b), '')


def _num(v):
    try: x = float(v)
    except (TypeError, ValueError): return None
    return x if x == x and abs(x) != float('inf') else None


def _closed(uid, admin):
    a, b = scope(uid, admin)
    rows = st.q("SELECT id,symbol,side,strategy,entry,sl,tp,fill,lots,pnl,closed,created,note,broker,reason FROM signals "
                "WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'') IN (?,?) ORDER BY COALESCE(closed,created) DESC, id DESC LIMIT %d" % MAX_ROWS, (a, b)) or []
    out = []
    for r in rows:
        p = _num(r.get('pnl'))
        if p is None: continue
        out.append({'id': r['id'], 't': int(r.get('closed') or r.get('created') or 0), 'opened': int(r.get('created') or 0), 'symbol': r['symbol'],
                    'side': str(r['side'] or '').lower(), 'strategy': r['strategy'], 'strategy_name': si.label(r['strategy']), 'pnl': round(p, 2),
                    'result': 'win' if p > 0 else 'loss', 'broker': broker_of(r), 'entry': r.get('entry'), 'fill': r.get('fill'), 'sl': r.get('sl'),
                    'tp': r.get('tp'), 'lots': r.get('lots'), 'why': rsn.short(r.get('reason')), '_raw': r.get('reason')})
    if uid:                                                  # phone-mode trades the person logged themselves (assist_log), broker 'Phone'
        try:
            for r in st.q("SELECT l.sid AS sid,l.pnl AS pnl,l.lots AS lots,l.done AS done,l.ts AS ts,s.symbol AS symbol,s.side AS side,s.strategy AS strategy,s.entry AS entry,s.sl AS sl,s.tp AS tp,s.created AS created,s.reason AS reason "
                          "FROM assist_log l JOIN signals s ON s.id=l.sid WHERE l.uid=? AND l.action='taken' AND l.pnl IS NOT NULL", (uid,)) or []:
                p = _num(r.get('pnl'))
                if p is None: continue
                out.append({'id': -int(r['sid']), 't': int(r.get('done') or r.get('ts') or r.get('created') or 0), 'opened': int(r.get('ts') or r.get('created') or 0), 'symbol': r['symbol'],
                            'side': str(r['side'] or '').lower(), 'strategy': r['strategy'], 'strategy_name': si.label(r['strategy']), 'pnl': round(p, 2),
                            'result': 'win' if p > 0 else 'loss', 'broker': 'Phone', 'entry': r.get('entry'), 'fill': None, 'sl': r.get('sl'),
                            'tp': r.get('tp'), 'lots': r.get('lots'), 'why': rsn.short(r.get('reason')), '_raw': r.get('reason')})
        except Exception as e: print('phone-mode rows skipped', e)
        out.sort(key=lambda r: (r['t'], r['id']), reverse=True)
    return out


def _detail(r):
    raw = r.pop('_raw', None); r['why_lines'] = rsn.lines(raw, r.get('strategy'))
    r['how'] = [{'name': si.name(x), 'about': si.desc(x)} for x in str(r.get('strategy') or '').split('+') if x]
    c = st.q("SELECT v FROM kv WHERE k=?", ('closedby:%s' % r['id'],), True); r['closed_by'] = c['v'] if c else ''


def open_now(uid, admin):
    a, b = scope(uid, admin); out = []
    for r in st.q("SELECT id,symbol,side,strategy,entry,sl,tp,fill,lots,created,status,reason FROM signals WHERE status IN('open','pending','sent') AND COALESCE(uid,'') IN (?,?) ORDER BY id DESC LIMIT 50", (a, b)) or []:
        out.append({'id': r['id'], 'symbol': r['symbol'], 'side': str(r['side'] or '').lower(), 'strategy_name': si.label(r['strategy']), 'status': r['status'], 'entry': r['entry'], 'fill': r['fill'],
                    'sl': r['sl'], 'tp': r['tp'], 'lots': r['lots'], 't': int(r['created'] or 0), 'why_lines': rsn.lines(r['reason'], r['strategy']),
                    'how': [{'name': si.name(x), 'about': si.desc(x)} for x in str(r['strategy'] or '').split('+') if x]})
    return out


def numbers(rows):
    """rows: newest first. Same maths the Stats tab always showed (break-even win rate, luck range), now on real trades."""
    n = len(rows); pn = [r['pnl'] for r in rows]
    w = [p for p in pn if p > 0]; l = [p for p in pn if p <= 0]
    gp = sum(w); gl = -sum(l)
    aw = gp / len(w) if w else 0.0; al = gl / len(l) if l else 0.0
    be = al / (aw + al) * 100 if aw + al else 50.0
    band = math.sqrt(be / 100 * (1 - be / 100) / n) * 196 if n else 0.0
    run = mx = 0; eq = peak = dd = 0.0
    for p in reversed(pn):                       # oldest first
        run = run + 1 if p <= 0 else 0; mx = max(mx, run)
        eq += p; peak = max(peak, eq); dd = max(dd, peak - eq)
    return {'trades': n, 'wins': len(w), 'losses': len(l), 'win_rate': round(len(w) / n * 100, 1) if n else 0.0, 'break_even': round(be, 1), 'band': round(band, 1),
            'won': round(gp, 2), 'lost': round(gl, 2), 'net': round(gp - gl, 2), 'per_trade': round((gp - gl) / n, 2) if n else 0.0, 'profit_factor': round(gp / gl, 2) if gl > 0 else None,
            'loss_streak': mx, 'best': round(max(pn), 2) if n else 0.0, 'worst': round(min(pn), 2) if n else 0.0, 'max_drawdown': round(dd, 2)}


def by_pair(rows):
    g = {}
    for r in rows:
        o = g.setdefault(r['symbol'], {'symbol': r['symbol'], 'n': 0, 'wins': 0, 'pnl': 0.0}); o['n'] += 1; o['wins'] += r['pnl'] > 0; o['pnl'] += r['pnl']
    out = sorted(g.values(), key=lambda o: (-o['n'], o['symbol']))
    for o in out: o['pnl'] = round(o['pnl'], 2); o['win_rate'] = round(o['wins'] / o['n'] * 100)
    return out


def snapshot(uid, admin=False, broker='', result='all', limit=LIMIT, now=None):
    allr = _closed(uid, admin); brokers = sorted({r['broker'] for r in allr}, key=lambda b: (b not in KNOWN, b))
    want = _canon(broker) or (str(broker or '').strip()[:20] if broker else '')
    rows = [r for r in allr if r['broker'] == want] if want else allr
    show = [r for r in rows if result == 'all' or r['result'] == result] if result in ('win', 'loss') else rows
    shown = show[:max(1, int(limit))]
    for r in shown: _detail(r)
    for r in allr: r.pop('_raw', None)
    return {'rows': shown, 'open': open_now(uid, admin), 'total': len(show), 'stats': numbers(rows), 'pairs': by_pair(rows), 'brokers': brokers, 'broker': want,
            'result': result if result in ('win', 'loss') else 'all', 'ts': int(now or time.time())}
