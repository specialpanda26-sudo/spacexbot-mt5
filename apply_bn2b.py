"""Section 5B-2b: switch the Binance SPOT TESTNET bot on (key check, loop started, Start bot, Trade on Binance, plain words). Idempotent. Run: python apply_bn2b.py
Needs 5A, 5B-1 and 5B-2a already applied. Real-money Binance is NOT touched (5B-3)."""
import os
R = os.path.dirname(os.path.abspath(__file__))
def edit(path, pairs):
    p = os.path.join(R, path); s = open(p, encoding='utf-8').read()
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, (path, old[:70], s.count(old))
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)

# ---- binance_bot.py: verify the saved TESTNET key
VERIFY = '''
_vlast = {}
def _mark(uid, status): st.x("UPDATE broker_links SET status=?,updated=? WHERE uid=? AND broker='Binance'", (status, int(time.time()), uid))

def verify(uid, http=None, now=None):
    """5B-2b: check the saved TESTNET key (demo mode) and read the test balance. Sets verified / rejected and a plain note. Returns (ok, message). Places no order."""
    now = now or time.time()
    if now - _vlast.get(uid, 0) < 8: return False, 'Wait a few seconds and try again.'
    _vlast[uid] = now
    sec = bk.secret(uid, 'Binance')
    if not sec or not sec.get('key') or not sec.get('secret'): return False, 'Save your Binance testnet key and secret first.'
    try: free, can = _free(sec['key'], sec['secret'], http, int(now * 1000))
    except ConnectionError as e:
        msg = str(e)
        if 'did not accept' in msg or 'does not match' in msg: _mark(uid, 'rejected'); bk.set_note(uid, 'Binance', msg)
        return False, msg
    except Exception as e:
        print('[binance_bot] check failed:', type(e).__name__)          # the type only: a message could hold the key
        return False, 'Could not reach Binance. Try again in a minute.'
    if not can:
        msg = 'This key cannot trade. Make a testnet key with trading allowed.'; _mark(uid, 'rejected'); bk.set_note(uid, 'Binance', msg); return False, msg
    bal = free + _held_cost(uid)
    _mark(uid, 'verified'); bk.set_bal(uid, 'Binance', bal, 'USD', demo=True, now=now)
    note = 'Testnet key works. Test balance about %s USDT (fake money). Binance trades on the testnet only for now. The bot checks the stop loss and take profit about once a minute, so a fast move can pass them.' % format(bal, ',.2f')
    bk.set_note(uid, 'Binance', note); return True, note
'''
edit('backend/binance_bot.py', [("\ndef _bot(uid): return bk.bot_flag(uid, 'Binance') is True\n", VERIFY + "\ndef _bot(uid): return bk.bot_flag(uid, 'Binance') is True\n")])

# ---- tradeon.py: Binance can trade now
edit('backend/tradeon.py', [
 ("CAN_TRADE = {'MT5': True, 'Deriv': True, 'Binance': False}", "CAN_TRADE = {'MT5': True, 'Deriv': True, 'Binance': True}          # Binance: testnet (fake money) only, 5B-2b"),
 ("    if n != 'Deriv' and st.q(\"SELECT 1 FROM broker_links WHERE uid=? AND broker='Deriv'\", (uid,), True):\n        bk.set_bot(uid, 'Deriv', False); bk.set_why(uid, 'Deriv', 'other platform')\n",
  "    if n != 'Deriv' and st.q(\"SELECT 1 FROM broker_links WHERE uid=? AND broker='Deriv'\", (uid,), True):\n        bk.set_bot(uid, 'Deriv', False); bk.set_why(uid, 'Deriv', 'other platform')\n"
  "    if n != 'Binance' and st.q(\"SELECT 1 FROM broker_links WHERE uid=? AND broker='Binance'\", (uid,), True):          # 5B-2b\n        bk.set_bot(uid, 'Binance', False); bk.set_why(uid, 'Binance', 'other platform')\n"),
 ("            'note': ('Binance does not trade yet, so nothing will trade while it is chosen.' if c == 'Binance' else\n",
  "            'note': ('Only Binance trades, on the testnet (fake money) for now. The other platforms stay stopped.' if c == 'Binance' else\n"),
])

# ---- brokers.py: words
edit('backend/brokers.py', [
 ("    'Binance': {'tile': 'Balance only, no trading', 'works': 'Key check and Spot balance read (read-only).', 'not': 'No trading. The bot never places a Binance order. A key that can withdraw is refused.'},",
  "    'Binance': {'tile': 'Testnet demo bot', 'works': 'Key check, test balance read, and a demo bot that buys and sells Spot crypto on the Binance TESTNET (fake money). Long-only: it buys, then sells.', 'not': 'Real-money Binance trading is not available yet. Use a testnet key from testnet.binance.vision, never your real Binance key.'},"),
 ("    'other platform': 'You chose another platform to trade on, so Deriv is paused. Change it on the Bot tab.',",
  "    'other platform': 'You chose another platform to trade on, so this one is paused. Change it on the Bot tab.',\n"
  "    'real not ready': 'Real-money Binance trading is not available yet. Switch to the testnet (demo).',\n"
  "    'no key': 'No Binance key is saved. Save your testnet key and secret again.',\n"
  "    'no crypto symbols': 'No crypto market is set to trade. The owner must add one (for example BTCUSD) to the symbols list.',\n"
  "    'cannot trade': 'This Binance key cannot trade. Make a testnet key with trading allowed.',"),
 ("'trades': r['broker'] != 'Binance',", "'trades': True,"),
])

# ---- botstate.py: say what Binance is doing on the Bot tab
edit('backend/botstate.py', [
 ("def _quiet_for(sc, now):",
  "def _binance_state(uid):\n"
  "    \"\"\"5B-2b: what the bot is doing on Binance (testnet), from the note the Binance loop saves after every round (brokers.REASONS).\"\"\"\n"
  "    try: b = next((r for r in bk.view(uid) if r['name'] == 'Binance'), None)\n"
  "    except Exception: b = None\n"
  "    if not b: return {'running': False, 'state': 'stopped', 'why': 'Binance is chosen but no key is saved. Save your testnet key on the Connect tab.', 'code': 'no key', 'broker': 'Binance'}\n"
  "    if not b.get('bot'): return {'running': False, 'state': 'stopped', 'why': PLAIN['bot off'], 'code': 'bot off', 'broker': 'Binance'}\n"
  "    code = b.get('why_code'); out = {'running': True, 'broker': 'Binance', 'checked': b.get('why_t')}\n"
  "    if code == 'ok': out.update(state='watching', code='watching', why='Connected to Binance (testnet, fake money) and watching. It checks the market each time a new 15-minute candle closes.')\n"
  "    elif code: out.update(state='waiting', code=code, why=b.get('why') or 'Waiting.')\n"
  "    else: out.update(state='waiting', code='starting', why='Binance is connected. The first check runs within a minute.')\n"
  "    return out\n\ndef _quiet_for(sc, now):"),
 ("    if not admin and not paid: out.update(state='stopped', why=PLAIN['plan ended'], code='plan ended'); return out\n",
  "    if not admin and not paid: out.update(state='stopped', why=PLAIN['plan ended'], code='plan ended'); return out\n"
  "    from . import tradeon\n"
  "    if tradeon.get(uid) == 'Binance': out.update(_binance_state(uid)); return out          # 5B-2b\n"),
])

# ---- guide.py
edit('backend/guide.py', [
 ("Binance: paste a key that can read, never one that can withdraw. Binance does not place trades yet.",
  "Binance: paste a TESTNET key (fake money) with trading allowed and withdrawals off. Binance trades on the testnet only for now."),
])

# ---- app.py
edit('backend/app.py', [
 ("authmail, binance, stake, envcheck", "authmail, binance, binance_bot, stake, envcheck"),
 ("    elif n == 'Binance': t = {'switch': 'Binance does not trade yet, so it has no demo or real switch.', 'bot': 'Binance does not trade yet, so there is no bot to start.'}[what]",
  "    elif n == 'Binance': t = {'switch': 'Binance trades on the testnet (demo) only for now, so it has no demo or real switch.', 'bot': 'Use the Binance card to start its bot.'}[what]"),
 ("MT5 brokers trade through the MT5 app; Binance does not trade yet.\"\"\"", "MT5 brokers trade through the MT5 app; Binance trades on the testnet only.\"\"\""),
 ("    ok, msg = deriv.verify(u['uid']) if n == 'Deriv' else binance.verify(u['uid'])\n",
  "    ok, msg = deriv.verify(u['uid']) if n == 'Deriv' else binance_bot.verify(u['uid']) if bk.mode(u['uid'], 'Binance') == 'demo' else binance.verify(u['uid'])          # 5B-2b: Binance demo = testnet key\n"),
 ("    if n != 'Deriv': return _not_deriv(n, 'bot')\n    on = _j().get('on') is True; r = st.q(\"SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'\", (u['uid'],), True)\n",
  "    if n not in ('Deriv', 'Binance'): return _not_deriv(n, 'bot')\n    on = _j().get('on') is True; r = st.q(\"SELECT status FROM broker_links WHERE uid=? AND broker=?\", (u['uid'], n), True); what = 'token' if n == 'Deriv' else 'key'\n"),
 ("        if not r: return jsonify(error='Save your Deriv token first.'), 400\n        if not u['active']: return jsonify(error='subscription required'), 402\n        if r['status'] != 'verified': return jsonify(error='Your token is not checked yet. Save it again to check it.'), 400\n",
  "        if not r: return jsonify(error='Save your %s %s first.' % (n, what)), 400\n        if not u['active']: return jsonify(error='subscription required'), 402\n        if r['status'] != 'verified': return jsonify(error='Your %s is not checked yet. Save it again to check it.' % what), 400\n"),
 ("        if tradeon.blocked_msg(u['uid'], 'Deriv'): return jsonify(error=tradeon.blocked_msg(u['uid'], 'Deriv')), 400          # 5A\n    bk.set_bot(u['uid'], n, on); learn.log",
  "        if tradeon.blocked_msg(u['uid'], n): return jsonify(error=tradeon.blocked_msg(u['uid'], n)), 400          # 5A\n"
  "        if n == 'Binance' and tradeon.get(u['uid']) != 'Binance': return jsonify(error='Choose Binance as your trading platform on the Bot tab first.'), 400          # 5B-2b: never on by default\n"
  "        if n == 'Binance' and bk.mode(u['uid'], n) == 'real': return jsonify(error='Real-money Binance trading is not available yet.'), 400\n"
  "    bk.set_bot(u['uid'], n, on); learn.log"),
 ("    if on: deriv.kick(u['uid'], _scan, _paid)\n    else: bk.set_why(u['uid'], n, 'bot off')\n    return jsonify(brokers=bk.view(u['uid']))",
  "    if on: (deriv if n == 'Deriv' else binance_bot).kick(u['uid'], _scan, _paid)\n    else: bk.set_why(u['uid'], n, 'bot off')\n    return jsonify(brokers=bk.view(u['uid']))"),
 ("def _deriv_bot(u, on):\n",
  "def _binance_bot(u, on):\n"
  "    \"\"\"5B-2b: the Bot tab's Start / Stop for Binance (testnet). None if fine, or (message, status). Stop never fails.\"\"\"\n"
  "    r = st.q(\"SELECT status FROM broker_links WHERE uid=? AND broker='Binance'\", (u['uid'],), True)\n"
  "    if not r: return ('Save your Binance testnet key on the Connect tab first.', 400) if on else None\n"
  "    if on and r['status'] != 'verified': return 'Your Binance key is not checked yet. Save it again to check it.', 400\n"
  "    if on and bk.mode(u['uid'], 'Binance') == 'real': return 'Real-money Binance trading is not available yet.', 400\n"
  "    bk.set_bot(u['uid'], 'Binance', on)\n"
  "    if on: binance_bot.kick(u['uid'], _scan, _paid)\n"
  "    else: bk.set_why(u['uid'], 'Binance', 'bot off')\n"
  "    return None\n\n"
  "def _deriv_bot(u, on):\n"),
 ("    if on and tp == 'Binance': return jsonify(error='Binance does not trade yet. Choose MT5 or Deriv as your trading platform first.'), 400          # 5A\n", "    # 5B-2b: Binance may start now when it was chosen (the old refusal is gone)\n"),
 ("    if u['admin']:\n        if m5: st.put('bot_enabled', '1' if on else '0')\n        learn.log(u['uid'], 'setting', data={'path': request.path, 'on': on})\n        if dv: _deriv_bot(u, on)\n",
  "    bn = (not on) or tp == 'Binance'          # 5B-2b: Binance starts only when it was chosen on purpose; Stop reaches it too\n"
  "    if u['admin']:\n        if m5: st.put('bot_enabled', '1' if on else '0')\n        learn.log(u['uid'], 'setting', data={'path': request.path, 'on': on})\n        if dv: _deriv_bot(u, on)\n"
  "        be = _binance_bot(u, on) if bn else None\n"
  "        if be: return jsonify(error=be[0]), be[1]\n"),
 ("    if not has_mt5 and not st.q(\"SELECT 1 FROM broker_links WHERE uid=? AND broker='Deriv'\", (u['uid'],), True): return jsonify(error='Make your MT5 key on the Connect tab first.'), 400\n",
  "    if not has_mt5 and not st.q(\"SELECT 1 FROM broker_links WHERE uid=? AND broker IN('Deriv','Binance')\", (u['uid'],), True): return jsonify(error='Make your MT5 key on the Connect tab first.'), 400\n"),
 ("    err = _deriv_bot(u, on) if dv else None\n    if err and not (has_mt5 and m5): return jsonify(error=err[0]), err[1]\n",
  "    err = _deriv_bot(u, on) if dv else None\n    err = err or (_binance_bot(u, on) if bn else None)\n    if err and not (has_mt5 and m5): return jsonify(error=err[0]), err[1]\n"),
 ("try: deriv.start(_scan, _paid)\nexcept Exception as e: print('deriv loop not started', e)\n",
  "try: deriv.start(_scan, _paid)\nexcept Exception as e: print('deriv loop not started', e)\ntry: binance_bot.start(_scan, _paid)          # 5B-2b: Binance testnet bot (every BINANCE_EVERY seconds, default 60)\nexcept Exception as e: print('binance loop not started', e)\n"),
])

# ---- static/index.html: the Binance card
edit('static/index.html', [
 ('"Read-only, no trading"', '(b.bot?"Testnet bot on":"Testnet demo")'),
 ('1. In Binance open API Management and make a key. 2. Turn Enable Reading ON and Withdrawals OFF (a key that can withdraw is refused). 3. Paste the key and secret below. We check them and read your Spot balance. Binance trading is not switched on: this app never places a Binance order.',
  '1. Open testnet.binance.vision and make an API key there (fake money). Never paste your real Binance key here. 2. Keep Withdrawals OFF. 3. Paste the key and secret below. We check them and read your test balance. 4. On the Bot tab choose Binance as your trading platform, then tap Start bot below. It trades Spot on the testnet only: it buys, then sells. It checks the stop loss and take profit about once a minute, so a fast move can pass them.'),
 ('(n==="Deriv"&&cur&&cur.status==="verified"?\'<div class="field"><p class="muted" id="pW">', '((n==="Deriv"||bn)&&cur&&cur.status==="verified"?\'<div class="field"><p class="muted" id="pW">'),
 ('window.SXA.api("/api/brokers/Deriv/bot",{method:"POST",body:{on:!cur.bot}}).then(function(j){bb.disabled=false;(j.brokers||[]).forEach(function(x){if(x.name==="Deriv"){cur=x;CN.Deriv=x}})',
  'window.SXA.api("/api/brokers/"+n+"/bot",{method:"POST",body:{on:!cur.bot}}).then(function(j){bb.disabled=false;(j.brokers||[]).forEach(function(x){if(x.name===n){cur=x;CN[n]=x}})'),
 ('tst(bn?"Binance key checked. Balance read.":', 'tst(bn?"Binance testnet key checked. Test balance read.":'),
])
print('5B-2b applied')
