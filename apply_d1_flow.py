"""D1: Deriv flow fixes (found by reading the code against Deriv's own docs). Run from the repo folder: python apply_d1_flow.py (safe to run twice).
1) Only DERIV_CLIENT_ID set (the OAuth app id): Log in with Deriv worked but the token check and the bot said "not switched on", because the code wanted DERIV_APP_ID.
   Now either variable switches Deriv on. The Deriv-App-ID header is sent only when DERIV_APP_ID itself is set (Deriv's docs need it for personal tokens only).
2) The Deriv login lasts about 30 days and has no refresh. When it ended the bot tile said "error" and the app asked Deriv again every minute.
   Now: status becomes rejected, the bot is switched off, the tile says "Your Deriv login ended...", and the person gets one alert a day.
Edits: backend/deriv.py, backend/brokers.py, backend/app.py, backend/connwhy.py, backend/envcheck.py."""
import sys


def rd(p):
    return open(p, encoding='utf-8').read()


def wr(p, s):
    open(p, 'w', encoding='utf-8').write(s)


def edit(path, old, new, marker):
    s = rd(path)
    if marker in s:
        print('skip (already there):', path, '->', marker[:40])
        return
    if s.count(old) != 1:
        print('STOP: cannot find exactly once in', path, '->', old[:70])
        sys.exit(1)
    wr(path, s.replace(old, new, 1))
    print('edited', path, '->', marker[:40])


D = 'backend/deriv.py'
edit(D, "APP = lambda: os.getenv('DERIV_APP_ID', '').strip()\n",
     "APP = lambda: os.getenv('DERIV_APP_ID', '').strip()\nCID = lambda: os.getenv('DERIV_CLIENT_ID', '').strip()          # D1: the OAuth app id; Log in with Deriv may use it alone\nON = lambda: bool(APP() or CID())          # D1: Deriv is switched on when either one is set\n",
     'ON = lambda: bool(APP() or CID())')
edit(D, "headers={'Authorization': 'Bearer ' + token, 'Deriv-App-ID': APP(), 'Accept': 'application/json'})",
     "headers=dict({'Authorization': 'Bearer ' + token, 'Accept': 'application/json'}, **({'Deriv-App-ID': APP()} if APP() else {})))",
     "**({'Deriv-App-ID': APP()} if APP() else {})")
edit(D, "    if not APP(): return False, 'Deriv trading is not switched on yet. Please try again soon.'",
     "    if not ON(): return False, 'Deriv trading is not switched on yet. Please try again soon.'", "if not ON(): return False, 'Deriv trading")
edit(D, "    if not APP(): return False\n    r = st.q(", "    if not ON(): return False\n    r = st.q(", "    if not ON(): return False\n")
edit(D, "    if not APP(): return 'off'", "    if not ON(): return 'off'", "if not ON(): return 'off'")
edit(D, "def _pick(accts, want_real):\n    return next((a for a in accts if a['demo'] != want_real), None)\n",
     "def _pick(accts, want_real):\n    return next((a for a in accts if a['demo'] != want_real), None)\n\n"
     "def _login_ended(uid, now):\n"
     "    \"\"\"D1: Deriv refused the saved login (it lasts about 30 days, no refresh). Stop asking every minute: mark it, switch the bot off, tell the person once a day.\"\"\"\n"
     "    _mark(uid, 'rejected'); bk.set_bot(uid, 'Deriv', False)\n"
     "    try: sbauth.notify('Deriv login ended', 'Tap Log in with Deriv on the Connect tab, then Start bot.', key='dend%s-%d' % (uid, int(now) // 86400), only=uid)\n"
     "    except Exception: pass\n"
     "    return 'login ended'\n",
     'def _login_ended(uid, now):')
edit(D, "    real = bk.mode(uid, 'Deriv') == 'real'\n    acct = _pick(accounts(sec['token'], http), real)\n",
     "    real = bk.mode(uid, 'Deriv') == 'real'\n    try: accts = accounts(sec['token'], http)\n    except PermissionError: return _login_ended(uid, now)\n    acct = _pick(accts, real)\n",
     'except PermissionError: return _login_ended(uid, now)')

edit('backend/brokers.py', "    'no demo account':",
     "    'login ended': 'Your Deriv login ended. Tap Log in with Deriv on the Connect tab, then Start bot.',\n    'no demo account':", "'login ended':")
edit('backend/app.py', "    if not deriv.APP(): bad.append('DERIV_APP_ID is missing. The Deriv bot cannot trade for anyone.')",
     "    if not deriv.ON(): bad.append('DERIV_APP_ID (or DERIV_CLIENT_ID) is missing. The Deriv bot cannot trade for anyone.')", 'if not deriv.ON(): bad.append')
edit('backend/connwhy.py', "    app, vault = bool(deriv.APP()), bk.ready()", "    app, vault = bool(deriv.ON()), bk.ready()", 'bool(deriv.ON())')
edit('backend/envcheck.py', "    need(G, 'DERIV_APP_ID', 'Not set. The Deriv bot cannot trade for anyone.')",
     "    if _g(e, 'DERIV_CLIENT_ID') and not _g(e, 'DERIV_APP_ID'): add(G, 'DERIV_CLIENT_ID', 'ok', 'Set. Used for Log in with Deriv and the Deriv bot.')\n"
     "    else: need(G, 'DERIV_APP_ID', 'Not set. The Deriv bot cannot trade for anyone.')", "add(G, 'DERIV_CLIENT_ID', 'ok'")

H = 'docs/HANDOFF.md'
s = rd(H)
if '## Section D1 ' in s:
    print('skip (already there): HANDOFF D1')
else:
    wr(H, s.rstrip('\n') + """

## Section D1 (Deriv flow check: DERIV_CLIENT_ID alone, ended login) DONE (Nov 22)
- Checked against Deriv's docs (developers.deriv.com): auth.deriv.com/oauth2/auth + /token, PKCE S256, no client secret, no refresh token, expires_in 30 days, exact redirect match, https, accounts GET and OTP POST on api.derivws.com (reply is data.url). The code already matched all of that.
- Fixed: (1) only DERIV_CLIENT_ID set -> login worked but the check and the bot said "not switched on". deriv.ON() = DERIV_APP_ID or DERIV_CLIENT_ID; the Deriv-App-ID header is sent only when DERIV_APP_ID is set (Deriv's docs need it for personal tokens only). (2) ended login (401): status becomes rejected, the bot is switched off, the tile says "Your Deriv login ended...", one alert a day (key dend<uid>-<day>), and the minute loop stops asking Deriv.
- Files: apply_d1_flow.py (edits deriv.py, brokers.py, app.py, connwhy.py, envcheck.py), tests/test_d1flow.py (16 checks), tools/deriv_probe.py (read-only: run once with your token; prints the real account, candle, symbol and quote shapes, never buys).
- NOT confirmed yet (Deriv's docs do not show them): the field names inside an account, candle requests (ticks_history style candles, granularity), gold symbol spelling (frxXAUUSD), MULTUP with limit_order on gold. deriv_probe.py answers these; a real login also needs the callback address registered at Deriv and BASE_URL on Render.
- Next: D2 (Deriv MT5 as a broker next to FBS), D3 (running positions), D4 (several accounts), D5 (bot switching), D6 (tests and deploy).
""")
    print('edited', H)
print('done: D1 Deriv flow fixes in place. Now run: python tests/test_d1flow.py')
