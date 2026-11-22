"""CY5: the Binance group close, the group loss limit and the auto-cycle (TESTNET spot, long-only). Binance has no basket, so, like Deriv (deriv_group.py), the bot adds the legs of one group up itself.
Each round (called from binance_bot._run_once, right after _track) it looks at every group of this person that is fully open on Binance and has a group profit target and/or loss limit (kv 'bg:<grp>', set by groupcap.py):
  1. total = profit already booked by members of the group + the live profit of the legs still open (qty x price, less an estimated 0.1% selling fee, minus what each leg cost).
  2. total >= target, or total <= minus the loss limit (percent of the balance saved when the group's first leg was bought)  ->  sell every open leg at market (closedby 'basket'), one alert for the whole group.
  3. only after a PROFIT close, with the cycle on, a normal multi-entry group, every leg sold, and the bot allowed to trade (switch on, plan active, Binance chosen, testnet): the NEXT group of the same size is queued through deriv_group.reopen (same gates, same daily limit).
Waits, never guesses: a group with a leg that is pending, 'sent' (buy unconfirmed) or 'closing' (sell unconfirmed), or a leg whose price cannot be read, is left alone this round. A leg that cannot be sold stays open and the total is counted again next round.
Spot has no stop built in, so the group is checked about once a minute: a fast move can pass the target or the limit. Nothing here claims it makes more money: repeating trades also repeats losses."""
import time
from decimal import Decimal
from . import store as st, binance_bot as bb, binance_trade as bt, deriv_group as dg, sbauth, push

FEE = 0.001          # ASSUMPTION: Binance spot taker fee, used only to estimate the selling fee of a leg that is still open


def _groups(uid):
    return [r['grp'] for r in st.q("SELECT DISTINCT grp FROM signals WHERE grp IS NOT NULL AND status='open' AND broker='Binance' AND uid=? ORDER BY grp LIMIT 20", (uid,))]


def _live(r, http):
    """-> (estimated profit of one open leg, price) or None when it cannot be worked out."""
    pos = bb._pos(r['id'])
    if not pos: return None
    px = bb._price(pos['pair'], http)
    try: qty, cost, feeq = float(pos['qty']), float(pos['cost']), float(pos.get('fee_q') or 0)
    except (KeyError, TypeError, ValueError): return None
    if px is None or px <= 0: return None
    return qty * px * (1 - FEE) - cost - feeq, px


def check(uid, key, secret, http, now, may_reopen=False):
    """One look at every open Binance group of this person. -> a list with one entry per group that was closed: {'grp','total','next'} (next = ids of the new group, or None)."""
    out = []
    for g in _groups(uid):
        m = dg._meta(g); tgt = dg._f((m or {}).get('tgt')) or dg._f((m or {}).get('dtgt')) or 0; lim = dg.loss_limit(m)
        if tgt <= 0 and lim <= 0: continue
        mem = st.q('SELECT %s FROM signals WHERE grp=? AND uid=? ORDER BY id' % dg.COLS, (g, uid))
        if any(r['status'] in ('pending', 'sent', 'closing') for r in mem): continue
        opn = [r for r in mem if r['status'] == 'open']
        if not opn: continue
        live, spot, skip = 0.0, None, False
        for r in opn:
            v = _live(r, http)
            if v is None: skip = True; break
            live += v[0]; spot = v[1]
        if skip: continue
        booked = sum(dg._f(r['pnl']) or 0 for r in mem if r['status'] == 'closed')
        tot = round(booked + live, 2); hit_t = tgt > 0 and tot >= tgt; hit_l = lim > 0 and tot <= -lim
        if not (hit_t or hit_l): continue
        done, fail = [], False
        for r in opn:
            pos = bb._pos(r['id'])
            if not st.x("UPDATE signals SET status='closing' WHERE id=? AND status='open'", (r['id'],), True): fail = True; continue          # claimed: one sell only
            o = bt.close_long(key, secret, pos['pair'], pos['qty'], 'sxb-%d-c' % r['id'], http, int(now * 1000))
            if not o.get('ok'):
                fail = True; msg = str(o.get('msg'))
                if 'already sent' in msg or 'may or may not' in msg: st.x("UPDATE signals SET note=? WHERE id=?", ('sell not confirmed, check Binance', r['id']))          # stays 'closing': never sold twice
                else: st.x("UPDATE signals SET status='open',note=? WHERE id=?", (msg[:120], r['id']))
                continue
            pnl = round(float(o['quote'] - o['fee_quote'] - Decimal(pos['cost']) - Decimal(pos.get('fee_q') or 0)), 2)
            st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=?", (pnl, int(now), r['id']))
            st.put('closedby:%d' % r['id'], 'basket'); st.put('exitpx:%d' % r['id'], float(o['avg'])); bb._report(uid, r['id'], 'closed', 'basket'); done.append(pnl)
        if not done: continue
        total = round(booked + sum(done), 2)
        try:
            sbauth.notify('%s group %s' % (opn[0]['symbol'], 'stopped at its loss limit' if hit_l and not hit_t else 'closed'), 'Total P/L %s' % total, key='grp%d-closed' % g, only=uid or None)
            push.notify(2 if total > 0 else 4, 'grp%d-closed' % g, sym=opn[0]['symbol'], pnl=total, only=uid or None)
        except Exception: pass
        nxt = None
        if may_reopen and not fail and total > 0 and not (hit_l and not hit_t) and (m or {}).get('k') == 'multi': nxt = dg.reopen(uid, g, m, mem[0], spot, now)
        out.append({'grp': g, 'total': total, 'next': nxt})
    return out
