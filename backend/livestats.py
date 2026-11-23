"""Section 3: live numbers for the app (Home card, Bot tab strip, the top chip). GET /api/live returns, for the signed-in person only:
state ('none' no broker balance read yet, 'live' at least one account answered recently, 'stale' balances exist but nothing answered recently),
mode ('real' if any connected account is real, else 'demo'), balance, equity, floating (equity - balance), today (profit of trades closed since the
server's day start), today_pct, open (count), trades (up to 8 open trades: symbol, side, price, strategy_name), sources (one row per account).
Where the numbers come from (nothing is invented, nothing is sample data):
- Deriv: the balance the Deriv loop last read (brokers bal:<uid>:Deriv). Deriv has no floating figure, so equity = balance.
- MT5: the account the EA last reported (the owner's EA for admins, the personal key for everyone else): balance, equity, open.
- today / open trades: the signals table, scope = the person's own uid (+ the owner's EA scope '' for admins).
Amounts are shown with $ like the live notification: the EA does not report the account currency (assumption).
ASSUMPTIONS (tunable): FRESH seconds a Deriv balance counts as live; MT5_FRESH is the same limit the rest of the app uses for 'EA online'."""
import time
from . import store as st, links, brokers as bk, strategy_info as si, pnlreset as pr, tradeon, burst_live, openlive

FRESH = 180
MT5_FRESH = 120
MAX_TRADES = 8


def _f(v):
    try: x = float(v)
    except (TypeError, ValueError): return None
    return x if x == x and abs(x) != float('inf') else None


def _mode(demo, saved):
    return 'demo' if demo is True else 'real' if demo is False else ('real' if saved == 'real' else 'demo')


def _dfloat(uid, admin, now):
    """BX1: live profit of the person's open Deriv trades: every open trade (openlive) when fresh, else the old burst-group figure (BT6)."""
    v = openlive.floating(uid, now)
    return v if v is not None else burst_live.floating(('' if admin else uid, uid), now)


def _results(sc, bq, since):
    """BX1: today's finished setups -> (wins, losses, last 3 as {symbol, pnl}). Entries opened together (same grp) count as ONE result, like the loss streak."""
    rows = st.q("SELECT id,grp,symbol,pnl FROM signals WHERE closed>=? AND pnl IS NOT NULL AND COALESCE(uid,'') IN (?,?)" + bq + " ORDER BY closed DESC, id DESC LIMIT 500", (since, sc[0], sc[1])) or []
    seen, out = {}, []
    for r in rows:
        p = _f(r['pnl'])
        if p is None: continue
        k = ('g', r['grp']) if r.get('grp') else ('i', r['id'])
        if k in seen: seen[k]['pnl'] = round(seen[k]['pnl'] + p, 2); continue
        seen[k] = {'symbol': r['symbol'], 'pnl': round(p, 2)}; out.append(seen[k])
    return sum(1 for o in out if o['pnl'] > 0), sum(1 for o in out if o['pnl'] < 0), out[:3]


def sources(uid, admin, now):
    out = []
    for b in bk.view(uid):
        if b.get('name') not in ('Deriv', 'Binance'): continue          # LV4: Binance (testnet balance) is a source too
        bal = _f(b.get('balance'))
        if bal is None: continue
        t = _f(b.get('bal_t')) or 0
        out.append({'id': b['name'], 'name': b['name'], 'mode': _mode(b.get('acct_demo'), b.get('mode')), 'balance': round(bal, 2), 'equity': round(bal + (_dfloat(uid, admin, now) if b['name'] == 'Deriv' else 0.0), 2), 'open': None,          # BT6, BX1
                    'online': now - t < FRESH, 'age': int(max(0, now - t)) if t else None})
    lk = None if admin else links.get(uid)
    a = st.acct('') if admin else (st.acct(uid) if lk else {})
    bal = _f(a.get('balance'))
    if bal is not None:
        eq = _f(a.get('equity')); eq = bal if eq is None else eq
        seen = _f(a.get('seen')) or 0; n = a.get('open')
        out.append({'id': 'MT5', 'name': 'MT5', 'mode': _mode(a.get('demo'), (lk or {}).get('mode')), 'balance': round(bal, 2), 'equity': round(eq, 2),
                    'open': int(n) if _f(n) is not None else None, 'online': now - seen < MT5_FRESH, 'age': int(max(0, now - seen)) if seen else None})
    return out


def _scope_sql(ch):
    """LV4: which signal rows belong to the chosen platform. MT5 rows are marked 'MT5' (older ones are empty); Deriv and Binance rows carry their own name."""
    if not ch: return ''
    return " AND (COALESCE(broker,'')='MT5' OR COALESCE(broker,'')='')" if ch == 'MT5' else " AND COALESCE(broker,'')='%s'" % ch


def snapshot(uid, admin=False, now=None):
    now = now or time.time(); src = sources(uid, admin, now); sc = ('' if admin else uid, uid)
    ch = tradeon.get(uid)          # LV4: the platform the bot is set to trade on; nothing chosen = the old behaviour (every connected account)
    if ch: src = [s for s in src if s['id'] == ch]
    bq = _scope_sql(ch)
    t = st.q("SELECT COALESCE(SUM(pnl),0) p, COUNT(*) n FROM signals WHERE closed>=? AND pnl IS NOT NULL AND COALESCE(uid,'') IN (?,?)" + bq, (pr.since(uid), sc[0], sc[1]), True) or {}
    today = round(_f(t.get('p')) or 0.0, 2)
    n_sig = (st.q("SELECT COUNT(*) n FROM signals WHERE status='open' AND COALESCE(uid,'') IN (?,?)" + bq, sc, True) or {}).get('n') or 0
    rows = st.q("SELECT id,symbol,side,fill,entry,strategy FROM signals WHERE status='open' AND COALESCE(uid,'') IN (?,?)" + bq + " ORDER BY id DESC LIMIT %d" % MAX_TRADES, sc) or []
    bal = round(sum(s['balance'] for s in src), 2); eq = round(sum(s['equity'] for s in src), 2)
    state = 'none' if not src else 'live' if any(s['online'] for s in src) else 'stale'
    base = bal - today
    ol = openlive.get(uid, now) or {}; tw, tl, recent = _results(sc, bq, pr.since(uid))          # BX1
    return {'platform': ch, 'state': state, 'mode': 'real' if any(s['mode'] == 'real' for s in src) else 'demo', 'balance': bal, 'equity': eq, 'floating': round(eq - bal, 2),
            'today': today, 'today_w': tw, 'today_l': tl, 'recent': recent, 'today_reset': pr.get(uid) or None, 'today_pct': round(today / base * 100, 2) if base > 0 else 0.0, 'today_n': int(t.get('n') or 0),
            'open': max(int(n_sig), sum(s['open'] or 0 for s in src)),
            'trades': [{'id': r['id'], 'symbol': r['symbol'], 'side': str(r['side']).lower(), 'price': r.get('fill') or r.get('entry'), 'strategy_name': si.label(r['strategy']), 'pnl': ol.get(r['id'])} for r in rows],
            'sources': src, 'ts': int(now)}
