"""SC3c: plug() in static/screen.js finds the SxbScreen plugin three ways (Plugins, registerPlugin, nativePromise) and only inside the native app.
screen.js runs in node against a fake page. Run: python tests/test_sc3c.py"""
import os, sys, json, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = open(os.path.join(ROOT, 'static', 'screen.js'), encoding='utf-8').read()
P = F = 0
def T(n, ok):
    global P, F
    if ok: P += 1; print('PASS', n)
    else: F += 1; print('FAIL', n)

H = r"""
const vm=require("vm");const src=process.argv[1];const mode=process.argv[2];
function mk(){const e={listeners:{},style:{},hidden:false,_h:"",set innerHTML(v){this._h=v},get innerHTML(){return this._h},appendChild(c){return c},insertBefore(c){return c},addEventListener(t,f){this.listeners[t]=f},setAttribute(){},firstChild:null};return e}
const vb=mk();let card=null;vb.insertBefore=function(c){card=c;return c};
const handlers={};
const doc={head:mk(),getElementById:id=>id==="view-bot"?vb:null,createElement:()=>mk(),hidden:false,addEventListener(t,f){handlers[t]=f}};
const out={np:[],plug:[],reg:0,gdm:0};
const direct={start(o){out.plug.push(["Plugins.start",o]);return Promise.resolve()},stop(){out.plug.push(["Plugins.stop"]);return Promise.resolve()},setToken(o){out.plug.push(["Plugins.setToken",o]);return Promise.resolve()},status(){return Promise.resolve({running:true})}};
const viaReg={start(o){out.plug.push(["reg.start",o]);return Promise.resolve()},stop(){out.plug.push(["reg.stop"]);return Promise.resolve()},setToken(o){out.plug.push(["reg.setToken",o]);return Promise.resolve()},status(){return Promise.resolve({running:true})}};
const cap={isNativePlatform:()=>mode!=="web"};
if(mode==="plugins")cap.Plugins={SxbScreen:direct};
if(mode==="register"){cap.Plugins={};cap.registerPlugin=n=>{out.reg++;out.regName=n;return viaReg}}
if(mode==="registerthrows"||mode==="registernull"){cap.registerPlugin=()=>{if(mode==="registerthrows")throw new Error("no");return null};cap.nativePromise=(p,m,o)=>{out.np.push([p,m,o]);return Promise.resolve({running:true})}}
if(mode==="native"||mode==="web"||mode==="plugins_over_native"){cap.nativePromise=(p,m,o)=>{out.np.push([p,m,o]);return Promise.resolve({running:true})}}
if(mode==="plugins_over_native")cap.Plugins={SxbScreen:direct};
if(mode==="none"){}
const sb={document:doc,navigator:mode==="web"?{mediaDevices:{getDisplayMedia(){out.gdm++;return Promise.reject({name:"NotAllowedError"})}}}:{},location:{origin:"https://x.onrender.com"},Capacitor:cap,
 setTimeout:()=>1,clearTimeout(){},setInterval:(f)=>{out.iv=f;return 7},clearInterval(){},
 SXA:{user:()=>({uid:"u1",verified:true,admin:false,active:true}),token:()=>Promise.resolve("tok-1234567890123456789012345"),api:()=>Promise.resolve({on:true,trade:{allowed:true,used:0,cap:60},gap:10})}};
sb.window=sb;sb.IL2={};sb.sxToast=()=>{};sb.addEventListener=(t,f)=>{handlers[t]=f};
vm.runInNewContext(src,sb);
const settle=async()=>{for(let i=0;i<20;i++)await Promise.resolve()};
(async()=>{
 await settle();
 const click=a=>{card.listeners.click({target:{closest:()=>({getAttribute:()=>a,disabled:false})}})};
 click("watch");await settle();
 const r={html:card.innerHTML,out};
 r.bubble=/Stop bubble/.test(card.innerHTML);
 out.iv&&out.iv();await settle();                     /* token refresh */
 click("stop");await settle();                        /* stop */
 r.out=out;
 console.log(JSON.stringify(r));
})();
"""
def run(mode):
    r = subprocess.run(['node', '-e', H, J, mode], capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: print(r.stdout, r.stderr); return {}

# 1) ONLY nativePromise (a page loaded from Render): start, setToken, stop must arrive as nativePromise("SxbScreen", method, options)
n = run('native'); np = n.get('out', {}).get('np', [])
st = [x for x in np if x[1] == 'start']
T('nativePromise only: Watch calls nativePromise("SxbScreen","start",...) with server, token and trade context',
  len(st) == 1 and st[0][0] == 'SxbScreen' and st[0][2].get('server') == 'https://x.onrender.com' and len(st[0][2].get('token', '')) >= 20 and st[0][2].get('context') == 'trade')
T('nativePromise only: the card shows Stop bubble (not the browser share message)', n.get('bubble') is True and 'cannot share the screen' not in n.get('html', ''))
sk = [x for x in np if x[1] == 'setToken']
T('nativePromise only: the token refresh arrives as nativePromise("SxbScreen","setToken",{token})', len(sk) == 1 and sk[0][0] == 'SxbScreen' and len(sk[0][2].get('token', '')) >= 20)
T('nativePromise only: Stop arrives as nativePromise("SxbScreen","stop",{})', any(x[0] == 'SxbScreen' and x[1] == 'stop' and x[2] == {} for x in np))

# 2) order of preference
p = run('plugins'); o = p.get('out', {})
T('Capacitor.Plugins.SxbScreen still works and registerPlugin is not touched', p.get('bubble') is True and any(x[0] == 'Plugins.start' for x in o.get('plug', [])) and o.get('reg') == 0)
po = run('plugins_over_native'); oo = po.get('out', {})
T('Plugins beats nativePromise when both exist', any(x[0] == 'Plugins.start' for x in oo.get('plug', [])) and not oo.get('np'))
g = run('register'); og = g.get('out', {})
T('registerPlugin("SxbScreen") is used when Plugins has no SxbScreen', g.get('bubble') is True and og.get('regName') == 'SxbScreen' and any(x[0] == 'reg.start' for x in og.get('plug', [])))
T('registerPlugin is called once, not on every use', og.get('reg') == 1)
for m in ('registerthrows', 'registernull'):
    q = run(m); T('%s: falls through to nativePromise' % m, any(x[1] == 'start' for x in q.get('out', {}).get('np', [])) and q.get('bubble') is True)

# 3) not in the native app: no plugin, no nativePromise call; the browser share path is used
w = run('web'); ow = w.get('out', {})
T('in a normal browser nativePromise is never called and the browser share is tried', not ow.get('np') and ow.get('gdm') == 1 and w.get('bubble') is False)
# 4) native app with nothing usable: a clear message, no crash
z = run('none')
T('native app with no bridge at all: the browser-share message, no crash', 'cannot share the screen' in z.get('html', '') and z.get('bubble') is False)

# 5) text checks
T('the fallback is marked in the source', 'sxb-screen-fallback' in J and 'nativePromise("SxbScreen"' in J)
print('%d/%d passed' % (P, P + F)); sys.exit(1 if F else 0)
