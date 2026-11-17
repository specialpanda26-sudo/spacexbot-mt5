"""The brain's memory: what every user's bot did, kept in the database (Supabase).
Only strategy, symbol, side and result are kept. Never keys, emails or broker login numbers."""
import time, json
from . import store as st

def log(uid, kind, strategy='', symbol='', side='', pnl=None, data=None):
    try: st.x('INSERT INTO brain_events(uid,kind,strategy,symbol,side,pnl,data,ts) VALUES(?,?,?,?,?,?,?,?)',
              (uid or '', kind, strategy or '', symbol or '', side or '', pnl, json.dumps(data or {})[:1000], int(time.time())))
    except Exception as e: print('brain log failed', str(e)[:100])

def by_strategy():
    out = {}
    for r in st.q("SELECT strategy,pnl FROM brain_events WHERE kind='closed' AND pnl IS NOT NULL"):
        for n in (r['strategy'] or '').split('+'):
            o = out.setdefault(n, {'n': 0, 'wins': 0, 'pnl': 0.0}); o['n'] += 1; o['wins'] += r['pnl'] > 0; o['pnl'] += r['pnl']
    for o in out.values(): o['win_rate'] = round(100 * o['wins'] / o['n'], 1); o['pnl'] = round(o['pnl'], 2)
    return out

def summary():
    r = st.q('SELECT COUNT(DISTINCT uid) n, COUNT(*) e FROM brain_events', one=True) or {}
    return {'users': r.get('n') or 0, 'events': r.get('e') or 0}
