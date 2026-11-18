"""N1b apply script: fixes the phone-alert delivery path (Android foreground banner, live.js push fallback, per-trade tags,
owner trades to admins only, admin Send test alert button, env/README/HANDOFF). Edits only; the new test file is tests/test_push2.py (copy it in first).
Each old text must appear exactly once or NOTHING is changed. Safe to run twice. Files are written atomically. Then every test file runs and the result is printed.
Run from the repo folder:  python apply_n1b.py"""
import os, sys, re, subprocess, hashlib
ROOT = os.path.dirname(os.path.abspath(__file__))
HUNKS = {'.env.example': [('--- test',
                   '--- Phone alerts (Firebase Cloud Messaging). Full steps: README "Phone alerts" ---\n'
                   'FCM_SERVICE_ACCOUNT=         # Firebase > Project settings > Service accounts > Generate new private key. Paste the whole JSON on ONE line (or its base64). SECRET. Empty = no '
                   'phone alert is sent\n'
                   'PUBLIC_URL=https://your-service.onrender.com   # public address of this server; the alert pictures load from {PUBLIC_URL}/notif/<name>.png\n'
                   'PUSH_DAILY_CAP=12            # most alerts one person gets per day (risk and billing alerts ignore the cap). N2 raises the default to 30\n'
                   '# GOOGLE_SERVICES_JSON_BASE64 is NOT a Render variable. It is a GitHub secret (repo > Settings > Secrets and variables > Actions) used by the Android build:\n'
                   '#   base64 -w0 google-services.json    -> paste the output as the secret. Without it the APK is built without phone alerts.\n'
                   '# --- test')],
 'README.md': [('\n## Know',
                '\n'
                '## Phone alerts (Firebase)\n'
                'Alerts reach the Android app even when it is closed. Three things must all be in place, or nothing arrives:\n'
                '1. **Render:** variable `FCM_SERVICE_ACCOUNT` = the Firebase service-account JSON (Firebase console > Project settings > Service accounts > Generate new private key; paste the '
                "file's text, or its base64). Also set `PUBLIC_URL` to your server address (alert pictures load from it). Optional `PUSH_DAILY_CAP` (alerts per person per day, default 12).\n"
                '2. **GitHub:** repository secret `GOOGLE_SERVICES_JSON_BASE64` = `base64 -w0 google-services.json` (Firebase > Project settings > Your apps > Android, package `com.spacexbot.app`). '
                'It is a GitHub secret, not a Render variable. Then run the Android build again: an APK built without it has no phone alerts.\n'
                '3. **Phone:** install that APK, sign in, tap Allow on the notification question.\n'
                'Check it: sign in as admin, open `#admin`, press **Send test alert**. It reports how many phones it reached, or why not. It works with the app open or closed.\n'
                "- Who gets what: the owner's own trades (opened, take-profit, stop-loss, closed, skipped) go to the admins' phones only. A subscriber gets alerts for the trades of their own EA key, "
                'and phone-mode signals (kind 7).\n'
                '- Free Render sleeps after 15 minutes without a request. Alerts that fire on a timer need the server awake: ping `/healthz` every 10 minutes from a free uptime monitor, or use a '
                'paid plan.\n'
                '- Tests: `python tests/test_push1.py` (phone side), `python tests/test_push2.py` (delivery path).\n'
                '\n'
                '## Know')],
 'android-wrapper/native/LiveMessagingService.java': [('per).\n *', 'per); while the app is open they are also drawn here (N1b).\n *'),
                                                      ('super.onMessageReceived(message',
                                                       '/* N1b: Android calls this for a notification message ONLY while the app is open (closed or in the background it draws the banner itself).\n'
                                                       "           Capacitor's service draws nothing, so without this the person saw no alert while the app was open. */\n"
                                                       '        try { showForeground(message); } catch (Exception ignored) { }\n'
                                                       '        super.onMessageReceived(message);   // still tell the page (pushNotificationReceived)\n'
                                                       '    }\n'
                                                       '\n'
                                                       '    static final String CH_HIGH = "sxb_high";\n'
                                                       '    static final String CH_LOW = "sxb_low";\n'
                                                       '    static final int ALERT_ID = 7100;\n'
                                                       '\n'
                                                       '    /** Same channel as the server asked for, small icon ic_stat_sxb, tap opens the app carrying the message data (route, kind, tag...). */\n'
                                                       '    private void showForeground(RemoteMessage message) {\n'
                                                       '        RemoteMessage.Notification n = message.getNotification();\n'
                                                       '        if (n == null) return;                                   // data-only message: nothing to show\n'
                                                       '        Map<String, String> d = message.getData();\n'
                                                       '        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);\n'
                                                       '        if (nm == null) return;\n'
                                                       '\n'
                                                       '        String channel = n.getChannelId();\n'
                                                       '        if (channel == null || channel.isEmpty()) channel = CH_HIGH;\n'
                                                       '        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && nm.getNotificationChannel(channel) == null) {\n'
                                                       '            boolean low = CH_LOW.equals(channel);\n'
                                                       '            NotificationChannel ch = new NotificationChannel(channel, low ? "Reports and tips" : "Trades and alerts",\n'
                                                       '                    low ? NotificationManager.IMPORTANCE_LOW : NotificationManager.IMPORTANCE_HIGH);\n'
                                                       '            nm.createNotificationChannel(ch);\n'
                                                       '        }\n'
                                                       '\n'
                                                       '        int icon = getResources().getIdentifier("ic_stat_sxb", "drawable", getPackageName());\n'
                                                       '        if (icon == 0) icon = android.R.drawable.ic_dialog_info;\n'
                                                       '\n'
                                                       '        String tag = n.getTag();\n'
                                                       '        if ((tag == null || tag.isEmpty()) && d != null) tag = d.get("tag");\n'
                                                       '\n'
                                                       '        PendingIntent pi = null;\n'
                                                       '        Intent open = getPackageManager().getLaunchIntentForPackage(getPackageName());\n'
                                                       '        if (open != null) {\n'
                                                       '            open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);\n'
                                                       '            // Capacitor\'s push plugin fires "tap" only when this key is present; the rest is the data the page reads (route).\n'
                                                       '            String mid = message.getMessageId();\n'
                                                       '            open.putExtra("google.message_id", mid == null ? String.valueOf(System.currentTimeMillis()) : mid);\n'
                                                       '            if (d != null) for (Map.Entry<String, String> e : d.entrySet()) open.putExtra(e.getKey(), e.getValue());\n'
                                                       '            int req = (int) (System.currentTimeMillis() & 0x7fffffff);   // unique, so an older alert keeps its own data\n'
                                                       '            pi = PendingIntent.getActivity(this, req, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);\n'
                                                       '        }\n'
                                                       '\n'
                                                       '        String title = n.getTitle() == null ? "spaceXBot" : n.getTitle();\n'
                                                       '        String body = n.getBody() == null ? "" : n.getBody();\n'
                                                       '        NotificationCompat.Builder b = new NotificationCompat.Builder(this, channel)\n'
                                                       '                .setSmallIcon(icon)\n'
                                                       '                .setContentTitle(title)\n'
                                                       '                .setContentText(body)\n'
                                                       '                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))\n'
                                                       '                .setAutoCancel(true)\n'
                                                       '                .setPriority(CH_LOW.equals(channel) ? NotificationCompat.PRIORITY_LOW : NotificationCompat.PRIORITY_HIGH);\n'
                                                       '        if (pi != null) b.setContentIntent(pi);\n'
                                                       '        if (tag != null && !tag.isEmpty()) nm.notify(tag, ALERT_ID, b.build());   // same tag = replaces, like the background banner\n'
                                                       '        else nm.notify((int) (System.currentTimeMillis() & 0x7ffffff), b.build()')],
 'backend/app.py': [('one\n    try: sid',
                     'one\n'
                     "    aud = {'only': who} if who else {'admins': True}      # a subscriber's own EA: only that person. The OWNER's EA: only the admins' phones (subscribers get the signal alert, "
                     "kind 7, and their own EA's results)\n"
                     '    try: sid'),
                    ('only=only)\n'
                     "            else: push.notify({'tp': 2, 'sl': 3}.get(str(d.get('reason')), 4), f'sig{sid}-closed', sym=s['symbol'], pnl=s['pnl'], only=only)\n"
                     "    if stt == 'rejected': push.notify(8, f'sig{sid}-skipped', sym=(st.q('SELECT symbol FROM signals WHERE id=?', (sid,), True) or {}).get('symbol', ''), "
                     "reason=str(d.get('reason') or '')[:80], only=only",
                     '**aud)\n'
                     "            else: push.notify({'tp': 2, 'sl': 3}.get(str(d.get('reason')), 4), f'sig{sid}-closed', sym=s['symbol'], pnl=s['pnl'], **aud)\n"
                     "    if stt == 'rejected': push.notify(8, f'sig{sid}-skipped', sym=(st.q('SELECT symbol FROM signals WHERE id=?', (sid,), True) or {}).get('symbol', ''), "
                     "reason=str(d.get('reason') or '')[:80], **aud"),
                    ("'FCM_SERVICE_ACCOUNT is not set on the server'), 400\n"
                     "    n, why = push.send(u['uid'], 1, 'Test notification. If you can read this, phone alerts work.', title='spaceXBot test', force=True)\n"
                     "    return jsonify(sent=n, reason=why, devices=len(push.tokens(u['uid']))) if n else (jsonify(error=why or 'not sent', devices=len(push.tokens(u['uid']))",
                     "push.explain('FCM not configured'), devices=0), 400\n"
                     "    n, why = push.send(u['uid'], 1, 'Test notification. If you can read this, phone alerts work.', title='spaceXBot test', force=True)\n"
                     "    dev = len(push.tokens(u['uid']))\n"
                     '    return jsonify(sent=n, reason=why, devices=dev) if n else (jsonify(error=push.explain(why), devices=dev')],
 'backend/push.py': [('0))\n_T =', "0))\nTRADE_TAG_KINDS = {1, 2, 3, 4, 7, 8}         # the banner's tag carries the trade id, so two trades never replace each other\n_T ="),
                     ('])\n\n# --',
                      '])\n'
                      '\n'
                      'def tag_for(kind, key=None):\n'
                      '    """Android replaces a banner that has the same tag. Trade kinds carry the trade id (key \'sig12-open\', without the \'/<uid>\' that broadcast adds), others share one tag '
                      'per kind."""\n'
                      "    if kind in TRADE_TAG_KINDS and key: return ('k%s-%s' % (kind, str(key).split('/')[0]))[:60]\n"
                      "    return 'k%s' % kind\n"
                      '\n'
                      '# --'),
                     ("('k%s-%s' % (kind, key[:40])) if kind == 7 and key else 'k%s' % kind", 'tag_for(kind, key)'),
                     ('def recipients():\n'
                      '    """Subscribers and admins that have a phone registered."""\n'
                      "    admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}; now = time.time(); out = []\n"
                      "    for r in st.q('SELECT DISTINCT u.uid AS uid,u.email AS email,u.plan_until AS pu FROM users u JOIN push_tokens t ON t.uid=u.uid'):\n"
                      "        if (r['pu'] or 0) > now or (r['email'] or '').lower() in admins: out.append(r['uid'])\n"
                      '    return out\n'
                      '\n'
                      'def broadcast(kind, body, title=None, key=None, img=None, only=None):\n'
                      '    """Send in the background so a trade route is never slowed down. Returns immediately."""\n'
                      '    if not configured(): return\n'
                      '    def run():\n'
                      '        for uid in recipients(',
                      "WHY = {'no device': 'No phone is registered for your account. Open the app on your phone, sign in as admin, allow notifications, then try again.',\n"
                      "       'FCM not configured': 'The server has no FCM_SERVICE_ACCOUNT yet, so it cannot send phone alerts.',\n"
                      "       'category off': 'Trade alerts are switched off in your alert settings.'}\n"
                      'def explain(why):\n'
                      '    """A reason code from send() in plain words for the admin screen."""\n'
                      "    return WHY.get(why) or ('Not sent: %s' % why if why else 'Not sent.')\n"
                      '\n'
                      'def recipients(admins_only=False):\n'
                      '    """Subscribers and admins that have a phone registered. admins_only: just the admins (ADMIN_EMAILS)."""\n'
                      "    admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}; now = time.time(); out = []\n"
                      "    for r in st.q('SELECT DISTINCT u.uid AS uid,u.email AS email,u.plan_until AS pu FROM users u JOIN push_tokens t ON t.uid=u.uid'):\n"
                      "        is_admin = (r['email'] or '').lower() in admins\n"
                      "        if is_admin or (not admins_only and (r['pu'] or 0) > now): out.append(r['uid'])\n"
                      '    return out\n'
                      '\n'
                      'def broadcast(kind, body, title=None, key=None, img=None, only=None, admins=False):\n'
                      '    """Send in the background so a trade route is never slowed down. Returns immediately. only = one person; admins = admins only; neither = every subscriber."""\n'
                      '    if not configured(): return\n'
                      '    def run():\n'
                      '        for uid in recipients(admins'),
                     ('t, b, i = compose(kind, **facts); broadcast(kind, b, t, key, i, only',
                      "admins = bool(facts.pop('admins', False)); t, b, i = compose(kind, **facts); broadcast(kind, b, t, key, i, only, admins")],
 'docs/HANDOFF.md': [(')\n'
                      '- N1  DONE (static/live.js, code between /*N1-start*/ and /*N1-end*/: the Android app asks for notification permission, gets its Firebase token, POSTs /api/push/token, '
                      'unregisters on sign-out, tap opens the right screen; tests/test_push1.py). Before N1 nothing ever sent the token, so no push could reach a phone. Needs google-services.json in '
                      'the APK build and FCM_SERVICE_ACCOUNT on Render.\n'
                      '- N2  backend/alerts.py: one background loop for timed alerts, daily cap raised (PUSH_DAILY_CAP default 12 -> 30), quiet hours adjustable, admin "send test alert" button.\n'
                      '- N3  billing alerts: kinds 38-41 from payments, 42/43/44 plan ends in 3 days / tomorrow / ended.\n'
                      '- N4  trade + risk alerts: new signal to every subscriber (kind 7/1), 9, 10, and 11-18 from the risk gates.\n'
                      '- N5  market alerts: 19-25 (news soon, news lock, session opening, large gold move, market closed, spread).\n'
                      '- N6  system, daily, tips: 26-31, 32-37 reports, 45-49 nudges, 50 security',
                      '; DO THESE BEFORE 4C)\n'
                      'Audit: only kinds 1,2,3,4,7,8 have a trigger today (44 of the 50 in backend/push.py are never sent).\n'
                      'Rule for every alerts section: add a test that sends the kind through a FAKE FCM and checks the payload (title, body, channel_id, tag, data.kind/route). Copy the fake from '
                      'tests/test_push2.py (push.requests, push._account, push._access_token, a synchronous push.threading shim, push.quiet_now). Mutation-check as usual.\n'
                      '- N1  DONE (static/live.js, code between /*N1-start*/ and /*N1-end*/: the Android app asks for notification permission, gets its Firebase token, POSTs /api/push/token, '
                      'unregisters on sign-out, tap opens the right screen; tests/test_push1.py). Before N1 nothing ever sent the token, so no push could reach a phone. Needs google-services.json in '
                      'the APK build and FCM_SERVICE_ACCOUNT on Render.\n'
                      '- N1b DONE (delivery path; tests/test_push2.py, 50 checks): (1) android-wrapper/native/LiveMessagingService.java draws the banner itself while the app is open (same channel, '
                      "ic_stat_sxb, tap opens the app with the data extras + google.message_id so the page's tap listener fires); (2) static/live.js pushPlug() falls back to Capacitor.nativePromise "
                      '+ Capacitor.addListener and saves a short reason to localStorage sxb_pt_why (SXA.push.why()), cleared when a token is saved; (3) push.tag_for(): kinds 1-4, 7, 8 get tag '
                      'k<kind>-<key> (trade id) so two trades never replace each other; (4) DECISION (user said "decide"): the OWNER\'s EA trades (open, TP, SL, closed, skipped) go to ADMIN phones '
                      "only (push.notify(..., admins=True), push.recipients(admins_only)); a subscriber's own EA key still goes to that subscriber only; kind 7 (phone-mode signal) still goes to "
                      'subscribers. Email (sbauth.notify) was NOT changed and still goes to everyone; (5) admin panel "Phone alerts" card, code between /*N1b-start*/ and /*N1b-end*/, POST '
                      '/api/admin/push/test with plain-word errors (push.explain); (6) FCM_SERVICE_ACCOUNT, PUBLIC_URL, PUSH_DAILY_CAP, GOOGLE_SERVICES_JSON_BASE64 in .env.example and README "Phone '
                      'alerts". tests/test_all.py \'trade alerts are per user\' now asserts the owner push is admins-only. The Java service is compiled and run against recording stubs by '
                      'test_push2.py (needs javac, skipped without); a real APK build and a real phone test are still needed.\n'
                      '- N2  backend/alerts.py: one background loop for timed alerts, daily cap raised (PUSH_DAILY_CAP default 12 -> 30), quiet hours adjustable (setting in the app, default 22-06 '
                      'EAT), TP/SL/closed alerts (kinds 2,3,4) go through quiet hours. The admin test button is DONE (N1b). Render FREE SLEEPS after 15 min idle, so a timer loop only runs while the '
                      'server is awake: ping /healthz every ~10 min from a free uptime monitor, or use a paid plan (say this in the README).\n'
                      '- N3  billing alerts: kinds 38-41 from payments (hook: payments.activate()), 42/43/44 plan ends in 3 days / tomorrow / ended.\n'
                      '- N4  trade + risk alerts: new signal to every subscriber (kind 7/1), 9, 10, and 11-18 from the risk gates. Hooks: risk.global_gate / risk.symbol_gate already RETURN a reason '
                      'but never push; add the push at the call site in app._scan (one per reason per day, not per scan). Kinds 5 (breakeven), 6 (partial close) and 9 (pending order) need the EA '
                      '(ea/SpaceXBridge.mq5) to report them: add new status values to /api/ea/report (be, partial, pending) and the MQL5 side; until then they cannot fire.\n'
                      '- N5  market alerts: 19-25 (news soon, news lock, session opening, large gold move, market closed, spread).\n'
                      '- N6  system, daily, tips: 26-31, 32-37 reports, 45-49 nudges, 50 security.\n'
                      "- Owner trades now reach admin phones only (see N1b); remember this when N4 adds 'new signal to every subscriber'")],
 'static/index.html': [(' 0">Stra',
                        ' 0">Phone alerts</h3><p class="note">Sends one test alert to the phones signed in as you. It ignores quiet hours and the daily limit.</p><div '
                        'style="display:flex;gap:8px"><button class="btn primary" id="pnTest">Send test alert</button></div><p class="note" id="pnMsg" role="status"></p>\'+\n'
                        ' \'<h3 style="margin:8px 0 0">Stra'),
                       ('his)};\n var SUBS',
                        'his)};\n'
                        ' /*N1b-start*/\n'
                        ' $("#pnTest").onclick=function(){var b=this,m=$("#pnMsg");b.disabled=true;m.textContent="Sending...";\n'
                        '  SXA.api("/api/admin/push/test",{method:"POST"}).then(function(r){m.textContent="Sent to "+r.sent+(r.sent===1?" phone":" phones")+". Look at your phone (the app open or '
                        'closed).";tst("Test alert sent")}).catch(function(e){var w=SXA.push&&SXA.push.why?SXA.push.why():"";m.textContent=(e.message||"Not sent")+(w?" Phone says: "+w:"");tst("Test '
                        'alert not sent")}).then(function(){b.disabled=false})};\n'
                        ' /*N1b-end*/\n'
                        ' var SUBS')],
 'static/live.js': [('return (c.Plugins && c.Plugins.PushNotifications) || null;\n'
                     '  }\n'
                     '  function pushToken(t) {\n'
                     '    if (!t || !ME || ME.offline) return Promise.resolve();\n'
                     '    var key = ME.uid + ":" + t; if (PT.sent === key) return Promise.resolve();\n'
                     '    PT.sent = key;\n'
                     '    return api("/api/push/token", { method: "POST", body: { token: t, platform: "android" } }).then(function () { try { localStorage.setItem("sxb_pt", t',
                     'if (c.Plugins && c.Plugins.PushNotifications) return c.Plugins.PushNotifications;\n'
                     '    /* sxb-push-fallback: a remote page may get only the native bridge (no registerPlugin), like the Google sign-in above */\n'
                     '    if (c.nativePromise && c.addListener) {\n'
                     '      var call = function (m) { return function (o) { return c.nativePromise("PushNotifications", m, o || {}); }; };\n'
                     '      return { checkPermissions: call("checkPermissions"), requestPermissions: call("requestPermissions"), register: call("register"),\n'
                     '               addListener: function (ev, fn) { return c.addListener("PushNotifications", ev, fn); } };\n'
                     '    }\n'
                     '    return null;\n'
                     '  }\n'
                     '  /* A short reason the phone alerts did not start, kept on the phone so the admin test button can show it. */\n'
                     '  function pushWhy(m) { try { localStorage.setItem("sxb_pt_why", String(m).slice(0, 200) + " @ " + new Date().toISOString()); } catch (x) {} }\n'
                     '  function pushToken(t) {\n'
                     '    if (!t || !ME || ME.offline) return Promise.resolve();\n'
                     '    var key = ME.uid + ":" + t; if (PT.sent === key) return Promise.resolve();\n'
                     '    PT.sent = key;\n'
                     '    return api("/api/push/token", { method: "POST", body: { token: t, platform: "android" } }).then(function () { try { localStorage.setItem("sxb_pt", t); '
                     'localStorage.removeItem("sxb_pt_why"'),
                    (' if (!P) return; PT.started = true; PT.plug = P;\n'
                     '    try {\n'
                     '      P.addListener("registration", function (t) { PT.tok = (t && t.value) || ""; pushToken(PT.tok); });\n'
                     '      P.addListener("registrationError", function () {',
                     '\n'
                     '    if (!P) { var c = window.Capacitor; pushWhy("no push plugin (Capacitor " + (c ? "found, keys " + Object.keys(c).slice(0, 12).join("/") : "missing") + ")"); return; }\n'
                     '    PT.started = true; PT.plug = P;\n'
                     '    try {\n'
                     '      P.addListener("registration", function (t) { PT.tok = (t && t.value) || ""; pushToken(PT.tok); });\n'
                     '      P.addListener("registrationError", function (e) { pushWhy("registration error: " + ((e && (e.error || e.message)) || "unknown")); '),
                    ('if (window.sxToast) window.sxToast("Allow notifications in your phone settings to get trade alerts.");\n    }).catch(function () {',
                     'pushWhy("notification permission " + ((r && r.receive) || "unknown"));\n'
                     '      if (window.sxToast) window.sxToast("Allow notifications in your phone settings to get trade alerts.");\n'
                     '    }).catch(function (e) { pushWhy("push start failed: " + ((e && (e.code || e.message)) || "unknown")); '),
                    ('oute },\n', 'oute, why: function () { try { return localStorage.getItem("sxb_pt_why") || ""; } catch (x) { return ""; } } },\n')],
 'tests/test_all.py': [(": got.append(('push', only", ", admins=False: got.append(('push', only, admins"),
                       (") in got and ('mail', None) in got and ('push', None) in got, got",
                        ", False) in got and ('mail', None) in got, got\n"
                        "    assert ('push', None, True) in got and ('push', None, False) not in got, got      # N1b: the OWNER's trade goes to the admins' phones only, never to every subscriber")]}
def sha(t): return hashlib.sha256(t.encode('utf-8')).hexdigest()[:10]
def main():
    if not os.path.exists(os.path.join(ROOT, 'tests', 'test_push2.py')): sys.exit('STOP: tests/test_push2.py is missing. Copy it into tests/ first. Nothing changed.')
    out = {}; applied = 0; skipped = 0
    for f, hs in HUNKS.items():
        p = os.path.join(ROOT, f)
        if not os.path.exists(p): sys.exit('STOP: %s not found. Nothing changed.' % f)
        t = open(p, encoding='utf-8', newline='').read(); orig = t
        for i, (old, new) in enumerate(hs):
            if new and old in new and t.count(new) >= 1: skipped += 1; continue      # insert-style change, already there
            if t.count(old) == 1: t = t.replace(old, new); applied += 1; continue
            if t.count(old) == 0 and (not new or t.count(new) >= 1): skipped += 1; continue   # already applied
            sys.exit('STOP: %s part %d does not fit (old text found %d times). Nothing changed.' % (f, i + 1, t.count(old)))
        if t != orig: out[f] = t
    for f, t in out.items():
        p = os.path.join(ROOT, f); tmp = p + '.tmp'
        open(tmp, 'w', encoding='utf-8', newline='').write(t); os.replace(tmp, p)
    print('changes applied: %d, already there: %d, files written: %d' % (applied, skipped, len(out)))
    tests = sorted(x for x in os.listdir(os.path.join(ROOT, 'tests')) if x.startswith('test_') and x.endswith('.py')); tot = ok = 0; bad = []
    for x in tests:
        r = subprocess.run([sys.executable, os.path.join('tests', x)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        last = (r.stdout.strip().splitlines() or [''])[-1]; m = re.search(r'(\d+)/(\d+) passed', last)
        if m: ok += int(m.group(1)); tot += int(m.group(2))
        if r.returncode != 0 or (m and m.group(1) != m.group(2)): bad.append(x)
        print('%-24s %s' % (x, last))
    for f in ('static/live.js', 'backend/push.py', 'android-wrapper/native/LiveMessagingService.java', 'tests/test_push2.py'):
        print('sha256 %s  %s' % (sha(open(os.path.join(ROOT, f), encoding='utf-8', newline='').read()), f))
    print('\nRESULT: %s  (%d/%d checks)' % ('ALL PASS' if not bad else 'FAILED in ' + ', '.join(bad), ok, tot))
    sys.exit(1 if bad else 0)
main()
