"""Pre-trade gates (ideas from claude-trading-skills: drawdown-circuit-breaker, pre-trade-discipline-gate,
exposure-coach). global_gate() runs before analysis, symbol_gate() after a side is known."""
import time, datetime as dt
from . import store as st, news, links, limits, brokers as bk, roadmap, userlim

def _week_start(now):
    d = dt.datetime.utcfromtimestamp(now); m = d - dt.timedelta(days=d.weekday())
    return int(dt.datetime(m.year, m.month, m.day).replace(tzinfo=dt.timezone.utc).timestamp())

def _pnl_since(ts, uid=''): return st.q("SELECT COALESCE(SUM(pnl),0) p FROM signals WHERE closed>=? AND COALESCE(uid,'')=?", (ts, uid), True)['p']

def open_count(uid='', a=None):
    """R4: positions this person holds right now, MT5 and Deriv together, plus signals about to open (pending / sent), so a burst of signals cannot all slip past the limit.
    Assumption: the account snapshot's open count is the larger of what the EA reports and what we recorded (an MT5 position opened by hand counts when the EA reports it)."""
    a = a if a is not None else st.acct(uid)
    r = {x['status']: x['n'] for x in st.q("SELECT status, COUNT(*) n FROM signals WHERE COALESCE(uid,'')=? AND status IN('open','pending','sent') GROUP BY status", (uid,))}
    try: ea = int(float(a.get('open') or 0))
    except (TypeError, ValueError): ea = 0
    return max(ea, r.get('open', 0)) + r.get('pending', 0) + r.get('sent', 0)

def bot_on(uid=''):
    """R7: is the bot switched on for this person? The MT5 link switch counts, and so does the Deriv switch, so a person with only a Deriv token (no MT5 key) can trade."""
    return bool(links.bot_on(uid)) or (bool(uid) and bk.bot_flag(uid, 'Deriv') is True)

def real_ok(uid, a):
    """R7: may this person's snapshot be a real-money account? A Deriv snapshot (src 'deriv') needs Real mode on the Deriv card; an MT5 snapshot needs Real mode on the MT5 link. One never unlocks the other."""
    if not a.get('allow_live'): return False
    return (bk.mode(uid, 'Deriv') if a.get('src') == 'deriv' else links.mode(uid)) == 'real'

CRYPTO = ('BTCUSD',)          # markets that never close (prefix match, so BTCUSDm, BTCUSD.a, BTCUSDT count too)

def weekend_shut(now=None):
    """Saturday, Sunday, or Friday from 20:00 UTC: gold and forex are closed or too risky."""
    d = dt.datetime.utcfromtimestamp(now or time.time()); return d.weekday() >= 5 or (d.weekday() == 4 and d.hour >= 20)

def is_crypto(sym): return str(sym or '').strip().upper().startswith(CRYPTO)

def crypto_open():
    """Weekend exemption: on unless the owner sets crypto_weekend to 0, and only while a crypto market is in the Symbols setting."""
    return st.get('crypto_weekend') != '0' and any(is_crypto(x) for x in (st.get('symbols') or '').split(','))

def weekend_skip(sym, now=None):
    """True = do not trade this market now because of the weekend rule (every market except crypto when the exemption is on)."""
    return weekend_shut(now) and not (st.get('crypto_weekend') != '0' and is_crypto(sym))

def weekday_skip(sym, now=None):
    """B1: 'weekends only' Bitcoin mode: a crypto market rests on weekdays (gold and forex trade then). Off when btc_mode is not 'weekend' or crypto_weekend = 0."""
    return is_crypto(sym) and st.get('crypto_weekend') != '0' and st.get('btc_mode') == 'weekend' and not weekend_shut(now)

def streak_state(uid='', now=None):
    """None, or the losing-streak pause that is on now: {'k', 'until', 'pnls' (the k last setup results), 'since' (when the last loss closed)}.
    Only setups closed AFTER the admin's approval (kv 'streakok:<uid>', see streakreq.py) count, so an approval starts the count again."""
    now = now or time.time(); k = limits.streak(uid)
    if k <= 0: return None
    try: ok_at = int(float(st.get('streakok:' + uid) or 0))
    except (TypeError, ValueError): ok_at = 0
    last = _setups(st.q("SELECT pnl,closed,grp FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? AND closed>? ORDER BY closed DESC LIMIT ?", (uid, ok_at, k * 12)))[:k]
    until = last[0]['closed'] + userlim.val(uid, 'streak_rest') * 3600 if last else 0
    if len(last) == k and all(x['pnl'] < 0 for x in last) and now < until: return {'k': k, 'until': until, 'pnls': [x['pnl'] for x in last], 'since': last[0]['closed']}
    return None

def day_since(uid='', now=None):
    """RS1: where today's loss count starts: the day start, or later when the person restarted it."""
    now = now or time.time(); base = int(now - now % 86400)
    try: t = int(float(st.get('dayok:' + (uid or '')) or 0))
    except (TypeError, ValueError): t = 0
    return max(base, t)

def global_gate(now=None, uid='', burst=False):
    now = now or time.time(); a = st.acct(uid); d = dt.datetime.utcfromtimestamp(now)
    if not bot_on(uid): return False, 'bot off'
    if now - a.get('seen', 0) > 120: return False, 'EA offline'
    if uid:      # a subscriber's EA: anything that is not a confirmed demo account needs Real mode ON and live trading allowed in the EA
        if a.get('demo') is not True and not real_ok(uid, a): return False, 'real account needs Real mode and live trading allowed'
        if a.get('demo') is not True and not roadmap.real_allowed(uid): return False, 'learning path not finished'          # C3: lessons + practice trades first
    elif a.get('demo') is False and not a.get('allow_live'): return False, 'live account not allowed in EA'
    if weekend_shut(now) and not crypto_open(): return False, 'weekend/Friday-night risk'          # a BTC market in Symbols keeps the bot looking; other markets are skipped per market (weekend_skip)
    if not burst and open_count(uid, a) >= limits.max_open(uid): return False, 'max open positions'          # burst mode has its own ceiling (burst.py)
    since = int(now - now % 86400)
    mt = limits.trades(uid)      # 0 = no daily trade limit (the stop loss and the loss limits protect the account)
    if mt > 0:
        n = st.q("SELECT COUNT(DISTINCT COALESCE(grp,id)) n FROM signals WHERE created>=? AND status IN('pending','sent','open','closed') AND COALESCE(uid,'')=?", (since, uid), True)['n']
        if n >= mt: return False, 'max trades today'
    bal = float(a.get('balance') or 0)
    dl, wl = userlim.val(uid, 'daily_loss'), userlim.val(uid, 'weekly_loss')          # RS5: the person's own numbers (0 = off)
    if bal and dl > 0 and _pnl_since(day_since(uid, now), uid) <= -bal * dl / 100: return False, 'daily loss limit hit'
    if bal and wl > 0 and _pnl_since(_week_start(now), uid) <= -bal * wl / 100: return False, 'weekly loss limit hit'
    s = streak_state(uid, now)          # streakreq.py: an admin approval restarts the count
    if s: return False, f"{s['k']} losses in a row: cooling down"
    return True, 'ok'

def _legs(sym, side):
    s = sym.upper(); sg = 1 if side == 'buy' else -1
    return {s[:3]: sg, s[3:6]: -sg} if len(s) >= 6 else {s: sg}

def _setups(rows):
    """R8: entries opened together for one setup (same grp) count as ONE result; their profit and loss are added up."""
    out, at = [], {}
    for x in rows:
        g = x['grp']
        if g and g in at: at[g]['pnl'] += x['pnl']; continue
        o = {'pnl': x['pnl'], 'closed': x['closed']}; out.append(o)
        if g: at[g] = o
    return out

def exposure(uid=''):
    """Net directional exposure per currency over open/pending/sent signals."""
    net, seen = {}, set()
    for r in st.q("SELECT id,symbol,side,grp FROM signals WHERE status IN('pending','sent','open') AND COALESCE(uid,'')=?", (uid,)):
        k = r['grp'] or -r['id']          # R8: every entry of one setup counts once
        if k in seen: continue
        seen.add(k)
        for c, v in _legs(r['symbol'], r['side']).items(): net[c] = net.get(c, 0) + v
    return net

def symbol_gate(sym, side, now=None, uid='', cool=True):
    now = now or time.time()
    nb, na = userlim.news(uid)          # RS5: the person's own news lock (0 = off)
    if nb > 0 or na > 0:
        b, why = news.blocked(sym, now, nb, na)
        if b: return False, why
    last = st.q("SELECT created FROM signals WHERE symbol=? AND COALESCE(uid,'')=? ORDER BY id DESC LIMIT 1", (sym, uid), True)
    if cool and last and now - last['created'] < userlim.val(uid, 'cooldown') * 60: return False, 'symbol cooldown'
    net = exposure(uid); cap = int(userlim.val(uid, 'same_dir'))
    if cap <= 0: cap = 1000          # RS5: 0 = off (the person's own choice)
    for c, v in _legs(sym, side).items():
        if abs(net.get(c, 0) + v) > cap: return False, f'{c} exposure already at limit (correlated trades)'
    return True, 'ok'
