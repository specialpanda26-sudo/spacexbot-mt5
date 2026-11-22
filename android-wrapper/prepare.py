"""Runs after `npx cap add android`. Adds the internet permission, version numbers and the native Google account picker."""
import os, re, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
APP = HERE / 'android' / 'app'
MAIN = APP / 'src' / 'main'
PKG = 'com.spacexbot.app'
KOTLIN_VERSION = '1.9.25'
CREDENTIALS_VERSION = '1.3.0'
GOOGLEID_VERSION = '1.1.1'

def patch_manifest():
    p = MAIN / 'AndroidManifest.xml'
    s = p.read_text(encoding='utf-8')
    add = ''
    for n in ('INTERNET', 'ACCESS_NETWORK_STATE'):
        if 'android.permission.' + n + '"' not in s:
            add += '    <uses-permission android:name="android.permission.' + n + '" />\n'
    if add:
        if '</manifest>' not in s: sys.exit('STOP: AndroidManifest.xml has no </manifest>')
        s = s.replace('</manifest>', add + '</manifest>', 1)
    s = s.replace('android:allowBackup="true"', 'android:allowBackup="false"')
    if 'android:exported' not in s.split('<activity', 1)[-1].split('>', 1)[0]:
        s = s.replace('<activity', '<activity android:exported="true"', 1)
    p.write_text(s, encoding='utf-8'); print('manifest ready')

def patch_version():
    code, name = os.environ.get('VERSION_CODE'), os.environ.get('VERSION_NAME')
    if not (code or name): return
    p = APP / 'build.gradle'; s = p.read_text(encoding='utf-8')
    if code:
        s, n = re.subn(r'versionCode\s+\d+', 'versionCode ' + str(int(code)), s, count=1)
        if not n: sys.exit('STOP: no versionCode line')
    if name:
        s, n = re.subn(r'versionName\s+"[^"]*"', 'versionName "' + name + '"', s, count=1)
        if not n: sys.exit('STOP: no versionName line')
    p.write_text(s, encoding='utf-8'); print('version', code, name)

def patch_google_signin():
    root = HERE / 'android' / 'build.gradle'; s = root.read_text(encoding='utf-8')
    if 'kotlin-gradle-plugin' not in s:
        s, n = re.subn(r"(classpath\s+['\"]com\.android\.tools\.build:gradle:[^'\"]+['\"])",
                       r"\1\n        classpath 'org.jetbrains.kotlin:kotlin-gradle-plugin:" + KOTLIN_VERSION + "'", s, count=1)
        if not n: sys.exit('STOP: no Android Gradle Plugin line in android/build.gradle')
        root.write_text(s, encoding='utf-8')
    g = APP / 'build.gradle'; s = g.read_text(encoding='utf-8')
    if 'androidx.credentials:credentials:' not in s:
        if "apply plugin: 'kotlin-android'" not in s:
            s, n = re.subn(r"(apply plugin: 'com\.android\.application')", r"\1\napply plugin: 'kotlin-android'", s, count=1)
            if not n: sys.exit('STOP: no application plugin line in app/build.gradle')
        s += ("\nandroid { kotlinOptions { jvmTarget = '17' } }\ndependencies {\n"
              "    implementation \"androidx.credentials:credentials:" + CREDENTIALS_VERSION + "\"\n"
              "    implementation \"androidx.credentials:credentials-play-services-auth:" + CREDENTIALS_VERSION + "\"\n"
              "    implementation \"com.google.android.libraries.identity.googleid:googleid:" + GOOGLEID_VERSION + "\"\n"
              "    implementation \"org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1\"\n}\n")
        g.write_text(s, encoding='utf-8')
    src = HERE / 'native'; pkgdir = MAIN / 'java' / Path(*PKG.split('.')); pkgdir.mkdir(parents=True, exist_ok=True)
    for old in pkgdir.glob('MainActivity.*'): old.unlink()
    shutil.copy(src / 'MainActivity.java', pkgdir / 'MainActivity.java')
    shutil.copy(src / 'GoogleSignInPlugin.kt', pkgdir / 'GoogleSignInPlugin.kt')
    print('native Google sign-in ready')

if not (MAIN / 'AndroidManifest.xml').exists(): sys.exit('STOP: run `npx cap add android` first')

ICON_XML = """<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24"><path android:fillColor="#FFFFFFFF" android:pathData="M12,2 L14.6,8.9 L22,9.3 L16.2,13.9 L18.2,21 L12,17 L5.8,21 L7.8,13.9 L2,9.3 L9.4,8.9 Z"/></vector>"""

def patch_push():
    """Push notifications: Firebase build plugin, permission, status-bar icon, default channel."""
    if not (APP / 'google-services.json').exists():
        print('no google-services.json: push notifications skipped'); return
    root = HERE / 'android' / 'build.gradle'; s = root.read_text(encoding='utf-8')
    if 'com.google.gms:google-services' not in s:
        s, n = re.subn(r"(classpath\s+['\"]com\.android\.tools\.build:gradle:[^'\"]+['\"])", r"\1\n        classpath 'com.google.gms:google-services:4.4.2'", s, count=1)
        if not n: sys.exit('STOP: no Android Gradle Plugin line for google-services')
        root.write_text(s, encoding='utf-8')
    g = APP / 'build.gradle'; s = g.read_text(encoding='utf-8')
    if 'google-services' not in s:
        s += "\napply plugin: 'com.google.gms.google-services'\n"; g.write_text(s, encoding='utf-8')
    d = MAIN / 'res' / 'drawable'; d.mkdir(parents=True, exist_ok=True)
    (d / 'ic_stat_sxb.xml').write_text(ICON_XML, encoding='utf-8')
    lg = HERE / 'branding' / 'ic_large_sxb.png'   # Rk4: large icon for the alerts the app draws itself
    if lg.exists():
        (MAIN / 'res' / 'drawable-nodpi').mkdir(parents=True, exist_ok=True); shutil.copy(lg, MAIN / 'res' / 'drawable-nodpi' / 'ic_large_sxb.png')
    m = MAIN / 'AndroidManifest.xml'; s = m.read_text(encoding='utf-8')
    if 'POST_NOTIFICATIONS' not in s:
        s = s.replace('</manifest>', '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n</manifest>', 1)
    if 'default_notification_icon' not in s:
        if '</application>' not in s: sys.exit('STOP: no </application> in manifest')
        meta = ('    <meta-data android:name="com.google.firebase.messaging.default_notification_icon" android:resource="@drawable/ic_stat_sxb" />\n'
                '    <meta-data android:name="com.google.firebase.messaging.default_notification_color" android:resource="@android:color/white" />\n'
                '    <meta-data android:name="com.google.firebase.messaging.default_notification_channel_id" android:value="sxb_high" />\n')
        s = s.replace('</application>', meta + '</application>', 1)
    m.write_text(s, encoding='utf-8'); print('push notifications ready')

patch_manifest(); patch_version(); patch_google_signin(); patch_push()

import live_patch; live_patch.run(MAIN, APP, HERE, PKG)
import launch_patch; launch_patch.run(MAIN, HERE)
import update_patch; update_patch.run(MAIN, HERE, PKG)
