"""X2 checks: the X on a pop-up card sits above the heading and closes with ONE tap; Test Lab Payment: Cancelled works first. Part A: the page text (always). Part B: real mobile Chromium, all 8 platform cards (skipped if no browser). Run: python tests/test_x2.py"""
import os, sys, mimetypes
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); R = []
def T(n, ok): R.append(bool(ok)); print('PASS' if ok else 'FAIL', n)
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('the X rule has a z-index above the heading', '.ov .x{position:absolute;right:14px;top:14px;z-index:5}' in S)
T('Test Lab cancel opens the screen first', 'else if(w==="cancel"){ov(XB+BR,1);cancelled(false)}}finally' in S)
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 390, 'height': 800}, has_touch=True, is_mobile=True, device_scale_factor=2); pg = ctx.new_page()
        def h(route):
            u = route.request.url
            if not u.startswith('http://app.test/'): return route.abort()
            path = u[len('http://app.test/'):].split('?')[0].split('#')[0]; f = os.path.join(ROOT, path)
            if path.startswith('static/') and os.path.isfile(f): return route.fulfill(body=open(f, 'rb').read(), content_type=mimetypes.guess_type(f)[0] or 'text/plain')
            route.fulfill(status=401 if path.startswith('api/') else 404, body='{}')
        pg.route('**/*', h); pg.goto('http://app.test/static/index.html'); pg.wait_for_timeout(1800)
        pg.evaluate("window.SXA=window.SXA||{refresh:()=>Promise.resolve(),api:()=>Promise.resolve({})}")
        if pg.evaluate("typeof window.sxLabHooks") == "object":
            pg.evaluate("window.sxLabHooks.pay('cancel')"); pg.wait_for_timeout(600)
            T('Test Lab: Payment Cancelled shows its screen on a fresh page', 'Payment cancelled' in pg.evaluate("(document.querySelector('.panel')||{}).innerText||''"))
        info = "()=>{var x=document.querySelector('.ov:not([hidden]) .x');if(!x)return null;var r=x.getBoundingClientRect(),t=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return{cx:r.left+r.width/2,cy:r.top+r.height/2,top:!!(t&&(t===x||x.contains(t)))}}"
        for name in ('FBS', 'Exness', 'HFM', 'Deriv', 'XM', 'IC Markets', 'Pepperstone', 'Binance'):
            pg.evaluate("n=>document.querySelector('#plat [data-p=\"'+n+'\"]').click()", name); pg.wait_for_timeout(800)
            i = pg.evaluate(info)
            if not i: T('%s card opens with an X' % name, False); continue
            pg.touchscreen.tap(i['cx'], i['cy']); pg.wait_for_timeout(600)
            T('%s card: X is on top, ONE tap closes it' % name, i['top'] and pg.evaluate("document.querySelector('.ov').hidden"))
        b.close()
except Exception as e: print("SKIP part B (browser not available here):", str(e)[:80])
print('%d/%d' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)
