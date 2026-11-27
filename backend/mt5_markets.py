"""PL6: which markets one account's MT5 bot may TRADE now, and a safe way to switch.
Found: the server's 'symbols' setting does not decide what the owner's own EA trades (the EA trades the markets in its own Symbols input and the server scans every
market the EA sends). So this is a separate, per-account choice that the scanner obeys:
 - nothing chosen (the default) = every market the EA sends, exactly as before;
 - a list = only those markets get NEW signals and bursts. Open trades are never touched.
Switching refuses a market the EA is not sending (the bot would silently trade nothing), and, for a managed plan, a market whose broker minimum lot is above the plan lot
(every trade there would be refused). It only changes the MT5 bot: Deriv and Binance follow the owner's 'symbols' setting.
Stored in kv 'mk:<uid>' (uid '' = the owner's own EA). Nothing here claims a market makes money."""
import json, re
from . import store as st

OK = re.compile(r'^[A-Z0-9._]{3,12}$')
MAX = 12
MODES = ('only', 'add', 'remove', 'all')


def get(uid=''):
    """The chosen markets, upper case, in order. [] = no choice made = every market the EA sends."""
    try: j = json.loads(st.get('mk:' + (uid or '')) or '[]')
    except (TypeError, ValueError): j = []
    return [x for x in j if isinstance(x, str) and OK.match(x)][:MAX] if isinstance(j, list) else []


def allowed(uid, sym):
    """The scanner asks this for every market the EA sends."""
    c = get(uid)
    return not c or str(sym or '').strip().upper() in c


def _put(uid, lst): st.put('mk:' + (uid or ''), json.dumps(lst)); return lst


def _reported(uid):
    """{market: {vol_min, tick_value, tick_size}} the EA told us about on its last sync ({} = an older EA, or nothing yet)."""
    from . import presets
    try: return presets.clean_sym((st.acct(uid) or {}).get('sym'))
    except Exception: return {}


def _plan_lot(uid):
    from . import burst
    return burst.plan_lot(burst.get(uid)['plan_usd']) if burst.plan_active(uid) else 0.0


def check(uid=''):
    """-> {all, chosen, ea_known, markets:[{sym, sent_by_ea, chosen, vol_min, plan_lot, lot_ok, note}]}. Words only; nothing here changes a setting."""
    rep = _reported(uid); chosen = get(uid); plan = _plan_lot(uid); rows = []
    for n in list(dict.fromkeys(list(rep) + chosen)):
        f = rep.get(n); r = {'sym': n, 'sent_by_ea': f is not None, 'chosen': (not chosen) or n in chosen, 'vol_min': f['vol_min'] if f else None,
                             'plan_lot': plan or None, 'lot_ok': None, 'note': ''}
        if rep and f is None: r['note'] = "The EA is not sending %s. Add it to the EA's Symbols input (and check the broker's name for it)." % n
        elif f and plan:
            r['lot_ok'] = plan + 1e-9 >= f['vol_min']
            if not r['lot_ok']: r['note'] = 'Broker minimum lot %g is above your plan lot %g, so trades here are refused.' % (f['vol_min'], plan)
        rows.append(r)
    return {'all': not chosen, 'chosen': chosen, 'ea_known': bool(rep), 'markets': rows}


def view(uid=''): return check(uid)


def switch(uid, to='', mode='only'):
    """mode: only = trade just this market, add = also this one, remove = stop this one, all = no choice (every market the EA sends). Raises ValueError with plain words."""
    if mode not in MODES: raise ValueError('mode must be only, add, remove or all')
    if mode == 'all': return _put(uid, [])
    if not isinstance(to, str) or not OK.match(to.strip().upper()): raise ValueError('Market name must be 3 to 12 letters or digits, like EURUSD')
    sym = to.strip().upper(); cur = get(uid); rep = _reported(uid)
    if mode == 'remove':
        base = cur or list(rep)
        new = [x for x in base if x != sym]
        if not new: raise ValueError('That would leave no market to trade. Pick another market first, or choose "all".')
        return _put(uid, new)
    if rep and sym not in rep: raise ValueError("The EA is not sending %s, so the bot would trade nothing there. Add it to the EA's Symbols input first." % sym)
    plan = _plan_lot(uid)
    if plan and sym in rep and plan + 1e-9 < rep[sym]['vol_min']:
        raise ValueError('Broker minimum lot for %s is %g, above your plan lot %g, so every trade there would be refused.' % (sym, rep[sym]['vol_min'], plan))
    if mode == 'add':
        if not cur: return cur          # nothing chosen = already every market
        if sym not in cur and len(cur) >= MAX: raise ValueError('At most %d markets' % MAX)
        return _put(uid, cur + [sym] if sym not in cur else cur)
    return _put(uid, [sym])
