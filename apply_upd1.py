"""UPD1: when a newer app is out, every phone with the app gets a notification (and an Alerts entry). Tapping it opens the update prompt.
Server: backend/update_alerts.py checks GitHub for the latest release every 30 minutes (push kind 51). App: tap on it -> SXBUpdate.open(). Safe to run twice."""
import sys, os

def patch(path, old, new, tag):
    s = open(path, encoding='utf-8').read()
    if tag in s: print('already done:', path); return
    if s.count(old) != 1: print('NOT FOUND (%d): %s -> %s' % (s.count(old), path, old[:60])); sys.exit(1)
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched:', path)

# 1) a new push kind, 51, and its tap route
patch('backend/push.py', " (50,'system','hi','Security notice')]", " (50,'system','hi','Security notice'),(51,'system','hi','App update available')]          # UPD1", 'UPD1')
patch('backend/push.py', "'route': '#connect' if kind == 7 else ROUTE[k['cat']]", "'route': '#update' if kind == 51 else '#connect' if kind == 7 else ROUTE[k['cat']]", "'#update' if kind == 51")

# 2) the server job
MOD = '''"""UPD1: tell the phones when a newer app is out. Push kind 51 (and an Alerts entry), once per person per build.
Every EVERY seconds the job asks GitHub for the latest release (tag app-<build>, same rule as static/update.js). A release older than FRESH_DAYS is not announced
(so the first run after this goes live never wakes everybody about an old build). A person in quiet hours is simply tried again on the next run.
Env: UPDATE_REPO = owner/repo (default below). The job only runs while the server is awake."""
import os, re, time, threading, datetime as dt
import requests
from . import store as st, push

REPO = os.getenv('UPDATE_REPO', 'specialpanda26-sudo/spacexbot-mt5')
EVERY = 1800            # seconds between checks
FRESH_DAYS = 3          # a release older than this is not announced

def build(tag):
    m = re.search(r'(\\d+)\\s*$', str(tag or ''))
    return int(m.group(1)) if m else 0

def latest():
    """-> {'build': int, 'at': unix seconds} for the newest release, or None. Never raises."""
    try:
        r = requests.get('https://api.github.com/repos/%s/releases/latest' % REPO, headers={'Accept': 'application/vnd.github+json'}, timeout=10)
        if r.status_code != 200: return None
        j = r.json(); b = build(j.get('tag_name'))
        at = int(dt.datetime.strptime(str(j.get('published_at')), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc).timestamp())
        return {'build': b, 'at': at} if b > 0 else None
    except Exception as e:
        print('[update] check failed', str(e)[:80]); return None

def people():
    return [r['uid'] for r in st.q('SELECT DISTINCT uid FROM push_tokens') if r['uid']]

def update_job(now=None, fetch=None):
    """Announce the newest release to everyone with a phone registered. Returns how many people were reached (for tests)."""
    now = now or time.time(); rel = (fetch or latest)()
    if not rel or now - rel['at'] > FRESH_DAYS * 86400: return 0
    n = 0
    for uid in people():
        try:
            sent, why = push.send(uid, 51, 'Build %d is ready. Tap to update.' % rel['build'], None, 'upd51-%d' % rel['build'])
            n += 1 if sent else 0
        except Exception as e: print('[update] send failed', str(e)[:80])
    return n

def _in_background():
    threading.Thread(target=update_job, daemon=True).start()          # a slow GitHub answer never holds up the other alert jobs

def register():
    """On the alerts loop every EVERY seconds. The first run is 60 seconds after the server starts (not at once), so a restart never piles up with the other start-up jobs."""
    from . import alerts
    alerts.register_job('update_alerts', EVERY, _in_background)
    alerts._jobs['update_alerts']['last_run'] = time.time() - EVERY + 60
'''
if os.path.exists('backend/update_alerts.py'): print('already done: backend/update_alerts.py')
else: open('backend/update_alerts.py', 'w', encoding='utf-8').write(MOD); print('created: backend/update_alerts.py')
patch('backend/app.py', "system_alerts.register(); report_alerts.register();", "system_alerts.register(); __import__('backend.update_alerts', fromlist=['x']).register(); report_alerts.register();", 'update_alerts')

# 3) the app: SXBUpdate.open() and the tap route
patch('static/update.js', "  window.SXBUpdate = { celebrate: celebrate,",
 '''  /*UPD1*/ function open() {          /* a tap on the "update available" notification: look right now and show the prompt */
    try { sessionStorage.removeItem(LATER); } catch (e) {}
    LAST = 0; FOUND = false;
    return Promise.resolve(check()).then(function () { if (!FOUND && native() && window.sxToast) window.sxToast("You are on the latest version."); });
  }
  window.SXBUpdate = { open: open, celebrate: celebrate,''', 'UPD1')
patch('static/live.js', 'var r = String((d && d.route) || "").replace(/^#/, ""); r = GOMAP[r] || r;',
 'var r = String((d && d.route) || "").replace(/^#/, ""); if (r === "update") { try { window.SXBUpdate && window.SXBUpdate.open(); } catch (x) {} return; } /*UPD1*/ r = GOMAP[r] || r;', 'UPD1')
print('UPD1 applied')
