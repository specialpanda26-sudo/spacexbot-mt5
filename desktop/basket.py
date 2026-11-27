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
    why = e.tiny_why(bk, i, acct, price, sl)          # LS5
    if why: return why
    n = len(ids); step = i['vol_step'] or 0.01; nd = max(0, -int(math.floor(math.log10(step) + 1e-9)))
    raw = acct['balance'] * risk / 100.0 / ((abs(price - sl) / i['tick_size']) * i['tick_value'])      # risk = ONE entry's share
    try: fl = float(bk.get('lot') or 0)          # LOT1: the person chose the lot of each entry
    except (TypeError, ValueError): fl = 0.0
    if fl > 0: raw = max(fl, i['vol_min'])
    lots = math.floor(raw / step + 1e-9) * step; want = n
    if lots < i['vol_min'] - 1e-12:
        want = int(math.floor(raw * n / i['vol_min'] + 1e-9)); lots = i['vol_min']
        if want < 2: return 'min lot too big for a group'
        want = min(want, n)
    cap, why = e.cap_for(bk, i)          # LC2: obey the person's biggest lot (it only ever lowers the lot)
    if why: return why
    lots = math.floor(min(lots, i['vol_max'], cap) / step + 1e-9) * step; lots = round(lots, nd)
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
    _register(e, bk, gid, placed, acct)          # DK2
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


# ---------------- DK2: closing the group ----------------
import time
ARM = 30          # percent: the give-back guard only starts once the group profit reached this share of its target (EA: BasketArmPct)


def _num(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError): return d


def _register(e, bk, gid, placed, acct):
    """Remember the group's rules (target, give-back, loss limit in money) so the watch can close it. Saved with the app's state."""
    if not placed: return
    tgt, each, loss = _num(bk.get('tgt')), _num(bk.get('each')), _num(bk.get('loss'))
    e.groups[gid] = {'t': round(tgt if tgt > 0 else each * len(placed), 2), 'b': int(_num(bk.get('gb'))), 'p': 0.0,
                     'l': round(acct['balance'] * loss / 100.0, 2) if loss > 0 else 0.0, 'x': 0, 's': None, 'o': e.clock(), 'sids': [s for s, _ in placed]}
    e._save()


def _group_of(e, sid):
    for g in e.groups.values():
        if sid in (g.get('sids') or ()): return g
    return None


def close_extra(e, sid, info):
    """What the 'closed' report carries. A trade the group watch closed says 'basket' (with the group profit); the closing price is sent when known."""
    out = {'pnl': info['pnl'], 'reason': info['reason']}
    if info.get('price'): out['price'] = info['price']
    g = _group_of(e, sid)
    if g is not None and g.get('x'):
        out['reason'] = 'basket'
        if g.get('s') is not None: out['gpnl'] = round(g['s'], 2)
    return out


def _close(e, ps):
    for p in ps:
        try: e.b.close_position(p, e.cfg['deviation'], e.cfg['magic'])
        except Exception as x: e.log('group close failed for %s: %s (will retry)' % (p.get('ticket'), x.__class__.__name__))


def manage(e):
    """One look at every open group. Same rules as ManageBaskets in the EA: loss limit first, then target, then give-back."""
    if not e.groups: return
    try: pos = e.b.positions_pl(e.cfg['magic'])
    except BrokerError: return
    except Exception as x: e.log('group watch: %s' % x.__class__.__name__); return
    live = {}
    for p in pos:
        g = gid_of(p['comment'])
        if g: live.setdefault(g, []).append(p)
    now = e.clock(); dirty = False
    for gid, m in list(e.groups.items()):
        ps = live.get(gid, [])
        if not ps:          # nothing left: forget it once every close was reported
            if not any(s in e.known for s in m.get('sids', ())) and now - (m.get('x') or m.get('o') or 0) > (60 if m.get('x') else 120): del e.groups[gid]; dirty = True
            continue
        if m.get('x'): _close(e, ps); continue          # already closing: finish it (retry what failed)
        total = round(sum(p['pl'] for p in ps), 2)
        if total > m['p']: m['p'] = total; dirty = True
        why = None
        if m['l'] > 0 and total <= -m['l']: why = 'hit its loss limit'
        elif m['t'] > 0 and total >= m['t']: why = 'reached its target'
        elif m['b'] > 0 and m['t'] > 0 and m['p'] >= m['t'] * ARM / 100.0 and total <= m['p'] * (1 - m['b'] / 100.0): why = 'is giving the profit back'
        if why:
            m['x'] = now; m['s'] = total; dirty = True
            e.log('burst group %d %s: %+.2f (best %+.2f, target %.2f) - closing the group' % (gid, why, total, m['p'], m['t'])); _close(e, ps)
    if dirty: e._save()


def pause(e, stop, secs):
    """Wait `secs` between passes, but look at the open groups about once a second (a small target can come and go within one pass)."""
    end = time.time() + secs
    while not stop.is_set():
        left = end - time.time()
        if left <= 0: break
        if e.groups:
            try: manage(e)
            except Exception as x: e.log('group watch error: %s' % x.__class__.__name__)
        stop.wait(min(1.0, max(0.05, left)))


# ---------------- DK3: 5-minute candles ----------------
def rates_m5(e, name, off):
    """The 5-minute candles for the server's burst scan (the EA sends them too: 450 on the first push, then the newest 14). [] when MT5 cannot give them,
    so the 15-minute and 1-hour candles still go."""
    try: r = e.b.rates(name, 'M5', 450 if e.first_push else 14)
    except Exception as x: e.log('%s 5-minute candles: %s' % (name, x)); return []
    return [[q[0] - off] + q[1:] for q in (r or [])]
