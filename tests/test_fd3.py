"""Section FD3: GET /api/news serves the real calendar and the page shows it (no made-up events).
Run: python tests/test_fd3.py"""
import os, sys, time, re, json, shutil, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); DB = os.path.join(HERE, 'fd3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t', PUBLIC_URL='http://t')
for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
sys.path.insert(0, ROOT)
from backend.app import app
from backend import news
R = []
def T(name, ok): R.append((name, bool(ok))); print('PASS' if ok else 'FAIL', name)

class Boom:
    def get(self, *a, **k): raise RuntimeError('no network in tests')
news.requests = Boom()
now = time.time()
def row(mins, imp, ccy='USD', title='X'):
    d = dt.datetime.fromtimestamp(now + mins * 60, dt.timezone.utc).isoformat()
    return {'date': d, 'impact': imp, 'country': ccy, 'title': title}

c = app.test_client()
# feed never loaded: honest "not loaded", no events, and no sign-in needed
news._rows = None; news._try = time.time()
r = c.get('/api/news'); j = r.get_json()
T('public (no sign-in)', r.status_code == 200)
T('not loaded says so', j['loaded'] is False and j['events'] == [])

rows = [row(-60, 'High', 'USD', 'Past'), row(30, 'Low', 'JPY', 'Low one'), row(200, 'Medium', 'GBP', 'Retail'),
        row(95, 'High', 'USD', 'Core PCE'), {'date': 'junk', 'impact': 'High', 'country': 'EUR', 'title': 'Bad'}]
news.set_rows(rows)
j = c.get('/api/news').get_json(); ev = j['events']
T('loaded true', j['loaded'] is True)
T('past event left out', all(e['title'] != 'Past' for e in ev))
T('low impact left out', all(e['impact'] != 'low' for e in ev))
T('bad row skipped, no crash', all(e['title'] != 'Bad' for e in ev))
T('sorted soonest first', [e['title'] for e in ev] == ['Core PCE', 'Retail'])
T('fields', ev[0]['ccy'] == 'USD' and ev[0]['impact'] == 'high' and 94 <= ev[0]['in_min'] <= 95 and ev[1]['impact'] == 'medium')
news.set_rows([row(10 + i, 'High', 'USD', 'E%d' % i) for i in range(20)])
T('at most 8', len(c.get('/api/news').get_json()['events']) == 8)
news.set_rows([row(-5, 'High')])
j = c.get('/api/news').get_json()
T('loaded but nothing ahead', j['loaded'] is True and j['events'] == [])
T('the news lock still sees the same feed', news.loaded() and news.next_high(now) is None)

# the page
S = open(os.path.join(ROOT, 'static', 'index.html'), encoding='utf-8').read()
for name in ('Core PCE Price Index', 'ECB President speaks', 'BoJ Summary of Opinions', 'Unemployment Claims'):
    T('page has no made-up event: ' + name, name not in S)
T('NEWS starts empty', 'var NEWS=[],NEWSST="load"' in S)
T('page loads /api/news at start', 'renderNews();loadNews();' in S and 'fetch("/api/news")' in S)
T('page says when nothing real', 'The calendar could not be loaded right now' in S and 'No high or medium impact events left this week.' in S)
T('medium maps to med', 'e.impact==="medium"?"med":e.impact' in S)

# run the page's own functions in node with a fake page
if shutil.which('node'):
    def grab(start):
        i = S.index(start); j = S.index('\n', i); return S[i:j]
    code = grab('function renderNews(){') + '\n' + grab('function loadNews(){') + '\n' + grab('function fmtIn(m){')
    js = ('var NEWS=[],NEWSST="load",out="";var ICON_NEWS="i";function esc(x){return String(x)}\n'
          'var L={set innerHTML(v){out=v},get innerHTML(){return out}};function $(s){return L}\n' + code + '\n'
          'var step=[];renderNews();step.push(out);\n'
          'global.fetch=function(){return Promise.resolve({ok:true,json:function(){return Promise.resolve({loaded:true,events:[{in_min:95,ccy:"USD",title:"Core PCE",impact:"high"},{in_min:200,ccy:"GBP",title:"Retail",impact:"medium"}]})}})};\n'
          'loadNews();setTimeout(function(){step.push(out);\n'
          'global.fetch=function(){return Promise.resolve({ok:true,json:function(){return Promise.resolve({loaded:false,events:[]})}})};loadNews();setTimeout(function(){step.push(out);\n'
          'global.fetch=function(){return Promise.reject(new Error("x"))};loadNews();setTimeout(function(){step.push(out);\n'
          'global.fetch=function(){return Promise.resolve({ok:true,json:function(){return Promise.resolve({loaded:true,events:[]})}})};loadNews();setTimeout(function(){step.push(out);console.log(JSON.stringify(step))},20)},20)},20)},20);\n')
    p = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    try: st = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception: st = ['', '', '', '', '']; print(p.stderr[:300])
    T('node: loading text first', 'Loading the calendar' in st[0])
    T('node: real rows drawn', 'USD · Core PCE' in st[1] and 'in 1h 35m' in st[1] and 'Medium' in st[1] and 'chip stop' in st[1])
    T('node: feed not loaded -> honest message', 'could not be loaded' in st[2])
    T('node: network error -> honest message', 'could not be loaded' in st[3])
    T('node: loaded but empty -> no events message', 'No high or medium impact events' in st[4])
else:
    print('node not found: page run skipped')

for f in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(f): os.remove(f)
bad = [n for n, ok in R if not ok]
print('%d/%d passed' % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
