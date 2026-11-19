"""R5: the bot may add one more market by itself, from the OWNER's pool, when the markets it already trades are steady and profitable.
Rules (all measured from the bot's own closed trades; entries opened together for one setup count as ONE result):
 1. Only markets in the owner's pool (setting symbols_pool, in priority order) are ever added. The switch auto_markets is off by default.
 2. Steady and profitable = at least 20 closed setups in the last 30 days on the markets now traded, net profit above zero, and no run of losses as long as the
    loss-streak stop (default 3) in the last 7 days.
 3. One market at a time, then a 7 day wait. At most auto_markets_max markets added in total (default 2).
 4. It only edits the 'symbols' setting. Max positions, the owner's ceiling, the currency exposure limit and every gate still apply to the new market.
 5. A market added by the bot is dropped again if its first 10 closed setups lose money; it is not added again for 30 days.
 6. Switching auto_markets off removes every market the bot added (the owner's own list comes back).
Nothing here claims it makes more money: a market being steady in the past does not mean the next trade wins. Only tools/backtest.py on real candles can say whether it helps.
MT5 note: the EA only sends candles for the markets in its own Symbols input, so a market the bot adds trades on MT5 only if that input already lists it. Deriv and the server feed follow the 'symbols' setting directly."""
import json, re, time, threading
from . import store as st, limits

DAY = 86400
MIN_TRADES, WINDOW, WAIT, STREAK_LOOK, PROBATION, REDO = 20, 30 * DAY, 7 * DAY, 7 * DAY, 10, 30 * DAY
OK = re.compile(r'^[A-Z0-9._]{3,12}$')

def _list(k): return [x.strip().upper() for x in (st.get(k) or '').split(',') if x.strip()]
def _json(k, d):
    try: v = json.loads(st.get(k) or ''); return v if isinstance(v, type(d)) else d
    except (TypeError, ValueError): return d
def on(): return st.get('auto_markets') == '1'
def pool(): return [x for x in _list('symbols_pool') if OK.match(x)]
def cap():
    try: return max(0, min(10, int(float(st.get('auto_markets_max')))))
    except (TypeError, ValueError): return 2
def added(): return [a for a in _json('am:added', []) if isinstance(a, dict) and a.get('s')]

def setups(since, syms=None):
    """Closed results since a time, oldest first. Entries of one setup (same grp) are added into one result."""
    out, at = [], {}
    for r in st.q("SELECT symbol,pnl,closed,grp FROM signals WHERE status='closed' AND pnl IS NOT NULL AND closed>=? ORDER BY closed", (int(since),)):
        if syms is not None and (r['symbol'] or '').upper() not in syms: continue
        g = r['grp']
        if g and g in at: at[g]['pnl'] += r['pnl']; continue
        o = {'pnl': r['pnl'], 'closed': r['closed']}; out.append(o)
        if g: at[g] = o
    return out

def _note(msg):
    log = _json('am:log', []); log.append('%s %s' % (time.strftime('%Y-%m-%d %H:%M', time.gmtime()), msg)); st.put('am:log', json.dumps(log[-20:])); print('[markets]', msg)

def _set_symbols(lst): st.put('symbols', ','.join(lst))

def check(now=None):
    """-> (ok, why, candidate). Says in plain words what is missing."""
    now = now or time.time(); active = _list('symbols')
    if len(added()) >= cap(): return False, 'already added the most allowed (%d)' % cap(), None
    last = int(float(st.get('am:last') or 0))
    if now - last < WAIT: return False, 'waiting %d more days after the last market was added' % (-(-(WAIT - (now - last)) // DAY)), None
    rows = setups(now - WINDOW, set(active))
    if len(rows) < MIN_TRADES: return False, 'only %d of %d closed trades in the last 30 days' % (len(rows), MIN_TRADES), None
    net = sum(r['pnl'] for r in rows)
    if net <= 0: return False, 'the markets traded now are not in profit over 30 days', None
    k = limits.streak('') or 3; run = 0
    for r in setups(now - STREAK_LOOK, set(active)):
        run = run + 1 if r['pnl'] < 0 else 0
        if run >= k: return False, 'a run of %d losses in the last 7 days' % k, None
    dropped = _json('am:dropped', {})
    for s in pool():
        if s in active: continue
        if now - float(dropped.get(s, 0)) < REDO: continue
        return True, 'ok', s
    return False, 'the pool has no new market to add', None

def tick(now=None):
    """One pass: drop what lost, add what the rules allow. Returns a short text. Never raises."""
    now = now or time.time()
    try:
        active, mine = _list('symbols'), added()
        if not on():
            if mine:
                _set_symbols([s for s in active if s not in {a['s'] for a in mine}] or active); st.put('am:added', '[]'); _note('switched off: removed ' + ', '.join(a['s'] for a in mine))
            return 'off'
        keep, dropped = [], _json('am:dropped', {})
        for a in mine:
            if a['s'] not in active: continue               # the owner took it out by hand: forget it
            rows = setups(a['at'], {a['s']})
            if len(rows) >= PROBATION and sum(r['pnl'] for r in rows) < 0:
                active = [s for s in active if s != a['s']]; dropped[a['s']] = int(now); _note('dropped %s: lost over its first %d trades' % (a['s'], len(rows)))
            else: keep.append(a)
        if keep != mine or active != _list('symbols'):
            _set_symbols(active); st.put('am:added', json.dumps(keep)); st.put('am:dropped', json.dumps(dropped))
        ok, why, cand = check(now)
        if not ok: return why
        _set_symbols(_list('symbols') + [cand]); keep.append({'s': cand, 'at': int(now)}); st.put('am:added', json.dumps(keep)); st.put('am:last', int(now))
        _note('added %s' % cand); return 'added ' + cand
    except Exception as e:
        print('[markets] tick failed', repr(e)[:100]); return 'error'

def status(now=None):
    now = now or time.time(); ok, why, cand = check(now)
    return {'on': on(), 'pool': pool(), 'active': _list('symbols'), 'added': added(), 'max_added': cap(), 'can_add_now': bool(ok), 'next': cand, 'why_not': '' if ok else why, 'log': _json('am:log', [])[-10:]}

_started = False
def start():
    global _started
    if _started: return
    _started = True
    def loop():
        while True:
            time.sleep(600); tick()
    threading.Thread(target=loop, daemon=True).start()
