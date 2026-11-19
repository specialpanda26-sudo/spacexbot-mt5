"""Section 4: what the bot is really doing, in plain words. Nothing here is made up: it reads the real switch, the EA's last
heartbeat, the real risk gates and the note the scanner leaves after each candle ('scan:<uid>:<symbol>')."""
import json, time
from . import store as st, links, risk, brokers as bk

PLAIN = {
    'bot off': 'The bot is stopped. Tap Start bot.',
    'EA offline': 'MT5 is not talking to the server. Open MT5 on your computer and check the SpaceX bridge is running.',
    'real account needs Real mode and live trading allowed': 'This is a real account. Real mode and live trading must both be switched on first.',
    'live account not allowed in EA': 'This is a live account and live trading is not allowed in the MT5 bridge settings.',
    'weekend/Friday-night risk': 'Markets are closed or too risky now (weekend or Friday night). It waits.',
    'max open positions': 'It already has the most open trades it is allowed. It waits for one to close.',
    'max trades today': 'It reached the most trades allowed for today. It starts again tomorrow.',
    'daily loss limit hit': 'The daily loss limit was reached. It stops for the rest of the day to protect the account.',
    'weekly loss limit hit': 'The weekly loss limit was reached. It stops until next week to protect the account.',
    'symbol cooldown': 'It just traded this market. It waits a while before the next one.',
    'plan ended': 'Your plan has ended. Renew it to trade.',
}
SCAN = {
    'nosetup': 'Looked at the market. No good setup yet, so it did not trade. That is normal.',
    'signal': 'Found a setup and sent it to MT5.',
}

def note(uid, sym, code, why=''):
    """Called by the scanner after each candle. code: nosetup | signal | gate | skip."""
    try: st.put('scan:%s:%s' % (uid or '', sym), json.dumps({'t': int(time.time()), 'c': code, 'w': str(why)[:120]}))
    except Exception as e: print('scan note failed', str(e)[:80])

def _last(uid):
    best = None
    for r in st.q("SELECT v FROM kv WHERE k LIKE ?", ('scan:%s:%%' % (uid or ''),)):
        try: j = json.loads(r['v'])
        except (TypeError, ValueError): continue
        if isinstance(j, dict) and (best is None or j.get('t', 0) > best.get('t', 0)): best = j
    return best

def _words(why): why = str(why or ''); return PLAIN.get(why) or ('Waiting: %s.' % why if why else 'Waiting for a safe moment.')

def _deriv(uid):
    """The person's Deriv connection row (no secrets), or None."""
    try: return next((r for r in bk.view(uid) if r['name'] == 'Deriv'), None)
    except Exception: return None

def _dbot(uid):
    from . import deriv
    try: return bool(deriv._bot(uid))
    except Exception: return False

def _deriv_state(uid, dv):
    """What the bot is doing on Deriv, from the note the Deriv loop saves after every round (brokers.REASONS)."""
    if not _dbot(uid): return {'running': False, 'state': 'stopped', 'why': PLAIN['bot off'], 'code': 'bot off', 'broker': 'Deriv'}
    code = dv.get('why_code'); out = {'running': True, 'broker': 'Deriv', 'checked': dv.get('why_t')}
    if code == 'ok': out.update(state='watching', code='watching', why='Connected to Deriv and watching. It checks the market each time a new 15-minute candle closes.')
    elif code: out.update(state='waiting', code=code, why=dv.get('why') or 'Waiting.')
    else: out.update(state='waiting', code='starting', why='Deriv is connected. The first check runs within a minute.')
    return out

def explain(uid, admin, paid=True, now=None):
    """-> {running, state, why, checked}. state: stopped | waiting | watching. Scope is the owner's EA for admins, the person's own link otherwise."""
    now = now or time.time(); sc = '' if admin else uid
    running = links.bot_on(sc); a = st.acct(sc); out = {'running': running, 'checked': None}
    if not admin and not paid: out.update(state='stopped', why=PLAIN['plan ended'], code='plan ended'); return out
    mt5_up = bool(a.get('seen')) and now - a.get('seen', 0) <= 120
    dv = None if mt5_up else _deriv(uid)
    if dv is not None and (_dbot(uid) or not running): out.update(_deriv_state(uid, dv)); return out          # Deriv is the one that is running (or nothing is): say so, not "MT5 is not talking"
    if not running: out.update(state='stopped', why=PLAIN['bot off'], code='bot off'); return out
    if not a.get('seen') or now - a.get('seen', 0) > 120: out.update(state='waiting', why=PLAIN['EA offline'], code='EA offline'); return out
    ok, why = risk.global_gate(now, uid=sc)
    if not ok: out.update(state='waiting', why=_words(why), code=why); return out
    n = _last(sc)
    if n and n.get('c') == 'skip':
        out.update(checked=n['t'], state='waiting', why=_words(n.get('w') or ''), code=n.get('w'))
    elif n and n.get('c') in SCAN:
        out.update(checked=n['t'], state='watching', why=SCAN[n['c']], code=n['c'])
    elif n:
        # an old 'gate' note (for example 'bot off' left while it was stopped): the live gates above just passed, so it is stale.
        # No market was looked at then, so it is not shown as a market check either.
        out.update(state='watching', why='Connected and watching. It checks the market each time a new 15-minute candle closes.', code='watching')
    else: out.update(state='watching', why='Connected and watching. It checks the market each time a new 15-minute candle closes.', code='watching')
    return out
