"""Section: the server enforces Max trades a day and the loss-streak stop per person (limits.py). backend/limits.py and tests/test_limits.py are written
just before this by the same command. Wires the risk gate, two routes (GET/POST /api/limits) and the Session limits card to the server.
Each old text must be found exactly once or NOTHING is changed. Safe to run twice."""
import sys, os

ROUTE = """@app.get('/api/limits')
@need(verified=True)
def limits_get(u): return jsonify(limits.view(_mine(u)))

@app.post('/api/limits')
@need(verified=True)
def limits_set(u):
    j = _j()
    try: out = limits.save(_mine(u), j.get('max_trades'), j.get('streak'))
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in ('max_trades', 'streak')}})
    return jsonify(out)

"""
A1 = '$("#uTp").value=X.tp;$("#uMax").value=X.maxT;$("#uStr").value=X.streak;us();'
A2 = """function limLoad(){if(!window.SXA)return;SXA.api("/api/limits").then(function(r){X.maxT=r.max_trades||0;X.streak=r.streak||0;$("#uMax").value=X.maxT||"";$("#uStr").value=X.streak||"";$("#uMax").placeholder=r.cap_trades?"Owner limit "+r.cap_trades:"No limit";$("#uStr").placeholder=r.cap_streak?"Owner limit "+r.cap_streak:"Off";sv()}).catch(function(){})}
 function limSave(k,n,el,nm){var b={};b[k==="maxT"?"max_trades":"streak"]=Math.round(n);SXA.api("/api/limits",{method:"POST",body:b}).then(function(r){X.maxT=r.max_trades||0;X.streak=r.streak||0;el.value=(k==="maxT"?X.maxT:X.streak)||"";sv();ja("rule",nm+" saved on the server: "+(el.value||"default"));bn();toast(nm+" saved on the server")}).catch(function(e){el.value=(k==="maxT"?X.maxT:X.streak)||"";toast(e.message||"Not saved. Sign in first")})}
 """ + A1 + "limLoad();"
B1 = 'function(){var n=parseFloat(this.value);if(n>=0){X[a[1]]=n;sv();ja("rule",a[2]+" set to "+n);bn()}'
B2 = 'function(){var sv2=a[1]==="maxT"||a[1]==="streak",n=sv2&&this.value===""?0:parseFloat(this.value);if(n>=0){if(sv2){if(window.SXA)limSave(a[1],n,this,a[2]);else toast("Sign in first");return}X[a[1]]=n;sv();ja("rule",a[2]+" set to "+n);bn()}'
C1 = '" · Max "+X.maxT+" trades · Stop after "+X.streak+" losses"'
C2 = '" · "+(X.maxT?"Max "+X.maxT+" trades":"No trade limit")+" · "+(X.streak?"Stop after "+X.streak+" losses":"No loss-streak stop")'
HAND = '- Limits on the server (Nov 19 plan, leftover of section 4): backend/limits.py + GET/POST /api/limits + risk.global_gate reads limits.trades(uid) / limits.streak(uid) + the Session limits card saves Max trades a day and Loss streak stop to the server (tests/test_limits.py). A subscriber can only be stricter than the owner. Daily profit target and Profit lock are still page-only.\n\n'
EDITS = [
 ('backend/risk.py', 'from . import store as st, news, links\n', 'from . import store as st, news, links, limits\n', 'links, limits\n'),
 ('backend/risk.py', "mt = int(st.fget('max_trades_day') or 0)", 'mt = limits.trades(uid)', 'mt = limits.trades(uid)'),
 ('backend/risk.py', "k = int(st.fget('max_losing_streak'))", 'k = limits.streak(uid)', 'k = limits.streak(uid)'),
 ('backend/app.py', 'brokers as bk, deriv, livestats\n', 'brokers as bk, deriv, livestats, limits\n', 'livestats, limits\n'),
 ('backend/app.py', "@app.post('/api/admin/testprice')", ROUTE + "@app.post('/api/admin/testprice')", 'def limits_get('),
 ('static/index.html', A1, A2, 'function limLoad()'),
 ('static/index.html', B1, B2, 'limSave(a[1],n,this,a[2])'),
 ('static/index.html', C1, C2, 'No trade limit'),
 ('docs/HANDOFF.md', '## REMAINING (do in this order', HAND + '## REMAINING (do in this order', 'Limits on the server (Nov 19 plan'),
]
if not os.path.isdir('backend') or not os.path.isdir('static'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
if not os.path.exists('backend/limits.py'): print('STOP: backend/limits.py is missing'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
