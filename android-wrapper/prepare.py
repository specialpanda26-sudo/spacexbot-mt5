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
patch_manifest(); patch_version(); patch_google_signin()
