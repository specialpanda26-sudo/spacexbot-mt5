"""Called at the end of prepare.py. SC3 screen assistant: copies the SxbScreen plugin, the floating-bubble service and their logic file into the app, adds the
permissions (foreground service, media projection, display over other apps, notifications) and declares the service as a mediaProjection foreground service."""
import shutil, sys
from pathlib import Path

FILES = ('ScreenLogic.java', 'ScreenPlugin.java', 'OverlayService.java')
PERMS = ('FOREGROUND_SERVICE', 'FOREGROUND_SERVICE_MEDIA_PROJECTION', 'SYSTEM_ALERT_WINDOW', 'POST_NOTIFICATIONS')
SERVICE = '    <service android:name=".OverlayService" android:exported="false" android:foregroundServiceType="mediaProjection" />\n'

def run(MAIN, HERE, PKG):
    pkgdir = MAIN / 'java' / Path(*PKG.split('.')); pkgdir.mkdir(parents=True, exist_ok=True)
    for n in FILES: shutil.copy(HERE / 'native' / n, pkgdir / n)
    m = MAIN / 'AndroidManifest.xml'; s = m.read_text(encoding='utf-8')
    add = ''.join('    <uses-permission android:name="android.permission.%s" />\n' % p for p in PERMS if 'android.permission.%s"' % p not in s)
    if add:
        if '</manifest>' not in s: sys.exit('STOP: no </manifest> in manifest')
        s = s.replace('</manifest>', add + '</manifest>', 1)
    if '.OverlayService' not in s:
        if '</application>' not in s: sys.exit('STOP: no </application> in manifest')
        s = s.replace('</application>', SERVICE + '</application>', 1)
    m.write_text(s, encoding='utf-8'); print('screen assistant ready')
