"""Called at the end of prepare.py. Dark launch screen (no white flash) and, if branding/logo.png exists, the app icon, splash logo and notification icon."""
import os
from pathlib import Path

BG = os.environ.get('ICON_BG', '#10151E')

def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding='utf-8')

def run(MAIN, HERE):
    """Dark launch (no white flash) and, when branding/logo.png exists, the app icon + splash logo + notification icon."""
    res = MAIN / 'res'; LOGO = HERE / 'branding' / 'logo.png'
    for f in res.glob('drawable*/splash.png'): f.unlink()
    _write(res / 'values' / 'sxb_colors.xml', '<?xml version="1.0" encoding="utf-8"?>\n<resources><color name="sxb_bg">' + BG + '</color></resources>\n')
    _write(res / 'values' / 'ic_launcher_background.xml', '<?xml version="1.0" encoding="utf-8"?>\n<resources><color name="ic_launcher_background">' + BG + '</color></resources>\n')
    have = LOGO.exists()
    if have:
        from PIL import Image
        logo = Image.open(LOGO).convert('RGBA')
        bb = logo.getbbox()
        if bb: logo = logo.crop(bb)
        def fit(canvas, frac, bg=(0, 0, 0, 0)):
            c = Image.new('RGBA', (canvas, canvas), bg); k = canvas * frac / max(logo.size)
            im = logo.resize((max(1, round(logo.width * k)), max(1, round(logo.height * k))), Image.LANCZOS)
            c.alpha_composite(im, ((canvas - im.width) // 2, (canvas - im.height) // 2)); return c
        bgc = tuple(int(BG[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
        for d, px in (('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)):
            out = res / ('mipmap-' + d); out.mkdir(parents=True, exist_ok=True)
            for old in out.glob('ic_launcher*'): old.unlink()
            full = fit(px, 0.78, bgc); full.convert('RGB').save(out / 'ic_launcher.png')
            circ = Image.new('L', (px, px), 0)
            from PIL import ImageDraw; ImageDraw.Draw(circ).ellipse((0, 0, px - 1, px - 1), fill=255)
            r = full.copy(); r.putalpha(circ); r.save(out / 'ic_launcher_round.png')
            fg = fit(round(px * 108 / 48), 0.56); fg.save(out / 'ic_launcher_foreground.png')   # adaptive: logo inside the safe zone
        for f in list(res.glob('drawable*/ic_launcher_foreground.xml')) + list(res.glob('drawable*/ic_launcher_background.xml')): f.unlink()
        ad = '<?xml version="1.0" encoding="utf-8"?>\n<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@color/ic_launcher_background"/><foreground android:drawable="@mipmap/ic_launcher_foreground"/></adaptive-icon>\n'
        _write(res / 'mipmap-anydpi-v26' / 'ic_launcher.xml', ad); _write(res / 'mipmap-anydpi-v26' / 'ic_launcher_round.xml', ad)
        (res / 'drawable').mkdir(parents=True, exist_ok=True); fit(432, 0.5).save(res / 'drawable' / 'sxb_splash_logo.png')
        splash = ('<?xml version="1.0" encoding="utf-8"?>\n<layer-list xmlns:android="http://schemas.android.com/apk/res/android"><item android:drawable="@color/sxb_bg"/>'
                  '<item android:width="160dp" android:height="160dp" android:gravity="center" android:drawable="@drawable/sxb_splash_logo"/></layer-list>\n')
        # notification small icon: white silhouette of the logo, only if the logo has a transparent background
        a = logo.getchannel('A'); corner = a.getpixel((0, 0))
        if corner < 40:
            for d, px in (('mdpi', 24), ('hdpi', 36), ('xhdpi', 48), ('xxhdpi', 72), ('xxxhdpi', 96)):
                sil = Image.new('RGBA', (px, px), (255, 255, 255, 0)); k = px * 0.9 / max(logo.size)
                al = a.resize((max(1, round(logo.width * k)), max(1, round(logo.height * k))), Image.LANCZOS)
                white = Image.new('RGBA', al.size, (255, 255, 255, 255)); white.putalpha(al)
                sil.alpha_composite(white, ((px - al.width) // 2, (px - al.height) // 2))
                (res / ('drawable-' + d)).mkdir(parents=True, exist_ok=True); sil.save(res / ('drawable-' + d) / 'ic_stat_sxb.png')
            (res / 'drawable' / 'ic_stat_sxb.xml').unlink(missing_ok=True); print('notification icon from logo')
        print('app icon + splash logo from branding/logo.png')
    else:
        splash = '<?xml version="1.0" encoding="utf-8"?>\n<layer-list xmlns:android="http://schemas.android.com/apk/res/android"><item android:drawable="@color/sxb_bg"/></layer-list>\n'
        print('no branding/logo.png: default icon kept, dark launch screen only')
    _write(res / 'drawable' / 'splash.xml', splash)
    styles = ('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        '  <style name="AppTheme" parent="Theme.AppCompat.DayNight.DarkActionBar"><item name="colorPrimary">@color/sxb_bg</item><item name="colorPrimaryDark">@color/sxb_bg</item><item name="colorAccent">@color/sxb_bg</item></style>\n'
        '  <style name="AppTheme.NoActionBar" parent="Theme.AppCompat.DayNight.NoActionBar"><item name="windowActionBar">false</item><item name="windowNoTitle">true</item>'
        '<item name="android:background">@color/sxb_bg</item><item name="android:windowBackground">@color/sxb_bg</item><item name="android:statusBarColor">@color/sxb_bg</item><item name="android:navigationBarColor">@color/sxb_bg</item></style>\n'
        '  <style name="AppTheme.NoActionBarLaunch" parent="AppTheme.NoActionBar"><item name="android:background">@drawable/splash</item><item name="android:windowBackground">@drawable/splash</item></style>\n'
        '</resources>\n')
    _write(res / 'values' / 'styles.xml', styles)
    v31 = ('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n  <style name="AppTheme.NoActionBarLaunch" parent="AppTheme.NoActionBar"><item name="android:windowSplashScreenBackground">@color/sxb_bg</item>'
           + ('<item name="android:windowSplashScreenAnimatedIcon">@drawable/sxb_splash_logo</item>' if have else '') + '</style>\n</resources>\n')
    _write(res / 'values-v31' / 'styles.xml', v31)
    print('launch screen ready')
