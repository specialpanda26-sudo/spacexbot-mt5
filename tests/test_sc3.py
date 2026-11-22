"""SC3a checks: Android screen assistant (floating bubble + screen capture). The Android classes cannot be compiled here (no Android SDK), so:
1) ScreenLogic.java (no Android classes) is compiled and run with plain javac: address check, read gap, picture size, request body, every server answer -> what the bubble says.
2) The Android sources are checked as text for the rules that matter (order of calls Android 14 needs, nothing written to disk, no logging, no storage of the token).
3) screen_patch.py is run on a fake app folder: permissions, service declaration, files copied, safe to run twice.
Skipped if javac is missing. Run: python tests/test_sc3.py"""
import os, re, sys, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); WR = os.path.join(HERE, '..', 'android-wrapper'); NAT = os.path.join(WR, 'native')
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def rd(p): return open(p, encoding='utf-8').read()
def src(n): return rd(os.path.join(NAT, n))

# ---------------- 1) the logic, really run ----------------
CHECK = r'''
package com.spacexbot.app;
public class ScreenLogicCheck {
    static void t(String n, boolean ok) { System.out.println((ok ? "PASS " : "FAIL ") + n); }
    static boolean has(String s, String x) { return s != null && s.indexOf(x) >= 0; }
    public static void main(String[] a) throws Exception {
        t("endpoint: https address -> full read address, trailing slash trimmed", "https://a.onrender.com/api/screen/read".equals(ScreenLogic.endpoint(" https://a.onrender.com/ ", true)));
        t("endpoint: http refused when strict, accepted only in tests", ScreenLogic.endpoint("http://a.example.com", true) == null && ScreenLogic.endpoint("http://a.example.com", false) != null);
        t("endpoint: null, empty, short, spaces, query, fragment, user@ all refused", ScreenLogic.endpoint(null, true) == null && ScreenLogic.endpoint("", true) == null && ScreenLogic.endpoint("https://a", true) == null
            && ScreenLogic.endpoint("https://a b.example.com", true) == null && ScreenLogic.endpoint("https://a.example.com?x=1", true) == null
            && ScreenLogic.endpoint("https://a.example.com#x", true) == null && ScreenLogic.endpoint("https://evil.com@a.example.com", true) == null && ScreenLogic.endpoint("ftp://a.example.com", true) == null);
        t("gap: first read goes at once", ScreenLogic.waitLeft(1000000L, 0) == 0);
        t("gap: 5 s after a read -> wait 6 s", ScreenLogic.waitLeft(1005000L, 1000000L) == 6000);
        t("gap: 11 s and 20 s after -> go", ScreenLogic.waitLeft(1011000L, 1000000L) == 0 && ScreenLogic.waitLeft(1020000L, 1000000L) == 0);
        int[] f = ScreenLogic.fit(2400, 1080); int[] g = ScreenLogic.fit(1080, 2400); int[] h = ScreenLogic.fit(800, 600);
        t("size: long side 1280 (landscape and portrait), small pictures untouched, empty -> null", f[0] == 1280 && f[1] == 576 && g[0] == 576 && g[1] == 1280 && h[0] == 800 && h[1] == 600 && ScreenLogic.fit(0, 5) == null);
        t("body: context and picture, trade by default, learn allowed", ScreenLogic.body("QUJD", null).equals("{\"context\":\"trade\",\"image\":\"QUJD\"}") && has(ScreenLogic.body("QUJD", "learn"), "\"learn\"") && has(ScreenLogic.body("QUJD", "x\"y"), "\"trade\""));
        boolean bad = false; try { ScreenLogic.body("AB\",\"x\":\"", "trade"); } catch (IllegalArgumentException e) { bad = true; }
        boolean bad2 = false; try { ScreenLogic.body(null, "trade"); } catch (IllegalArgumentException e) { bad2 = true; }
        t("body: nothing but base64 gets into the request", bad && bad2);
        t("limits are the server's: 800000 base64, 10 s gap", ScreenLogic.MAX_B64 < 800000 && ScreenLogic.GAP_MS > 10000);

        ScreenLogic.Verdict v = ScreenLogic.verdict(0, "");
        t("no connection: stop tone, says internet", v.tone.equals("stop") && has(v.say, "internet") && v.ring == ScreenLogic.BERRY);
        v = ScreenLogic.verdict(401, "{}"); t("401: asks to open the app to sign in again", v.signIn && has(v.say, "Open spaceXBot"));
        v = ScreenLogic.verdict(429, "{\"error\":\"One read every 10 seconds, please wait a moment.\"}"); t("429: the server's own words, sun colour", v.tone.equals("watch") && has(v.say, "One read every 10") && v.ring == ScreenLogic.SUN && !v.signIn);
        v = ScreenLogic.verdict(402, "{\"error\":\"needs an active plan\"}"); t("402: plan needed", has(v.head, "active plan") && has(v.say, "needs an active plan"));
        v = ScreenLogic.verdict(403, "{\"error\":\"switched off for now\"}"); t("403: assistant is off", has(v.head, "is off") && v.tone.equals("stop"));
        v = ScreenLogic.verdict(500, "not json at all"); t("500 with a broken body: plain words, no crash", v.tone.equals("stop") && has(v.say, "Try again"));
        v = ScreenLogic.verdict(502, "{\"error\":\"The AI reader did not answer (500). Try again in a moment.\"}"); t("502: the server's words shown", has(v.say, "did not answer"));
        v = ScreenLogic.verdict(200, "{\"ok\":true,\"read\":{\"readable\":false,\"note\":\"blurry\"},\"bot\":null}"); t("unreadable chart: says so with the AI's note", has(v.head, "could not read") && has(v.say, "blurry") && v.ring == ScreenLogic.BERRY);
        v = ScreenLogic.verdict(200, "garbage"); t("200 with garbage: treated as unreadable", has(v.head, "could not read"));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true,\"note\":\"Uptrend.\"},\"bot\":null}"); t("read but no bot answer: info", v.tone.equals("info") && has(v.say, "Uptrend"));
        String agree = "{\"read\":{\"readable\":true,\"last_price\":1,\"support\":[7],\"note\":\"AI note\"},\"bot\":{\"code\":\"agree\",\"text\":\"The bot agrees.\",\"signal\":{\"side\":\"buy\",\"entry\":2000.0,\"sl\":1990.5,\"tp\":2020}}}";
        v = ScreenLogic.verdict(200, agree);
        t("agree: green, the bot's words, its own entry, stop and target", v.tone.equals("ok") && v.ring == ScreenLogic.GREEN && has(v.say, "The bot agrees.") && has(v.say, "Entry 2000, stop 1990.50, target 2020") && has(v.say, "the bot's own"));
        t("agree: no number from the AI's read is shown", !has(v.say, "AI note") && !has(v.say, "last_price"));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"agree\",\"text\":\"The bot agrees.\",\"signal\":{\"entry\":\"2000\"}}}"); t("agree with a damaged signal: words only, no numbers", !has(v.say, "Entry") && has(v.say, "The bot agrees."));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"blocked\",\"text\":\"cannot work right now: bot off. It does not trade.\",\"signal\":{\"entry\":1,\"sl\":2,\"tp\":3}}}");
        t("blocked: sun colour, reason shown, NO entry/stop/target offered", v.tone.equals("watch") && v.ring == ScreenLogic.SUN && has(v.say, "bot off") && !has(v.say, "Entry"));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"disagree\",\"text\":\"stays out\",\"signal\":{\"entry\":1,\"sl\":2,\"tp\":3}}}"); t("disagree: stays out, no levels", has(v.head, "stay out") && !has(v.say, "Entry"));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"no_setup\",\"text\":\"none of the strategies\"}}"); t("no_setup: muted colour", v.ring == ScreenLogic.MUTED && has(v.head, "Nothing to trade"));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"bot_only\",\"text\":\"bot sees\",\"signal\":{\"entry\":1,\"sl\":2,\"tp\":3}}}"); t("bot_only: watch, no levels", v.tone.equals("watch") && !has(v.say, "Entry"));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"something_new\",\"text\":\"x\"}}"); t("a code from a newer server: shown as info, no crash", v.tone.equals("info"));
        v = ScreenLogic.verdict(200, "{\"read\":{\"readable\":true},\"bot\":{\"code\":\"no_data\",\"text\":\"The bot has no candles for this market.\"}}"); t("no_data: AI read only", has(v.head, "AI read") && has(v.say, "no candles"));
        Object o = ScreenLogic.Json.parse("{\"a\":\"x\\ny\\\"z\\u0041\",\"b\":[1,2.5,-3e2],\"c\":{\"d\":null,\"e\":true}}");
        java.util.Map m = (java.util.Map) o; java.util.List l = (java.util.List) m.get("b");
        t("json: escapes, numbers, nesting, null and booleans", "x\ny\"zA".equals(m.get("a")) && l.size() == 3 && ((Double) l.get(2)) == -300.0 && Boolean.TRUE.equals(((java.util.Map) m.get("c")).get("e")));
        StringBuilder deep = new StringBuilder(); for (int i = 0; i < 40; i++) deep.append('['); for (int i = 0; i < 40; i++) deep.append(']'); boolean thrown = false; try { ScreenLogic.Json.parse(deep.toString()); } catch (RuntimeException e) { thrown = true; }
        boolean extra = false; try { ScreenLogic.Json.parse("{} x"); } catch (RuntimeException e) { extra = true; }
        t("json: too-deep and trailing text are refused (no crash)", thrown && extra);
    }
}
'''
if not shutil.which('javac') or not shutil.which('java'): print('SKIP javac not installed (the text checks below still run)'); ran = False
else:
    B = os.path.join(HERE, '_sc3_build'); shutil.rmtree(B, ignore_errors=True); os.makedirs(os.path.join(B, 'com', 'spacexbot', 'app'))
    shutil.copy(os.path.join(NAT, 'ScreenLogic.java'), os.path.join(B, 'com', 'spacexbot', 'app', 'ScreenLogic.java'))
    open(os.path.join(B, 'com', 'spacexbot', 'app', 'ScreenLogicCheck.java'), 'w').write(CHECK)
    c = subprocess.run(['javac', '-Xlint:all', '-d', os.path.join(B, 'out'), os.path.join(B, 'com', 'spacexbot', 'app', 'ScreenLogic.java'), os.path.join(B, 'com', 'spacexbot', 'app', 'ScreenLogicCheck.java')], capture_output=True, text=True)
    T('ScreenLogic.java compiles with plain javac', c.returncode == 0)
    if c.returncode != 0: print(c.stderr[-1500:])
    else:
        r = subprocess.run(['java', '-cp', os.path.join(B, 'out'), 'com.spacexbot.app.ScreenLogicCheck'], capture_output=True, text=True, timeout=60)
        for line in r.stdout.splitlines():
            if line.startswith(('PASS ', 'FAIL ')): print(line); R.append(line.startswith('PASS '))
        T('the logic check ran to the end', r.returncode == 0 and len([l for l in r.stdout.splitlines() if l.startswith(('PASS', 'FAIL'))]) >= 28)
    shutil.rmtree(B, ignore_errors=True)

# ---------------- 2) the Android sources, as text ----------------
S, P, L, M = src('OverlayService.java'), src('ScreenPlugin.java'), src('ScreenLogic.java'), src('MainActivity.java')
def code(s): return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', s, flags=re.S))      # no comments
S0, P0, L0 = code(S), code(P), code(L)
T('service: starts as a mediaProjection foreground service BEFORE it asks for the projection (Android 14)', 0 < S0.find('startForeground(') < S0.find('getMediaProjection(') and 'FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION' in S0)
T('service: the projection callback is registered BEFORE the virtual display (Android 14)', 0 < S0.find('projection.registerCallback(') < S0.find('projection.createVirtualDisplay('))
T('service: ONE virtual display per projection (Android 14 allows no second)', S0.count('createVirtualDisplay(') == 1 and S0.count('projection.createVirtualDisplay(') == 1)
T('service: an early exit never skips startForeground', S0.find('startForeground(') < S0.find('shutdown(); return START_NOT_STICKY; }\n        // ') or S0.find('startForeground(') < S0.find('if (endpoint == null'))
T('service: the bubble is a TYPE_APPLICATION_OVERLAY window and does not take focus', 'TYPE_APPLICATION_OVERLAY' in S0 and 'FLAG_NOT_FOCUSABLE' in S0)
T('service: tap reads, long press stops, the bubble hides while the picture is taken', 'readNow()' in S0 and 'postDelayed(hold, 700)' in S0 and 'bubble.setVisibility(View.INVISIBLE)' in S0)
T('service: it posts the picture itself with the bearer token, to the checked address only', 'Authorization' in S0 and 'Bearer ' in S0 and 'new URL(ep)' in S0 and 'ScreenLogic.body(' in S0)
T('service: the picture is never written to disk', not re.search(r'FileOutputStream|openFileOutput|getExternalFilesDir|getExternalStorage|MediaStore|createTempFile|getCacheDir|getFilesDir', S0 + P0))
T('service: nothing is logged (no picture, no token)', 'Log.' not in S0 + P0 + L0 and 'System.out' not in S0 + P0 + L0 and 'printStackTrace' not in S0 + P0 + L0)
T('service: the token is not saved anywhere (no preferences, database or file)', not re.search(r'SharedPreferences|getSharedPreferences|SQLite|openOrCreateDatabase|Settings\.(System|Secure|Global)\.put', S0 + P0))
t = S0[S0.find('private void shutdown()'):]
T('service: stopping drops the token and the address, releases display, reader and projection', 'token = null' in t and 'endpoint = null' in t and 'display.release()' in t and 'reader.close()' in t and 'projection.stop()' in t and 'removeView(bubble)' in t)
T('service: a 401 drops the token (the page must hand over a new one)', re.search(r'if \(code == 401\) token = null', S0) is not None)
T('service: does not try to get around protected windows', 'FLAG_SECURE' not in S0 + P0 and 'setSecure' not in S0 + P0)
T('service: only the server answers; the AI numbers are never drawn (verdict comes from ScreenLogic)', 'ScreenLogic.verdict(' in S0 and 'last_price' not in S0)
T('service: picture is scaled and JPEG-compressed with the shared limits', 'ScreenLogic.fit(' in S0 and 'ScreenLogic.QUALITY' in S0 and 'ScreenLogic.MAX_B64' in S0 and 'Bitmap.CompressFormat.JPEG' in S0)
T('service: gap between reads kept on the phone too', re.search(r'long left = ScreenLogic\.waitLeft\(System\.currentTimeMillis\(\), lastRead\);\s*if \(left > 0\)', S0) is not None)
T('plugin: named SxbScreen with status, start, setToken, stop', '@CapacitorPlugin(name = "SxbScreen")' in P0 and all(('public void %s(PluginCall call)' % x) in P0 for x in ('status', 'start', 'setToken', 'stop')))
st = P0[P0.find('public void start('):]
T('plugin: https address and token checked, then overlay permission, THEN the share consent', 0 < st.find('ScreenLogic.endpoint(') < st.find('canDrawOverlays') < st.find('createScreenCaptureIntent()') and 'call.getString("server"), true)' in st)
T('plugin: a refused consent starts nothing and clears what was handed over', 'DENIED' in P0 and P0.find('OverlayService.clear()') < P0.find('DENIED'))
M0 = code(M)
T('plugin: registered in MainActivity before super.onCreate', 'registerPlugin(ScreenPlugin.class)' in M0 and M0.find('registerPlugin(ScreenPlugin.class)') < M0.find('super.onCreate'))
T('logic: no Android classes (so it can be tested with plain javac)', not re.search(r'import android\.|import androidx\.|import com\.getcapacitor', L))
T('logic: colours baked from the site palette (green #4CD97B, sun #FFCB3D, berry #FF7377, sky #5BB0FF)', all(x in L for x in ('0xFF4CD97B', '0xFFFFCB3D', '0xFFFF7377', '0xFF5BB0FF', '0xFF1A2130')))

# ---------------- 3) the build patch on a fake app folder ----------------
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('screen_patch', os.path.join(WR, 'screen_patch.py')); sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
tree = Path(HERE) / '_sc3_tree'; shutil.rmtree(tree, ignore_errors=True); main = tree / 'src' / 'main'; main.mkdir(parents=True)
(main / 'AndroidManifest.xml').write_text('<?xml version="1.0"?>\n<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n    <application>\n        <activity android:name=".MainActivity" />\n    </application>\n</manifest>\n', encoding='utf-8')
sp.run(main, Path(WR), 'com.spacexbot.app'); sp.run(main, Path(WR), 'com.spacexbot.app')
mf = (main / 'AndroidManifest.xml').read_text(encoding='utf-8')
T('patch: the four permissions are there, each once (an existing one is not doubled)', all(mf.count('android.permission.%s"' % p) == 1 for p in ('FOREGROUND_SERVICE', 'FOREGROUND_SERVICE_MEDIA_PROJECTION', 'SYSTEM_ALERT_WINDOW', 'POST_NOTIFICATIONS')))
T('patch: the service is declared once, not exported, type mediaProjection, inside <application>', mf.count('.OverlayService') == 1 and 'android:exported="false" android:foregroundServiceType="mediaProjection"' in mf and mf.find('.OverlayService') < mf.find('</application>'))
T('patch: all three java files copied into the app package', all((main / 'java' / 'com' / 'spacexbot' / 'app' / n).exists() for n in ('ScreenLogic.java', 'ScreenPlugin.java', 'OverlayService.java')))
T('patch: prepare.py runs it', 'import screen_patch; screen_patch.run(MAIN, HERE, PKG)' in rd(os.path.join(WR, 'prepare.py')))
shutil.rmtree(tree, ignore_errors=True)
bad = Path(HERE) / '_sc3_tree'; (bad / 'src' / 'main').mkdir(parents=True); (bad / 'src' / 'main' / 'AndroidManifest.xml').write_text('<manifest></manifest>', encoding='utf-8')
try: sp.run(bad / 'src' / 'main', Path(WR), 'com.spacexbot.app'); stopped = False
except SystemExit: stopped = True
shutil.rmtree(bad, ignore_errors=True)
T('patch: a manifest without <application> stops the build with a clear message', stopped)
print('\n%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
