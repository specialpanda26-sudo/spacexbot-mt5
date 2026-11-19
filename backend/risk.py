"""Pre-trade gates (ideas from claude-trading-skills: drawdown-circuit-breaker, pre-trade-discipline-gate,
exposure-coach). global_gate() runs before analysis, symbol_gate() after a side is known."""
import time, datetime as dt
from . import store as st, news, links

def _week_start(now):
    d = dt.datetime.utcfromtimestamp(now); m = d - dt.timedelta(days=d.weekday())
    return int(dt.datetime(m.year, m.month, m.day).replace(tzinfo=dt.timezone.utc).timestamp())

def _pnl_since(ts, uid=''): return st.q("SELECT COALESCE(SUM(pnl),0) p FROM signals WHERE closed>=? AND COALESCE(uid,'')=?", (ts, uid), True)['p']

def global_gate(now=None, uid=''):
    now = now or time.time(); a = st.acct(uid); d = dt.datetime.utcfromtimestamp(now)
    if not links.bot_on(uid): return False, 'bot off'
    if now - a.get('seen', 0) > 120: return False, 'EA offline'
    if uid:      # a subscriber's EA: anything that is not a confirmed demo account needs Real mode ON and live trading allowed in the EA
        if a.get('demo') is not True and not (links.mode(uid) == 'real' and a.get('allow_live')): return False, 'real account needs Real mode and live trading allowed'
    elif a.get('demo') is False and not a.get('allow_live'): return False, 'live account not allowed in EA'
    if d.weekday() >= 5 or (d.weekday() == 4 and d.hour >= 20): return False, 'weekend/Friday-night risk'
    if int(a.get('open', 0)) >= int(st.fget('max_open')): return False, 'max open positions'
    since = int(now - now % 86400)
    mt = int(st.fget('max_trades_day') or 0)      # 0 = no daily trade limit (the stop loss and the loss limits protect the account)
    if mt > 0:
        n = st.q("SELECT COUNT(*) n FROM signals WHERE created>=? AND status IN('pending','sent','open','closed') AND COALESCE(uid,'')=?", (since, uid), True)['n']
        if n >= mt: return False, 'max trades today'
    bal = float(a.get('balance') or 0)
    if bal and _pnl_since(since, uid) <= -bal * st.fget('max_daily_loss_pct') / 100: return False, 'daily loss limit hit'
    if bal and _pnl_since(_week_start(now), uid) <= -bal * st.fget('max_weekly_loss_pct') / 100: return False, 'weekly loss limit hit'
    k = int(st.fget('max_losing_streak'))
    last = st.q("SELECT pnl,closed FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? ORDER BY closed DESC LIMIT ?", (uid, k))
    if k > 0 and len(last) == k and all(x['pnl'] < 0 for x in last) and now - last[0]['closed'] < st.fget('streak_cooldown_h') * 3600:
        return False, f'{k} losses in a row: cooling down'
    return True, 'ok'

def _legs(sym, side):
    s = sym.upper(); sg = 1 if side == 'buy' else -1
    return {s[:3]: sg, s[3:6]: -sg} if len(s) >= 6 else {s: sg}

def exposure(uid=''):
    """Net directional exposure per currency over open/pending/sent signals."""
    net = {}
    for r in st.q("SELECT symbol,side FROM signals WHERE status IN('pending','sent','open') AND COALESCE(uid,'')=?", (uid,)):
        for c, v in _legs(r['symbol'], r['side']).items(): net[c] = net.get(c, 0) + v
    return net

def symbol_gate(sym, side, now=None, uid=''):
    now = now or time.time()
    if st.get('news_lock') == '1':
        b, why = news.blocked(sym, now, st.fget('news_before_min'), st.fget('news_after_min'))
        if b: return False, why
    last = st.q("SELECT created FROM signals WHERE symbol=? AND COALESCE(uid,'')=? ORDER BY id DESC LIMIT 1", (sym, uid), True)
    if last and now - last['created'] < st.fget('cooldown_min') * 60: return False, 'symbol cooldown'
    net = exposure(uid); cap = int(st.fget('max_ccy_exposure'))
    for c, v in _legs(sym, side).items():
        if abs(net.get(c, 0) + v) > cap: return False, f'{c} exposure already at limit (correlated trades)'
    return True, 'ok'
