"""PH2: the Watch-my-screen button uses the Android app's own screen plugin (SxbScreen) instead of the browser's screen share.
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
