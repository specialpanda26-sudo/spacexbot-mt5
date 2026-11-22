"""Finishes docs/HANDOFF.md (safe to run twice).
1. removes the duplicated "Section 5A" block,
2. replaces the stale "Do the NEXT section: ..." order in the prompt for the next AI,
3. appends the Nov 22 STATUS BOARD and the AI SCREEN ASSISTANT plan (SC1-SC7).
Run from the repo folder:  python apply_handoff_final.py"""
import sys

P = 'docs/HANDOFF.md'
MARK = '## STATUS BOARD Nov 22 (newest; read this first)'
s = open(P, encoding='utf-8').read()
if MARK in s:
    print('already applied'); sys.exit(0)

H = '## Section 5A (trade on ONE platform at a time: MT5 / Deriv / Binance) DONE (Nov 22)'
N = '## Section C-AUTH 2 (Log in with Deriv button and logo) DONE (Nov 22)'
a = s.find(H); b = s.find(H, a + 1); c = s.find(N)
if a < 0 or b < 0 or c < 0:
    print('STOP: cannot find the 5A blocks'); sys.exit(1)
if s[a:b].strip() == s[b:c].strip():
    s = s[:b] + s[c:]
    print('removed the duplicate 5A block')
else:
    print('note: the two 5A blocks differ, left both')

OLD = ('Do the NEXT section: first the unfinished item of the "SECTIONS 1-5" plan, then the PHONE ALERTS N3..N6, '
       'then the S2..S6 plan, then strategy 4C, then the backtest. One section per reply.')
NEW = ('Do the NEXT section named in "STATUS BOARD Nov 22" (the newest board, at the end of the file): the AI SCREEN '
       'ASSISTANT, starting with SC1. Older plans above it are history; trust the newest board and the code. '
       'One section per reply.')
if s.count(OLD) != 1:
    print('STOP: prompt sentence not found exactly once'); sys.exit(1)
s = s.replace(OLD, NEW)

s = s.rstrip('\n') + '\n\n' + r'''
''' + MARK + r'''
- DONE since the Nov 21 board (each has its own section above): N4, N5, N6a-N6e (alerts, only kind 35 is open), BTC weekend plan sections 2-6B, 4C (orb_session), SW1, fake-data fixes FD1-FD4, cartoons Rk1-Rk6, Nav3, X1, X2, Rk5 (email GIFs), U7 (in-app update), 5A (trade on ONE platform), C-AUTH 2 (Log in with Deriv), Test Lab 1, Binance spot testnet 5B-1, 5B-2a, 5B-2b.
- THE OWNER STILL HAS TO PUSH / RUN (nothing here is proven on a real phone): Nav3, X1, Rk5 then Actions > "Rebuild email GIFs" then `git pull`, U7 then Actions > "Build Android APK" and install it once, 5B-2b, and docs/PHONE_CHECKLIST.md on a real phone.
- STILL OPEN, in this order of priority: (1) the AI SCREEN ASSISTANT below (owner's next move, Nov 22); (2) the backtest on real data (needs the owner's MT5 M15 + H1 CSVs; the BTC range / weekend / orb_session switches are unproven until then); (3) 5B-3 Real Binance (own key check with withdrawals OFF, the word REAL, plan, loss limits) - only when the owner says; (4) N6 kind 35 (owner has not said what it should do); (5) C5 (PDF) and C6 (Teach the bot): listed in an older note, not built as far as this file says (backend/taught.py exists, check it first).
- KNOWN: tests/test_n4.py failed once in a full run (timing), passes alone. The two duplicate 5A blocks were merged by apply_handoff_final.py.
- Owner's wording of Nov 22 (dictated): "finish the handoff", then integrate the bot with a SCREEN-SHARE AI like the Gemini feature: the bot looks at the screen (a chart of a derivative market), says the possible strategies, and may trade automatically. The app gets "display over other apps". Everything must match the website (same colours, the site's own cartoons). It is for the app first; the website can have it too.

## AI SCREEN ASSISTANT PLAN (Nov 22, owner request; NOTHING BUILT YET; one section per reply, owner says "go SCn")
What it is: the person presses Watch; the app (or the website) captures what is on the screen, sends one picture at a time to a vision model on the server, and gets back a plain-words read of the chart: market, timeframe, trend, key levels, which of OUR strategies (backend/strategy_info.py names) the picture looks like, and a bias. On the phone a small round bubble with the site's character floats over other apps (Android "Display over other apps"), tap it to read the screen now.
Facts found in the repo (Nov 22, re-check if in doubt):
- NO language-model or vision code exists today: no API key in .env.example, no anthropic/openai/gemini call anywhere, requirements.txt has only requests. backend/assist.py is "Phone mode" (signals handed to people who place trades by hand), it has nothing to do with AI.
- The Android wrapper (android-wrapper/prepare.py, update_patch.py, live_patch.py) patches AndroidManifest.xml and registers Capacitor plugins from android-wrapper/native/*.java (pattern: AppUpdatePlugin + update_patch.py + javac stub test in tests/test_upd7.py). It has NO overlay, screen-capture or foreground-service code yet. Native changes need an APK rebuild (Actions > Build Android APK); backend/static changes need only a Render deploy.
- window.IL2 is shared (props: coin cookie cx doc lock mail off ok paid phone plug push rocket rs shield sleep wait yay). The character CH2 is NOT global (update.js carries its own copy, tests/test_update5.py checks it matches index.html). Logos and PNGs are in android-wrapper/branding (make_logo.py).
- Existing safety path for any trade: risk.global_gate, limits.max_open, trade_on (ONE platform), bot switch, plan check, Real needs the word REAL, demo first. The screen feature must go through ALL of it and never around it.
RULES (do not break):
1. HONESTY. A screenshot read is a vision model's opinion; it can misread the symbol, the timeframe, the price scale, or a stale/zoomed chart. Never write that it "works" or promises profit; wording = "a read of your screen, not advice". Only a log of reads against what happened next (SC6) can say anything, and Auto (SC5) stays locked until the owner has seen those numbers.
2. THREE LEVELS per person, default EXPLAIN. Explain = words only. Suggest = also creates a signal card like phone mode (person places it by hand). Auto = CONFIRM-ONLY: the screen read may confirm or veto a signal that the server's own scan already produced (same symbol, same direction, produced in the last N minutes, last price in the picture within X percent of the server's last price). The model NEVER invents entry, stop or target: they come from the server signal (brain rules: stop 0.5-3.5 ATR, 2R). Then the normal path: _place, risk gates, trade_on, limits, demo first, Real needs the word REAL again for screen mode.
3. PRIVACY. Frames are sent only while the person has pressed Watch. A visible sign is always on (the bubble pulses and Android shows its own foreground-service notification). Frames are kept in memory only, dropped after the reply; the database stores only the JSON read + time + symbol (table screen_reads). Say in plain words: everything visible on the screen goes to the AI service, close private screens first. Windows that block capture (FLAG_SECURE) show black; do not try to get around that.
4. COST AND ABUSE. Off by default (setting screen_on = 0, admin switch). Paid plan only. Daily cap per person (env SCREEN_DAILY_CAP, default 60), minimum 10 s between reads, picture max 1280 px long side as JPEG, at most about 600 KB (413 otherwise). Not a live video stream: one frame every 20 s (adjustable) or on tap; cheaper and simpler than streaming.
5. PROVIDER. One function backend/screenread.py read_chart(jpeg_bytes, hints) -> dict, so the model can be swapped (Gemini or another). Default: Anthropic vision API, key only on Render (ANTHROPIC_API_KEY, model name in VISION_MODEL), never in the app. The model is told to answer JSON only; the reply is validated against a schema; anything else becomes "I could not read this chart" in plain words. Needs `requests` only.
6. SCOPE. Derivative charts first (Deriv markets the person has open: synthetics, forex, metals). Symbol mapped through backend/automarkets.py / brokers.py; unknown symbol = Explain only, never Suggest or Auto.
7. WEBSITE VIBE. Cards use the site classes (.card .card-head .chip .stats .btn .seg .note), CSS variables only, wording friendly and factual. New cartoon IL2.eye (the site's character with a magnifier over candles, same outline style as IL2.shield / IL2.wait); existing props for states (wait = idle, yay = good read, shield = limit hit, off = cannot read). The native overlay cannot read CSS variables: bake its colours once from the site palette into the branding files (the ONE allowed exception, say so in its section).
SECTIONS (do in this order):
- SC1 backend only: backend/screenread.py (read_chart + schema check + provider switch + a FAKE provider for tests), table screen_reads, POST /api/screen/read (signed in, verified, plan active, screen_on, size and rate caps, daily cap), GET /api/screen/status, env docs in .env.example and README. tests/test_sc1.py with a fake provider: wrong JSON rejected, oversize rejected, plan gate, daily cap, rate gap, kill switch, frame never written to the database or logs, unknown symbol marks explain-only. Mutation-check each rule.
- SC2 website + app page (no native yet): static/screen.js (card "Screen assistant" on the Bot tab, like static/trade_on.js): Watch / Stop, level picker (Explain / Suggest / Auto locked), frame grab with getDisplayMedia (works in desktop browsers; phone browsers do not support it, say so in words), result card (bias chip, strategy name, levels in words, "not advice" line), IL2.eye cartoon with motion only inside prefers-reduced-motion:no-preference. Test in node + real Chromium with a fake getDisplayMedia and a fake server.
- SC3 Android native (needs an APK rebuild): android-wrapper/native/ScreenPlugin.java (Capacitor plugin SxbScreen: asks the system for screen capture consent, foreground service of type mediaProjection, ImageReader frame -> JPEG), OverlayService.java (floating bubble with the character, TYPE_APPLICATION_OVERLAY, permission SYSTEM_ALERT_WINDOW via Settings.ACTION_MANAGE_OVERLAY_PERMISSION, tap = read now, long press = stop, ring colour = last bias), screen_patch.py called from prepare.py (manifest permissions FOREGROUND_SERVICE, FOREGROUND_SERVICE_MEDIA_PROJECTION, SYSTEM_ALERT_WINDOW, POST_NOTIFICATIONS; service declarations). IMPORTANT: the page's JavaScript is paused when the app is in the background, so the NATIVE service must POST the frame to /api/screen/read itself with a short-lived token handed over by the plugin, and show the result in the bubble / a small card. Test with javac stubs like tests/test_upd7.py. Honest limits to write in the section: Android 14+ asks for consent every time; some apps (banking, DRM video) show black; a real phone test is required.
- SC4 Suggest mode: a read that matches one of our strategies and a known symbol creates a "screen signal" card (same look as the phone-mode signal card, name from strategy_info), with a push (new kind, add to backend/push.py + pushcopy.py + the kind test). The person places it by hand.
- SC5 Auto, confirm-only (see rule 2): demo / testnet only first; locked until the owner unlocks it in the admin panel after seeing SC6 numbers; every Auto trade is labelled strategy "screen" in the Journal. All existing gates apply; a test must fail if any gate is skipped.
- SC6 Accuracy log: Journal card "How the screen reads did": every read vs what price did after N candles (server candles) and vs the outcome of the matching signal. Numbers only, "no claim" wording, per symbol.
- SC7 Polish: cartoons per state (watching, cannot read, market closed, limit hit), notification pictures, items added to docs/PHONE_CHECKLIST.md, final check (Render env ANTHROPIC_API_KEY + VISION_MODEL + SCREEN_DAILY_CAP, APK rebuild, real phone).
OPEN QUESTIONS (defaults used if the owner just says "go"): provider = Anthropic vision (owner mentioned Gemini only as an example of the feel); frame every 20 s plus tap; paid plans only; Auto stays locked until SC6; website version = desktop browsers only.
Next: SC1.
'''
open(P, 'w', encoding='utf-8').write(s)
print('HANDOFF finished')
