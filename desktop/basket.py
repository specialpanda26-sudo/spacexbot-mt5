"""Burst baskets for the desktop app. The server sends a burst group as ONE `basket` (res['basket']) instead of a `signal`.
Mirrors ExecuteBasket in ea/SpaceXBridge.mq5: every entry gets the comment SXB<signal id>G<group id>, the risk is ONE entry's share,
and when one entry's lot would be below the broker minimum only as many minimum-lot entries open as the group's total risk allows.
Closing the group at its target / give-back / loss limit is DK2 (until then every entry still closes at its own stop or take profit)."""
import math
from .broker import BrokerError


def sid_of(cm):
    """Signal id from an MT5 comment: 'SXB12' (single trade) or 'SXB12G5' (burst entry). 0 = not ours."""
    cm = cm or ''
    if not cm.startswith('SXB'): return 0
    a = cm[3:].split('G', 1)
    if not a[0].isdigit() or (len(a) == 2 and not a[1].isdigit()): return 0
    return int(a[0])


def gid_of(cm):
    cm = cm or ''
    if sid_of(cm) and 'G' in cm[3:]: return int(cm[3:].split('G', 1)[1])
    return 0


def _ids(bk):
    return [int(x) for x in str(bk.get('ids') or '').replace(' ', '').split(',') if x.isdigit()]


def _open(e, bk, ids, acct, bot):
    """None = the entries were handled (opened or rejected one by one); text = the whole group is refused."""
    c = e.cfg
    if not bot: return 'bot is off in the app'
    if not acct['demo'] and not c['allow_live']: return 'live account blocked (allow_live is off)'
    if not acct['trade_allowed']: return 'Algo Trading is off in MetaTrader 5'
    side = bk.get('side'); canon = str(bk.get('symbol') or '').strip(); sym = e._resolve(canon) if canon else None
    try: sl, tp, risk, gid = float(bk['sl']), float(bk['tp']), float(bk['risk_pct']), int(bk['gid'])
    except (KeyError, TypeError, ValueError): return 'bad signal'
    if side not in ('buy', 'sell') or not (0 < risk <= 5): return 'bad signal'
    i = e.b.symbol(sym) if sym else None
    if not i or not i['tradable']: return 'symbol not found or not tradable'
    pt, ask, bid = i['point'], i['ask'], i['bid']
    if ask <= 0 or bid <= 0: return 'no price'
    if (ask - bid) / pt > c['max_spread_points']: return 'spread too wide'
    buy = side == 'buy'; price = ask if buy else bid; sl, tp = round(sl, i['digits']), round(tp, i['digits'])
    if not ((sl < price < tp) if buy else (tp < price < sl)): return 'SL/TP wrong side of price (stale signal)'
    lvl = i['stops_level'] * pt
    if abs(price - sl) < lvl or abs(price - tp) < lvl: return 'inside broker stop level'
    if i['tick_value'] <= 0 or i['tick_size'] <= 0: return 'no tick value'
    n = len(ids); step = i['vol_step'] or 0.01; nd = max(0, -int(math.floor(math.log10(step) + 1e-9)))
    raw = acct['balance'] * risk / 100.0 / ((abs(price - sl) / i['tick_size']) * i['tick_value'])      # risk = ONE entry's share
    lots = math.floor(raw / step + 1e-9) * step; want = n
    if lots < i['vol_min'] - 1e-12:
        want = int(math.floor(raw * n / i['vol_min'] + 1e-9)); lots = i['vol_min']
        if want < 2: return 'min lot too big for a group'
        want = min(want, n)
    lots = round(min(lots, i['vol_max'], c['max_lots']), nd)
    placed = []
    for k, sid in enumerate(ids):
        if k >= want: e._queue(sid, 'rejected', reason='min lot: group trimmed to keep the risk'); continue
        try: r = e.b.send_market(sym, side, lots, sl, tp, 'SXB%dG%d' % (sid, gid), c['deviation'], c['magic'], i['fill'])
        except Exception as x: r = {'ok': False, 'retcode': 'MT5 error ' + x.__class__.__name__}
        if r['ok']: placed.append((sid, r))
        else: e._queue(sid, 'rejected', reason=('order failed %s' % r['retcode'])[:120])
    try: pos = {sid_of(p['comment']): p['pid'] for p in e.b.positions(c['magic'])}
    except BrokerError: pos = {}          # the next pass adopts them from the comment
    for sid, r in placed:
        if sid in pos: e.known[sid] = pos[sid]
        e._queue(sid, 'open', ticket=r['ticket'], lots=lots, price=r['price'])
    e.log('burst group %d: %d of %d %s %s opened, %.2f lots each' % (gid, len(placed), n, side.upper(), sym, lots))
    return None


def run(e, bk, acct, bot):
    ids = [x for x in _ids(bk) if x not in e.done]          # never place the same entry twice
    if not ids: return
    e.done = (e.done + ids)[-200:]
    try: why = _open(e, bk, ids, acct, bot)
    except BrokerError as x: why = 'MetaTrader 5: %s' % x
    if why:
        e.log('burst group refused: %s' % why)
        for sid in ids: e._queue(sid, 'rejected', reason=why[:120])
