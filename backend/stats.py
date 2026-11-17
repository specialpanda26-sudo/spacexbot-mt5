"""Per-strategy results from closed trades (claude-trading-skills: signal-postmortem / trade-performance-coach idea).
A trade fired by 'a+b' counts for both, so attribution is approximate."""
from . import store as st

def by_strategy(uid=''):
    out = {}
    for r in st.q("SELECT strategy,pnl FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=?", (uid,)):
        for name in (r['strategy'] or '').split('+'):
            o = out.setdefault(name, {'n': 0, 'wins': 0, 'pnl': 0.0}); o['n'] += 1; o['wins'] += r['pnl'] > 0; o['pnl'] += r['pnl']
    for o in out.values(): o['win_rate'] = round(100 * o['wins'] / o['n'], 1); o['avg'] = round(o['pnl'] / o['n'], 2); o['pnl'] = round(o['pnl'], 2)
    return out

def summary(uid=''):
    rows = st.q("SELECT pnl FROM signals WHERE status='closed' AND pnl IS NOT NULL AND COALESCE(uid,'')=? ORDER BY closed", (uid,))
    n = len(rows); w = [r['pnl'] for r in rows if r['pnl'] > 0]; l = [r['pnl'] for r in rows if r['pnl'] <= 0]
    eq = peak = dd = 0.0
    for r in rows: eq += r['pnl']; peak = max(peak, eq); dd = max(dd, peak - eq)
    return {'trades': n, 'win_rate': round(100 * len(w) / n, 1) if n else 0, 'net': round(eq, 2),
            'profit_factor': round(sum(w) / -sum(l), 2) if l and sum(l) < 0 else None, 'max_drawdown': round(dd, 2)}

def losers(min_trades=20, uid=''):
    """Strategies with enough trades and a negative average; used only if auto_disable is on."""
    return {k for k, v in by_strategy(uid).items() if v['n'] >= min_trades and v['avg'] < 0}
