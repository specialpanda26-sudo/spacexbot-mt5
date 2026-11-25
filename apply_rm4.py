import sys
def edit(p, old, new):
    s = open(p, encoding='utf-8', newline='').read()
    if s.count(old) == 1:
        open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new)); print('done', p)
    elif s.count(new) >= 1: print('skip (already done)', p)
    else: print('STOP: cannot find exactly once in', p); sys.exit(1)

F = 'tests/test_bn2b.py'
edit(F, r'''from backend import store as st, links, brokers as bk, tradeon, alerts, botstate, binance_bot as bb, binance_trade as bt
''',
     r'''from backend import store as st, links, brokers as bk, alerts, botstate, binance_bot as bb, binance_trade as bt
''')
edit(F, r'''T('plain words exist for every new reason', all(k in bk.REASONS and len(bk.REASONS[k]) > 20 for k in ('real not ready', 'no key', 'no crypto symbols', 'cannot trade', 'other platform')))
T("'other platform' no longer names Deriv (it is shown on the Binance tile too)", 'Deriv' not in bk.REASONS['other platform'])
''',
     r'''T('plain words exist for every new reason', all(k in bk.REASONS and len(bk.REASONS[k]) > 20 for k in ('real not ready', 'no key', 'no crypto symbols', 'cannot trade')))
''')
edit(F, r'''def tile_bot(email, on): return c.post('/api/brokers/Binance/bot', json={'on': on}, headers=H(email))
T('Binance card: Start before choosing Binance is refused (never on by default)', tile_bot('amy@x.com', True).status_code == 400 and 'Choose Binance' in tile_bot('amy@x.com', True).get_json()['error'] and bk.bot_flag(A, 'Binance') is not True and not KICKS)
c.post('/api/trade-on', json={'platform': 'Deriv'}, headers=H('amy@x.com'))
r = tile_bot('amy@x.com', True)
''',
     r'''def tile_bot(email, on): return c.post('/api/brokers/Binance/bot', json={'on': on}, headers=H(email))
r = tile_bot('amy@x.com', True)
''')
edit(F, r'''T('Binance card: Start while Deriv is chosen is refused with the chosen name', r.status_code == 400 and 'Deriv' in r.get_json()['error'] and not KICKS)
c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('amy@x.com'))
r = tile_bot('amy@x.com', True)
T('Binance chosen + checked + plan: Start works, flag on, the loop is kicked once', r.status_code == 200 and bk.bot_flag(A, 'Binance') is True and KICKS == [A])
''',
     r'''KICKS.clear(); r = tile_bot('amy@x.com', True)
T('Binance checked + plan: Start works, flag on, the loop is kicked once', r.status_code == 200 and bk.bot_flag(A, 'Binance') is True and KICKS == [A])
''')
edit(F, r'''bk.set_bot(A, 'Binance', True)
c.post('/api/trade-on', json={'platform': 'MT5'}, headers=H('amy@x.com'))
T('choosing MT5 switches the Binance bot off and says why', bk.bot_flag(A, 'Binance') is False and binrow(A)['why_code'] == 'other platform')
c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('amy@x.com'))
r = c.post('/api/bot', json={'on': True}, headers=H('bob@x.com'))
''',
     r'''bk.set_bot(A, 'Binance', True)
r = c.post('/api/bot', json={'on': True}, headers=H('bob@x.com'))
''')
edit(F, r'''T('a person with no Binance key: Start with Binance chosen asks for the key, nothing starts', (c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('bob@x.com')), c.post('/api/bot', json={'on': True}, headers=H('bob@x.com')))[1].status_code == 400 and bk.bot_flag(B, 'Binance') is None)
''',
     r'''T('a person with no Binance key and no MT5 key: Start asks for a key, nothing starts', c.post('/api/bot', json={'on': True}, headers=H('bob@x.com')).status_code == 400 and bk.bot_flag(B, 'Binance') is None)
''')
edit(F, r'''KICKS.clear(); links.new_key(A); c.post('/api/trade-on', json={'platform': 'MT5'}, headers=H('amy@x.com')); links.set_bot(A, False)          # Amy has an MT5 key here, so the request really reaches the platform gates
''',
     r'''KICKS.clear(); links.new_key(A); links.set_bot(A, False)          # Amy has an MT5 key here, so the request really reaches the platform gates
''')
edit(F, r'''T('with MT5 chosen the Bot tab Start starts MT5 and never touches Binance', links.bot_on(A) is True and bk.bot_flag(A, 'Binance') is not True and not KICKS)
''',
     r'''T('with an MT5 key too, the Bot tab Start starts MT5 and the checked Binance key', links.bot_on(A) is True and bk.bot_flag(A, 'Binance') is True)
''')
edit(F, r'''c.post('/api/trade-on', json={'platform': 'Binance'}, headers=H('boss@x.com')); KICKS.clear()
''',
     r'''KICKS.clear()
''')
edit(F, r'''T('owner: Start with Binance chosen starts Binance and leaves the owner EA switch off', r.status_code == 200 and bk.bot_flag(O, 'Binance') is True and st.get('bot_enabled') != '1' and KICKS == [O])
''',
     r'''T('owner: Start starts Binance (and the owner EA switch, nothing is paused)', r.status_code == 200 and bk.bot_flag(O, 'Binance') is True and KICKS == [O])
''')
edit(F, r'''bk.set_bot(A, 'Binance', False); tradeon.set_(A, False, 'Binance')
''',
     r'''bk.set_bot(A, 'Binance', False); links.set_bot(A, False)
''')
edit(F, r'''e = botstate.explain(A, False, True)
T('Bot tab, Binance chosen and bot off: stopped, broker Binance', e['state'] == 'stopped' and e['broker'] == 'Binance' and e['running'] is False)
bk.set_bot(A, 'Binance', True); bk.set_why(A, 'Binance', 'ok'); e = botstate.explain(A, False, True)
''',
     r'''e = botstate.explain(A, False, True)
bk.set_bot(A, 'Binance', True); bk.set_why(A, 'Binance', 'ok'); e = botstate.explain(A, False, True)
''')
edit(F, r'''tradeon.set_(A, False, 'Deriv'); T('Binance not chosen: the Bot tab is the old one (no broker Binance)', botstate.explain(A, False, True).get('broker') != 'Binance')
''',
     r'''bk.set_bot(A, 'Binance', False); T('Binance bot off: the Bot tab is the old one (no broker Binance)', botstate.explain(A, False, True).get('broker') != 'Binance')
''')
edit(F, r'''# ---- 5A gate and the loop are wired
T('trade-on view: Binance trades, note says testnet', (tradeon.set_(A, False, 'Binance'), c.get('/api/trade-on', headers=H('amy@x.com')).get_json())[1]['platforms'][2]['trades'] is True and 'testnet' in tradeon.view(A)['note'])
bb.round_all  # exists
''',
     r'''# ---- 5A gate and the loop are wired
bb.round_all  # exists
''')
edit(F, r'''T('the old "does not trade yet" words are gone from the server', 'does not trade yet' not in src and 'does not trade yet' not in open(os.path.join(ROOT, 'backend', 'tradeon.py')).read())
''',
     r'''T('the old "does not trade yet" words are gone from the server', 'does not trade yet' not in src)
''')
