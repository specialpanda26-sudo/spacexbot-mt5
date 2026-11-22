"""Section 5A: trade on ONE platform at a time (MT5 / Deriv / Binance). Per-person setting, kept as a kv row 'trade_on:<scope>'
(no schema change). Never set = nothing changes from before (every platform that has its bot on may trade).
scope = the person's uid; for the OWNER the same choice is also kept under scope '' because the owner's own EA calls the server with no uid.
Binance cannot trade yet (backend/binance.py is read-only), so choosing it means nothing trades, and the app says so."""
from . import store as st, links, brokers as bk

PLATFORMS = ('MT5', 'Deriv', 'Binance')
CAN_TRADE = {'MT5': True, 'Deriv': True, 'Binance': True}          # Binance: testnet (fake money) only, 5B-2b

def canon(name):
    n = str(name or '').strip().lower()
    return next((p for p in PLATFORMS if p.lower() == n), None)

def get(scope):
    """The chosen platform, or None when the person never chose (old behaviour)."""
    v = st.get('trade_on:%s' % (scope or ''))
    return v if v in PLATFORMS else None

def allows(scope, platform):
    """May `platform` trade for this scope? True when nothing was chosen, or when it is the chosen one."""
    c = get(scope)
    return c is None or c == platform

def set_(uid, admin, name):
    """Choose the platform and switch every OTHER platform's bot off. Raises ValueError for an unknown name."""
    n = canon(name)
    if not n: raise ValueError('Choose MT5, Deriv or Binance.')
    st.put('trade_on:%s' % uid, n)
    if admin: st.put('trade_on:', n)
    if n != 'MT5':
        if links.get(uid): links.set_bot(uid, False)
        if admin: st.put('bot_enabled', '0')
    if n != 'Deriv' and st.q("SELECT 1 FROM broker_links WHERE uid=? AND broker='Deriv'", (uid,), True):
        bk.set_bot(uid, 'Deriv', False); bk.set_why(uid, 'Deriv', 'other platform')
    if n != 'Binance' and st.q("SELECT 1 FROM broker_links WHERE uid=? AND broker='Binance'", (uid,), True):          # 5B-2b
        bk.set_bot(uid, 'Binance', False); bk.set_why(uid, 'Binance', 'other platform')
    return n

def blocked_msg(scope, platform):
    """Plain words for 'you chose another platform', or '' when `platform` may trade."""
    c = get(scope)
    if c is None or c == platform: return ''
    return 'You chose %s as your trading platform, so %s does not trade. Change it on the Bot tab first.' % (c, platform)

def view(uid, admin=False):
    c = get(uid)
    return {'trade_on': c, 'platforms': [{'name': p, 'trades': CAN_TRADE[p]} for p in PLATFORMS],
            'note': ('Only Binance trades, on the testnet (fake money) for now. The other platforms stay stopped.' if c == 'Binance' else
                     'Only %s trades. The other platforms stay stopped.' % c if c else 'No platform chosen: every platform whose bot is on may trade.')}
