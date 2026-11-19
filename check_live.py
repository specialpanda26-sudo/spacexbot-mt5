"""Read-only check of R6, R8 and R5 on the live site. It changes nothing and never prints your pass.
Run: python check_live.py            (or: python check_live.py https://your-site.onrender.com)"""
import sys, json, getpass, urllib.request, urllib.error
SITE = (sys.argv[1] if len(sys.argv) > 1 else 'https://spacexbot-gn73.onrender.com').rstrip('/')

def call(path, body=None, tok=None):
    h = {'Content-Type': 'application/json'}
    if tok: h['X-Admin-Pass'] = tok
    req = urllib.request.Request(SITE + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=90) as r: code, raw = r.status, r.read().decode()
    except urllib.error.HTTPError as e: code, raw = e.code, e.read().decode()
    except Exception as e: return 0, {'error': str(e)[:80]}
    try: return code, json.loads(raw or '{}')
    except ValueError: return code, {'text': raw[:60]}

def line(ok, msg): print(('PASS  ' if ok else 'FAIL  ') + msg)

print('Site:', SITE, '(a sleeping Render server can take a minute)')
c, j = call('/healthz'); line(c == 200, 'site awake (HTTP %s)' % c)
if c != 200: sys.exit(1)
c, j = call('/api/admin/pass', {'code': getpass.getpass('Admin access pass (hidden): ')})
tok = j.get('token') if c == 200 else None
line(bool(tok), 'access pass accepted' if tok else 'access pass NOT accepted (HTTP %s) %s' % (c, j.get('error', '')))
if not tok: sys.exit(1)

c, s = call('/api/admin/settings', {}, tok)
line(c == 200 and 'multi_entries' in s, 'R8 is deployed: multi_entries = %s (1 means off), multi_min_score = %s' % (s.get('multi_entries'), s.get('multi_min_score')))
line(c == 200 and 'auto_markets' in s, 'R5 is deployed: auto_markets = %s (0 means off), pool = %r, max added = %s' % (s.get('auto_markets'), s.get('symbols_pool'), s.get('auto_markets_max')))
print('      markets now traded:', s.get('symbols'), '| positions at once:', s.get('max_open'), '| risk %:', s.get('risk_pct'))

c, m = call('/api/admin/markets', None, tok)
line(c == 200, 'R5 status route works (HTTP %s)%s' % (c, '' if c == 200 else ' - if 500, the grp column is missing in the database: run the grp line from supabase_schema.sql'))
if c == 200: print('      can add a market now:', m.get('can_add_now'), '| why not:', m.get('why_not') or '-', '| added:', [a.get('s') for a in m.get('added', [])])

c, l = call('/api/admin/lag', None, tok)
line(c == 200, 'R6 timing report works (HTTP %s)' % c)
if c == 200:
    print('      signals with timings:', l.get('count'), '| typical seconds:', l.get('typical_seconds'), '| biggest step:', l.get('biggest'))
    if not l.get('count'): print('      (nothing yet: the bot has not made a signal since the deploy)')

c, h = call('/api/admin/health', None, tok)
line(c == 200 and h.get('ok'), 'server health ok' if c == 200 and h.get('ok') else 'server health: %s' % (h.get('problems') or c))
