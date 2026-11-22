"""Section FD3: the News card shows the real economic calendar (GET /api/news, from backend/news.py) instead of 5 made-up events.
Run from the project folder: python apply_fd3.py  (safe to run twice). Edits backend/news.py, backend/app.py, static/index.html, docs/HANDOFF.md."""
def edit(path, pairs):
    s = open(path, encoding='utf-8').read(); o = s
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, path + ': need exactly one: ' + old[:60]
        s = s.replace(old, new, 1)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)

OLD = "def loaded(): return _rows is not None"
NEW = OLD + '''

def upcoming(now=None, limit=8, impact=('high', 'medium')):
    """FD3: the real calendar for the page. [{in_min, ccy, title, impact}], soonest first, only events still ahead."""
    now = now or time.time()
    with _lock: _fetch()
    out = []
    for r in (_rows or []):
        try: t = dt.datetime.fromisoformat(r['date']).timestamp()
        except Exception: continue
        imp = (r.get('impact') or '').lower()
        if imp in impact and t >= now: out.append((t, {'in_min': int((t - now) / 60), 'ccy': r.get('country'), 'title': r.get('title'), 'impact': imp}))
    out.sort(key=lambda x: x[0])
    return [e for _, e in out[:limit]]'''
edit('backend/news.py', [(OLD, NEW)])

OLD = "@app.get('/api/bridge')\n@need(verified=True)\ndef bridge_api(u):"
NEW = '''@app.get('/api/news')
def news_list():
    """FD3: public, read-only. The real week's high and medium impact events still ahead (same feed as the news lock). loaded=false means the feed could not be read yet."""
    ev = news.upcoming()
    return jsonify(loaded=news.loaded(), events=ev)

''' + OLD
edit('backend/app.py', [(OLD, NEW)])

OLDN = 'var NEWS=[{m:95,c:"USD",e:"Core PCE Price Index",i:"high"},{m:240,c:"EUR",e:"ECB President speaks",i:"high"},{m:420,c:"GBP",e:"Retail Sales m/m",i:"med"},{m:1500,c:"JPY",e:"BoJ Summary of Opinions",i:"med"},{m:1800,c:"USD",e:"Unemployment Claims",i:"low"}];'
NEWN = 'var NEWS=[],NEWSST="load";/*FD3: the real calendar, filled by loadNews() from GET /api/news; nothing is invented*/'
OLDR = ('''function renderNews(){$("#newsList").innerHTML=NEWS.map(function(n){return '<li class="row"><span class="ic nw">'+ICON_NEWS+'</span><span class="t">'+n.c+' · '+esc(n.e)+'</span><span class="r"><span class="chip '+(n.i==="high"?"stop":n.i==="med"?"watch":"")+'">'+({high:"High",med:"Medium",low:"Low"})[n.i]+'</span></span><span class="s">in '+fmtIn(n.m)+'</span></li>'}).join("")}''')
NEWR = ('''function renderNews(){var L=$("#newsList");if(!L)return;if(!NEWS.length){L.innerHTML='<li class="row"><span class="t" style="grid-column:1/4">'+(NEWSST==="load"?"Loading the calendar...":NEWSST==="err"?"The calendar could not be loaded right now. Try again in a few minutes.":"No high or medium impact events left this week.")+'</span></li>';return}L.innerHTML=NEWS.map(function(n){return '<li class="row"><span class="ic nw">'+ICON_NEWS+'</span><span class="t">'+esc(n.c)+' · '+esc(n.e)+'</span><span class="r"><span class="chip '+(n.i==="high"?"stop":n.i==="med"?"watch":"")+'">'+({high:"High",med:"Medium",low:"Low"})[n.i]+'</span></span><span class="s">in '+fmtIn(n.m)+'</span></li>'}).join("")}\n'''
        '''function loadNews(){fetch("/api/news").then(function(r){return r.ok?r.json():Promise.reject()}).then(function(j){if(!j||!j.loaded){NEWS=[];NEWSST="err"}else{NEWS=(j.events||[]).map(function(e){return{m:e.in_min,c:e.ccy||"",e:e.title||"",i:e.impact==="medium"?"med":e.impact}});NEWSST="ok"}renderNews()},function(){NEWS=[];NEWSST="err";renderNews()})}/*FD3*/''')
OLDC = 'renderCards();renderNews();renderBotSettings()'
NEWC = 'renderCards();renderNews();loadNews();setInterval(loadNews,600000);renderBotSettings()'
edit('static/index.html', [(OLDN, NEWN), (OLDR, NEWR), (OLDC, NEWC)])

NOTE = """
## Section FD3 (fake data fix c: the News card shows the real calendar) DONE (Nov 22)
- New GET /api/news (backend/app.py, public and read-only, no sign-in): the real week's HIGH and MEDIUM impact events still ahead, soonest first, at most 8, as {in_min, ccy, title, impact}, plus loaded (false = the feed was never read). backend/news.py got upcoming() (same cached feed as the news lock, so no extra requests to the feed). In static/index.html the 5 made-up events (Core PCE, ECB speaks, ...) are gone: NEWS starts empty, loadNews() fills it from /api/news (once at start, then every 10 minutes), renderNews shows 'Loading the calendar...', 'The calendar could not be loaded right now...' or 'No high or medium impact events left this week.' when there is nothing real to show. nextHigh() (the demo Home 'Waiting for news' state) now reads the real list too.
- NOT changed: the server's real news lock (news.blocked) and /api/status news_next. Feed times come from the ForexFactory weekly feed; the list only covers this week (it is empty on a quiet Sunday night until the new week loads). tests/test_fd3.py. apply_fd3.py.
- Fake data scan items 4-5 are still open (d Weekly brief / Home chart / Autobot log labels). Owner picks.
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Section FD3' not in h:
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h.rstrip('\n') + '\n' + NOTE)
print('ok docs/HANDOFF.md')
