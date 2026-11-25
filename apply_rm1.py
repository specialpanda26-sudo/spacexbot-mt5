import sys
def edit(p, old, new):
    s = open(p, encoding='utf-8', newline='').read()
    if s.count(old) == 1:
        open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new)); print('done', p)
    elif s.count(new) >= 1: print('skip (already done)', p)
    else: print('STOP: cannot find exactly once in', p); sys.exit(1)
import os, subprocess
for f in ('backend/tradeon.py', 'static/trade_on.js', 'tests/test_lv4.py', 'tests/test_tp5a.py'):
    if os.path.exists(f): subprocess.run(['git', 'rm', '-q', '-f', f]); print('removed', f)
    else: print('skip (already gone)', f)

F = 'backend/app.py'
edit(F, r'''st.init(); assist.init(); screenread.init()

''',
     r'''st.init(); assist.init(); screenread.init()
try:          # one-time cleanup: the old "Trade on" limit is gone, so forget its saved choice and the "paused" note it left on each broker
    st.x("DELETE FROM kv WHERE k LIKE 'trade_on:%'")
    for _r in st.q("SELECT k,v FROM kv WHERE k LIKE 'why:%'") or []:
        if '"other platform"' in str(_r['v']): st.x('DELETE FROM kv WHERE k=?', (_r['k'],))
except Exception as _e: print('trade-on cleanup skipped', str(_e)[:80])

''')
edit(F, r'''from . import manual_close, burst_scope, btc_switch, tradeon, course, roadmap, guide, deriv_oauth, testlab
''',
     r'''from . import manual_close, burst_scope, btc_switch, course, roadmap, guide, deriv_oauth, testlab
''')
edit(F, r'''    if s and who and risk.bot_on(who) and not links.bot_on(who): s = None          # R7: the bot is on only for Deriv, so this signal is for Deriv; the MT5 bridge never sees it (the MT5 bridge itself ignores the bot flag)
    if s and not tradeon.allows(who, 'MT5'): s = None          # 5A: another platform was chosen, so the MT5 bridge gets nothing
    bk = burst.basket(s, who) if s else None          # a burst group goes out ALL AT ONCE as one basket (the old way would send one entry per poll)
''',
     r'''    if s and who and risk.bot_on(who) and not links.bot_on(who): s = None          # R7: the bot is on only for Deriv, so this signal is for Deriv; the MT5 bridge never sees it (the MT5 bridge itself ignores the bot flag)
    bk = burst.basket(s, who) if s else None          # a burst group goes out ALL AT ONCE as one basket (the old way would send one entry per poll)
''')
edit(F, r'''        return jsonify(signal=None, basket=bk, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'), qp=quickprofit.usd_for(who))
''',
     r'''        return jsonify(signal=None, basket=bk, bot=links.bot_on(who), symbols=st.get('symbols'), qp=quickprofit.usd_for(who))
''')
edit(F, r'''    return jsonify(signal=s, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'), qp=quickprofit.usd_for(who))
''',
     r'''    return jsonify(signal=s, bot=links.bot_on(who), symbols=st.get('symbols'), qp=quickprofit.usd_for(who))
''')
edit(F, r'''    if on and assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400
    if on and tradeon.blocked_msg(u['uid'], 'MT5'): return jsonify(error=tradeon.blocked_msg(u['uid'], 'MT5')), 400          # 5A
    return _link_edit(u, lambda: links.set_bot(u['uid'], on))
''',
     r'''    if on and assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400
    return _link_edit(u, lambda: links.set_bot(u['uid'], on))
''')
edit(F, r'''        if assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400
        if tradeon.blocked_msg(u['uid'], n): return jsonify(error=tradeon.blocked_msg(u['uid'], n)), 400          # 5A
        if n == 'Binance' and tradeon.get(u['uid']) != 'Binance': return jsonify(error='Choose Binance as your trading platform on the Bot tab first.'), 400          # 5B-2b: never on by default
        if n == 'Binance' and bk.mode(u['uid'], n) == 'real': return jsonify(error='Real-money Binance trading is not available yet.'), 400
''',
     r'''        if assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400
        if n == 'Binance' and bk.mode(u['uid'], n) == 'real': return jsonify(error='Real-money Binance trading is not available yet.'), 400
''')
edit(F, '\n@app.get(\'/api/trade-on\')\n@need(verified=True)\ndef trade_on_get(u):\n    """5A: which platform trades (MT5, Deriv or Binance), or null when the person never chose."""\n    return jsonify(tradeon.view(u[\'uid\'], bool(u[\'admin\'])))\n\n@app.post(\'/api/trade-on\')\n@need(verified=True)\ndef trade_on_set(u):\n    """5A: choose the ONE platform that trades. Every other platform\'s bot is switched off. Real-money rules (plan, REAL word, limits) are unchanged."""\n    try: n = tradeon.set_(u[\'uid\'], bool(u[\'admin\']), _j().get(\'platform\'))\n    except ValueError as e: return jsonify(error=str(e)), 400\n    learn.log(u[\'uid\'], \'setting\', data={\'path\': request.path, \'platform\': n})\n    return jsonify(ok=True, **tradeon.view(u[\'uid\'], bool(u[\'admin\'])))\n\n@app.get(\'/api/screen/status\')\n',
     "\n@app.get('/api/screen/status')\n")
edit(F, r'''    on = _j().get('on') is True; tp = tradeon.get(u['uid'])
    # 5B-2b: Binance may start now when it was chosen (the old refusal is gone)
    m5, dv = (not on) or tradeon.allows(u['uid'], 'MT5'), (not on) or tradeon.allows(u['uid'], 'Deriv')          # 5A: Start reaches only the chosen platform; Stop always reaches all
    bn = (not on) or tp == 'Binance'          # 5B-2b: Binance starts only when it was chosen on purpose; Stop reaches it too
''',
     r'''    on = _j().get('on') is True
    m5 = dv = True          # Start / Stop reaches every platform this person has connected; nothing is paused for choosing another
    bn = (not on) or bool(st.q("SELECT 1 FROM broker_links WHERE uid=? AND broker='Binance'", (u['uid'],), True))
''')
edit(F, r'''    if not has_mt5 and not st.q("SELECT 1 FROM broker_links WHERE uid=? AND broker IN('Deriv','Binance')", (u['uid'],), True): return jsonify(error='Make your MT5 key on the Connect tab first.'), 400
    if on and tp == 'MT5' and not has_mt5: return jsonify(error='Make your MT5 key on the Connect tab first.'), 400
    if has_mt5 and m5: links.set_bot(u['uid'], on)
''',
     r'''    if not has_mt5 and not st.q("SELECT 1 FROM broker_links WHERE uid=? AND broker IN('Deriv','Binance')", (u['uid'],), True): return jsonify(error='Make your MT5 key on the Connect tab first.'), 400
    if has_mt5 and m5: links.set_bot(u['uid'], on)
''')
