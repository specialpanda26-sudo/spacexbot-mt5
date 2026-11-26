"""TB1: top banner (Search, Alerts, Settings) + the in-app notification inbox. Run from the repo root: python apply_tb1.py   (safe to run twice).
Needs apply_qp1.py run first (it adds next to that script tag), and the two new files: backend/inbox.py and static/topbar_ui.js. apply_sf4.py is what makes a search result land on the exact field.
 - backend/push.py: send() also keeps every notification the person would get in their inbox (words only, nothing about phone delivery changes).
 - backend/app.py: GET /api/inbox, POST /api/inbox/seen, POST /api/inbox/clear.
 - static/index.html: the search/scan code is shared with the new panels (window.SXfind, SXscan, SXfb) and topbar_ui.js is loaded.
Nothing is written if any step cannot find its place exactly once."""
import sys, os

STEPS = [
 ('backend/push.py',
  '    """Send one notification kind to one person. key makes it idempotent per person. Returns (sent_count, reason)."""\n    if not configured(): return 0, \'FCM not configured\'\n',
  '    """Send one notification kind to one person. key makes it idempotent per person. Returns (sent_count, reason)."""\n    k0 = KINDS.get(kind)          # TB1: the in-app inbox keeps it too (unless that category is switched off)\n    if k0:\n        try:\n            from . import inbox\n            if prefs(uid).get(k0[\'cat\'], True): inbox.add(uid, kind, title or k0[\'title\'], body, k0[\'cat\'], key)\n        except Exception as e: print(\'[push] inbox failed\', str(e)[:80])\n    if not configured(): return 0, \'FCM not configured\'\n'),
 ('backend/app.py',
  'from . import quickprofit          # QP1: take small profits\n',
  'from . import quickprofit          # QP1: take small profits\nfrom . import inbox as inbox_mod          # TB1: in-app notification inbox\n'),
 ('backend/app.py',
  "@app.get('/api/quickprofit')          # QP1: take small profits\n",
  '''@app.get('/api/inbox')          # TB1: the bell at the top of the app
@need()
def inbox_get(u): return jsonify(inbox_mod.view(u['uid']))

@app.post('/api/inbox/seen')
@need()
def inbox_seen(u):
    inbox_mod.mark_seen(u['uid']); return jsonify(inbox_mod.view(u['uid']))

@app.post('/api/inbox/clear')
@need()
def inbox_clear(u):
    inbox_mod.clear(u['uid']); return jsonify(inbox_mod.view(u['uid']))

@app.get('/api/quickprofit')          # QP1: take small profits
'''),
 ('static/index.html', 'window.SXgo=go;', 'window.SXgo=go;window.SXfind=find;window.SXscan=scan;window.SXfb=FB;'),
 ('static/index.html', '<script src="/static/quick_ui.js"></script>', '<script src="/static/quick_ui.js"></script><script src="/static/topbar_ui.js"></script>'),
]
for need_file in ('backend/inbox.py', 'static/topbar_ui.js'):
    if not os.path.exists(need_file): sys.exit('STOP: %s is missing. Create it first (the cat command), then run this again.' % need_file)
files, done = {}, set()
for path, old, new in STEPS:
    if path not in files: files[path] = open(path, encoding='utf-8').read()
    s = files[path]
    if new in s: continue
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:70].replace('\n', ' ')))
    files[path] = s.replace(old, new); done.add(path)
for p in sorted(done): open(p, 'w', encoding='utf-8', newline='').write(files[p]); print(p, ': edited')
if not done: print('already ok, nothing to do')
