"""SC3a: Android screen assistant (floating bubble + screen capture). Run from the repo folder: python apply_sc3.py (safe to run twice).
Needs these files first (paste blocks 1-5): android-wrapper/native/ScreenLogic.java, ScreenPlugin.java, OverlayService.java, android-wrapper/screen_patch.py, tests/test_sc3.py.
It edits: android-wrapper/native/MainActivity.java (registers the plugin), android-wrapper/prepare.py (runs screen_patch), docs/HANDOFF.md."""
import sys, os
need = ['android-wrapper/native/ScreenLogic.java', 'android-wrapper/native/ScreenPlugin.java', 'android-wrapper/native/OverlayService.java', 'android-wrapper/screen_patch.py', 'tests/test_sc3.py']
miss = [p for p in need if not os.path.exists(p)]
if miss: print('STOP: paste these first:', ', '.join(miss)); sys.exit(1)
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, s): open(p, 'w', encoding='utf-8').write(s)
def edit(path, old, new, marker):
    s = rd(path)
    if marker in s: print('skip (already there):', path, marker[:40]); return
    if s.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    wr(path, s.replace(old, new, 1)); print('edited', path)

edit('android-wrapper/native/MainActivity.java', "        registerPlugin(AppUpdatePlugin.class);\n", "        registerPlugin(AppUpdatePlugin.class);\n        registerPlugin(ScreenPlugin.class);\n", 'registerPlugin(ScreenPlugin.class)')
edit('android-wrapper/prepare.py', "import update_patch; update_patch.run(MAIN, HERE, PKG)", "import update_patch; update_patch.run(MAIN, HERE, PKG)\nimport screen_patch; screen_patch.run(MAIN, HERE, PKG)", 'screen_patch')
s = rd('docs/HANDOFF.md')
if '## Section SC3a' in s: print('skip (already there): HANDOFF SC3a')
else:
    wr('docs/HANDOFF.md', s.rstrip('\n') + """

## Section SC3a (Android screen assistant: floating bubble + screen capture, native only) DONE (Nov 22)
- New: android-wrapper/native/ScreenLogic.java (no Android classes: https address check, 11 s gap, picture size 1280 long side, request body, server answer -> what the bubble says, small JSON reader; colours baked ONCE from the site's dark palette: green #4CD97B, sun #FFCB3D, berry #FF7377, sky #5BB0FF, surface #1A2130), native/ScreenPlugin.java (Capacitor plugin SxbScreen: status, start{server, token, context}, setToken{token}, stop), native/OverlayService.java (foreground service type mediaProjection: bubble = TYPE_APPLICATION_OVERLAY window, tap = ONE read, long press = stop, drag to move, card with the bot's words; posts the picture to /api/screen/read ITSELF with the bearer token because the page is paused in the background), android-wrapper/screen_patch.py (copies the three files, adds FOREGROUND_SERVICE, FOREGROUND_SERVICE_MEDIA_PROJECTION, SYSTEM_ALERT_WINDOW, POST_NOTIFICATIONS, declares the service), prepare.py calls it, MainActivity registers the plugin, tests/test_sc3.py, apply_sc3.py.
- Flow: page calls SxbScreen.start -> https + token check -> overlay permission (opens Android's settings page, user presses Watch again) -> Android's own screen-share consent (every time on Android 14+) -> service starts foreground FIRST, then gets the projection, registers its callback, makes ONE virtual display (Android 14 rules) -> bubble. Tap: bubble hides 300 ms (out of the picture), one frame -> JPEG (70/55/40 until under 780000 base64) -> POST. Answer: ring colour + card (agree green with the BOT'S own entry/stop/target, blocked/disagree/bot_only sun, no setup grey, errors red). 401 drops the token: the page must call setToken again.
- Privacy kept: picture only in local variables, never on disk, never logged; token in memory only, dropped when the service ends; FLAG_SECURE windows come out black and nothing tries to get around that.
- Tests (tests/test_sc3.py, 60 checks, 23 deliberate breaks each went red): the logic file is compiled and run with plain javac; the Android files are checked as text (call order Android 14 needs, nothing to disk, no logging, token not stored, plugin registered); screen_patch is run on a fake app folder (twice).
- NOT compiled here: OverlayService.java and ScreenPlugin.java need the Android SDK and Capacitor, which this session does not have. The first APK build is their compile check: if the build fails with a Java error, send the log. NOT run on a phone: needs a real phone test (bubble visible over Deriv, tap reads, consent every time on Android 14+, banking/DRM apps show black).
- Honest limits: Android 13+ needs the notification permission for the notification to show (the service still runs; asking for it is SC7). Reading is by tap only (no 20 s auto loop on the phone yet). The page does not call SxbScreen yet.
- Next: SC3b (page side: static/screen.js asks the plugin on the phone app, hands over the token and refreshes it with setToken before it expires, shows state), then SC3c "Go to the market" (the bubble opens a Deriv market; find out first which Deriv link opens a given market).
""")
    print('HANDOFF updated')
print('SC3a applied')
