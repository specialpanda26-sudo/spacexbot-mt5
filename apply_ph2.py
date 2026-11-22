"""PH2: phone-only bot + working Watch-my-screen on the phone app. Run from the repo folder: python apply_ph2.py   (add --test to also run the tests)
Safe to run twice. If any old text is not found exactly once, NOTHING is changed.
1) Phone flow: bot app + Deriv app + MT5 app. No EA, no key, no bridge. Deriv trades by itself; MT5 gets signals with your lot size; the PC bridge is folded under Advanced; the server price feed is on by default.
2) Watch my screen: in the Android app it now starts the floating bubble (SxbScreen plugin, already in the APK code) instead of the browser share that phones do not have.
   Needs a new APK build after you push (GitHub Actions > Build Android APK)."""
import os, sys, subprocess
H, B, R = 'static/index.html', 'backend/brokers.py', 'render.yaml'
E = [
 (B, "'mt5': {'tile': 'Via your MT5 app', 'works': 'Trades through your MT5 app and the SpaceXBridge EA.', 'not': 'This site does not check your key or read your balance. Your MT5 app does that.'},",
     "'mt5': {'tile': 'Signals to your MT5 app', 'works': 'Sends you each signal with your lot size. You tap Take it and place it in your MT5 phone app. No EA and no key needed.', 'not': 'It does not place the trade inside MT5 for you, and this site does not read your MT5 balance. A PC with the EA is only an advanced option.'},", "Signals to your MT5 app"),
 (B, "'Deriv MT5': {'tile': 'Via your MT5 app', 'works': 'Trades on your Deriv MT5 account through the SpaceXBridge EA, next to FBS. Your positions show in your MT5 app.', 'not': 'The MT5 phone app cannot run the EA: MT5 must be open on a Windows PC or a VPS. Deriv may name markets differently (set Symbols or SymbolSuffix in the EA). This site does not read your Deriv MT5 balance.'},",
     "'Deriv MT5': {'tile': 'Signals to your MT5 app', 'works': 'Sends you each signal with your lot size. You tap Take it and place it in your Deriv MT5 phone app. No EA and no key needed.', 'not': 'It does not place the trade inside MT5 for you. Deriv may name markets differently, so check the symbol on your MT5 chart. For fully automatic trading use the Deriv tile.'},", "place it in your Deriv MT5 phone app"),
 (H, "Step 1 of 3. Type your broker's server name (you see it when you log in to MT5), for example FBS-Demo. Never type your MT5 password here. Step 2: make your key in the Connect your MT5 card. Step 3: put the key into the SpaceXBridge EA and keep MT5 open. Connected shows only once your MT5 reports in.",
     "Type your broker's server name (you see it when you log in to MT5), for example FBS-Demo. Never type your MT5 password here. Next: open the Connect tab and turn on Phone mode. The bot then sends you each signal with your lot size and you place it in your MT5 app. No EA and no key needed.", "No EA and no key needed.\""),
 (H, "server name saved. Next: make your key in Connect your MT5.", "server name saved. Next: turn on Phone mode in the Connect tab.", "Next: turn on Phone mode in the Connect tab"),
 (H, "<p class=\"note\">For MT5 brokers only (FBS, Exness, HFM, XM, IC Markets, Pepperstone). Using Deriv? You do not need this card.</p>'; }",
     "<p class=\"note\">Advanced: only for a PC or VPS with MT5 open. On a phone you do NOT need this card. Use Phone mode (signals for your MT5 app) or the Deriv tile (the bot trades by itself). Using Deriv? You do not need this card.</p>'; }", "Advanced: only for a PC or VPS"),
 (H, "'<p class=\"note\">Make your personal key, then paste it into the EA on your own MT5. Your trades, limits and results stay separate from everyone else.</p><button class=\"btn primary block\" data-act=\"mk\"' + (BUSY ? \" disabled\" : \"\") + '>Make my key</button><p class=\"err\" role=\"alert\">' + esc(ERR) + \"</p>\" + steps();",
     "'<p class=\"note\">Nothing to set up on a phone. Turn on <b>Phone mode</b> below for MT5 signals, or connect Deriv for automatic trading. Only if you run MT5 on a PC or VPS, open Advanced to make a key.</p><details><summary>Advanced: PC bridge (EA and key)</summary><button class=\"btn primary block\" data-act=\"mk\"' + (BUSY ? \" disabled\" : \"\") + '>Make my key</button><p class=\"err\" role=\"alert\">' + esc(ERR) + \"</p>\" + steps() + \"</details>\";", "Advanced: PC bridge (EA and key)"),
 (R, "    healthCheckPath: /healthz\n", "    healthCheckPath: /healthz\n    envVars:\n      - key: FEED_ON          # phone-only: the server finds signals itself, no EA needed\n        value: \"1\"\n", "key: FEED_ON"),
 ('static/live.js', r"""ready: ready, api: api, user:""", r"""ready: ready, api: api, token: tok, user:""", "api: api, token: tok"),
 ('static/screen.js', r"""var STREAM = null, VID = null, TIMER = 0, UID = null;""", r"""var STREAM = null, VID = null, TIMER = 0, UID = null, NATIVE = false, TT = 0;""", "NATIVE = false, TT = 0"),
 ('static/screen.js', r"""  function canShare() { return !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia); }""",
  r"""  function canShare() { return !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia); }
  function plug() { var c = window.Capacitor; return (c && c.isNativePlatform && c.isNativePlatform() && c.Plugins && c.Plugins.SxbScreen) || null; }   /* PH2: the Android app's own screen plugin */""", "function plug()"),
 ('static/screen.js', r"""'<button type="button" class="btn" data-a="stop">Stop watching</button><button type="button" class="btn primary" data-a="now"' + (BUSY ? " disabled" : "") + ">Read now</button>""",
  r"""'<button type="button" class="btn" data-a="stop">' + (NATIVE ? "Stop bubble" : "Stop watching") + '</button><button type="button" class="btn primary" data-a="now"' + (BUSY ? " disabled" : "") + (NATIVE ? " hidden" : "") + ">Read now</button>""", "NATIVE ? \"Stop bubble\""),
 ('static/screen.js', r"""        (ERR ? '<p class="err">' + esc(ERR) + "</p>" : "") +""",
  r"""        (NATIVE ? '<p class="note">The bubble is on. Open your MT5 app, then tap the bubble to read the chart. Android asks you to allow screen sharing each time.</p>' : "") +
        (ERR ? '<p class="err">' + esc(ERR) + "</p>" : "") +""", "The bubble is on. Open your MT5 app"),
 ('static/screen.js', r"""    STREAM = null; if (VID) { try { VID.srcObject = null; } catch (e) {} } VID = null; WATCH = false; BUSY = false;""",
  r"""    STREAM = null; if (VID) { try { VID.srcObject = null; } catch (e) {} } VID = null; WATCH = false; BUSY = false;
    if (NATIVE) { NATIVE = false; clearInterval(TT); var P0 = plug(); if (P0 && P0.stop) { try { P0.stop(); } catch (e) {} } }""", "var P0 = plug()"),
 ('static/screen.js', r"""  function start() {
    if (WATCH) return;""",
  r"""  function refreshTok(P) { SXA.token().then(function (n) { if (n && P.setToken) P.setToken({ token: n }); }).catch(function () {}); }   /* sign-in tokens expire: hand over a fresh one */
  function startNative(P) {
    ERR = "";
    SXA.token().then(function (t) {
      if (!t) { ERR = "Please sign in first."; draw(); return; }
      return P.start({ server: location.origin, token: t, context: "trade" }).then(function () {
        NATIVE = true; WATCH = true; R = { kind: "idle" }; draw();
        clearInterval(TT); TT = setInterval(function () { refreshTok(P); }, 600000);
      });
    }).catch(function (e) { ERR = (e && e.message) ? String(e.message) : "Could not start the screen bubble."; draw(); });
  }
  function start() {
    if (WATCH) return;""", "function startNative(P)"),
 ('static/screen.js', r"""    if (!canShare()) { ERR = "This browser cannot share the screen. Use Chrome, Edge or Firefox on a computer. The phone app version comes later."; draw(); return; }""",
  r"""    var P = plug();
    if (P && P.start) { startNative(P); return; }          /* PH2: in the Android app use the floating bubble, not the browser's screen share */
    if (!canShare()) { ERR = "This browser cannot share the screen. It works in the spaceXBot Android app (install the newest build) or in Chrome, Edge or Firefox on a computer."; draw(); return; }""", "var P = plug();"),
 ('static/screen.js', r"""  window.addEventListener("pagehide", function () { stop(true); });""",
  r"""  window.addEventListener("pagehide", function () { if (!NATIVE) stop(true); });          /* the bubble must keep running while MT5 is on top */
  if (document.addEventListener) document.addEventListener("visibilitychange", function () {
    var P = NATIVE ? plug() : null; if (!P || document.hidden) return;
    refreshTok(P);
    if (P.status) P.status().then(function (s) { if (s && s.running === false) { NATIVE = false; WATCH = false; clearInterval(TT); R = { kind: "idle" }; draw(); } }).catch(function () {});
  });""", "visibilitychange"),

 ('tests/test_d2.py', r"""T('its note says the phone app cannot run the EA', 'phone app cannot run the EA' in a['not'] and 'EA' in a['works'])""",
  r"""T('its note says no EA and no key are needed', 'No EA and no key needed' in a['works'] and 'MT5 phone app' in a['works'])""", "its note says no EA and no key"),
 ('tests/test_d2.py', r"""T('its note warns about market names', 'SymbolSuffix' in a['not'])""", r"""T('its note warns about market names', 'name markets differently' in a['not'])""", "name markets differently' in a"),
 ('tests/test_deriv_e2e.py', r"""T('W1 MT5 popup gives three plain steps', 'Step 1 of 3' in idx and 'Connect your MT5 card' in idx)""",
  r"""T('W1 MT5 popup is phone-first: no EA, no key', 'turn on Phone mode' in idx and 'No EA and no key needed.' in idx)""", "W1 MT5 popup is phone-first"),

]
TEST = r'''"""PH2: the Watch-my-screen button uses the Android app's own screen plugin (SxbScreen) instead of the browser's screen share.
screen.js runs in node against a fake page and a fake native plugin. Run: python tests/test_ph2.py"""
import os, sys, json, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = open(os.path.join(ROOT, 'static', 'screen.js'), encoding='utf-8').read()
L = open(os.path.join(ROOT, 'static', 'live.js'), encoding='utf-8').read()
P = F = 0
def T(n, ok):
    global P, F
    if ok: P += 1; print('PASS', n)
    else: F += 1; print('FAIL', n)
T('live.js hands out the sign-in token', 'token: tok' in L)
H = r"""
const vm=require("vm");const src=process.argv[1];const out={calls:[],plug:[],stopped:0};
function mk(){const e={children:[],listeners:{},style:{},hidden:false,_h:"",set innerHTML(v){this._h=v},get innerHTML(){return this._h},appendChild(c){return c},insertBefore(c){return c},addEventListener(t,f){this.listeners[t]=f},setAttribute(){},firstChild:null};return e}
const vb=mk();let card=null;vb.insertBefore=function(c){card=c;return c};
const handlers={};
const doc={head:mk(),getElementById:id=>id==="view-bot"?vb:null,createElement:()=>mk(),hidden:false,addEventListener(t,f){handlers[t]=f}};
let running=true;
const plugin={start(o){out.plug.push(["start",o]);return Promise.resolve({running:true})},stop(){out.stopped++;return Promise.resolve()},setToken(o){out.plug.push(["setToken",o]);return Promise.resolve()},status(){return Promise.resolve({running})}};
const sb={document:doc,navigator:{},location:{origin:"https://x.onrender.com"},Capacitor:{isNativePlatform:()=>true,Plugins:{SxbScreen:plugin}},
 setTimeout:(f)=>1,clearTimeout(){},setInterval:(f)=>{out.iv=f;return 7},clearInterval(){},
 SXA:{user:()=>({uid:"u1",verified:true,admin:false,active:true}),token:()=>Promise.resolve("tok-1234567890123456789012345"),api:(p,x)=>{out.calls.push(p);return Promise.resolve({on:true,trade:{allowed:true,used:0,cap:60},gap:10})}}};
sb.window=sb;sb.IL2={};sb.sxToast=()=>{};sb.addEventListener=(t,f)=>{handlers[t]=f};
vm.runInNewContext(src,sb);
const settle=async()=>{for(let i=0;i<15;i++)await Promise.resolve()};
(async()=>{
 const r={};await settle();
 const click=a=>{card.listeners.click({target:{closest:()=>({getAttribute:()=>a,disabled:false})}})};
 click("watch");await settle();
 const st=out.plug.find(x=>x[0]==="start");
 r.started=!!st&&st[1].server==="https://x.onrender.com"&&st[1].token.length>=20&&st[1].context==="trade";
 r.ui=/Stop bubble/.test(card.innerHTML)&&/hidden>Read now/.test(card.innerHTML)&&/tap the bubble/.test(card.innerHTML)&&!/cannot share the screen/.test(card.innerHTML);
 handlers.pagehide&&handlers.pagehide();r.keptOnPagehide=out.stopped===0;
 out.iv&&out.iv();await settle();r.refreshed=out.plug.some(x=>x[0]==="setToken");
 running=false;doc.hidden=false;handlers.visibilitychange&&handlers.visibilitychange();await settle();
 r.resync=/Watch my screen/.test(card.innerHTML)&&!/Stop bubble/.test(card.innerHTML);
 click("watch");await settle();click("stop");await settle();r.stopCalled=out.stopped>=1&&/Watch my screen/.test(card.innerHTML);
 console.log(JSON.stringify(r));
})();
"""
r = subprocess.run(['node', '-e', H, J], capture_output=True, text=True, timeout=60)
try: O = json.loads(r.stdout.strip().splitlines()[-1])
except Exception: O = {}; print(r.stdout, r.stderr)
T('Watch in the Android app starts the native bubble with server, token and trade context', O.get('started'))
T('the card shows Stop bubble and the MT5 hint, no browser share message, no Read now', O.get('ui'))
T('leaving the app for MT5 does not stop the bubble', O.get('keptOnPagehide'))
T('a fresh sign-in token is handed to the bubble', O.get('refreshed'))
T('if Android stopped the bubble, the card resets', O.get('resync'))
T('Stop bubble stops the native service', O.get('stopCalled'))
print('%d/%d passed' % (P, P + F)); sys.exit(1 if F else 0)
'''
files, bad = {}, []
for p, old, new, mk in E:
    s = files.get(p)
    if s is None: s = files[p] = open(p, encoding='utf-8').read()
    if mk in s: print('skip (already there):', mk[:46]); continue
    if s.count(old) != 1: bad.append((p, old[:60], s.count(old))); continue
    files[p] = s.replace(old, new, 1); print('edited:', mk[:46])
if bad:
    for b in bad: print('STOP: not found exactly once (found %d) in %s -> %s' % (b[2], b[0], b[1]))
    print('Nothing was changed.'); sys.exit(1)
files['tests/test_ph2.py'] = TEST
for p, s in files.items():
    open(p + '.new', 'w', encoding='utf-8').write(s); os.replace(p + '.new', p)
print('edits done.')
if '--test' not in sys.argv: print('Not testing (add --test to run the tests). Next: git add -A, commit, push, then build the APK.'); sys.exit(0)
fails = []
for f in sorted(os.listdir('tests')):
    if not (f.startswith('test_') and f.endswith('.py')) or f == 'test_rk5.py': continue
    r = subprocess.run([sys.executable, 'tests/' + f], capture_output=True, text=True, timeout=300)
    if r.returncode: fails.append(f); print('FAIL', f, (r.stdout.strip().splitlines() or [''])[-1])
print('RESULT:', 'ALL TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
