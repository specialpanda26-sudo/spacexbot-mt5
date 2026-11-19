"""Per-strategy results from closed trades (claude-trading-skills: signal-postmortem / trade-performance-coach idea).
A trade fired by 'a+b' counts for both, so attribution is approximate."""
import json
from . import store as st, regime as rgm

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

MIN_FLOOR = 5          # never switch a strategy off on fewer trades than this, whatever the setting says (a couple of losses is noise)

def by_regime(uid=''):
    """{strategy: {regime: {n, wins, pnl, avg, win_rate}}} from this scope's closed trades that saved their regime (R1). Older trades have none and are left out.
    Entries opened together for one setup (same grp) count as ONE result. A trade fired by 'a+b' counts for both, as in by_strategy."""
    setups = {}
    for r in st.q("SELECT id,grp,strategy,pnl,reason FROM signals WHERE status='closed' AND pnl IS NOT NULL AND reason IS NOT NULL AND COALESCE(uid,'')=?", (uid,)):
        try: rg = json.loads(r['reason']).get('regime')
        except (TypeError, ValueError, AttributeError): continue
        if rg not in rgm.LABELS: continue
        o = setups.setdefault(r['grp'] or -r['id'], {'strategy': r['strategy'], 'regime': rg, 'pnl': 0.0}); o['pnl'] += r['pnl']
    out = {}
    for o in setups.values():
        for name in (o['strategy'] or '').split('+'):
            if not name: continue
            c = out.setdefault(name, {}).setdefault(o['regime'], {'n': 0, 'wins': 0, 'pnl': 0.0}); c['n'] += 1; c['wins'] += o['pnl'] > 0; c['pnl'] += o['pnl']
    for cells in out.values():
        for c in cells.values(): c['win_rate'] = round(100 * c['wins'] / c['n'], 1); c['avg'] = round(c['pnl'] / c['n'], 2); c['pnl'] = round(c['pnl'], 2)
    return out

def regime_off(uid='', min_trades=None):
    """{strategy: {regimes}}: the regimes where this strategy has enough trades (at least MIN_FLOOR) and a negative average. Used only when regime_switch is on."""
    try: mt = int(min_trades if min_trades is not None else st.fget('regime_min_trades'))
    except (TypeError, ValueError): mt = 10
    mt = max(MIN_FLOOR, mt); out = {}
    for name, cells in by_regime(uid).items():
        bad = {rg for rg, c in cells.items() if c['n'] >= mt and c['avg'] < 0}
        if bad: out[name] = bad
    return out
