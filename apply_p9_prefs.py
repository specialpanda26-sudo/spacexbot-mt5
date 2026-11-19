"""P9: per-person strategy picks, entries per setup, auto-scale, fuller journal. Run once from the repo root."""
import sys
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if s.count(old) != 1: sys.exit('NOT FOUND exactly once in %s: %r' % (path, old[:70]))
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)

edit('backend/app.py', [
    ("from . import lag, multi, automarkets\n", "from . import lag, multi, automarkets, prefs, scale\n"),
    ("    info = {}; s = brain.evaluate(m15, h1, int(st.fget('min_confluence')), st.fget('rr'), off, solo=solo, info=info, off_reg=orf)",
     "    off, solo, mc = prefs.apply(uid, off, solo, int(st.fget('min_confluence')))\n    info = {}; s = brain.evaluate(m15, h1, mc, st.fget('rr'), off, solo=solo, info=info, off_reg=orf)"),
    ("n = multi.entries(uid, s['score']);", "n = multi.entries(uid, s['score'], s['strategy']);"),
    ("@app.post('/api/admin/testprice')", '''@app.get('/api/prefs')
@need(verified=True)
def prefs_get(u):
    sc = _mine(u); from . import strategies as S
    p = prefs.get(sc); hot = scale.hot(sc)
    return jsonify(prefs=p, strategies=[{'id': f.__name__, 'name': si.name(f.__name__), 'about': si.desc(f.__name__)} for f in S.ALL],
                   ceiling=limits.ceiling(), scale_now={'on': hot[0], 'why': hot[1]}, owner_entries=multi._g('multi_entries', 1))

@app.post('/api/prefs')
@need(verified=True)
def prefs_set(u):
    j = _j()
    try: out = prefs.save(_mine(u), j)
    except ValueError as e: return jsonify(error=str(e)), 400
    learn.log(u['uid'], 'setting', data={'path': request.path, **{k: v for k, v in j.items() if k in ('min_conf', 'entries', 'alone', 'scale')}})
    return jsonify(prefs=out)

@app.post('/api/admin/testprice')'''),
])

edit('backend/journal.py', [
    ("'tp': r.get('tp'), 'lots': r.get('lots'), 'why': rsn.short(r.get('reason'))})",
     "'tp': r.get('tp'), 'lots': r.get('lots'), 'why': rsn.short(r.get('reason')), '_raw': r.get('reason')})"),
    ("    return {'rows': show[:max(1, int(limit))],",
     "    shown = show[:max(1, int(limit))]\n    for r in shown: _detail(r)\n    for r in allr: r.pop('_raw', None)\n    return {'rows': shown, 'open': open_now(uid, admin),"),
    ("def numbers(rows):", '''def _detail(r):
    raw = r.pop('_raw', None); r['why_lines'] = rsn.lines(raw, r.get('strategy'))
    r['how'] = [{'name': si.name(x), 'about': si.desc(x)} for x in str(r.get('strategy') or '').split('+') if x]
    c = st.q("SELECT v FROM kv WHERE k=?", ('closedby:%s' % r['id'],), True); r['closed_by'] = c['v'] if c else ''


def open_now(uid, admin):
    a, b = scope(uid, admin); out = []
    for r in st.q("SELECT id,symbol,side,strategy,entry,sl,tp,fill,lots,created,status,reason FROM signals WHERE status IN('open','pending','sent') AND COALESCE(uid,'') IN (?,?) ORDER BY id DESC LIMIT 50", (a, b)) or []:
        out.append({'id': r['id'], 'symbol': r['symbol'], 'side': str(r['side'] or '').lower(), 'strategy_name': si.label(r['strategy']), 'status': r['status'], 'entry': r['entry'], 'fill': r['fill'],
                    'sl': r['sl'], 'tp': r['tp'], 'lots': r['lots'], 't': int(r['created'] or 0), 'why_lines': rsn.lines(r['reason'], r['strategy']),
                    'how': [{'name': si.name(x), 'about': si.desc(x)} for x in str(r['strategy'] or '').split('+') if x]})
    return out


def numbers(rows):'''),
])

edit('backend/botstate.py', [
    ("    else: out.update(state='watching', why='Connected and watching. It checks the market each time a new 15-minute candle closes.', code='watching')\n    return out\n",
     "    else: out.update(state='watching', why='Connected and watching. It checks the market each time a new 15-minute candle closes.', code='watching')\n    out['quiet_min'] = _quiet_min(sc, now)\n    return out\n"),
    ("def _scan_words(", '''def _quiet_min(sc, now):
    r = st.q("SELECT MAX(created) c FROM signals WHERE COALESCE(uid,'')=?", (sc or '',), True) or {}
    return int(max(0, now - r['c']) // 60) if r.get('c') else None

def _scan_words('''),
])

edit('backend/multi.py', [
    ("from . import store as st, limits, risk", "from . import store as st, limits, risk, prefs, scale"),
    (open('backend/multi.py', encoding='utf-8').read()[open('backend/multi.py', encoding='utf-8').read().index("def cap():"):open('backend/multi.py', encoding='utf-8').read().index("def share(")], '''def cap(uid=''):
    p = prefs.get(uid)
    return max(1, min(HI, p['entries'] or _g('multi_entries', 1)))

def min_score():
    return max(1, _g('multi_min_score', 3))

def entries(uid, score, strategy=''):
    c = cap(uid); p = prefs.get(uid)
    try: sc = int(score or 0)
    except (TypeError, ValueError): sc = 0
    if c <= 1: return 1
    if p['scale']:
        if not scale.hot(uid, strategy)[0]: return 1
    elif sc < min_score() and not p['entries']: return 1
    room = limits.max_open(uid) - risk.open_count(uid)
    mt = limits.trades(uid)
    if mt > 0:
        used = st.q("SELECT COUNT(*) n FROM signals WHERE created>=? AND status IN('pending','sent','open','closed') AND COALESCE(uid,'')=?", (st.day_start(), uid), True)['n']
        room = min(room, mt - used)
    return max(1, min(c, room))

'''),
])
print('P9 applied')
