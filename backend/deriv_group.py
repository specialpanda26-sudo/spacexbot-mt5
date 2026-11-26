"""CY2: the Deriv group close and the auto-cycle. Deriv has no basket, so the bot adds the entries of one group up itself.
Each round (called from deriv._run_once, right after _track) it looks at every group that is fully open on Deriv and has a group profit target (kv 'bg:<grp>', 'tgt' in USD, set by groupcap.py).
  1. total = profit already booked by members of the group + the live profit of the members still open.
  2. total >= target  ->  sell every open member at market (closedby 'basket'), one alert for the whole group.
  2b. GL1: total <= minus the group loss limit (loss percent of the balance saved when the group opened)  ->  the same sale; a loss never starts the next group.
  3. only if the cycle is on (cycle.py), the group is a normal multi-entry group, it ended in profit and every member was sold:
     open the NEXT group of the same size: same symbol, side and stop/target distances, around the current price.
     The new entries are ordinary pending signals, so the same round opens them through the normal Deriv path (_trade).
The new group still has to pass the risk gates (bot on, loss limits, daily trade limit, open-position room, weekend rules, news lock, currency exposure),
and the cycle stops for the day after cycle.max_per_day new groups. A group that ended on a stop loss, by hand or on a failed sell never starts the next one.
Nothing here claims it makes more money: repeating trades also repeats losses. Deriv still refuses a stake under 1 USD (deriv._size), a new entry that cannot be sized is rejected as usual."""
import json, time
from . import store as st, cycle, groupcap, risk, multi, links, limits, learn, sbauth, push, burst_live, manual_close, openrisk

COLS = 'id,grp,symbol,side,entry,sl,tp,risk_pct,strategy,score,reason,ticket,status,pnl'


def _meta(g):
    try: j = json.loads(st.get('bg:%d' % int(g)) or 'null')
    except (TypeError, ValueError): return None
    return j if isinstance(j, dict) else None


def _f(x):
    try: v = float(x)
    except (TypeError, ValueError): return None
    return v if v == v and abs(v) < 1e12 else None


def _day_key(uid, now): return 'cyc:%s:%d' % (uid or '', int(now) // 86400)


def used_today(uid, now=None): return int(_f(st.get(_day_key(uid, now or time.time()))) or 0)


def _open_groups(uid):
    return [r['grp'] for r in st.q("SELECT DISTINCT grp FROM signals WHERE grp IS NOT NULL AND status='open' AND ticket IS NOT NULL AND broker='Deriv' AND COALESCE(uid,'')=? ORDER BY grp LIMIT 20", (uid or '',))]


def _sell(sess, cid, fallback):
    """Sell one contract at market. -> its final profit, or None when Deriv did not confirm the sale."""
    d = sess.ask({'sell': cid, 'price': 0}); s = d.get('sell') if isinstance(d, dict) else None
    if not isinstance(s, dict) or (s.get('sold_for') is None and not s.get('contract_id')): return None
    p = sess.ask({'proposal_open_contract': 1, 'contract_id': cid}).get('proposal_open_contract')
    v = _f(p.get('profit')) if isinstance(p, dict) else None
    return round(v if v is not None else fallback, 2)


def note_open_balance(grp, bal):
    """GL1: save the account balance from just BEFORE this group's first entry was bought (kv 'bg:<grp>', 'bal0'). The group loss limit is a percent of it. Saved once.
    -> True when saved, False when the group is unknown, the balance is not a positive number, or it was saved before."""
    m = _meta(grp); b = _f(bal)
    if not m or not b or b <= 0 or _f(m.get('bal0')): return False
    m['bal0'] = round(b, 2); st.put('bg:%d' % int(grp), json.dumps(m)); return True


def loss_limit(m):
    """GL1: the group loss in USD at which the group is stopped (loss percent x the saved balance / 100), or 0 when there is no limit or no saved balance."""
    lp = _f((m or {}).get('loss')) or 0; b0 = _f((m or {}).get('bal0')) or 0
    return round(b0 * lp / 100.0, 2) if lp > 0 and b0 > 0 else 0.0


def check(sess, uid, acct, now=None):
    """One look at every open Deriv group of this person. -> a list with one entry per group that was closed: {'grp','total','next'} (next = ids of the new group, or None)."""
    now = now or time.time(); out = []
    for g in _open_groups(uid):
        m = _meta(g); tgt = _f((m or {}).get('tgt')) or _f((m or {}).get('dtgt')) or 0
        lim = loss_limit(m)
        manual = manual_close.on(uid)          # MC1: the owner closes the profits: no sale at the target, the live profit is still read
        if manual: tgt = 0
        if tgt <= 0 and lim <= 0 and not manual: continue
        mem = st.q('SELECT %s FROM signals WHERE grp=? AND COALESCE(uid,\'\')=? ORDER BY id' % COLS, (g, uid or ''))
        if any(r['status'] in ('pending', 'sent') for r in mem): continue          # not all entries are open yet, or one buy is unconfirmed: the total would be wrong
        opn = [r for r in mem if r['status'] == 'open' and r['ticket']]
        if not opn: continue
        live, spot, seen, skip = 0.0, None, {}, False
        for r in opn:
            try: cid = int(r['ticket'])
            except (TypeError, ValueError): skip = True; break
            p = sess.ask({'proposal_open_contract': 1, 'contract_id': cid}).get('proposal_open_contract')
            pr = _f(p.get('profit')) if isinstance(p, dict) else None
            if pr is None or str(p.get('is_sold')).lower() in ('1', 'true'): skip = True; break          # _track records a sold entry first; then the total is right
            live += pr; seen[r['id']] = (cid, pr); spot = spot or _f(p.get('current_spot'))
        if skip: continue
        booked = sum(_f(r['pnl']) or 0 for r in mem if r['status'] == 'closed')
        tot = round(booked + live, 2); hit_t = tgt > 0 and tot >= tgt; hit_l = lim > 0 and tot <= -lim
        burst_live.save(g, live, tot, len(opn), tgt, lim, now)          # BT6: the card and the floating figure read this
        if not (hit_t or hit_l): continue
        done, fail = [], False
        for r in opn:
            cid, pr = seen[r['id']]
            fin = _sell(sess, cid, pr)
            if fin is None: fail = True; continue          # stays open; the next round tries again with the total re-counted
            if st.x("UPDATE signals SET status='closed',pnl=?,closed=? WHERE id=? AND status='open'", (fin, int(now), r['id']), True):
                st.put('closedby:%d' % r['id'], 'basket')
                learn.log(uid, 'closed', r['strategy'], r['symbol'], r['side'], fin, {'reason': 'basket'}); done.append(fin)
        if not done: continue
        total = round(booked + sum(done), 2)
        try:
            sbauth.notify('%s group %s' % (opn[0]['symbol'], 'stopped at its loss limit' if hit_l and not hit_t else 'closed'), 'Total P/L %s' % total, key='grp%d-closed' % g, only=uid or None)
            push.notify(2 if total > 0 else 4, 'grp%d-closed' % g, sym=opn[0]['symbol'], pnl=total, only=uid or None)
        except Exception: pass
        nxt = None
        if not fail and total > 0 and not (hit_l and not hit_t) and (m or {}).get('k') == 'multi': nxt = reopen(uid, g, m, mem[0], spot, now)
        out.append({'grp': g, 'total': total, 'next': nxt})
    return out


def reopen(uid, parent, m, first, spot, now=None):
    """The next group, or None. Every refusal is saved as a plain-words note (kv 'cyc_why:<uid>') for the Bot tab."""
    now = now or time.time(); uid = uid or ''
    n = int(m.get('n') or 0); r = cycle.rules(uid, n)
    if not r: return _why(uid, 'cycle off', None)
    if used_today(uid, now) >= r['max_per_day']: return _why(uid, 'daily limit of %d new groups reached' % r['max_per_day'], None)
    spot = _f(spot)
    if not spot or spot <= 0: return _why(uid, 'no current price', None)
    sym, side = first['symbol'], first['side']
    e, sl, tp = _f(first['entry']), _f(first['sl']), _f(first['tp'])
    if not e or sl is None or tp is None or sl == e or tp == e: return _why(uid, 'the old stop or target is unreadable', None)
    ok, why = risk.global_gate(now, uid=uid)
    if ok and risk.weekend_skip(sym, now): ok, why = False, 'weekend/Friday-night risk'
    if ok and risk.weekday_skip(sym, now): ok, why = False, 'Bitcoin rests on weekdays'
    if ok: ok, why = risk.symbol_gate(sym, side, now, uid=uid, cool=False)          # no cooldown: the cycle is the point; news lock and exposure still count
    if not ok: return _why(uid, why, None)
    if limits.max_open(uid) - risk.open_count(uid) < n: return _why(uid, 'not enough room for %d entries' % n, None)
    if not openrisk.total_fits(uid, links.risk(uid) if uid else st.fget('risk_pct')): return _why(uid, 'open stop-loss ceiling reached', None)          # Section 2
    dsl, dtp = abs(e - sl), abs(tp - e); sg = 1 if side == 'buy' else -1
    nsl, ntp = round(spot - sg * dsl, 5), round(spot + sg * dtp, 5)
    base = links.risk(uid) if uid else st.fget('risk_pct'); rp = multi.share(openrisk.eff_base(uid, base), n)
    sql = 'INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'
    a = (sym, side, spot, nsl, ntp, rp, first['strategy'], first['score'], 'pending', int(now), uid or None)
    g = st.x(sql, a + (None, first['reason'])); st.x('UPDATE signals SET grp=? WHERE id=?', (g, g)); ids = [g]
    for _ in range(n - 1): ids.append(st.x(sql, a + (g, first['reason'])))
    groupcap.mark(g, uid, n, now)
    st.put('cyc_from:%d' % g, int(parent)); st.put(_day_key(uid, now), used_today(uid, now) + 1); _why(uid, '', None)
    return ids


def _why(uid, text, ret):
    st.put('cyc_why:%s' % (uid or ''), text); return ret


def why(uid=''): return st.get('cyc_why:%s' % (uid or '')) or ''
