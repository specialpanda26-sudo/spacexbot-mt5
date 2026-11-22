"""Rk4: the notification large icon. A round violet badge with the character's face (same look as the rocket cartoons) is added as android-wrapper/branding/ic_large_sxb.png; prepare.py copies it to res/drawable-nodpi; LiveMessagingService.java sets it as the large icon of the alerts it draws and of the pinned "Bot running" notification (nothing happens if the file is missing). The small status-bar icon is NOT changed (Android only draws it as a flat white shape). Also: test_push2.py stubs learn setLargeIcon/Bitmap/BitmapFactory and check it; HANDOFF gets an entry. Safe to run twice."""
import base64, os, sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')
PNG = """
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
"""
dst = 'android-wrapper/branding/ic_large_sxb.png'; data = base64.b64decode(PNG)
if os.path.exists(dst) and open(dst, 'rb').read() == data: print(dst, ': already ok')
else: open(dst, 'wb').write(data); print(dst, ': written', len(data), 'bytes')
edit('android-wrapper/prepare.py', """    (d / 'ic_stat_sxb.xml').write_text(ICON_XML, encoding='utf-8')
""", """    (d / 'ic_stat_sxb.xml').write_text(ICON_XML, encoding='utf-8')
    lg = HERE / 'branding' / 'ic_large_sxb.png'   # Rk4: large icon for the alerts the app draws itself
    if lg.exists():
        (MAIN / 'res' / 'drawable-nodpi').mkdir(parents=True, exist_ok=True); shutil.copy(lg, MAIN / 'res' / 'drawable-nodpi' / 'ic_large_sxb.png')
""", 'ic_large_sxb')
J = 'android-wrapper/native/LiveMessagingService.java'
edit(J, """        if (pi != null) b.setContentIntent(pi);
        if (tag != null && !tag.isEmpty()) nm.notify(tag, ALERT_ID, b.build());""", """        if (pi != null) b.setContentIntent(pi);
        android.graphics.Bitmap lg = largeIcon(); if (lg != null) b.setLargeIcon(lg);
        if (tag != null && !tag.isEmpty()) nm.notify(tag, ALERT_ID, b.build());""", 'Bitmap lg = largeIcon()')
edit(J, """        if (pi != null) b.setContentIntent(pi);
        nm.notify(NOTIF_ID, b.build());""", """        if (pi != null) b.setContentIntent(pi);
        android.graphics.Bitmap lg2 = largeIcon(); if (lg2 != null) b.setLargeIcon(lg2);
        nm.notify(NOTIF_ID, b.build());""", 'Bitmap lg2 = largeIcon()')
edit(J, """    private void handleLive(Map<String, String> d) {""", """    /** Rk4: the round badge (res/drawable-nodpi/ic_large_sxb.png). No file = no large icon, never an error. */
    private android.graphics.Bitmap largeIcon() {
        try {
            int id = getResources().getIdentifier("ic_large_sxb", "drawable", getPackageName());
            if (id == 0) return null;
            return android.graphics.BitmapFactory.decodeResource(getResources(), id);
        } catch (Exception e) { return null; }
    }

    private void handleLive(Map<String, String> d) {""", 'Bitmap largeIcon()')
T = 'tests/test_push2.py'
edit(T, "public boolean autoCancel,ongoing;", "public boolean autoCancel,ongoing,large;", 'autoCancel,ongoing,large;')
edit(T, "public Builder setSmallIcon(int i){n.icon=i;return this;}", "public Builder setSmallIcon(int i){n.icon=i;return this;} public Builder setLargeIcon(android.graphics.Bitmap b){n.large=b!=null;return this;}", 'setLargeIcon(android.graphics.Bitmap')
edit(T, " 'android/os/Build.java':", """ 'android/graphics/Bitmap.java': 'package android.graphics; public class Bitmap {}',
 'android/graphics/BitmapFactory.java': 'package android.graphics; public class BitmapFactory { public static Bitmap decodeResource(android.content.res.Resources r,int id){return id==0?null:new Bitmap();} }',
 'android/os/Build.java':""", "'android/graphics/Bitmap.java'")
edit(T, '"|icon=" + n.icon + ', '"|icon=" + n.icon + "|large=" + n.large + ', '"|large=" + n.large')
edit(T, """L['nochannel'][-1].get('super'))
    shutil.rmtree(tmp, ignore_errors=True)""", """L['nochannel'][-1].get('super'))
        T('java foreground (Rk4): the large icon badge is set on an alert when the resource exists', fg.get('large') == 'true')
        T('java (Rk4): the pinned "Bot running" notification gets the large icon too', lv.get('large') == 'true')
        T('java (Rk4): no resource (id 0) gives no large icon and never throws', 'if (id == 0) return null;' in SRCJ and 'catch (Exception e) { return null; }' in SRCJ and SRCJ.count('largeIcon()') == 3)
    shutil.rmtree(tmp, ignore_errors=True)""", 'large icon badge is set on an alert')
H = 'docs/HANDOFF.md'; h = open(H, encoding='utf-8').read()
if '## Section Rk4' in h: print(H, ': already ok')
else:
    open(H, 'w', encoding='utf-8').write(h.rstrip('\n') + """

## Section Rk4 (notification large icon) DONE (Nov 22)
- New android-wrapper/branding/ic_large_sxb.png (128 px round violet badge with the character's face, rocket look). prepare.py (patch_push) copies it to res/drawable-nodpi/. LiveMessagingService.java: largeIcon() loads it by name (no file = null) and sets it as the large icon of (1) alerts the app draws while it is open and (2) the pinned "Bot running" notification. The lock-screen public version has none on purpose.
- The small status-bar icon (ic_stat_sxb) is unchanged: Android draws it as a flat white shape, so a cartoon cannot go there.
- Limit: a push the system draws while the app is closed (FCM notification message) cannot carry this icon; only Firebase's small icon and colour can be set for those. To show it there the server would have to send data-only messages that the app draws itself (not done).
- tests/test_push2.py: stubs know setLargeIcon/Bitmap/BitmapFactory, 3 new checks (needs javac, SKIP without). tests/test_rk4.py checks the PNG and the build copy.
- NOT done yet: a real APK build and a look at the notification on a phone; the logo-style symbol cartoons on the legal pages and the 5 email GIFs (Rk5).
""")
    print(H, ': entry added')
