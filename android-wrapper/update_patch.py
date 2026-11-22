"""Called at the end of prepare.py. In-app update: copies the SxbUpdate plugin and its FileProvider, adds the install permission, the provider and its path file."""
import shutil, sys
from pathlib import Path

def run(MAIN, HERE, PKG):
    pkgdir = MAIN / 'java' / Path(*PKG.split('.')); pkgdir.mkdir(parents=True, exist_ok=True)
    for n in ('AppUpdatePlugin.java', 'SxbFileProvider.java'): shutil.copy(HERE / 'native' / n, pkgdir / n)
    x = MAIN / 'res' / 'xml'; x.mkdir(parents=True, exist_ok=True)
    (x / 'sxb_update_paths.xml').write_text('<?xml version="1.0" encoding="utf-8"?>\n<paths><cache-path name="updates" path="updates/" /></paths>\n', encoding='utf-8')
    m = MAIN / 'AndroidManifest.xml'; s = m.read_text(encoding='utf-8')
    if 'REQUEST_INSTALL_PACKAGES' not in s:
        if '</manifest>' not in s: sys.exit('STOP: no </manifest> in manifest')
        s = s.replace('</manifest>', '    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />\n</manifest>', 1)
    if '.sxbupdate' not in s:
        if '</application>' not in s: sys.exit('STOP: no </application> in manifest')
        prov = ('    <provider android:name=".SxbFileProvider" android:authorities="${applicationId}.sxbupdate" android:exported="false" android:grantUriPermissions="true">\n'
                '        <meta-data android:name="android.support.FILE_PROVIDER_PATHS" android:resource="@xml/sxb_update_paths" />\n'
                '    </provider>\n')
        s = s.replace('</application>', prov + '</application>', 1)
    m.write_text(s, encoding='utf-8'); print('in-app update ready')
