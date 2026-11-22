"""LIVE2: the live 'Bot running' notification follows Deriv too, and can say why it is not showing.
Bug: for the owner, live.snapshot only looked at the MT5 EA (uid ''), so a bot running on Deriv counted as OFF and the notification was hidden / removed.
Fix: the person's numbers and 'bot running' come from livestats (Deriv + MT5 together, same as the Home card). Running = a connected account answered recently AND that
account's own bot switch is on (Deriv switch for Deriv, MT5 switch for the EA). Adds GET /api/live/why (plain words) and a 'Not showing? Check' button under the switch.
Nothing removed. Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
L = 'backend/live.py'
edit(L, "from . import store as st, push, links\n", "from . import store as st, push, links, livestats\n", "push, links, livestats")
edit(L, """def snapshot(now=None, uid=''):
    now = now or time.time(); a = st.acct(uid)
    on = links.bot_on(uid) and now - a.get('seen', 0) < 120
    t = st.q("SELECT COUNT(*) n, COALESCE(SUM(pnl),0) pnl FROM signals WHERE created>=? AND COALESCE(uid,'')=?", (st.day_start(), uid), True) or {}
    opn = st.q("SELECT symbol,side,fill,entry FROM signals WHERE status='open' AND COALESCE(uid,'')=? ORDER BY id DESC LIMIT 6", (uid,)) or []
    return {'on': on, 'a': a, 'today': t.get('pnl') or 0, 'open': list(opn), 'now': now}
""", """def _admins(): return {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}

def _is_admin(uid):
    r = st.q('SELECT email FROM users WHERE uid=?', (uid,), True) or {}
    return (r.get('email') or '').lower() in _admins()

def _running(uid, admin, srcs):
    \"\"\"LIVE2: the bot counts as running when a connected account answered recently AND that account's own switch is on:
    Deriv -> the Deriv switch, MT5 -> the MT5 switch (the owner's EA switch for admins). Before, only the MT5 EA was looked at.\"\"\"
    from . import deriv
    for s in srcs:
        if not s.get('online'): continue
        if s['id'] == 'Deriv' and deriv._bot(uid): return True
        if s['id'] == 'MT5' and links.bot_on('' if admin else uid): return True
    return False

def snapshot(now=None, uid=''):
    now = now or time.time(); admin = _is_admin(uid)
    ls = livestats.snapshot(uid, admin, now); srcs = ls.get('sources') or []
    a = {'balance': ls['balance'], 'equity': ls['equity'], 'open': ls['open']} if srcs else {}
    return {'on': _running(uid, admin, srcs), 'a': a, 'today': ls['today'], 'open': list(ls.get('trades') or []), 'now': now}

def explain(uid, now=None):
    \"\"\"LIVE2: (ok, plain words) for the person: is the notification being sent to their phone, and if not, the first thing to fix.\"\"\"
    now = now or time.time()
    if os.getenv('LIVE_NOTIF', '1') == '0': return False, 'The server has LIVE_NOTIF set to 0 on Render. Remove it, or set it to 1.'
    if not push.configured(): return False, 'Phone alerts are not set up on the server: FCM_SERVICE_ACCOUNT is missing on Render.'
    r = st.q('SELECT email,plan_until pu,notif FROM users WHERE uid=?', (uid,), True) or {}
    admin = (r.get('email') or '').lower() in _admins()
    if not push.tokens(uid): return False, 'No phone has registered for alerts yet. Open the Android app while signed in and allow notifications.'
    if not (admin or (r.get('pu') or 0) > now): return False, 'Your plan has ended, so live status is paused.'
    try: pref = json.loads(r.get('notif') or '{}').get('live', 1) not in (0, False, '0')
    except ValueError: pref = True
    if not pref: return False, 'The Live bot status switch is off in Profile, Notifications.'
    if not snapshot(now, uid)['on']: return False, 'The bot is not running, or no account has answered in the last 2 to 3 minutes. Start the bot and keep Deriv or the MT5 EA connected.'
    return True, 'Everything is in place. It appears within a minute. If it does not, allow notifications for this app in your phone settings.'
""", "def explain(uid, now=None)")
edit(L, """        sc = '' if admin else uid; s = snaps.get(sc) or snaps.setdefault(sc, snapshot(now, sc))""",
        """        s = snaps.get(uid) or snaps.setdefault(uid, snapshot(now, uid))          # LIVE2: one look per person (the owner's Deriv counts too)""", "one look per person")
edit(L, "str(o['side']).upper() + ' ' + str(o['symbol']) + ' at ' + str(o.get('fill') or o.get('entry') or '--')", "str(o['side']).upper() + ' ' + str(o['symbol']) + ' at ' + str(o.get('fill') or o.get('entry') or o.get('price') or '--')", "o.get('price')")
P = 'backend/app.py'
edit(P, "@app.get('/api/groupcap')", "@app.get('/api/live/why')          # LIVE2: why is the phone notification not showing\n@need(verified=True)\ndef live_why(u):\n    from . import live\n    ok, why = live.explain(u['uid']); return jsonify(ok=ok, why=why)\n\n@app.get('/api/groupcap')", "def live_why(u)")
I = 'static/index.html'
edit(I, "n.live==null?1:n.live)+'</div>'+", "n.live==null?1:n.live)+'<div class=\"pfr\"><div><b>Not showing?</b><span>Find out why the live notification is missing.</span></div><button type=\"button\" class=\"btn\" id=\"liveWhy\" style=\"padding:9px 14px\">Check</button></div></div>'+", 'id="liveWhy"')
J = 'static/live.js'
s = open(J, encoding='utf-8').read()
if 'LIVE2-start' in s: print(J, ': already ok')
else:
    open(J, 'a', encoding='utf-8').write("""
/*LIVE2-start*/
(function () {
  "use strict";
  if (typeof document === "undefined" || !document || !document.addEventListener) return;
  document.addEventListener("click", function (e) {
    var b = e.target && e.target.closest ? e.target.closest("#liveWhy") : null; if (!b || !window.SXA) return;
    b.disabled = true;
    SXA.api("/api/live/why").then(function (j) { if (window.sxToast) window.sxToast((j && j.why) || "No answer."); }, function () { if (window.sxToast) window.sxToast("Cannot reach the server."); }).then(function () { b.disabled = false; });
  });
})();
/*LIVE2-end*/
""")
    print(J, ': appended')
H = 'docs/HANDOFF.md'
s = open(H, encoding='utf-8').read()
if '## Section LIVE2' in s: print(H, ': already ok')
else:
    open(H, 'a', encoding='utf-8').write("""

## Section LIVE2 (live 'Bot running' notification follows Deriv) DONE (Nov 22)
- Bug: backend/live.py snapshot() read only the owner's MT5 EA (st.acct(''), links.bot_on('')), so for the owner a bot running on Deriv counted as OFF and the notification was hidden. Now snapshot(now, uid) uses livestats.snapshot (Deriv + MT5 together, same numbers as the Home card) and running = a source is online AND its own switch is on (deriv._bot for Deriv, links.bot_on for MT5). tick() looks once per person (no shared owner snapshot).
- live.explain(uid) + GET /api/live/why -> {ok, why} in plain words (LIVE_NOTIF=0, no FCM_SERVICE_ACCOUNT, no phone registered, plan ended, switch off, bot not running / nothing answered, or all fine). Profile > Notifications has a 'Not showing? Check' row (static/live.js block /*LIVE2-start*/). tests/test_live2.py.
- Still true: Render FREE sleeps after 15 min idle and the sender is a timer inside the server, so the notification disappears (6 min timeout on the phone) while the server sleeps. A ping every 10 minutes (UptimeRobot) keeps it awake.
""")
    print(H, ': appended')
