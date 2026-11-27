"""Burst mode (quick-profit scalps). Section 1 = the server engine. Nothing here places a trade by itself: the scanner (Section 2) asks it,
and the MT5 bridge (Section 3) does the closing.

The idea, in plain words:
 - QUIET: when the bot has not made a signal for `idle_min` minutes, it is allowed to take a small, quick chance (quick burst).
 - QUICK burst: `quick_n` entries on the SAME idea (same side, stop and target), each aiming for `quick_usd` USD profit of its own.
 - BIG burst (rare): when `burst_big_score` or more strategies agree, `big_n` entries, each aiming for `big_usd` USD.
 - GIVE-BACK guard: `giveback` percent. If the group was in profit and that profit then falls by this share from its best, the bridge closes the
   whole group (the profit is going away). 0 = off.
 - The entries SHARE the normal risk of one trade (multi.share), so one failed burst loses what one normal trade would have lost.
 - It never goes past the burst ceiling (owner setting burst_ceiling, default 15) for positions held at once, and every other gate still applies:
   bot on, EA online, demo/real rules, weekend, daily and weekly loss limits, loss-streak stop, max trades a day, news lock, currency exposure.
   Only two things are relaxed for a burst: the normal 'max open positions' number (the burst ceiling replaces it) and the 60-minute symbol cooldown.
 - One burst at a time per person: a new one waits until the last burst is closed.
Settings are saved per person in kv 'burst:<uid>' (uid '' = the owner's own bot). Group facts are kept in kv 'bg:<group id>'.
Nothing here claims it makes more money. Only a demo run or tools/backtest.py can say that."""
import json, time
from . import store as st, links, risk, limits, multi, groupcap, burst_look, burst_live, burst_results, automode, burst_bridge, openrisk

HI = 30
AUTO_WHY = 'Auto mode is on, and Auto mode turns burst off'          # BX1: the scanner always stopped here, the card never said so
DEF = {'on': False, 'idle_min': 5, 'quick_n': 5, 'big_n': 15, 'quick_usd': 0.5, 'big_usd': 1.0, 'giveback': 40, 'stake_usd': 0.5, 'minute': False, 'minute_n': 2, 'loss_usd': 0.0}
KEYS = tuple(DEF)
USD_LO, USD_HI = 0.05, 1000.0
SAFE_MAX_LOT = 0.06          # LS1: the biggest lot any one MT5 trade may have unless the person raises it on their own panel
SMALLEST_LOT = 0.01          # LS1: what 'Smallest lot' asks for; the bridge lifts it to the broker's own minimum when that is bigger
LOT_MODES = ('smallest', 'fixed', 'auto')


def enabled():
    """The owner's master switch (setting burst_enabled, default on). Off = nobody gets burst."""
    return st.get('burst_enabled') != '0'


def ceiling():
    """Most positions held at once while bursting (owner setting burst_ceiling, default 15, at most 30, at least 2)."""
    try: v = int(float(st.get('burst_ceiling')))
    except (TypeError, ValueError): v = 15
    return max(2, min(HI, v))


def big_score():
    """How many strategies must agree before a burst counts as BIG (owner setting burst_big_score, default 3)."""
    try: v = int(float(st.get('burst_big_score')))
    except (TypeError, ValueError): v = 3
    return max(2, min(10, v))


def _balance(uid):          # BT13
    try: return float((st.acct(uid) or {}).get('balance') or 0)
    except (TypeError, ValueError): return 0.0


def _raw(uid):
    try: j = json.loads(st.get('burst:' + (uid or '')) or '{}')
    except (TypeError, ValueError): j = {}
    return j if isinstance(j, dict) else {}


def _clamp(v, lo, hi, d, f=int):
    if isinstance(v, bool): return d
    try: x = f(float(v))
    except (TypeError, ValueError, OverflowError): return d
    if x != x: return d
    return max(lo, min(hi, x))


def _mode(j):
    """LS1: how the lot is chosen. A saved mode wins; an older save with a fixed lot stays 'fixed'; nothing saved = 'auto' (sized by risk, then cut to the biggest lot)."""
    m = j.get('lot_mode')
    if m in LOT_MODES: return m
    return 'fixed' if _clamp(j.get('lot'), 0, 100.0, 0.0, float) > 0 else 'auto'


def get(uid=''):
    """The person's choices, always valid (a bad saved value falls back to the default)."""
    j = _raw(uid); c = ceiling()
    quick = min(c, _clamp(j.get('quick_n'), 1, c, DEF['quick_n']))
    big = max(quick, min(c, _clamp(j.get('big_n'), 1, c, DEF['big_n'])))
    return {'on': j.get('on') is True, 'idle_min': _clamp(j.get('idle_min'), 1, 60, DEF['idle_min']), 'quick_n': quick, 'big_n': big,
            'quick_usd': round(_clamp(j.get('quick_usd'), USD_LO, USD_HI, DEF['quick_usd'], float), 2),
            'big_usd': round(_clamp(j.get('big_usd'), USD_LO, USD_HI, DEF['big_usd'], float), 2),
            'giveback': _clamp(j.get('giveback'), 0, 90, DEF['giveback']),
            'stake_usd': round(_clamp(j.get('stake_usd'), 0, USD_HI, DEF['stake_usd'], float), 2),
            'loss_usd': round(_clamp(j.get('loss_usd'), 0, USD_HI, 0.0, float), 2), 'lot': round(_clamp(j.get('lot'), 0, 100.0, 0.0, float), 2), 'max_lot': round(_clamp(j.get('max_lot'), 0, 100.0, 0.0, float), 2),          # LOT1
            'lot_mode': _mode(j),          # LS1: smallest | fixed | auto
                      # BT13
            'minute': j.get('minute') is True, 'minute_n': _clamp(j.get('minute_n'), 2, c, DEF['minute_n'])}          # BT7


def eff_max_lot(uid=''):
    """LS1: the biggest lot for any one MT5 trade. The person's own number, or SAFE_MAX_LOT (0.06) when they have not set one."""
    m = get(uid)['max_lot']
    return m if m > 0 else SAFE_MAX_LOT


def max_lot_soft(uid=''):
    """LS1: 1 when the biggest lot is only the safe default (the person set none). The bridge then never refuses a trade just because the broker's own
    minimum lot is above 0.06: it uses that minimum. A number the person typed is never softened (0 = not soft)."""
    return 1 if get(uid)['max_lot'] <= 0 else 0


def eff_lot(uid=''):
    """LS1: the lot the bridge must use for each entry. 0 = size by risk (the bridge then cuts it to the biggest lot).
    Smallest -> 0.01 (lifted to the broker minimum by the bridge). Fixed -> the person's number, never above the biggest lot."""
    g = get(uid)
    if g['lot_mode'] == 'smallest': return SMALLEST_LOT
    if g['lot_mode'] == 'fixed' and g['lot'] > 0: return min(g['lot'], eff_max_lot(uid))
    return 0.0


def _whole(v, lo, hi, name):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('%s must be a whole number' % name)
    try: f = float(v)
    except ValueError: raise ValueError('%s must be a whole number' % name)
    if f != f or f != int(f) or f < lo or f > hi: raise ValueError('%s must be a whole number from %d to %d' % (name, lo, hi))
    return int(f)


def _money(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('%s must be a number in USD' % name)
    try: f = float(v)
    except ValueError: raise ValueError('%s must be a number in USD' % name)
    if f != f or f < USD_LO or f > USD_HI: raise ValueError('%s must be from %g to %g USD' % (name, USD_LO, USD_HI))
    return round(f, 2)


def save(uid, d):
    """Validate and save. Raises ValueError (nothing saved) on bad input. Returns get(uid)."""
    if not isinstance(d, dict): raise ValueError('Send the choices as an object')
    cur = _raw(uid); c = ceiling(); new = {}
    if 'on' in d:
        if not isinstance(d['on'], bool): raise ValueError('on must be true or false')
        new['on'] = d['on']
    if 'idle_min' in d: new['idle_min'] = _whole(d['idle_min'], 1, 60, 'Quiet minutes')
    if 'minute' in d:          # BT7
        if not isinstance(d['minute'], bool): raise ValueError('minute must be true or false')
        new['minute'] = d['minute']
    if 'minute_n' in d: new['minute_n'] = _whole(d['minute_n'], 2, c, 'Entries each minute')
    if 'quick_n' in d: new['quick_n'] = _whole(d['quick_n'], 1, c, 'Quick burst entries')
    if 'big_n' in d: new['big_n'] = _whole(d['big_n'], 1, c, 'Big burst entries')
    if 'quick_usd' in d: new['quick_usd'] = _money(d['quick_usd'], 'Quick target')
    if 'big_usd' in d: new['big_usd'] = _money(d['big_usd'], 'Big target')
    if 'giveback' in d: new['giveback'] = _whole(d['giveback'], 0, 90, 'Give-back guard')
    if 'stake_usd' in d:
        try: sv = float('nan') if isinstance(d['stake_usd'], bool) else float(d['stake_usd'])
        except (TypeError, ValueError): sv = float('nan')
        if sv != sv or not (sv == 0 or 0.1 <= sv <= USD_HI): raise ValueError('Stake per entry must be 0 (normal sizing) or from 0.1 to %g USD' % USD_HI)
        new['stake_usd'] = round(sv, 2)
    if 'loss_usd' in d:          # BT13: the most one burst group may lose, in USD (0 = no limit)
        try: lv = float('nan') if isinstance(d['loss_usd'], bool) else float(d['loss_usd'])
        except (TypeError, ValueError): lv = float('nan')
        if lv != lv or not (lv == 0 or 0.1 <= lv <= USD_HI): raise ValueError('Most a burst group may lose must be 0 (no limit) or from 0.1 to %g USD' % USD_HI)
        new['loss_usd'] = round(lv, 2)
    if 'lot' in d:          # LOT1: lots for each burst entry on MT5 (0 = automatic)
        try: tv = float('nan') if isinstance(d['lot'], bool) else float(d['lot'])
        except (TypeError, ValueError): tv = float('nan')
        if tv != tv or not (tv == 0 or 0.01 <= tv <= 100): raise ValueError('Lot per entry must be from 0.01 to 100')
        new['lot'] = round(tv, 2)
    if 'max_lot' in d:          # LC1: the biggest lot any one MT5 trade may have (0 = no cap)
        try: mv = float('nan') if isinstance(d['max_lot'], bool) else float(d['max_lot'])
        except (TypeError, ValueError): mv = float('nan')
        if mv != mv or not (mv == 0 or 0.01 <= mv <= 100): raise ValueError('Biggest lot must be from 0.01 to 100 (empty or 0 = the safe default, %g)' % SAFE_MAX_LOT)
        new['max_lot'] = round(mv, 2)
    if 'lot' in d and 'lot_mode' not in d: new['lot_mode'] = 'fixed' if new.get('lot', 0) > 0 else 'auto'          # LS1: older callers send only the lot (0 = automatic)
    if 'lot_mode' in d:          # LS1
        if d['lot_mode'] not in LOT_MODES: raise ValueError('Lot mode must be smallest, fixed or auto')
        new['lot_mode'] = d['lot_mode']
    chk = dict(cur); chk.update(new)          # LS1: a fixed lot above the biggest lot would be silently cut, so say so instead
    mode = _mode(chk); big = _clamp(chk.get('max_lot'), 0, 100.0, 0.0, float); big = big if big > 0 else SAFE_MAX_LOT
    if mode == 'fixed':
        fl = _clamp(chk.get('lot'), 0, 100.0, 0.0, float)
        if fl <= 0: raise ValueError('Fixed lot needs a lot size from 0.01, for example 0.02')
        if fl > big + 1e-9: raise ValueError('Lot per entry (%g) is above your biggest lot (%g). Raise the biggest lot first, or choose a smaller lot.' % (fl, big))
    cur.update(new)
    st.put('burst:' + (uid or ''), json.dumps(cur))
    return get(uid)


# ---------------- the quiet timer ----------------
def _last_signal(uid):
    r = st.q("SELECT MAX(created) c FROM signals WHERE COALESCE(uid,'')=?", (uid or '',), True) or {}
    return int(r.get('c') or 0)


def closed(uid='', now=None):
    """The scanner calls this whenever the bot could NOT trade (stopped, MT5 offline, a loss limit). The quiet timer then starts again from here,
    so turning the bot on after a long stop does not fire a burst on the first look."""
    st.put('burst:closed:' + (uid or ''), int(now or time.time()))


def quiet_since(uid=''):
    try: c = int(float(st.get('burst:closed:' + (uid or '')) or 0))
    except (TypeError, ValueError): c = 0
    return max(_last_signal(uid), c)


def meta(grp):
    """The burst facts of a group: {k: 'quick'|'big', n, each (USD per entry), gb (give-back percent), t}. None = not a burst group."""
    try: j = json.loads(st.get('bg:%d' % int(grp)) or 'null')
    except (TypeError, ValueError): return None
    return j if isinstance(j, dict) else None


def active(uid=''):
    """Is a burst of this person still waiting or open?"""
    for r in st.q("SELECT DISTINCT grp FROM signals WHERE grp IS NOT NULL AND status IN('pending','sent','open') AND COALESCE(uid,'')=?", (uid or '',)):
        m = meta(r['grp'])
        if m and m.get('k') != 'multi': return True          # a normal multi-entry group is not a burst: it must not hold the next burst back
    return False


def due(uid='', now=None):
    """-> (ok, why). ok = the bot may look for a burst chance right now. why is plain words when it is not ok."""
    now = now or time.time(); p = get(uid)
    if not enabled(): return False, 'burst mode is switched off by the owner'
    if not p['on']: return False, 'burst mode is off'
    if automode.on(): return False, AUTO_WHY          # BX1
    ok, why = risk.global_gate(now, uid=uid, burst=True)
    if not ok: return False, why
    mm = p.get('minute') is True          # BT7: trade every minute: a new group every minute, even while the last one is still open
    if active(uid) and not mm: return False, 'a burst is already running'
    quiet = int(now - quiet_since(uid)); need = 1 if mm else p['idle_min']
    if quiet < need * 60: return False, 'quiet for %d of %d minutes' % (quiet // 60, need)
    return True, 'ok'


def look(uid='', now=None):
    """due() for the scanner. When the bot cannot trade right now (stopped, MT5 offline, a loss limit...) the quiet timer starts again from this moment."""
    now = now or time.time(); ok, why = due(uid, now)
    if not ok and not (why.startswith('quiet for') or why in ('a burst is already running', 'burst mode is off', 'burst mode is switched off by the owner', AUTO_WHY)): closed(uid, now)
    return ok, why


def plan(uid, score, now=None, n=None):
    """-> (plan or None, why). The kind and size of the burst for a setup that `score` strategies agree on."""
    p = get(uid); big = n is None and int(score or 0) >= big_score() and p['big_n'] > p['quick_n']          # BT7: an entries number given (every minute) is never a big burst
    want = n if n else p['big_n'] if big else p['quick_n']
    room = (limits.UNLIMITED if limits.no_cap(uid) else ceiling()) - risk.open_count(uid)          # OC1: no burst ceiling for the owner when 'No limit' is on
    mt = limits.trades(uid)
    if mt > 0:
        used = st.q("SELECT COUNT(*) n FROM signals WHERE created>=? AND status IN('pending','sent','open','closed') AND COALESCE(uid,'')=?", (st.day_start(), uid or ''), True)['n']
        room = min(room, mt - used)
    if not openrisk.total_fits(uid, links.risk(uid) if uid else st.fget('risk_pct')): return None, 'open stop-loss ceiling reached'          # Section 2
    n = min(want, room)
    if n < 2: return None, 'not enough room for a burst (%d free)' % max(0, room)
    if p['loss_usd'] > 0 and _balance(uid) <= 0: return None, 'the account balance is not known yet, so the loss limit of %g USD cannot be set' % p['loss_usd']          # BT13
    return {'kind': 'big' if big else 'quick', 'n': n, 'each': p['big_usd'] if big else p['quick_usd'], 'giveback': p['giveback'], 'score': int(score or 0), 'stake': p['stake_usd']}, 'ok'


def create(uid, sym, s, pl, reason='', now=None):
    """Write the group: pl['n'] pending signals with the same side, stop and target, sharing the normal risk of one trade.
    s = the setup dict from brain.evaluate (side, entry, sl, tp, strategy, score). Returns the list of new signal ids (the first is the group id)."""
    now = int(now or time.time()); n = int(pl['n']); uid = uid or ''
    base = links.risk(uid) if uid else st.fget('risk_pct'); rp = multi.share(openrisk.eff_base(uid, base), n)          # Section 2: a managed size risks a share of its size, not of the balance
    sql = 'INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'
    first = st.x(sql, (sym, s['side'], s['entry'], s['sl'], s['tp'], rp, s['strategy'], s['score'], 'pending', now, uid or None, None, reason))
    st.x('UPDATE signals SET grp=? WHERE id=?', (first, first))
    ids = [first]
    for _ in range(n - 1):
        ids.append(st.x(sql, (sym, s['side'], s['entry'], s['sl'], s['tp'], rp, s['strategy'], s['score'], 'pending', now, uid or None, first, reason)))
    gm = {'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now, 'stake': pl.get('stake', 0), 'lot': eff_lot(uid)}
    gr = groupcap.rules(uid, n)          # the person's group target / loss limit, when they switched it on
    if gr: gm.update(tgt=gr['tgt'], loss=gr['loss'])
    if not gr: gm['dtgt'] = round(float(pl['each']) * n, 2)          # BT2: the Deriv engine closes the group when the entries together reach entries x target each
    lu = get(uid)['loss_usd']; bal = _balance(uid)          # BT13: the person's USD loss limit becomes the percent of the balance the bridge and the Deriv engine already stop a group at; the smaller of two limits wins
    if lu > 0 and bal > 0:
        pc = min(100.0, round(lu / bal * 100, 4)); gm['loss'] = min(gm['loss'], pc) if gm.get('loss') else pc; gm['loss_usd'] = lu
    st.put('bg:%d' % first, json.dumps(gm))
    return ids


def basket(s, uid=''):
    """If the pending signal `s` belongs to a burst group, return the WHOLE group for the EA: {gid, symbol, side, sl, tp, risk_pct, each, gb, ids:'1,2,3'}.
    Only entries still pending, of this person only. Anything that is not a burst group (a normal single trade, a normal multi-entry group) -> None."""
    if not s: return None
    g = (st.q('SELECT grp FROM signals WHERE id=?', (s['id'],), True) or {}).get('grp')
    m = meta(g) if g else None
    if not m: return None
    ids = [r['id'] for r in st.q("SELECT id FROM signals WHERE grp=? AND status='pending' AND COALESCE(uid,'')=? ORDER BY id", (g, uid or ''))]
    if not ids: return None
    return {'gid': int(g), 'symbol': s['symbol'], 'side': s['side'], 'sl': s['sl'], 'tp': s['tp'], 'risk_pct': s['risk_pct'],
            'each': groupcap.each_for(m, len(ids)) if m.get('tgt') or m.get('k') == 'multi' else m.get('each'), 'gb': m.get('gb', 0),
            'tgt': float(m.get('tgt') or 0), 'loss': float(m.get('loss') or 0), 'lot': float(m.get('lot') or 0), 'kind': m.get('k'), 'ids': ','.join(str(i) for i in ids)}


# ---------------- what the app shows ----------------
def explain(uid='', now=None, admin=False):
    """-> {state, why}. state: off | running | waiting | ready."""
    from . import botstate
    now = now or time.time(); p = get(uid)
    if not enabled(): return {'state': 'off', 'why': 'Burst mode is switched off by the owner.'}
    if not p['on']: return {'state': 'off', 'why': 'Burst mode is off.'}
    if active(uid): return {'state': 'running', 'why': 'A burst is running. It closes at the profit target, or when the profit starts to go away.'}
    ok, why = due(uid, now)
    if why == AUTO_WHY: return {'state': 'waiting', 'blocked': 'auto', 'why': 'Paused: Auto mode is ON, and Auto mode turns burst off. Switch Auto mode off (admin page, or AUTO_MODE=0 on Render) and burst starts.'}          # BX1
    if ok: return {'state': 'ready', 'why': 'Quiet long enough. It looks for a quick chance on the next candle check.'}
    if why.startswith('quiet for'): return {'state': 'waiting', 'why': 'Watching. The bot has been %s without a trade; after that it looks for a quick small-profit chance.' % why[len('quiet for '):]}
    w = botstate._words(why)
    if why == 'EA offline': w += burst_bridge.since(uid, now)          # BT12: how long the MT5 bridge has been silent
    return {'state': 'waiting', 'why': w}


def minlot(uid=''):
    """LOT3: {known, warn, message}. Words only."""
    out = {'known': False, 'warn': False, 'message': ''}
    try:
        from . import presets, bars, indicators
        a = st.acct(uid) or {}; bal = _balance(uid); sym = presets.clean_sym(a.get('sym'))
        if bal <= 0 or not sym: return out
        p = get(uid); n = max(2, p['quick_n']); base = links.risk(uid) if uid else st.fget('risk_pct'); total = bal * float(base) / 100.0
        mine = {x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()}; wide = automode.max_stop(); lines = []
        for name, f in sym.items():
            if mine and name not in mine: continue
            b = bars.get(name, 'M15', uid)
            if len(b) < 15: continue
            r = indicators.atr(b)[-1]
            if not r > 0: continue
            one = f['vol_min'] * (r * wide / f['tick_size']) * f['tick_value']
            el = eff_lot(uid)          # LS1
            if el > 0:
                lot = max(el, f['vol_min']); each = one * lot / f['vol_min']
                lines.append('%s: %g lot each risks up to about $%.2f per entry, $%.2f for %d entries.%s' % (name, lot, each, each * n, n, ' (Your lot is under the broker minimum, so %g is used.)' % f['vol_min'] if el < f['vol_min'] - 1e-12 else ''))
            elif one * n > total:
                fit = int(total // one) if one > 0 else n
                lines.append('%s: the smallest lot (%g) risks up to about $%.2f each, but your risk of $%.2f is shared by %d entries, so only %d would open. Raise Risk %%, or set Lot per entry, or use fewer entries.' % (name, f['vol_min'], one, total, n, max(fit, 0)))
        if not lines: return out
        out.update(known=True, warn=True, message=' '.join(lines[:3]))
    except Exception as e: print('[burst] minlot failed', repr(e)[:80])
    return out


def view(uid='', now=None):
    return {'minlot': minlot(uid), 'settings': get(uid), 'enabled': enabled(), 'ceiling': ceiling(), 'big_score': big_score(), 'now': explain(uid, now), 'look': burst_look.last(uid, now), 'group': burst_live.group(uid, now), 'results': burst_results.line(uid, now)}


def fixed_size(entry, sl, tp, bal, stake, mult):
    """BT2: (stake, stop_loss_money, take_profit_money) or None. The person chose the stake of each burst entry (Deriv). Same multiplier maths as
    deriv._size: the loss at the stop = stake x multiplier x stop distance, and it must stay under the stake. Deriv itself decides if the stake is big enough."""
    try: entry, sl, tp, bal, stake, mult = float(entry), float(sl), float(tp), float(bal), float(stake), float(mult)
    except (TypeError, ValueError): return None
    if not entry or entry == sl or entry == tp or bal <= 0 or stake <= 0 or mult <= 0: return None
    risk = round(stake * mult * abs(entry - sl) / entry, 2)
    if stake > bal * 0.5 or risk <= 0 or risk >= stake: return None
    return round(stake, 2), risk, round(risk * abs(tp - entry) / abs(entry - sl), 2)
