"""apply_ac1.py: Journal shows what the bot is doing now (new file backend/activity.py must exist first). Run in the repo folder:  python apply_ac1.py
Every old text must appear exactly once or NOTHING is changed. Safe to run twice. Atomic writes. Runs the tests at the end."""
import os, sys, subprocess
PAIRS = [
('backend/botstate.py',
"    except Exception as e: print('scan note failed', str(e)[:80])\n",
'    except Exception as e: print(\'scan note failed\', str(e)[:80])\n    try:\n        from . import activity\n        t = scan_text({\'c\': code, \'w\': why})\n        activity.log(uid, (\'Checked %s: \' % sym if code == \'nosetup\' else \'%s: \' % sym) + t, \'trade\' if code == \'signal\' else \'wait\' if code in (\'gate\', \'skip\') else \'check\')\n    except Exception as e: print(\'activity note failed\', str(e)[:80])\n\ndef scan_text(j):\n    """AC1: one scanner note in plain words (also used for the Journal \'markets\' list)."""\n    c, w = j.get(\'c\'), str(j.get(\'w\') or \'\').strip()\n    if c == \'signal\': return \'Found a setup and sent it.\'\n    if c == \'nosetup\': return \'No good setup yet.\' + (\' \' + w if w else \'\')\n    return _words(w)\n'),
('backend/burst_look.py',
"    st.put('blook:' + (uid or ''), json.dumps({'t': int(now or time.time()), 'why': str(text)[:240]}))\n",
"    st.put('blook:' + (uid or ''), json.dumps({'t': int(now or time.time()), 'why': str(text)[:240]}))\n    try:\n        from . import activity\n        activity.log(uid, 'Burst: ' + str(text), 'check', now)          # AC1\n    except Exception as e: print('activity note failed', str(e)[:80])\n"),
('backend/brokers.py',
"def set_bot(uid, name, on): st.put('bot:%s:%s' % (uid, name), '1' if on else '0')\n",
"def set_bot(uid, name, on):\n    st.put('bot:%s:%s' % (uid, name), '1' if on else '0')\n    try:\n        from . import activity\n        activity.log(uid, 'Bot switched %s on %s.' % ('ON' if on else 'OFF', name), 'bot')          # AC1\n    except Exception as e: print('activity note failed', str(e)[:80])\n"),
('backend/brokers.py',
"    st.put('why:%s:%s' % (uid, name), json.dumps({'r': str(reason)[:30], 't': int(now or time.time())}))\n",
"    st.put('why:%s:%s' % (uid, name), json.dumps({'r': str(reason)[:30], 't': int(now or time.time())}))\n    try:\n        from . import activity\n        activity.log(uid, '%s: %s' % (name, 'Connected and watching.' if reason == 'ok' else REASONS.get(reason, 'Not trading: %s' % reason)), 'check' if reason == 'ok' else 'wait', now)          # AC1\n    except Exception as e: print('activity note failed', str(e)[:80])\n"),
('backend/links.py',
"def set_bot(uid, on): st.x('UPDATE links SET bot=? WHERE uid=?', (1 if on else 0, uid))\n",
"def set_bot(uid, on):\n    st.x('UPDATE links SET bot=? WHERE uid=?', (1 if on else 0, uid))\n    try:\n        from . import activity\n        activity.log(uid, 'Bot switched %s on MT5.' % ('ON' if on else 'OFF'), 'bot')          # AC1\n    except Exception as e: print('activity note failed', str(e)[:80])\n"),
('backend/app.py',
'pnlreset, connwhy\n',
'pnlreset, connwhy, activity\n'),
('backend/app.py',
"@app.get('/api/journal')\n",
'@app.get(\'/api/activity\')\n@need(verified=True)\ndef activity_api(u):\n    """AC1: what the bot is doing right now + the live feed of its checks, for the Journal tab."""\n    return jsonify(activity.snapshot(u[\'uid\'], bool(u[\'admin\']), _paid(u[\'uid\'])))\n\n@app.get(\'/api/journal\')\n'),
('static/index.html',
'window.SXJ=SXJ;window.jmsg=jmsg;',
'var SXAC={now:null,markets:[],items:[],state:"idle"};window.SXAC=SXAC;/* AC1: what the bot is doing now, from GET /api/activity */\nwindow.SXJ=SXJ;window.jmsg=jmsg;'),
('static/index.html',
'function jall(){var T=SXJ.state',
'function acm(r){var h=function(s){var d=new Date(s*1000);return d.getHours()+":"+("0"+d.getMinutes()).slice(-2)};return r.m+(r.t-r.a>=120?" (same since "+h(r.a)+")":"")}\nfunction jall(){var AC=(window.SXAC&&window.SXAC.state==="ok")?window.SXAC:null,B=AC?AC.items.map(function(r){return{t:r.t*1000,k:"bot",m:acm(r)}}):[],T=SXJ.state'),
('static/index.html',
'return X.j.filter(function(e){var m=e.m||"";return!((e.k==="bot"&&/setup passed',
'return X.j.filter(function(e){var m=e.m||"";return!((AC&&e.k==="bot")||(e.k==="bot"&&/setup passed'),
('static/index.html',
'(e.k==="note"&&/^Backtest ran: profit factor/.test(m)))}).concat(T).sort',
'(e.k==="note"&&/^Backtest ran: profit factor/.test(m)))}).concat(T).concat(B).sort'),
('static/index.html',
'function jr(){var f=X.jf,A=jall()',
'function jn(){var el=$("#jNow");if(!el)return;var a=window.SXAC,n=a&&a.now,g=function(s){s=Math.max(0,Math.round(Date.now()/1000-s));return s<60?"just now":s<3600?Math.floor(s/60)+" min ago":Math.floor(s/3600)+" h ago"};\n if(!a||a.state!=="ok"||!n){el.innerHTML=!a||a.state==="out"?"":\'<p class="note">\'+(a.state==="err"?"Cannot load what the bot is doing right now.":"Loading what the bot is doing...")+"</p>";return}\n el.innerHTML=\'<div class="callout"><b>\'+esc(n.headline)+\'</b><br>\'+esc(n.detail)+(n.checked?\'<br><small>Last market check \'+g(n.checked)+\'</small>\':"")+\'</div>\'+(a.markets.length?\'<b style="font-size:13px" class="muted">MARKETS IT LOOKED AT</b>\'+a.markets.map(function(o){return\'<div class="al"><time style="min-width:78px">\'+g(o.t)+\'</time><span><b class="jt bot">\'+esc(o.symbol)+\'</b>\'+esc(o.m)+\'</span></div>\'}).join(""):"")}\nfunction jr(){jn();var f=X.jf,A=jall()'),
('static/index.html',
'vt.appendChild(card(["Journal",\'<span class="chip info" id="jCount"></span>\'],\'<div class="jrow">',
'vt.appendChild(card(["Journal",\'<span class="chip info" id="jCount"></span>\'],\'<div id="jNow"></div><div class="jrow">'),
('static/index.html',
'/*S6-end*/\n</script>\n',
'/*S6-end*/\n</script>\n<script>\n/*AC1-start*/\n(function(){"use strict";var vt=document.getElementById("view-trades");if(!vt||!window.SXA||!window.SXAC)return;\nvar C=window.SXAC,BUSY=false,TK=0,SG="";\nfunction me(){try{return SXA.user()}catch(e){return null}}\nfunction shown(){var c=vt.querySelector(\'[data-t="journal"]\');return vt.classList.contains("on")&&!document.hidden&&c&&!c.classList.contains("th")}\nfunction paint(){try{if(window.jr)window.jr()}catch(e){}}\nfunction poll(){var u=me();if(!u||!u.verified||BUSY)return;BUSY=true;if(C.state==="idle"||C.state==="out"){C.state="load";paint()}\n SXA.api("/api/activity",{method:"GET"}).then(function(j){C.now=j.now||null;C.markets=j.markets||[];C.items=j.items||[];C.state="ok"},function(){if(C.state!=="ok")C.state="err"}).then(function(){BUSY=false;paint()})}\nsetInterval(function(){var u=me(),sg=u&&u.verified?u.uid:"";TK++;\n if(sg!==SG){SG=sg;C.now=null;C.markets=[];C.items=[];C.state=sg?"idle":"out";paint()}\n if(sg&&shown()&&(TK%10===0||C.state==="idle"))poll()},1000);\ndocument.addEventListener("click",function(e){if(e.target&&e.target.closest&&e.target.closest(\'[data-ut="journal"]\'))setTimeout(poll,60)});\n})();\n/*AC1-end*/\n</script>\n'),
]
def main():
    if not os.path.exists('backend/activity.py'): sys.exit('STOP: backend/activity.py is missing. Paste Part 1..N of it first.')
    data = {}; todo = []
    for f, o, n in PAIRS:
        s = data.get(f) or open(f, encoding='utf-8').read()
        if n in s: continue
        if s.count(o) != 1: sys.exit('STOP: in %s the old text appears %d times (need 1). Nothing changed.' % (f, s.count(o)))
        data[f] = s.replace(o, n, 1); todo.append(f)
    for f, s in data.items():
        open(f + '.tmp', 'w', encoding='utf-8').write(s); os.replace(f + '.tmp', f)
    print('changed:', sorted(set(todo)) or 'nothing (already applied)')
    r = subprocess.run([sys.executable, 'tests/test_ac1.py']); print('RESULT:', 'ALL PASS' if r.returncode == 0 else 'TESTS FAILED')
    sys.exit(r.returncode)
main()
