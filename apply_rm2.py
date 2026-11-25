import sys
def edit(p, old, new):
    s = open(p, encoding='utf-8', newline='').read()
    if s.count(old) == 1:
        open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new)); print('done', p)
    elif s.count(new) >= 1: print('skip (already done)', p)
    else: print('STOP: cannot find exactly once in', p); sys.exit(1)

F = 'backend/binance_bot.py'
edit(F, r'''from . import store as st, brokers as bk, bars, tradeon, binance_trade as bt
''',
     r'''from . import store as st, brokers as bk, bars, binance_trade as bt
''')
edit(F, r'''        binance_group.check(uid, key, secret, http, now, bool(paid(uid)) and tradeon.get(uid) == 'Binance' and _bot(uid) and bk.mode(uid, 'Binance') != 'real')
''',
     r'''        binance_group.check(uid, key, secret, http, now, bool(paid(uid)) and _bot(uid) and bk.mode(uid, 'Binance') != 'real')
''')
edit(F, r'''    if not paid(uid): return 'plan ended'
    if tradeon.get(uid) != 'Binance': return 'other platform'          # Binance trades only when it was chosen on purpose
    if not _bot(uid): return 'bot off'
''',
     r'''    if not paid(uid): return 'plan ended'
    if not _bot(uid): return 'bot off'
''')

F = 'backend/botstate.py'
edit(F, r'''    from . import tradeon
    if tradeon.get(uid) == 'Binance': out.update(_binance_state(uid)); return out          # 5B-2b
''',
     r'''    if not running and not _dbot(uid) and bk.bot_flag(uid, 'Binance'): out.update(_binance_state(uid)); return out          # only Binance is running
''')

F = 'backend/brokers.py'
edit(F, r'''    'bot off': 'The bot is off. Tap Start bot.',
    'other platform': 'You chose another platform to trade on, so this one is paused. Change it on the Bot tab.',
    'real not ready': 'Real-money Binance trading is not available yet. Switch to the testnet (demo).',
''',
     r'''    'bot off': 'The bot is off. Tap Start bot.',
    'real not ready': 'Real-money Binance trading is not available yet. Switch to the testnet (demo).',
''')

F = 'backend/burst_scope.py'
edit(F, r'''Now: owner + Deriv or Binance chosen on 'Trade on' -> the card uses the owner's own uid. Anyone else, and the owner on MT5 or with nothing chosen, is unchanged.
''',
     r'''Now: owner with the Deriv or Binance bot switched on -> the card uses the owner's own uid. Anyone else, and the owner on MT5 only, is unchanged.
''')
edit(F, r'''from . import store as st, tradeon
''',
     r'''from . import store as st, brokers as bk
''')
edit(F, r'''    if tradeon.get(uid) in OWN_UID:
''',
     r'''    if any(bk.bot_flag(uid, p) for p in OWN_UID):          # the owner's Deriv or Binance bot is switched on, so it scans under the owner's own uid
''')

F = 'backend/deriv.py'
edit(F, r'''    until then the old MT5-link switch still counts, so nothing that worked before stops working."""
    from . import tradeon
    if not tradeon.allows(uid, 'Deriv'): return False          # 5A: another platform was chosen
    f = bk.bot_flag(uid, 'Deriv')
''',
     r'''    until then the old MT5-link switch still counts, so nothing that worked before stops working."""
    f = bk.bot_flag(uid, 'Deriv')
''')
edit(F, r'''    if not paid(uid): return 'plan ended'
    from . import tradeon
    if not tradeon.allows(uid, 'Deriv'): return 'other platform'          # 5A
    if not _bot(uid): return 'bot off'
''',
     r'''    if not paid(uid): return 'plan ended'
    if not _bot(uid): return 'bot off'
''')

F = 'backend/livestats.py'
edit(F, r'''from . import store as st, links, brokers as bk, strategy_info as si, pnlreset as pr, tradeon, burst_live, openlive
''',
     r'''from . import store as st, links, brokers as bk, strategy_info as si, pnlreset as pr, burst_live, openlive
''')
edit(F, r'''    ch = tradeon.get(uid)          # LV4: the platform the bot is set to trade on; nothing chosen = the old behaviour (every connected account)
    if ch: src = [s for s in src if s['id'] == ch]
''',
     r'''    ch = None          # every connected account is shown
''')

F = 'backend/mt5_cycle.py'
edit(F, r'''from . import store as st, tradeon, deriv_group as dg
''',
     r'''from . import store as st, deriv_group as dg
''')
edit(F, r'''    if not closed or total <= 0: return None          # a loss limit or a stop loss never starts the next group
    if not tradeon.allows(uid, 'MT5'): return None          # the person moved to another platform
    if not st.x("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING", ('cyc_done:%d' % int(g), str(int(now))), True): return None          # this group already started its successor
''',
     r'''    if not closed or total <= 0: return None          # a loss limit or a stop loss never starts the next group
    if not st.x("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING", ('cyc_done:%d' % int(g), str(int(now))), True): return None          # this group already started its successor
''')

F = 'static/index.html'
edit(F, r'''<script src="/static/prefs_ui.js"></script><script src="/static/streak_ui.js"></script><script src="/static/share_ui.js"></script><script src="/static/quick_ui.js"></script><script src="/static/trade_on.js"></script><script src="/static/screen.js"></script><script src="/static/deriv_login.js"></script><script src="/static/test_lab.js"></script><script src="/static/course.js"></script><script src="/static/roadmap.js"></script><script src="/static/guide.js"></script><script src="/static/running.js"></script><script src="/static/update.js"></script>
''',
     r'''<script src="/static/prefs_ui.js"></script><script src="/static/streak_ui.js"></script><script src="/static/share_ui.js"></script><script src="/static/quick_ui.js"></script><script src="/static/screen.js"></script><script src="/static/deriv_login.js"></script><script src="/static/test_lab.js"></script><script src="/static/course.js"></script><script src="/static/roadmap.js"></script><script src="/static/guide.js"></script><script src="/static/running.js"></script><script src="/static/update.js"></script>
''')
