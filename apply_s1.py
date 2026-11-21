"""Section 1: MT5 wording + Connect steps + honest server messages + fix the 2 old tests.
Every old text must appear exactly once or NOTHING is changed. Safe to run twice. Run from the repo folder."""
import re
IDX, APP, CW = 'static/index.html', 'backend/app.py', 'backend/connwhy.py'
TA, TT = 'tests/test_accounts.py', 'tests/test_trail.py'
E = [
 # --- tile: say what was saved, never look connected from a saved server name ---
 (IDX, r'''(CN[p[0]]?plT(CN[p[0]]):p[1])''', r'''(CN[p[0]]?plT(CN[p[0]]):p[1]==="MT5 bridge"?"Via your MT5 app":p[1])'''),
 (IDX, r'''CN[p[0]].status!=="rejected"?" on":""''', r'''CN[p[0]].status!=="rejected"&&CN[p[0]].kind!=="mt5"?" on":""'''),
 (IDX, r'''if(b.kind==="mt5")return"Saved";''', r'''if(b.kind==="mt5")return"Server name saved";'''),
 # --- connect popup: plain numbered steps ---
 (IDX, r'''"Tell us your broker's server name. Your MT5 password stays inside MT5, never type it here. Then make your key in the Connect MT5 card."''',
       r'''"Step 1 of 3. Type your broker's server name (you see it when you log in to MT5), for example FBS-Demo. Never type your MT5 password here. Step 2: make your key in the Connect your MT5 card. Step 3: put the key into the SpaceXBridge EA and keep MT5 open. Connected shows only once your MT5 reports in."'''),
 (IDX, r'''"Create a token in your Deriv account settings with Read and Trade scopes. Start on a virtual account."''',
       r'''"1. In your Deriv account open Settings, then API token. 2. Make a token with the Read and Trade scopes. 3. Paste it below. We check it and show your demo balance. 4. Tap Start bot. Use a demo (virtual) account first."'''),
 (IDX, r'''tst(n+(bn?" saved, not checked yet":" saved"))''', r'''tst(bn?n+" saved, not checked yet":n+" server name saved. Next: make your key in Connect your MT5.")'''),
 # --- Connect your MT5 card ---
 (IDX, r'''function head(chip) { return '<div class="card-head"><h2>Connect your MT5</h2>' + (chip || "") + "</div>"; }''',
       r'''function head(chip) { return '<div class="card-head"><h2>Connect your MT5</h2>' + (chip || "") + '</div><p class="note">For MT5 brokers only (FBS, Exness, HFM, XM, IC Markets, Pepperstone). Using Deriv? You do not need this card.</p>'; }'''),
 (IDX, r'''"Your MT5 is not reporting yet. Put the key in the EA and keep MT5 open."''', r'''"Your MT5 is not reporting yet. Put the key in the EA, turn Algo Trading on and keep MT5 open."'''),
 # --- Connection check card: a way you do not use is one calm line, not a list of failed checks ---
 (IDX, '''    h += '<p class="note">' + esc(r.headline) + "</p>";\n    if (r.state !== "ok" && r.checks && r.checks.length) {''',
       '''    h += '<p class="note">' + esc(r.state === "none" && r.id === "MT5" ? "Only needed if you trade through an MT5 broker (FBS, Exness, HFM...). Skip it if you use Deriv." : r.headline) + "</p>";\n    if (r.state === "none") { if (r.id !== "MT5" && r.fix) h += '<p class="note">' + esc(r.fix) + "</p>"; }\n    else if (r.state !== "ok" && r.checks && r.checks.length) {'''),
 (CW, r'''{'id': 'MT5', 'name': 'MT5 bridge',''', r'''{'id': 'MT5', 'name': 'MT5 app (FBS, Exness...)','''),
 # --- server words: Binance is not described as an MT5 broker ---
 (APP, r'''    if n != 'Deriv': return jsonify(error='Checking this broker is not available yet.'), 400''', r'''    if n != 'Deriv': return _not_deriv(n, 'check')'''),
 (APP, r'''    if n != 'Deriv': return jsonify(error='This broker trades through the MT5 app. Change its mode on the Connect MT5 card.'), 400''', r'''    if n != 'Deriv': return _not_deriv(n, 'switch')'''),
 (APP, r'''    if n != 'Deriv': return jsonify(error='This broker trades through the MT5 app. Use the Connect MT5 card.'), 400''', r'''    if n != 'Deriv': return _not_deriv(n, 'bot')'''),
 (APP, "@app.post('/api/brokers/<name>/verify')\n", '''def _not_deriv(n, what):
    """Plain words for 'this broker has no <what>' (what = check | switch | bot). MT5 brokers trade through the MT5 app; Binance does not trade yet."""
    if bk.CATALOG.get(n) == 'mt5': t = {'check': 'MT5 brokers are checked by your MT5 app, not here. See the Connect your MT5 card.', 'switch': 'This broker trades through the MT5 app. Change its mode on the Connect your MT5 card.', 'bot': 'This broker trades through the MT5 app. Use the Connect your MT5 card.'}[what]
    elif n == 'Binance': t = {'check': 'Checking Binance is not available yet.', 'switch': 'Binance does not trade yet, so it has no demo or real switch.', 'bot': 'Binance does not trade yet, so there is no bot to start.'}[what]
    else: t = 'Unknown broker'
    return jsonify(error=t), 400

@app.post('/api/brokers/<name>/verify')
'''),
 # --- the 2 old tests ---
 (TA, r'''T('unverified cannot start a payment', c.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': '0712345678'}, headers={'Authorization': 'Bearer z'}).status_code == 403)''',
      r'''T('unverified can still get the M-Pesa prompt (pay4: not blocked by the email check)', c.post('/api/pay/mpesa', json={'plan': 'p1', 'phone': '0712345678'}, headers={'Authorization': 'Bearer z'}).status_code not in (401, 403))
T('unverified cannot start a PayPal payment', c.post('/api/pay/paypal', json={'plan': 'p1'}, headers={'Authorization': 'Bearer z'}).status_code == 403)'''),
 (TT, 'def fake_eval(w, h, mc, rr, off):', 'def fake_eval(w, h, mc, rr, off, max_stop=3.5):'),
]
S = {}
for f, o, n in E: S.setdefault(f, open(f, encoding='utf-8').read())
if all(n in S[f] for f, o, n in E): print('already applied'); raise SystemExit
M = re.compile(r'function steps\(\) \{.*?\n  \}\n  function linked\(\) \{', re.S)
assert len(M.findall(S[IDX])) == 1, 'steps() not found exactly once'
for f, o, n in E: assert S[f].count(o) == 1 or n in S[f], 'anchor not found exactly once in %s: %s' % (f, o[:60])
STEPS = r'''function steps() {
    return '<ol class="steps"><li><div><b>Install the EA</b><span>Copy <code>SpaceXBridge.mq5</code> into <code>MQL5/Experts</code> in MT5, then compile it.</span></div></li>' +
      '<li><div><b>Allow the address</b><span>In MT5 open Tools, Options, Expert Advisors, tick Allow WebRequest and add <code>' + esc(location.origin) + "</code> (no slash at the end).</span></div></li>" +
      '<li><div><b>Attach it and paste your key</b><span>Drag SpaceXBridge onto the XAUUSD chart. Press F7 and set <code>ServerUrl</code> to <code>' + esc(location.origin) + '</code> and <code>EAKey</code> to your key. Keep <code>AllowLive</code> off while you practise.</span></div></li>' +
      "<li><div><b>Turn Algo Trading on</b><span>The Algo Trading button at the top of MT5 must be green.</span></div></li>" +
      "<li><div><b>Keep MT5 open</b><span>MT5 must stay running on a PC or VPS. This page is the remote control. It shows MT5 online within 2 minutes.</span></div></li></ol>";
  }
  function linked() {'''
S[IDX] = M.sub(lambda m: STEPS, S[IDX])
for f, o, n in E:
    if o in S[f]: S[f] = S[f].replace(o, n)
for f, t in S.items(): open(f, 'w', encoding='utf-8').write(t)
print('done:', len(E), 'edits + steps()')
