"""P9c: optional 5-minute scanning (fast scan). Per person switch (prefs 'fast'). Off by default: nothing changes until someone turns it on.
Needs the updated EA (sends M5 candles) for MT5; Deriv fetches M5 itself. Run once from the repo root."""
import sys
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if s.count(old) != 1: sys.exit('NOT FOUND exactly once in %s: %r' % (path, old[:70]))
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)

edit('backend/prefs.py', [
    ("The person can only choose things", "  fast       : True = also scan 5-minute candles (more checks per hour). Needs M5 candles from the EA / Deriv.\nThe person can only choose things"),
    ("'scale': j.get('scale') is True}", "'scale': j.get('scale') is True, 'fast': j.get('fast') is True}"),
    ("for k in ('alone', 'scale'):", "for k in ('alone', 'scale', 'fast'):"),
])

edit('backend/app.py', [
    ("""def _scan(sym, uid=''):
    k = (uid, sym)
    if time.time() - _last_scan.get(k, 0) < 20: return
    _last_scan[k] = time.time()
    m15 = bars.get(sym, 'M15', uid); h1 = bars.get(sym, 'H1', uid)
    if not m15: return
    key = f'lastbar:{uid}:{sym}' if uid else f'lastbar:{sym}'
""", """def _scan(sym, uid=''):
    _scan_tf(sym, uid, 'M15', 'H1')
    if prefs.get(uid)['fast']: _scan_tf(sym, uid, 'M5', 'M15')          # fast scan: the same strategies on 5-minute candles, 15-minute candles as the higher chart

def _scan_tf(sym, uid, tf, hi):
    k = (uid, sym) if tf == 'M15' else (uid, sym, tf)
    if time.time() - _last_scan.get(k, 0) < 20: return
    _last_scan[k] = time.time()
    m15 = bars.get(sym, tf, uid); h1 = bars.get(sym, hi, uid)          # (names kept from the 15-minute code: m15 = the main candles, h1 = the higher chart)
    if not m15:
        if tf != 'M15': botstate.note(uid, sym, 'nosetup', '5-minute candles have not arrived yet. Update the EA, then give it a minute.')
        return
    key = (f'lastbar:{uid}:{sym}' if uid else f'lastbar:{sym}') + ('' if tf == 'M15' else ':' + tf)
"""),
    ("    if not s: botstate.note(uid, sym, 'nosetup', rgm.note_text(info)); return\n",
     "    if not s: botstate.note(uid, sym, 'nosetup', rgm.note_text(info)); return\n    if tf != 'M15': s.setdefault('why', {})['tf'] = tf\n"),
    ("if who and (tf not in ('M15', 'H1') or not isinstance(rows, list)): continue", "if who and (tf not in ('M5', 'M15', 'H1') or not isinstance(rows, list)): continue"),
])

edit('backend/reason.py', [
    ("    adx = _n(j.get('adx')); rg = j.get('regime')\n",
     "    if j.get('tf') == 'M5': out.append('Found on the 5-minute chart (fast scan). Its stop and target are sized from 5-minute candles.')\n    adx = _n(j.get('adx')); rg = j.get('regime')\n"),
])

edit('backend/deriv.py', [
    ("GRAN = {'M15': 900, 'H1': 3600}", "GRAN = {'M5': 300, 'M15': 900, 'H1': 3600}"),
    ("""                for tf in ('M15', 'H1'):
                    rows = candles(sess, sym, tf, 300 if tf == 'M15' else 200, now)""",
     """                from . import prefs
                for tf in (('M5', 'M15', 'H1') if prefs.get(uid)['fast'] else ('M15', 'H1')):
                    rows = candles(sess, sym, tf, 200 if tf == 'H1' else 300, now)"""),
])

edit('ea/SpaceXBridge.mq5', [
    (r'''BarsJson(list[i], PERIOD_H1, firstPush ? 320 : 4)''',
     r'''BarsJson(list[i], PERIOD_H1, firstPush ? 320 : 4) + ",\"M5\":" + BarsJson(list[i], PERIOD_M5, firstPush ? 450 : 14)'''),
])

edit('static/prefs_ui.js', [
    ("scale: !!p.scale }; }", "scale: !!p.scale, fast: !!p.fast }; }"),
    ('else if (key === "scale") D.scale = !D.scale;', 'else if (key === "scale") D.scale = !D.scale; else if (key === "fast") D.fast = !D.fast;'),
    ("entries: D.entries, scale: D.scale }", "entries: D.entries, scale: D.scale, fast: D.fast }"),
    ("""      if (ERR) h += '<p class="note">' + esc(ERR) + "</p>";
      h += '<div class="jrow">""", """      h += sw("fast", "Also scan every 5 minutes", "Checks 5-minute candles too, so it looks for setups more often. Not tested on past data yet: use a demo account. MT5 users need the updated EA.", D.fast);
      if (ERR) h += '<p class="note">' + esc(ERR) + "</p>";
      h += '<div class="jrow">"""),
])

open('tools/fetch_gold_m5.py', 'w', encoding='utf-8').write('''"""Downloads ~60 days of gold futures (GC=F) 5-minute and 15-minute candles from Yahoo into XAUUSD_M5.csv and XAUUSD_M15.csv (UTC).
Then test the fast scan on it:  python tools/backtest.py XAUUSD_M5.csv XAUUSD_M15.csv --solo
Futures prices differ slightly from your broker's spot XAUUSD: a rough check only. Needs internet.\"\"\"
import json, urllib.request, datetime as dt
def get(interval, out):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval}&range=60d'
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
    r = d['chart']['result'][0]; q = r['indicators']['quote'][0]; n = 0
    with open(out, 'w') as f:
        for i, t in enumerate(r['timestamp']):
            o, h, l, c = q['open'][i], q['high'][i], q['low'][i], q['close'][i]
            if None in (o, h, l, c): continue
            x = dt.datetime.fromtimestamp(t, dt.timezone.utc)
            f.write(f"{x:%Y.%m.%d},{x:%H:%M},{o},{h},{l},{c}\\n"); n += 1
    print(out, n, 'candles')
get('5m', 'XAUUSD_M5.csv'); get('15m', 'XAUUSD_M15.csv')
''')
print('P9c applied')
