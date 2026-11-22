"""Test Lab 1: owner-only fake Deriv-login and payment cases. backend/testlab.py + static/test_lab.js are already written. Edits backend/app.py and static/index.html. Idempotent. Run: python apply_testlab1.py"""
import os
R = os.path.dirname(os.path.abspath(__file__))
def edit(path, pairs):
    p = os.path.join(R, path); s = open(p, encoding='utf-8').read()
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, (path, old[:60], s.count(old))
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)
edit('backend/app.py', [
 ('from . import btc_switch, tradeon, course, roadmap, guide, deriv_oauth\n', 'from . import btc_switch, tradeon, course, roadmap, guide, deriv_oauth, testlab\n'),
 ("@app.get('/api/deriv/login')\n",
  "@app.get('/api/admin/testlab')\n@need(admin=True)\ndef testlab_list(u):\n    \"\"\"Test Lab: the fake cases, only for an admin and only while TEST_LAB=1.\"\"\"\n    return jsonify(on=testlab.enabled(), cases=testlab.cases() if testlab.enabled() else [])\n\n"
  "@app.post('/api/admin/testlab/run')\n@need(admin=True)\ndef testlab_run(u):\n    \"\"\"Test Lab: hands back the words of one fake case. Writes nothing, trades nothing.\"\"\"\n    r, why = testlab.run(_j().get('case'))\n    if why: return jsonify(error=why), (403 if not testlab.enabled() else 400)\n    return jsonify(r)\n\n"
  "@app.get('/api/deriv/login')\n"),
])
edit('static/index.html', [
 ("'<h3 style=\"margin:8px 0 0\">Price feed</h3>", "'<div id=\"tlab\"></div>'+\n '<h3 style=\"margin:8px 0 0\">Price feed</h3>"),
 ("function payWatch(ref,i,first){",
  "window.sxLabHooks={pay:function(w){var sp=payPend(),sw=PAYW,i={name:\"Test plan\",amt:\"KES 0\",m:\"mpesa\",receipt:\"TEST\"};try{if(w===\"ok\")payDone(i,false);else if(w===\"fail\")payFail(\"timeout\",\"TEST\",false,false);else if(w===\"slow\")paySlow(\"TEST\",i,false);else if(w===\"cancel\")cancelled(false)}finally{if(sp)payPend(sp);PAYW=sw}},stop:function(){closeOv()}};\nfunction payWatch(ref,i,first){"),
 ('<script src="/static/deriv_login.js"></script>', '<script src="/static/deriv_login.js"></script><script src="/static/test_lab.js"></script>'),
])
print('Test Lab 1 applied')
