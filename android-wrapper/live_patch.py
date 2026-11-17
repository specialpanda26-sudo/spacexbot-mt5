"""Called at the end of prepare.py. Adds the live 'Bot running' notification: our push service replaces Capacitor's (it passes every normal alert on to it)."""
import re, shutil, sys
from pathlib import Path

def run(MAIN, APP, HERE, PKG):
    if not (APP / 'google-services.json').exists():
        print('no google-services.json: live notification skipped'); return
    pkgdir = MAIN / 'java' / Path(*PKG.split('.')); pkgdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / 'native' / 'LiveMessagingService.java', pkgdir / 'LiveMessagingService.java')
    m = MAIN / 'AndroidManifest.xml'; s = m.read_text(encoding='utf-8')
    if 'xmlns:tools=' not in s:
        s, n = re.subn(r'<manifest\b', '<manifest xmlns:tools="http://schemas.android.com/tools"', s, count=1)
        if not n: sys.exit('STOP: no <manifest> tag')
    if 'LiveMessagingService' not in s:
        if '</application>' not in s: sys.exit('STOP: no </application> in manifest')
        svc = ('    <service android:name="com.capacitorjs.plugins.pushnotifications.MessagingService" tools:node="remove" />\n'
               '    <service android:name=".LiveMessagingService" android:exported="false">\n'
               '        <intent-filter android:priority="100"><action android:name="com.google.firebase.MESSAGING_EVENT" /></intent-filter>\n'
               '    </service>\n')
        s = s.replace('</application>', svc + '</application>', 1)
    m.write_text(s, encoding='utf-8')
    g = APP / 'build.gradle'; t = g.read_text(encoding='utf-8')
    if 'firebase-messaging' not in t:
        t += "\ndependencies {\n    implementation 'com.google.firebase:firebase-messaging:23.4.1'\n}\n"; g.write_text(t, encoding='utf-8')
    print('live notification ready')
