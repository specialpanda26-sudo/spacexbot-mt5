"""SC3b: draws the pictures the floating screen assistant shows on Android, from the WEBSITE'S OWN cartoons (window.IL2 in static/index.html), not from anything
drawn separately. Each prop is rendered in a real Chromium on the real page (dark theme, still pose, transparent background) and saved as a PNG.
Used by .github/workflows/android.yml before the APK is built; android-wrapper/screen_patch.py copies the PNGs into the app.
Run from the repo root: python tools/make_screen_art.py [output folder]   (needs playwright + chromium)"""
import os, sys, pathlib, threading, http.server

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROPS = ('eye', 'ok', 'wait', 'shield', 'sleep', 'off', 'coin', 'cx', 'lock')   # the states of the bubble card, see ScreenLogic.PICS
W, H = 360, 255                                                         # px, the cartoons' own 240 x 170 shape; the app shows them about 96 dp wide

class _Site(http.server.SimpleHTTPRequestHandler):
    """Serves the repo like the site does (/ = static/index.html, /static/..., /config.js missing) so the page's own scripts load. Nothing leaves this computer."""
    def log_message(self, *a): pass
    def translate_path(self, path):
        path = path.split('?')[0]
        if path in ('/', '/index.html'): path = '/static/index.html'
        return str(ROOT) + path

def clean(f):
    """The page leaves a faint haze (alpha under 16) behind the picture; drop it so the card is clean and the file small."""
    from PIL import Image
    im = Image.open(f).convert('RGBA'); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a < 16: px[x, y] = (0, 0, 0, 0)
    im.save(f, optimize=True)

def main(out):
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Site); threading.Thread(target=srv.serve_forever, daemon=True).start()
    host = 'http://127.0.0.1:%d' % srv.server_address[1]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 480, 'height': 480}, reduced_motion='reduce', color_scheme='dark', device_scale_factor=1)
        pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(host) else r.abort())
        pg.goto(host + '/'); pg.wait_for_function('window.IL2 && window.IL2.eye', timeout=20000)
        pg.add_style_tag(content='html,body{background:transparent!important}body>*:not(#sxart){display:none!important}#sxart{position:fixed;left:0;top:0;width:%dpx;height:%dpx}#sxart svg{width:100%%;height:100%%}' % (W, H))
        pg.set_viewport_size({'width': W, 'height': H})
        made = []
        for k in PROPS:
            ok = pg.evaluate("""k => { var o = document.getElementById('sxart'); if (!o) { o = document.createElement('div'); o.id = 'sxart'; document.body.appendChild(o); }
                                       if (!window.IL2[k]) return false; o.innerHTML = window.IL2[k]; return true; }""", k)
            if not ok: print('STOP: no cartoon named', k); sys.exit(1)
            f = out / ('sxart_%s.png' % k)
            pg.locator('#sxart').screenshot(path=str(f), omit_background=True)
            clean(f); made.append(f.name)
        b.close()
    srv.shutdown()
    print('drew', ' '.join(made))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'android-wrapper' / 'branding' / 'art'))
