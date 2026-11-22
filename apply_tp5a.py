"""Section 5A: trade on ONE platform at a time. Adds backend/tradeon.py (already written), gates, routes. Idempotent. Run: python apply_tp5a.py"""
import os
R = os.path.dirname(os.path.abspath(__file__))
def edit(path, pairs):
    p = os.path.join(R, path); s = open(p, encoding='utf-8').read()
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, (path, old[:60], s.count(old))
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)

edit('backend/app.py', [
 ("from . import btc_switch\n", "from . import btc_switch, tradeon\n"),
 # EA poll: the MT5 bridge sees no signal unless MT5 is the chosen platform (or none was chosen)
 ("    bk = burst.basket(s, who) if s else None          # a burst group",
  "    if s and not tradeon.allows(who, 'MT5'): s = None          # 5A: another platform was chosen, so the MT5 bridge gets nothing\n    bk = burst.basket(s, who) if s else None          # a burst group"),
 ("        return jsonify(signal=None, basket=bk, bot=links.bot_on(who), symbols=st.get('symbols'))",
  "        return jsonify(signal=None, basket=bk, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'))"),
 ("    return jsonify(signal=s, bot=links.bot_on(who), symbols=st.get('symbols'))\n\n@app.post('/api/ea/report')",
  "    return jsonify(signal=s, bot=links.bot_on(who) and tradeon.allows(who, 'MT5'), symbols=st.get('symbols'))\n\n@app.post('/api/ea/report')"),
 # MT5 link switch
 ("    if on and assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400\n    return _link_edit(u, lambda: links.set_bot(u['uid'], on))",
  "    if on and assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400\n    if on and tradeon.blocked_msg(u['uid'], 'MT5'): return jsonify(error=tradeon.blocked_msg(u['uid'], 'MT5')), 400          # 5A\n    return _link_edit(u, lambda: links.set_bot(u['uid'], on))"),
 # Deriv tile switch
 ("        if assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400\n    bk.set_bot(u['uid'], n, on); learn.log",
  "        if assist.is_on(u['uid']): return jsonify(error='Turn off Phone mode first, so the same signal is not traded twice.'), 400\n        if tradeon.blocked_msg(u['uid'], 'Deriv'): return jsonify(error=tradeon.blocked_msg(u['uid'], 'Deriv')), 400          # 5A\n    bk.set_bot(u['uid'], n, on); learn.log"),
 # Bot tab Start / Stop
 ("    on = _j().get('on') is True\n    if u['admin']:\n        st.put('bot_enabled', '1' if on else '0'); learn.log(u['uid'], 'setting', data={'path': request.path, 'on': on}); _deriv_bot(u, on)\n        return jsonify(ok=True, **botstate.explain(u['uid'], True))",
  "    on = _j().get('on') is True; tp = tradeon.get(u['uid'])\n    if on and tp == 'Binance': return jsonify(error='Binance does not trade yet. Choose MT5 or Deriv as your trading platform first.'), 400          # 5A\n    m5, dv = (not on) or tradeon.allows(u['uid'], 'MT5'), (not on) or tradeon.allows(u['uid'], 'Deriv')          # 5A: Start reaches only the chosen platform; Stop always reaches all\n    if u['admin']:\n        if m5: st.put('bot_enabled', '1' if on else '0')\n        learn.log(u['uid'], 'setting', data={'path': request.path, 'on': on})\n        if dv: _deriv_bot(u, on)\n        return jsonify(ok=True, **botstate.explain(u['uid'], True))"),
 ("    if has_mt5: links.set_bot(u['uid'], on)\n    err = _deriv_bot(u, on)\n    if err and not has_mt5: return jsonify(error=err[0]), err[1]",
  "    if on and tp == 'MT5' and not has_mt5: return jsonify(error='Make your MT5 key on the Connect tab first.'), 400\n    if has_mt5 and m5: links.set_bot(u['uid'], on)\n    err = _deriv_bot(u, on) if dv else None\n    if err and not (has_mt5 and m5): return jsonify(error=err[0]), err[1]"),
 # the new routes, just before the Bot tab routes
 ("def _deriv_bot(u, on):",
  "@app.get('/api/trade-on')\n@need(verified=True)\ndef trade_on_get(u):\n    \"\"\"5A: which platform trades (MT5, Deriv or Binance), or null when the person never chose.\"\"\"\n    return jsonify(tradeon.view(u['uid'], bool(u['admin'])))\n\n@app.post('/api/trade-on')\n@need(verified=True)\ndef trade_on_set(u):\n    \"\"\"5A: choose the ONE platform that trades. Every other platform's bot is switched off. Real-money rules (plan, REAL word, limits) are unchanged.\"\"\"\n    try: n = tradeon.set_(u['uid'], bool(u['admin']), _j().get('platform'))\n    except ValueError as e: return jsonify(error=str(e)), 400\n    learn.log(u['uid'], 'setting', data={'path': request.path, 'platform': n})\n    return jsonify(ok=True, **tradeon.view(u['uid'], bool(u['admin'])))\n\ndef _deriv_bot(u, on):"),
])
edit('backend/deriv.py', [
 ("    f = bk.bot_flag(uid, 'Deriv')\n    return f if f is not None else links.bot_on(uid)",
  "    from . import tradeon\n    if not tradeon.allows(uid, 'Deriv'): return False          # 5A: another platform was chosen\n    f = bk.bot_flag(uid, 'Deriv')\n    return f if f is not None else links.bot_on(uid)"),
 ("    if not _bot(uid): return 'bot off'\n    r = st.q(\"SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'\"",
  "    from . import tradeon\n    if not tradeon.allows(uid, 'Deriv'): return 'other platform'          # 5A\n    if not _bot(uid): return 'bot off'\n    r = st.q(\"SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'\""),
])
edit('backend/brokers.py', [
 ("    'bot off': 'The bot is off. Tap Start bot.',", "    'bot off': 'The bot is off. Tap Start bot.',\n    'other platform': 'You chose another platform to trade on, so Deriv is paused. Change it on the Bot tab.',"),
])
print('5A applied')
# the screen: static/trade_on.js + its script tag (the file itself ships in the repo)
edit('static/index.html', [('<script src="/static/prefs_ui.js"></script>', '<script src="/static/prefs_ui.js"></script><script src="/static/trade_on.js"></script>')])
