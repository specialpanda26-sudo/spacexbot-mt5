"""OF1 tests: branded offline page + service worker (no Render 502 page for people who have visited before). Needs node for the worker checks. Run: python tests/test_of1.py"""
import os, sys, json, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(HERE, '_of1_test.db'), PAYHERO_CALLBACK_SECRET='s', BASE_URL='http://t', BROKER_KEY='unit-test-lock-key-0123456789', SYMBOLS='XAUUSD')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
sys.path.insert(0, ROOT)
from backend import app as A
R = []
def T(n, ok): R.append((n, bool(ok))); print('PASS' if ok else 'FAIL', n)
c = A.app.test_client()
r = c.get('/sw.js')
T('/sw.js is served as JavaScript', r.status_code == 200 and 'javascript' in r.headers.get('Content-Type', ''))
T('/sw.js is never cached by the browser and may control the whole site', 'no-cache' in r.headers.get('Cache-Control', '') and r.headers.get('Service-Worker-Allowed') == '/')
o = c.get('/offline.html'); body = o.get_data(as_text=True)
T('/offline.html is served and says it is spaceXBot', o.status_code == 200 and 'spaceXBot' in body and 'Try again' in body)
T('the offline page needs nothing from outside (no http links, no other files)', 'http://' not in body and 'https://' not in body and 'src=' not in body and '<link' not in body)
html = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
T('page registers the worker once, only on https', html.count('/*OF1-start*/') == 1 and 'register("/sw.js")' in html and 'location.protocol==="https:"' in html)
sw = open(os.path.join(ROOT, 'static', 'sw.js'), encoding='utf-8').read()
T('the worker never looks at /api/ and never at POST', "'/api/'" not in sw and "req.method !== 'GET'" in sw)
if not shutil.which('node'): print('SKIP node worker checks'); R_ = R
else:
    JS = r"""
const fs=require('fs'),vm=require('vm');const OUT=[];const ok=(n,c)=>OUT.push([n,!!c]);
function mk(net){const store=new Map(),L={},calls=[];
 const caches={open:async()=>({put:async(k,v)=>{store.set(typeof k==='string'?k:k.url,v)},add:async(r)=>{store.set('/offline.html',new Response('OFFLINE PAGE'))}}),
  match:async(k)=>{const u=typeof k==='string'?k:k.url;const v=store.get(u)||store.get(u.replace('https://x.test',''));return v?v.clone():undefined},keys:async()=>[],delete:async()=>true};
 const self={location:{origin:'https://x.test'},addEventListener:(t,f)=>{L[t]=f},skipWaiting:async()=>{},clients:{claim:async()=>{}}};
 class RQ extends Request{constructor(u,o){super(typeof u==='string'&&u[0]==='/'?'https://x.test'+u:u,o)}}
 const ctx={self,caches,Request:RQ,Response,URL,Promise,setTimeout,clearTimeout,fetch:async(r)=>{calls.push(r.url);return net(r)}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);
 const ev=(url,o={})=>{const req=new Request('https://x.test'+url,{method:o.method||'GET'});if(o.nav)Object.defineProperty(req,'mode',{value:'navigate'});let p=null;L.fetch({request:req,respondWith:x=>{p=x}});return p&&Promise.resolve(p)};
 return {L,store,calls,ev}}
(async()=>{
 let up=true,code=200;const W=mk(async()=>{if(!up)throw new Error('net');return new Response(code===200?'FRESH':'BAD',{status:code})});
 let r=await W.ev('/',{nav:1});ok('online: the page comes from the network',(await r.text())==='FRESH');
 ok('the good copy was saved',W.store.has('/'));await new Promise(r=>setTimeout(r,20));
 code=502;r=await W.ev('/',{nav:1});ok('Render 502: shows the saved app, not the 502',r.status===200&&(await r.text())==='FRESH');
 code=503;r=await W.ev('/?x=1',{nav:1});ok('503 too',(await r.text())==='FRESH');
 up=false;r=await W.ev('/',{nav:1});ok('no network: shows the saved app',(await r.text())==='FRESH');
 const W2=mk(async()=>{throw new Error('net')});await new Promise(rs=>W2.L.install({waitUntil:q=>q.then(rs)}));r=await W2.ev('/',{nav:1});ok('never visited + down: our offline page',(await r.text())==='OFFLINE PAGE');
 const W3=mk(async()=>new Response('x',{status:200}));ok('an /api/ call is not touched',W3.ev('/api/me')==null&&W3.calls.length===0);
 ok('a POST is not touched',W3.ev('/static/live.js',{method:'POST'})==null);
 ok('another page that is not a navigation or a static file is not touched',W3.ev('/healthz')==null);
 code=200;up=true;const W4=mk(async()=>new Response('JS1',{status:200}));r=await W4.ev('/static/live.js');ok('a static file is fetched fresh',(await r.text())==='JS1');
 await new Promise(r=>setTimeout(r,20));W4.calls.length=0;
 const W5=mk(async()=>new Response('x',{status:502}));ok('static file while down and nothing saved: 504, no crash',(await(await W5.ev('/static/live.js')).status)===504);
 console.log(JSON.stringify(OUT));})();
"""
    open(os.path.join(HERE, '_of1_node.js'), 'w').write(JS)
    p = subprocess.run(['node', os.path.join(HERE, '_of1_node.js'), os.path.join(ROOT, 'static', 'sw.js')], capture_output=True, text=True, timeout=90)
    os.remove(os.path.join(HERE, '_of1_node.js'))
    try:
        for n, k in json.loads(p.stdout.strip().splitlines()[-1]): T('worker: ' + n, k)
    except Exception: print(p.stdout[-300:], p.stderr[-600:]); T('worker checks ran', False)
p_, f_ = sum(1 for _, ok in R if ok), sum(1 for _, ok in R if not ok)
print('%d passed, %d failed' % (p_, f_)); os.remove(os.environ['DB_PATH']); sys.exit(1 if f_ else 0)
