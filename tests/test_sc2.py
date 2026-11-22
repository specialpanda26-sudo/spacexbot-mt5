"""Checks Section SC2: the Screen assistant card and talking panel (static/screen.js + IL2.eye in static/index.html).
screen.js runs in node against a fake page, a fake screen share and a fake server (no temp files, no network). Run: python tests/test_sc2.py"""
import os, re, sys, json, shutil, subprocess
import xml.etree.ElementTree as ET
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
J = open(os.path.join(ROOT, 'static', 'screen.js'), encoding='utf-8').read()
R = []
def T(n, ok): R.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n)
def done(): print('%d/%d passed' % (sum(R), len(R))); sys.exit(0 if all(R) else 1)

# ---- static checks ----
T('index.html loads screen.js once, right after trade_on.js', S.count('/static/screen.js') == 1 and '<script src="/static/trade_on.js"></script><script src="/static/screen.js"></script>' in S)
T('IL2.eye is defined once, inside the picture closure', S.count('IL2.eye=il(') == 1 and S.find('IL2.eye=il(') < S.find('var ILM={plug:'))
css = J[J.find('st.textContent ='):J.find('document.head.appendChild(st)')]
T('the style uses no hard-coded colour and no font name', css != '' and not re.search(r'#[0-9a-fA-F]{3,8}\b|Arial|rgb\(|hsl\(', css))
m = re.search(r'@media \(prefers-reduced-motion:no-preference\)\{', css)
T('all animation sits inside prefers-reduced-motion:no-preference', bool(m) and 'animation' not in css[:m.start()] and css[m.start():].count('animation:') == 2)
T('the picture is never put in storage, a log or an alert', not re.search(r'localStorage|sessionStorage|indexedDB|console\.|alert\(|document\.cookie', J))
T('the picture is only sent to the one read route, as context trade', J.count('"/api/screen/read"') == 1 and 'context: "trade"' in J)
T('no Claude / Anthropic wording on the page code', not re.search(r'(?i)claude|anthropic', J))
T('the page never says the AI works or promises profit', not re.search(r'(?i)\bprofit\b|guarantee|will win|sure ', J))
if not shutil.which('node'): print('SKIP node not installed'); done()

# ---- the cartoons, run from the real page code ----
a = S.find('var CH2='); b = S.find('IL2.rs=', a); c = S.find('/* ---- topic cartoons'); d = S.find('var ILM=', c); d2 = S.find(';', S.find('}', d)) + 1
code = S[a:b] + 'IL2.rs=0;' + S[c:d2] + ';return {IL2:IL2};'
r = subprocess.run(['node', '-e', 'const o=new Function("window",process.argv[1])({});console.log(JSON.stringify(o.IL2))', code], capture_output=True, text=True)
if r.returncode: print(r.stderr[-400:]); T('node ran the picture code', False); done()
I = json.loads(r.stdout.strip().splitlines()[-1])
CH = I['mail'][I['mail'].find('<g transform="translate(112 40)">'):]
try: ET.fromstring(I['eye']); ok = True
except Exception: ok = False
T('eye: a valid picture with the same dark-haired character as the rest', ok and CH in I['eye'] and I['eye'].startswith('<svg class="ill2"'))
T('eye: a magnifier that can sweep (class mg), candles, sparkles', 'class="mg"' in I['eye'] and I['eye'].count('<rect') >= 3 and I['eye'].count('class="sp"') == 2)
T('every picture the panel can show exists', all(k in I for k in ('eye', 'ok', 'shield', 'sleep', 'wait', 'off', 'coin', 'cx')))

# ---- screen.js in node: fake page, fake share, fake server ----
H = r'''
const vm=require("vm");const src=process.argv[1];const IL=JSON.parse(process.argv[2]);
function run(o){
  o=o||{};const out={calls:[],toasts:[],timers:[],stopped:0,gdm:[],ended:[]};
  function mk(tag){const e={tag,children:[],listeners:{},style:{},hidden:false,_h:"",attrs:{},videoWidth:o.vw==null?1920:o.vw,videoHeight:o.vh==null?1080:o.vh,
    set innerHTML(v){this._h=v},get innerHTML(){return this._h},appendChild(c){this.children.push(c);return c},insertBefore(c){this.children.push(c);return c},
    addEventListener(t,f){this.listeners[t]=f},setAttribute(k,v){this.attrs[k]=v},firstChild:null,textContent:"",
    getContext(){return {drawImage(){}}},toDataURL(t,q){out.q=(out.q||[]).concat([q]);const n=(o.big||[]).indexOf(q)>-1?900000:1200;return "data:image/jpeg;base64,"+"A".repeat(n)},play(){return Promise.resolve()}};return e}
  const vb=mk("div"),head=mk("head");let card=null;
  const doc={getElementById:id=>id==="view-bot"?vb:null,createElement:t=>mk(t),head:head};
  vb.appendChild=vb.insertBefore=function(c){card=c;return c};
  const tracks=[{stop(){out.stopped++},onended:null}];
  const sb={document:doc,navigator:o.noShare?{}:{mediaDevices:{getDisplayMedia(c){out.gdm.push(c);return o.deny?Promise.reject({name:"NotAllowedError"}):Promise.resolve({getTracks:()=>tracks})}}},
    setTimeout:(f,ms)=>{const t={f,ms,on:true};out.timers.push(t);return out.timers.length},clearTimeout:id=>{if(out.timers[id-1])out.timers[id-1].on=false},setInterval:(f)=>{out.iv=f;return 1},
    SXA:{user:()=>sb.U,api:(p,x)=>{out.calls.push({p,x});const h=o.server||(()=>({}));try{const v=h(p,x);if(v&&v.err){const e=new Error(v.err);e.status=v.status;return Promise.reject(e)}return Promise.resolve(v)}catch(e){return Promise.reject(e)}}},
    U:o.user||{uid:"u1",verified:true,admin:false,active:true}};
  sb.window=sb;sb.IL2=IL;sb.sxToast=t=>out.toasts.push(t);sb.addEventListener=()=>{};
  vm.runInNewContext(src,sb);
  out.sb=sb;out.card=()=>card;out.html=()=>card?card.innerHTML:"";out.tracks=tracks;
  out.click=a=>{const b={getAttribute:()=>a,disabled:false};card.listeners.click({target:{closest:()=>b}})};
  out.tick=async()=>{const t=out.timers.filter(x=>x.on).pop();if(!t)return null;t.on=false;t.f();for(let i=0;i<6;i++)await Promise.resolve();return t};
  out.settle=async()=>{for(let i=0;i<12;i++)await Promise.resolve()};
  return out}
const STATUS={on:true,trade:{allowed:true,used:0,cap:60},learn:{allowed:true,used:0,cap:10},gap:10};
const READ={readable:true,symbol:"XAUUSD",timeframe:"M15",trend:"up",bias:"buy",patterns:["pullback"],support:[2310.5],resistance:[2330],last_price:2320,strategies:["jg_pullback"],note:"x"};
const SIG={side:"buy",strategy:"jg_pullback",strategy_name:"Pullback",entry:2320,sl:2312,tp:2336};
const srv=(over)=>(p,x)=>p==="/api/screen/status"?STATUS:(over?over(p,x):{ok:true,read:READ,bot:{code:"agree",text:"The bot agrees: its strategies (Pullback) also see a buy.",signal:SIG},used:1,cap:60,context:"trade"});
const res={};
(async()=>{
 // 1 off, ordinary person: card hidden. off, admin: card with switch
 let a=run({server:srv(),user:{uid:"u1",verified:true,admin:false,active:true}});a.sb.SXA.api=((f)=>(p,x)=>p==="/api/screen/status"?Promise.resolve({on:false,trade:{allowed:true,used:0,cap:60},gap:10}):f(p,x))(a.sb.SXA.api);
 // (re-run with a proper off status through a custom server)
 a=run({server:(p)=>p==="/api/screen/status"?{on:false,trade:{allowed:true,used:0,cap:60},gap:10}:{},user:{uid:"u1",verified:true,admin:false,active:true}});await a.tick();await a.tick();await a.settle();
 res.offHidden=a.card().hidden===true;
 a=run({server:(p,x)=>p==="/api/screen/status"?{on:false,trade:{allowed:true,used:0,cap:60},gap:10}:{ok:true},user:{uid:"u1",verified:true,admin:true,active:true}});await a.tick();await a.settle();
 res.offAdmin={shown:a.card().hidden===false,off:/>Off</.test(a.html()),sw:a.html().includes('data-a="admin1"'),watchDisabled:/data-a="watch" disabled/.test(a.html())};
 a.click("admin1");await a.settle();res.adminCall=a.calls.filter(c=>c.p==="/api/admin/settings").map(c=>c.x.body);
 // 2 no plan
 a=run({server:(p)=>p==="/api/screen/status"?{on:true,trade:{allowed:false,used:0,cap:60},gap:10}:{},user:{uid:"u1",verified:true,admin:false,active:false}});await a.tick();await a.settle();
 res.noPlan={chip:/Plan needed/.test(a.html()),watchDisabled:/data-a="watch" disabled/.test(a.html())};
 // 3 happy path
 a=run({server:srv()});await a.tick();await a.settle();
 res.ready={chip:/>Ready</.test(a.html()),watchOn:!/data-a="watch" disabled/.test(a.html()),idlePic:a.html().includes(IL.eye)};
 a.click("watch");await a.settle();
 res.gdm={n:a.gdm.length,audio:a.gdm[0]&&a.gdm[0].audio,fps:a.gdm[0]&&a.gdm[0].video&&a.gdm[0].video.frameRate,watching:/Watching/.test(a.html())&&/Stop watching/.test(a.html())};
 await a.tick();await a.settle();
 const rd=a.calls.filter(c=>c.p==="/api/screen/read");
 res.read={n:rd.length,ctx:rd[0]&&rd[0].x.body.context,method:rd[0]&&rd[0].x.method,len:rd[0]&&rd[0].x.body.image.length,isB64:rd[0]&&/^A+$/.test(rd[0].x.body.image),q:a.q};
 res.agree={head:/I see a possible trade/.test(a.html()),pic:a.html().includes(IL.ok),plan:/own plan: buy near 2320, stop loss 2312, target 2336 \(Pullback\)/.test(a.html()),levels:/Support near 2310.5\. Resistance near 2330/.test(a.html()),
   market:/Market: XAUUSD/.test(a.html()),notAdvice:/not advice/.test(a.html()),used:/1 of 60 reads used today/.test(a.html()),noImage:!a.html().includes("AAAAAAAA")};
 const nx=a.timers.filter(x=>x.on).pop();res.next=nx&&nx.ms;
 // stop
 a.click("stop");res.stop={stopped:a.stopped,html:/Watch my screen/.test(a.html()),pending:a.timers.filter(x=>x.on).length};
 // 3b big picture: reduces quality in steps
 a=run({server:srv(),big:[0.7,0.55]});await a.tick();await a.settle();a.click("watch");await a.settle();await a.tick();await a.settle();
 res.steps={q:a.q,sent:a.calls.filter(c=>c.p==="/api/screen/read").length};
 a=run({server:srv(),big:[0.7,0.55,0.4]});await a.tick();await a.settle();a.click("watch");await a.settle();await a.tick();await a.settle();
 res.tooBig={sent:a.calls.filter(c=>c.p==="/api/screen/read").length,msg:/too big/.test(a.html()),watching:/Stop watching/.test(a.html())};
 // 4 errors
 for(const [k,st,msg] of [["e429",429,"One read every 10 seconds, please wait a moment."],["e402",402,"The screen assistant needs an active plan."],["e403",403,"The screen assistant is switched off for now."],["e502",502,"The AI reader did not answer (500). Try again in a moment."]]){
   a=run({server:srv((p)=>({err:msg,status:st}))});await a.tick();await a.settle();a.click("watch");await a.settle();await a.tick();await a.settle();
   res[k]={text:a.html().includes(msg.replace(/&/g,"&amp;")),watching:/Stop watching/.test(a.html()),stopped:a.stopped,pic:["e429","e402","e403","e502"].indexOf(k)}; res[k].picName=({e429:"wait",e402:"coin",e403:"off",e502:"cx"})[k];res[k].picOk=a.html().includes(IL[res[k].picName])}
 // 5 each verdict
 for(const [code,head,pic,text] of [["blocked","cannot trade right now","shield","The bot sees a buy setup but this cannot work right now: daily loss limit hit. It does not trade."],["blocked","cannot trade right now","sleep","this cannot work right now: weekend/Friday-night risk. It does not trade."],["disagree","We do not agree","wait","x"],["no_setup","Nothing to trade here yet","wait","x"],["bot_only","The bot sees a setup","wait","x"],["no_data","only give you the AI read","wait","x"]]){
   a=run({server:srv(()=>({ok:true,read:READ,bot:{code,text,signal:code==="agree"?SIG:null},used:2,cap:60}))});await a.tick();await a.settle();a.click("watch");await a.settle();await a.tick();await a.settle();
   (res.verdicts=res.verdicts||[]).push({code,head:a.html().includes(head),pic:a.html().includes(IL[pic]),notOk:!a.html().includes("I see a possible trade")})}
 // unreadable
 a=run({server:srv(()=>({ok:true,read:{readable:false,note:"I cannot see a price."},bot:null,used:1,cap:60}))});await a.tick();await a.settle();a.click("watch");await a.settle();await a.tick();await a.settle();
 res.unread={head:/I could not read this chart/.test(a.html()),pic:a.html().includes(IL.off),note:/cannot see a price/.test(a.html())};
 // 5b words from the server or the AI are shown as text, never as page code
 a=run({server:srv(()=>({ok:true,read:Object.assign({},READ,{symbol:"<img src=x onerror=1>",patterns:["<b>x</b>"]}),bot:{code:"no_setup",text:"<script>1</script>",signal:null},used:1,cap:60}))});await a.tick();await a.settle();a.click("watch");await a.settle();await a.tick();await a.settle();
 res.xss={raw:/<img src=x|<script>|<b>x<\/b>/.test(a.html()),esc:/&lt;img src=x/.test(a.html())&&/&lt;script&gt;/.test(a.html())};
 // 6 no share support / cancelled
 a=run({server:srv(),noShare:true});await a.tick();await a.settle();a.click("watch");await a.settle();res.noShare=/cannot share the screen/.test(a.html())&&!/Stop watching/.test(a.html());
 a=run({server:srv(),deny:true});await a.tick();await a.settle();a.click("watch");await a.settle();res.deny=/Sharing was cancelled\. Nothing was sent/.test(a.html())&&a.calls.filter(c=>c.p==="/api/screen/read").length===0;
 // 7 the browser's own Stop sharing button
 a=run({server:srv()});await a.tick();await a.settle();a.click("watch");await a.settle();a.tracks[0].onended();res.ended={stopped:a.stopped,html:/Watch my screen/.test(a.html()),timers:a.timers.filter(x=>x.on).length};
 // 8 another person signs in: sharing stops
 a=run({server:srv()});await a.tick();await a.settle();a.click("watch");await a.settle();a.sb.U={uid:"u2",verified:true,admin:false,active:true};a.iv();await a.settle();res.switchUser={stopped:a.stopped>0};
 // 9 gap: next read waits max(20 s, gap + 1 s)
 const S2=Object.assign({},STATUS,{gap:45});a=run({server:(p,x)=>p==="/api/screen/status"?S2:srv()(p,x)});await a.tick();await a.settle();a.click("watch");await a.settle();await a.tick();await a.settle();const n2=a.timers.filter(x=>x.on).pop();res.gapMs=n2&&n2.ms;
 // 10 read now button while busy does nothing twice
 a=run({server:srv()});await a.tick();await a.settle();a.click("watch");await a.settle();a.click("now");a.click("now");await a.settle();res.once=a.calls.filter(c=>c.p==="/api/screen/read").length;
 // 11 pure helpers
 const SX=a.sb.SXSC;res.fit=[SX.fit(1920,1080),SX.fit(800,600),SX.fit(0,5),SX.fit(1000,3000)];
 console.log(JSON.stringify(res));
})().catch(e=>{console.log(JSON.stringify({crash:String(e&&e.stack||e)}))});
'''
r = subprocess.run(['node', '-e', H, J, json.dumps(I)], capture_output=True, text=True)
try: O = json.loads(r.stdout.strip().splitlines()[-1])
except Exception: print(r.stdout[-600:], r.stderr[-600:]); T('node ran screen.js', False); done()
if 'crash' in O: print(O['crash'][:600]); T('node ran screen.js', False); done()
T('with the switch off an ordinary person sees no card', O['offHidden'])
T('with the switch off an admin sees the card, chip Off, a Switch it on button and no Watch', O['offAdmin'] == {'shown': True, 'off': True, 'sw': True, 'watchDisabled': True})
T('the admin button posts screen_on 1 to the admin settings route', O['adminCall'] == [{'screen_on': '1'}])
T('without a plan: chip Plan needed and Watch disabled', O['noPlan'] == {'chip': True, 'watchDisabled': True})
T('ready: chip Ready, Watch enabled, the eye cartoon shows', O['ready'] == {'chip': True, 'watchOn': True, 'idlePic': True})
T('Watch asks for the screen with no audio and 1 frame a second, then the chip says Watching', O['gdm'] == {'n': 1, 'audio': False, 'fps': 1, 'watching': True})
T('one read is POSTed as context trade with a base64 picture under the size cap', O['read']['n'] == 1 and O['read']['ctx'] == 'trade' and O['read']['method'] == 'POST' and 0 < O['read']['len'] <= 780000 and O['read']['isB64'])
T('the first try uses JPEG quality 0.7', O['read']['q'][0] == 0.7)
T('agree: "I see a possible trade", the ok cartoon, the bot\'s own plan, levels, market, a not-advice line, the reads used', all(O['agree'].values()))
T('the picture is not left in the page', O['agree']['noImage'])
T('the next read waits at least 20 s', O['next'] == 20000)
T('Stop watching stops the share tracks, clears the timer and shows Watch again', O['stop'] == {'stopped': 1, 'html': True, 'pending': 0})
T('a picture too big at 0.7 and 0.55 is sent at 0.4 (steps down)', O['steps']['q'][:3] == [0.7, 0.55, 0.4] and O['steps']['sent'] == 1)
T('a picture too big at every quality is not sent and says so in words', O['tooBig'] == {'sent': 0, 'msg': True, 'watching': True})
for k, pic in (('e429', 'wait'), ('e402', 'coin'), ('e403', 'off'), ('e502', 'cx')):
    T(k + ': the server\'s own words and the ' + pic + ' cartoon', O[k]['text'] and O[k]['picOk'])
T('429 and 502 keep watching; 402 and 403 stop the share', O['e429']['watching'] and O['e502']['watching'] and not O['e402']['watching'] and not O['e403']['watching'] and O['e402']['stopped'] == 1 and O['e403']['stopped'] == 1 and O['e429']['stopped'] == 0)
for v in O['verdicts']: T('verdict %s: its headline and cartoon, never "possible trade"' % v['code'], v['head'] and v['pic'] and v['notOk'])
T('a chart the AI could not read: "could not read", the off cartoon, the AI note', O['unread'] == {'head': True, 'pic': True, 'note': True})
T('text from the server or the AI is escaped, never shown as page code', O['xss'] == {'raw': False, 'esc': True})
T('a browser that cannot share the screen says so in words', O['noShare'])
T('cancelling the share sends nothing', O['deny'])
T('the browser\'s own Stop sharing button ends watching and clears the timer', O['ended'] == {'stopped': 1, 'html': True, 'timers': 0})
T('another person signing in stops the share', O['switchUser']['stopped'])
T('the wait between reads follows the server gap plus one second', O['gapMs'] == 46000)
T('tapping Read now twice sends one read', O['once'] == 1)
T('fit: long side 1280, never bigger, bad sizes refused', O['fit'][0] == {'w': 1280, 'h': 720} and O['fit'][1] == {'w': 800, 'h': 600} and O['fit'][2] is None and O['fit'][3] == {'w': 427, 'h': 1280})
done()
