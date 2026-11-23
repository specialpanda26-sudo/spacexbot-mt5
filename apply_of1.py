"""apply_of1.py: offline page + service worker (needs static/sw.js, static/offline.html, tests/test_of1.py first, and AC1 applied). Run in the repo folder:  python apply_of1.py
Every old text must appear exactly once or NOTHING is changed. Safe to run twice. Atomic writes. Runs the tests at the end."""
import os, sys, subprocess
PAIRS = [
('backend/app.py',
"@app.get('/favicon.ico')\n",
'@app.get(\'/sw.js\')\ndef sw_js():\n    """OF1: the offline worker. Never cached by the browser, allowed to cover the whole site."""\n    r = send_from_directory(\'../static\', \'sw.js\', mimetype=\'application/javascript\'); r.headers[\'Cache-Control\'] = \'no-cache\'; r.headers[\'Service-Worker-Allowed\'] = \'/\'; return r\n\n@app.get(\'/offline.html\')\ndef offline_html(): return send_from_directory(\'../static\', \'offline.html\')\n\n@app.get(\'/favicon.ico\')\n'),
('static/index.html',
'/*AC1-end*/\n</script>\n',
'/*AC1-end*/\n</script>\n<script>\n/*OF1-start*/\ntry{if("serviceWorker" in navigator&&location.protocol==="https:")window.addEventListener("load",function(){navigator.serviceWorker.register("/sw.js").catch(function(){})})}catch(e){}\n/*OF1-end*/\n</script>\n'),
]
def main():
    for need in ('static/sw.js', 'static/offline.html', 'tests/test_of1.py'):
        if not os.path.exists(need): sys.exit('STOP: %s is missing. Paste its parts first.' % need)
    data = {}; todo = []
    for f, o, n in PAIRS:
        s = data.get(f) or open(f, encoding='utf-8').read()
        if n in s: continue
        if s.count(o) != 1: sys.exit('STOP: in %s the old text appears %d times (need 1). Nothing changed.' % (f, s.count(o)))
        data[f] = s.replace(o, n, 1); todo.append(f)
    for f, s in data.items():
        open(f + '.tmp', 'w', encoding='utf-8').write(s); os.replace(f + '.tmp', f)
    print('changed:', sorted(set(todo)) or 'nothing (already applied)')
    r = subprocess.run([sys.executable, 'tests/test_of1.py']); print('RESULT:', 'ALL PASS' if r.returncode == 0 else 'TESTS FAILED')
    sys.exit(r.returncode)
main()
