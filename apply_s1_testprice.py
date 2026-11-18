"""Section 1: admin 'Test price' card. Lets the admin set ANY amount (KES 1+, USD 0.01+) as a one-tap test package, and fixes the
USD box so a phone keypad can type decimals. Each old text must appear exactly once or NOTHING is changed. Safe to run twice."""
import sys, os

TEST = r'''"""Section 1 checks: admin test price. Run: python tests/test_testprice.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'testprice_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import payments as pay
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
R = []
def T(name, ok): R.append((name, bool(ok)))
def mine(r): return [p for p in r.json if p['id'] == 'ptest']
C.get('/api/me', headers=A); C.get('/api/me', headers=U)
T('normal user cannot set a test price', C.post('/api/admin/testprice', json={'kes': 1, 'usd': 0.01}, headers=U).status_code == 403)
r = C.post('/api/admin/testprice', json={'kes': 1, 'usd': 0.01, 'days': 1}, headers=A)
t = mine(r) if r.status_code == 200 else []
T('admin sets KES 1 / USD 0.01', len(t) == 1 and t[0]['kes'] == 1 and abs(t[0]['usd'] - 0.01) < 1e-9 and t[0]['days'] == 1)
T('customers see the test package', any(p['id'] == 'ptest' for p in C.get('/api/plans').json))
T('the normal packages are kept', {'p1', 'p2', 'p3'} <= {p['id'] for p in C.get('/api/plans').json})
t = mine(C.post('/api/admin/testprice', json={'kes': 77, 'usd': 0.55, 'days': 2}, headers=A))
T('setting again replaces it, no duplicate', len(t) == 1 and t[0]['kes'] == 77 and abs(t[0]['usd'] - 0.55) < 1e-9 and t[0]['days'] == 2)
T('pay.plan() finds it with the new price', (pay.plan('ptest') or {}).get('kes') == 77)
for bad in ({'kes': 0, 'usd': 1}, {'kes': 5, 'usd': 0}, {'kes': 5, 'usd': 0.004}, {'kes': 'x', 'usd': 1}, {'kes': 5, 'usd': 1, 'days': 0}, {'kes': 5, 'usd': 1, 'days': 99999}, {'kes': 9999999, 'usd': 1}):
    T('refuses bad input %s' % bad, C.post('/api/admin/testprice', json=bad, headers=A).status_code == 400)
T('a refused request changes nothing', (pay.plan('ptest') or {}).get('kes') == 77)
t = mine(C.post('/api/admin/testprice', json={'kes': 77, 'usd': 1.234, 'days': 2}, headers=A))
T('USD is rounded to cents', len(t) == 1 and t[0]['usd'] == 1.23)
r = C.post('/api/admin/testprice', json={'off': True}, headers=A)
T('off removes the test package only', r.status_code == 200 and not mine(r) and {'p1', 'p2', 'p3'} <= {p['id'] for p in r.json})
T('off twice is harmless', C.post('/api/admin/testprice', json={'off': True}, headers=A).status_code == 200)
for n, ok in R: print(('PASS ' if ok else 'FAIL ') + n)
bad = [n for n, ok in R if not ok]; print('\n%d/%d passed' % (len(R) - len(bad), len(R)))
try: os.remove(DB)
except OSError: pass
sys.exit(1 if bad else 0)
'''

PAY_NEW = r'''def set_test_plan(kes=None, usd=None, days=1, off=False):
    """Admin quick test price. Keeps one package with id 'ptest'; any KES 1+ and USD 0.01+. Raises ValueError on bad input (nothing is saved)."""
    keep = [p for p in plans() if p['id'] != 'ptest']
    if off: return set_plans(keep)
    k = int(kes); u = round(float(usd), 2); d = int(days)
    if not (1 <= k <= 1000000 and 0.01 <= u <= 100000 and 1 <= d <= 3650): raise ValueError('bad test price')
    return set_plans(keep + [{'id': 'ptest', 'name': 'Test (admin)', 'days': d, 'kes': k, 'usd': u}])

'''

APP_NEW = r'''@app.post('/api/admin/testprice')
@need(admin=True)
def admin_testprice(u):
    j = _j()
    try: return jsonify(pay.set_test_plan(j.get('kes'), j.get('usd'), 1 if j.get('days') is None else j.get('days'), bool(j.get('off'))))
    except (ValueError, TypeError, KeyError, AttributeError): return jsonify(error='Enter KES 1 or more, USD 0.01 or more, and days 1 to 3650'), 400

'''

CARD = ('<h3 style="margin:8px 0 0">Test price</h3><p class="note">Set any amount to try the payment flow fast. It shows as a package called Test (admin) '
        'and customers can see it too, so remove it when you finish.</p><div class="sr"><input class="inp" id="tpK" placeholder="KES" inputmode="decimal" value="1" style="width:30%">'
        '<input class="inp" id="tpU" placeholder="USD" inputmode="decimal" value="0.01" style="width:30%"><input class="inp" id="tpD" placeholder="Days" inputmode="numeric" value="1" style="width:25%"></div>'
        '<div style="display:flex;gap:8px"><button class="btn primary" id="tpOn">Use this price</button><button class="btn" id="tpOff">Remove test</button></div>')

JS = r''' function tpSend(body,msg,btn){btn.disabled=true;SXA.api("/api/admin/testprice",{method:"POST",body:body}).then(function(a){if(Array.isArray(a)&&a.length){PK=a;rows=PK.map(function(p){return Object.assign({},p)});dr()}tst(msg);bar()}).catch(function(e){tst(e.message||"Could not save")}).then(function(){btn.disabled=false})}
 $("#tpOn").onclick=function(){var k=Math.round(+$("#tpK").value||0),u=Math.round((+$("#tpU").value||0)*100)/100,d=Math.round(+$("#tpD").value||0)||1;if(k<1||u<0.01)return tst("KES must be 1 or more and USD 0.01 or more");tpSend({kes:k,usd:u,days:d},"Test package is live: KES "+k+" / USD "+u,this)};
 $("#tpOff").onclick=function(){tpSend({off:true},"Test package removed",this)};
'''

EDITS = [
 ('backend/payments.py', "def activate(uid, pid, days=None):", PAY_NEW + "def activate(uid, pid, days=None):", 'def set_test_plan('),
 ('backend/app.py', "@app.post('/api/admin/grant')", APP_NEW + "@app.post('/api/admin/grant')", "def admin_testprice("),
 ('static/index.html', '<h2>Admin panel</h2><h3 style="margin:0">Packages</h3>', '<h2>Admin panel</h2>' + CARD + '<h3 style="margin:8px 0 0">Packages</h3>', 'id="tpOn"'),
 ('static/index.html', 'data-f="usd" data-i="\'+i+\'" inputmode="numeric"', 'data-f="usd" data-i="\'+i+\'" inputmode="decimal"', 'data-f="usd" data-i="\'+i+\'" inputmode="decimal"'),
 ('static/index.html', ' var SUBS=[];\n', JS + ' var SUBS=[];\n', 'function tpSend('),
 ('docs/HANDOFF.md', '## REMAINING (do in this order', '- Admin test price (Nov 18 plan, section 1): backend/payments.py set_test_plan + POST /api/admin/testprice + Test price card in the admin panel + tests/test_testprice.py.\n\n## REMAINING (do in this order', 'Admin test price (Nov 18'),
]
if not os.path.isdir('backend') or not os.path.isdir('static'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: print('already applied:', path, marker[:40]); new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
open('tests/test_testprice.py', 'w', encoding='utf-8', newline='').write(TEST)
print('patched OK')
