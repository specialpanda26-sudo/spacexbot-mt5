"""Burst mode, Section 2 (scanner hook). tests/test_burst2.py is written just before this by the same command.
Adds burst.look() and app._burst_scan(): when burst mode is on and the bot has been quiet long enough, it looks for a quick chance on the 5-minute
candles (15-minute if none), accepts ONE agreeing strategy (the regime filter still decides which kinds of strategy may fire), and writes the group.
Each old text must be found exactly once or NOTHING is changed. Safe to run twice."""
import sys, os

LOOK = '''def look(uid='', now=None):
    """due() for the scanner. When the bot cannot trade right now (stopped, MT5 offline, a loss limit...) the quiet timer starts again from this moment."""
    now = now or time.time(); ok, why = due(uid, now)
    if not ok and not (why.startswith('quiet for') or why in ('a burst is already running', 'burst mode is off', 'burst mode is switched off by the owner')): closed(uid, now)
    return ok, why


def plan(uid, score, now=None):'''

SCAN = '''def _burst_scan(sym, uid=''):
    """Burst mode: after the quiet minutes, take a quick chance. One strategy is enough (min_conf 1); the ADX regime filter, the stop-distance check,
    the news lock, currency exposure and every loss limit still apply. 5-minute candles when the EA sends them, else 15-minute."""
    if not burst.get(uid)['on']: return
    k = (uid, sym, 'burst')
    if time.time() - _last_scan.get(k, 0) < 20: return
    _last_scan[k] = time.time()
    ok, why = burst.look(uid)
    if not ok: return
    m5 = bars.get(sym, 'M5', uid); tf, hi = ('M5', 'M15') if m5 else ('M15', 'H1')
    m = m5 or bars.get(sym, 'M15', uid); h = bars.get(sym, hi, uid)
    if not m: return
    key = f'lastbar:{uid}:{sym}:burst'
    if st.get(key) == str(m[-1]['t']): return          # already looked at this candle
    st.put(key, m[-1]['t'])
    off = {x for x in (st.get('strategies_off') or '').split(',') if x}
    if st.get('auto_disable') == '1': off |= stats.losers(int(st.fget('auto_disable_min_trades')), uid)
    solo = {x for x in (st.get('strategies_solo') or '').split(',') if x}
    orf = stats.regime_off(uid) if st.get('regime_switch') == '1' else None
    off, solo, _mc = prefs.apply(uid, off, solo, 1)
    info = {}; s = brain.evaluate(m, h, 1, st.fget('rr'), off, solo=solo, info=info, off_reg=orf)
    if not s: return
    ok, why = risk.symbol_gate(sym, s['side'], uid=uid, cool=False)
    if not ok: print('burst skip', sym, s['side'], why); return
    pl, why = burst.plan(uid, s['score'])
    if not pl: print('burst skip', sym, why); return
    s.setdefault('why', {})['burst'] = {'kind': pl['kind'], 'n': pl['n'], 'each': pl['each'], 'tf': tf}
    ids = burst.create(uid, sym, s, pl, rsn.pack(s))
    sbauth.notify(f"BURST {s['side'].upper()} {sym}", si.alert_body(s['strategy'], s['entry'], s['sl'], s['tp']), key=f'sig{ids[0]}-new', only=uid or None)
    for i in ids: lag.created(i, m[-1]['t'], uid)
    print('burst', pl['kind'], sym, s['side'], pl['n'], 'entries', pl['each'], 'USD each')
    botstate.note(uid, sym, 'signal')
    learn.log(uid, 'signal', s['strategy'], sym, s['side'], data={'score': s['score'], 'adx': s['adx'], 'entry': s['entry'], 'burst': pl['kind'], 'n': pl['n']})
    if not uid: assist.announce(ids[0])

@app.post('/api/ea/sync')'''

CALL_OLD = "    if prefs.get(uid)['fast']: _scan_tf(sym, uid, 'M5', 'M15')          # fast scan: the same strategies on 5-minute candles, 15-minute candles as the higher chart"
CALL_NEW = CALL_OLD + "\n    try: _burst_scan(sym, uid)\n    except Exception as e: print('burst scan failed', sym, str(e)[:120])"
EDITS = [
 ('backend/burst.py', 'def plan(uid, score, now=None):', LOOK, 'def look(uid'),
 ('backend/app.py', CALL_OLD, CALL_NEW, 'try: _burst_scan(sym, uid)'),
 ('backend/app.py', "@app.post('/api/ea/sync')", SCAN, 'def _burst_scan('),
]
if not os.path.isdir('backend') or not os.path.isdir('static'): print('STOP: run this from the repo folder (spacexbot-mt5)'); sys.exit(1)
if not os.path.exists('backend/burst.py') or 'def burst_get(' not in open('backend/app.py', encoding='utf-8').read(): print('STOP: apply Section 1 first'); sys.exit(1)
new = {}
for path, old, rep, marker in EDITS:
    t = new.get(path) if path in new else open(path, encoding='utf-8', newline='').read()
    if marker in t: new[path] = t; continue
    if t.count(old) != 1: print('STOP: cannot find exactly once in', path, '->', old[:60]); sys.exit(1)
    new[path] = t.replace(old, rep)
for path, t in new.items(): open(path, 'w', encoding='utf-8', newline='').write(t)
print('patched OK')
