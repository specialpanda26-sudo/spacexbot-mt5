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
from . import store as st, links, risk, limits, multi

HI = 30
DEF = {'on': False, 'idle_min': 5, 'quick_n': 5, 'big_n': 15, 'quick_usd': 0.5, 'big_usd': 1.0, 'giveback': 40}
KEYS = tuple(DEF)
USD_LO, USD_HI = 0.05, 1000.0


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


def get(uid=''):
    """The person's choices, always valid (a bad saved value falls back to the default)."""
    j = _raw(uid); c = ceiling()
    quick = min(c, _clamp(j.get('quick_n'), 1, c, DEF['quick_n']))
    big = max(quick, min(c, _clamp(j.get('big_n'), 1, c, DEF['big_n'])))
    return {'on': j.get('on') is True, 'idle_min': _clamp(j.get('idle_min'), 1, 60, DEF['idle_min']), 'quick_n': quick, 'big_n': big,
            'quick_usd': round(_clamp(j.get('quick_usd'), USD_LO, USD_HI, DEF['quick_usd'], float), 2),
            'big_usd': round(_clamp(j.get('big_usd'), USD_LO, USD_HI, DEF['big_usd'], float), 2),
            'giveback': _clamp(j.get('giveback'), 0, 90, DEF['giveback'])}


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
    if 'quick_n' in d: new['quick_n'] = _whole(d['quick_n'], 1, c, 'Quick burst entries')
    if 'big_n' in d: new['big_n'] = _whole(d['big_n'], 1, c, 'Big burst entries')
    if 'quick_usd' in d: new['quick_usd'] = _money(d['quick_usd'], 'Quick target')
    if 'big_usd' in d: new['big_usd'] = _money(d['big_usd'], 'Big target')
    if 'giveback' in d: new['giveback'] = _whole(d['giveback'], 0, 90, 'Give-back guard')
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
        if meta(r['grp']): return True
    return False


def due(uid='', now=None):
    """-> (ok, why). ok = the bot may look for a burst chance right now. why is plain words when it is not ok."""
    now = now or time.time(); p = get(uid)
    if not enabled(): return False, 'burst mode is switched off by the owner'
    if not p['on']: return False, 'burst mode is off'
    ok, why = risk.global_gate(now, uid=uid, burst=True)
    if not ok: return False, why
    if active(uid): return False, 'a burst is already running'
    quiet = int(now - quiet_since(uid))
    if quiet < p['idle_min'] * 60: return False, 'quiet for %d of %d minutes' % (quiet // 60, p['idle_min'])
    return True, 'ok'


def look(uid='', now=None):
    """due() for the scanner. When the bot cannot trade right now (stopped, MT5 offline, a loss limit...) the quiet timer starts again from this moment."""
    now = now or time.time(); ok, why = due(uid, now)
    if not ok and not (why.startswith('quiet for') or why in ('a burst is already running', 'burst mode is off', 'burst mode is switched off by the owner')): closed(uid, now)
    return ok, why


def plan(uid, score, now=None):
    """-> (plan or None, why). The kind and size of the burst for a setup that `score` strategies agree on."""
    p = get(uid); big = int(score or 0) >= big_score() and p['big_n'] > p['quick_n']
    want = p['big_n'] if big else p['quick_n']
    room = ceiling() - risk.open_count(uid)
    mt = limits.trades(uid)
    if mt > 0:
        used = st.q("SELECT COUNT(*) n FROM signals WHERE created>=? AND status IN('pending','sent','open','closed') AND COALESCE(uid,'')=?", (st.day_start(), uid or ''), True)['n']
        room = min(room, mt - used)
    n = min(want, room)
    if n < 2: return None, 'not enough room for a burst (%d free)' % max(0, room)
    return {'kind': 'big' if big else 'quick', 'n': n, 'each': p['big_usd'] if big else p['quick_usd'], 'giveback': p['giveback'], 'score': int(score or 0)}, 'ok'


def create(uid, sym, s, pl, reason='', now=None):
    """Write the group: pl['n'] pending signals with the same side, stop and target, sharing the normal risk of one trade.
    s = the setup dict from brain.evaluate (side, entry, sl, tp, strategy, score). Returns the list of new signal ids (the first is the group id)."""
    now = int(now or time.time()); n = int(pl['n']); uid = uid or ''
    base = links.risk(uid) if uid else st.fget('risk_pct'); rp = multi.share(base, n)
    sql = 'INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid,grp,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'
    first = st.x(sql, (sym, s['side'], s['entry'], s['sl'], s['tp'], rp, s['strategy'], s['score'], 'pending', now, uid or None, None, reason))
    st.x('UPDATE signals SET grp=? WHERE id=?', (first, first))
    ids = [first]
    for _ in range(n - 1):
        ids.append(st.x(sql, (sym, s['side'], s['entry'], s['sl'], s['tp'], rp, s['strategy'], s['score'], 'pending', now, uid or None, first, reason)))
    st.put('bg:%d' % first, json.dumps({'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now}))
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
            'each': m.get('each'), 'gb': m.get('gb', 0), 'ids': ','.join(str(i) for i in ids)}


# ---------------- what the app shows ----------------
def explain(uid='', now=None, admin=False):
    """-> {state, why}. state: off | running | waiting | ready."""
    from . import botstate
    now = now or time.time(); p = get(uid)
    if not enabled(): return {'state': 'off', 'why': 'Burst mode is switched off by the owner.'}
    if not p['on']: return {'state': 'off', 'why': 'Burst mode is off.'}
    if active(uid): return {'state': 'running', 'why': 'A burst is running. It closes at the profit target, or when the profit starts to go away.'}
    ok, why = due(uid, now)
    if ok: return {'state': 'ready', 'why': 'Quiet long enough. It looks for a quick chance on the next candle check.'}
    if why.startswith('quiet for'): return {'state': 'waiting', 'why': 'Watching. The bot has been %s without a trade; after that it looks for a quick small-profit chance.' % why[len('quiet for '):]}
    return {'state': 'waiting', 'why': botstate._words(why)}


def view(uid='', now=None):
    return {'settings': get(uid), 'enabled': enabled(), 'ceiling': ceiling(), 'big_score': big_score(), 'now': explain(uid, now)}
