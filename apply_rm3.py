import sys
def edit(p, old, new):
    s = open(p, encoding='utf-8', newline='').read()
    if s.count(old) == 1:
        open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new)); print('done', p)
    elif s.count(new) >= 1: print('skip (already done)', p)
    else: print('STOP: cannot find exactly once in', p); sys.exit(1)

F = 'tests/test_bb2.py'
edit(F, r'''from backend import store as st, brokers as bk, binance_bot as bb, binance_trade as bt, tradeon
''',
     r'''from backend import store as st, brokers as bk, binance_bot as bb, binance_trade as bt
''')
edit(F, r'''T('Binance never chosen as the platform -> other platform, nothing called', bb.run_once(U, scan, yes, http, NOW) == 'other platform' and not S['calls'])
tradeon.set_(U, False, 'Binance')
''',
     r'''T('Binance bot never switched on -> bot off, nothing called', bb.run_once(U, scan, yes, http, NOW) == 'bot off' and not S['calls'])
''')

F = 'tests/test_bt9.py'
edit(F, r'''from backend import store as st, brain, burst, burst_scope as bs, tradeon, brokers as bk
''',
     r'''from backend import store as st, brain, burst, burst_scope as bs, brokers as bk
''')
edit(F, r'''def on(sc): return burst.get(sc)['on']

''',
     r'''def on(sc): return burst.get(sc)['on']
def pick(uid, p):          # which broker's bot is running (the old 'Trade on' choice is gone)
    for b in ('Deriv', 'Binance'): bk.set_bot(uid, b, b == p)

''')
edit(F, r'''tradeon.set_(UID, True, 'MT5'); c.post('/api/burst', json={'quick_n': 3}, headers=OW)
''',
     r'''pick(UID, 'MT5'); c.post('/api/burst', json={'quick_n': 3}, headers=OW)
''')
edit(F, r'''tradeon.set_(UID, True, 'Deriv')
''',
     r'''pick(UID, 'Deriv')
''')
edit(F, r'''tradeon.set_(UID, True, 'Binance'); T('Binance chosen: the owner uid', bs.scope({'uid': UID, 'admin': True}) == UID)
tradeon.set_(UID, True, 'MT5'); T('back to MT5: scope ""', bs.scope({'uid': UID, 'admin': True}) == '')
''',
     r'''pick(UID, 'Binance'); T('Binance chosen: the owner uid', bs.scope({'uid': UID, 'admin': True}) == UID)
pick(UID, 'MT5'); T('back to MT5: scope ""', bs.scope({'uid': UID, 'admin': True}) == '')
''')
edit(F, r'''tradeon.set_(AMY, False, 'Deriv'); T('subscriber on Deriv: still their uid', bs.scope({'uid': AMY, 'admin': False}) == AMY)
''',
     r'''pick(AMY, 'Deriv'); T('subscriber on Deriv: still their uid', bs.scope({'uid': AMY, 'admin': False}) == AMY)
''')

F = 'tests/test_bx1.py'
edit(F, r'''from backend import store as st, brain, burst, burst_look, automode, openlive, livestats, live, deriv, tradeon, brokers as bk, risk
''',
     r'''from backend import store as st, brain, burst, burst_look, automode, openlive, livestats, live, deriv, brokers as bk, risk
''')
edit(F, r'''burst.save(UID, {'on': True, 'minute': True}); tradeon.set_(UID, True, 'Deriv'); bk.set_bot(UID, 'Deriv', True)
''',
     r'''burst.save(UID, {'on': True, 'minute': True}); bk.set_bot(UID, 'Deriv', True)
''')
edit(F, r'''tradeon.set_(UID, True, 'Deriv'); sn = livestats.snapshot(UID, True, NOW)
''',
     r'''sn = livestats.snapshot(UID, True, NOW)
''')

F = 'tests/test_bx4.py'
edit(F, r'''from backend import store as st, livestats, live, brokers as bk, tradeon
''',
     r'''from backend import store as st, livestats, live, brokers as bk
''')
edit(F, r'''st.set_acct({'balance': 500, 'equity': 500, 'open': 2, 'demo': True, 'src': 'deriv'}, UID); bk.set_bal(UID, 'Deriv', 500, 'USD', True); tradeon.set_(UID, True, 'Deriv')
''',
     r'''st.set_acct({'balance': 500, 'equity': 500, 'open': 2, 'demo': True, 'src': 'deriv'}, UID); bk.set_bal(UID, 'Deriv', 500, 'USD', True)
''')

F = 'tests/test_cy4.py'
edit(F, r'''wipe(); on(); ids = group(n=1); one(ids, [0.5]); T('a single trade is not a group', not pend())
wipe(); on(); st.put('trade_on:', 'Deriv'); ids = group(); one(ids, [0.3, 0.3, 0.2]); T('the person moved to another platform: MT5 queues nothing', not pend())
wipe(); on(); ids = group(); one(ids, [0.3, 0.3, 0.2], price=None); T('the EA sent no closing price: nothing is queued and it says why', not pend() and 'price' in dg.why(''))
''',
     r'''wipe(); on(); ids = group(n=1); one(ids, [0.5]); T('a single trade is not a group', not pend())
wipe(); on(); ids = group(); one(ids, [0.3, 0.3, 0.2], price=None); T('the EA sent no closing price: nothing is queued and it says why', not pend() and 'price' in dg.why(''))
''')

F = 'tests/test_sc2.py'
edit(F, r'''T('index.html loads screen.js once, right after trade_on.js', S.count('/static/screen.js') == 1 and '<script src="/static/trade_on.js"></script><script src="/static/screen.js"></script>' in S)
''',
     r'''T('index.html loads screen.js once, right after quick_ui.js', S.count('/static/screen.js') == 1 and '<script src="/static/quick_ui.js"></script><script src="/static/screen.js"></script>' in S)
''')

F = 'tests/test_streakui.py'
edit(F, r'''T('the page loads streak_ui.js once, right after prefs_ui.js', html.count('/static/streak_ui.js') == 1 and html.find('prefs_ui.js') < html.find('streak_ui.js') < html.find('trade_on.js'))
''',
     r'''T('the page loads streak_ui.js once, right after prefs_ui.js', html.count('/static/streak_ui.js') == 1 and html.find('prefs_ui.js') < html.find('streak_ui.js') < html.find('quick_ui.js'))
''')
