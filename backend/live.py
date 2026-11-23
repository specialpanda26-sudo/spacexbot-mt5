"""Live 'Bot running' phone notification. Every minute, while the bot is on and the EA is online, each phone gets a silent
data message; the app's native service shows it as one pinned notification that updates in place.
Admins see balance and floating profit. Subscribers see only what the app already shows them: bot status, today, open trades."""
import os, time, json, threading
from . import store as st, push, links, livestats

PERIOD, HEARTBEAT = 60, 170          # check every 60 s; resend an unchanged notification every 170 s so it never times out
CUR = os.getenv('LIVE_CUR', '$')
_last = {}                           # uid -> (signature, time sent)
_started = False

def _m(v, signed=False):
    try: x = float(v)
    except (TypeError, ValueError): return '--'
    s = format(abs(x), ',.2f')
    return ('+' if x > 0 and signed else '-' if x < 0 else '') + CUR + s

def _admins(): return {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}

def _is_admin(uid):
    r = st.q('SELECT email FROM users WHERE uid=?', (uid,), True) or {}
    return (r.get('email') or '').lower() in _admins()

def _running(uid, admin, srcs):
    """LIVE2: the bot counts as running when a connected account answered recently AND that account's own switch is on:
    Deriv -> the Deriv switch, MT5 -> the MT5 switch (the owner's EA switch for admins). Before, only the MT5 EA was looked at."""
    from . import deriv
    for s in srcs:
        if not s.get('online'): continue
        if s['id'] == 'Deriv' and deriv._bot(uid): return True
        if s['id'] == 'MT5' and links.bot_on('' if admin else uid): return True
        if s['id'] == 'Binance':          # LV4
            from . import binance_bot
            if binance_bot._bot(uid): return True
    return False

def snapshot(now=None, uid=''):
    now = now or time.time(); admin = _is_admin(uid)
    ls = livestats.snapshot(uid, admin, now); srcs = ls.get('sources') or []
    a = {'balance': ls['balance'], 'equity': ls['equity'], 'open': ls['open'], 'label': ' (%s %s)' % (srcs[0]['id'], srcs[0]['mode']) if ls.get('platform') and len(srcs) == 1 else ''} if srcs else {}
    return {'on': _running(uid, admin, srcs), 'a': a, 'today': ls['today'], 'open': list(ls.get('trades') or []), 'now': now,
            'float': ls.get('floating'), 'w': ls.get('today_w', 0), 'l': ls.get('today_l', 0), 'recent': ls.get('recent') or [], 'burst': _burst(uid, admin, now)}          # BX1

def explain(uid, now=None):
    """LIVE2: (ok, plain words) for the person: is the notification being sent to their phone, and if not, the first thing to fix."""
    now = now or time.time()
    if os.getenv('LIVE_NOTIF', '1') == '0': return False, 'The server has LIVE_NOTIF set to 0 on Render. Remove it, or set it to 1.'
    if not push.configured(): return False, 'Phone alerts are not set up on the server: FCM_SERVICE_ACCOUNT is missing on Render.'
    r = st.q('SELECT email,plan_until pu,notif FROM users WHERE uid=?', (uid,), True) or {}
    admin = (r.get('email') or '').lower() in _admins()
    if not push.tokens(uid): return False, 'No phone has registered for alerts yet. Open the Android app while signed in and allow notifications.'
    if not (admin or (r.get('pu') or 0) > now): return False, 'Your plan has ended, so live status is paused.'
    try: pref = json.loads(r.get('notif') or '{}').get('live', 1) not in (0, False, '0')
    except ValueError: pref = True
    if not pref: return False, 'The Live bot status switch is off in Profile, Notifications.'
    if not snapshot(now, uid)['on']: return False, 'The bot is not running, or no account has answered in the last 2 to 3 minutes. Start the bot and keep Deriv or the MT5 EA connected.'
    return True, 'Everything is in place. It appears within a minute. If it does not, allow notifications for this app in your phone settings.'

def _lv(label, v):
    """BX4: '  SL 2640.5' for a price level, '' when the trade has none."""
    try: x = float(v)
    except (TypeError, ValueError): return ''
    return '' if x != x or x == 0 else '  %s %s' % (label, format(round(x, 5 if abs(x) < 100 else 2), 'g'))

def _burst(uid, admin, now):
    """BX1: one short line about burst for the banner, or '' when burst is off for this person."""
    try:
        from . import burst, burst_scope, burst_live
        sc = burst_scope.scope({'uid': uid, 'admin': admin}); ex = burst.explain(sc, now)
        if ex['state'] == 'off': return ''
        if ex.get('blocked'): return 'paused, Auto mode is on'
        if ex['state'] == 'running':
            g = burst_live.group(sc, now); return 'running. ' + g if g else 'running'
        return 'on, ready for a chance' if ex['state'] == 'ready' else 'on, watching'
    except Exception: return ''

def build(admin, s):
    a = s['a']; bal, eq = a.get('balance'), a.get('equity'); n = int(a.get('open') or len(s['open']) or 0)
    fl = s.get('float')
    if fl is None and bal is not None and eq is not None: fl = float(eq) - float(bal)
    w, l = int(s.get('w') or 0), int(s.get('l') or 0)
    title = 'Bot running' + ('  |  ' + _m(bal) if admin and bal is not None else '')
    text = 'Float ' + _m(fl, True) + '  |  Today ' + _m(s['today'], True) + '  |  W' + str(w) + ' L' + str(l) + '  |  ' + (str(n) + ' open' if n else 'none open')
    lines = []
    if admin and bal is not None: lines.append('Balance ' + _m(bal) + (a.get('label') or '') + ('   Equity ' + _m(eq) if eq is not None else ''))
    lines.append('Floating P/L ' + _m(fl, True))
    lines.append('Today ' + _m(s['today'], True) + '   Wins ' + str(w) + '   Losses ' + str(l) + ('   Win rate %d%%' % round(w * 100.0 / (w + l)) if w + l else ''))
    if s.get('burst'): lines.append('Burst: ' + s['burst'])
    if s['open']:
        lines.append('Open trades:')
        for o in s['open']:
            lines.append('  ' + str(o['side']).upper() + ' ' + str(o['symbol']) + ' at ' + str(o.get('fill') or o.get('entry') or o.get('price') or '--') + _lv('SL', o.get('sl')) + _lv('TP', o.get('tp')) + ('   ' + _m(o['pnl'], True) if o.get('pnl') is not None else ''))          # BX4
    else: lines.append('No open trades right now')
    if s.get('recent'):
        lines.append('Last results:')
        for r in s['recent']: lines.append('  ' + ('Win  ' if r['pnl'] > 0 else 'Loss ' if r['pnl'] < 0 else 'Flat ') + str(r['symbol']) + '  ' + _m(r['pnl'], True))
    return {'type': 'live', 'title': title, 'text': text, 'big': '\n'.join(lines), 'ts': int(s['now'])}

def tick(now=None):
    now = now or time.time(); snaps = {}
    admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}
    for r in st.q('SELECT DISTINCT u.uid AS uid,u.email AS email,u.plan_until AS pu,u.notif AS notif FROM users u JOIN push_tokens t ON t.uid=u.uid'):
        uid = r['uid']; admin = (r['email'] or '').lower() in admins
        if not (admin or (r['pu'] or 0) > now): continue
        try: pref = json.loads(r.get('notif') or '{}').get('live', 1) not in (0, False, '0')
        except ValueError: pref = True
        if not pref: continue
        s = snaps.get(uid) or snaps.setdefault(uid, snapshot(now, uid))          # LIVE2: one look per person (the owner's Deriv counts too)
        data = build(admin, s) if s['on'] else {'type': 'live', 'off': '1'}
        sig = json.dumps({k: v for k, v in data.items() if k != 'ts'}, sort_keys=True); prev = _last.get(uid)
        if not s['on'] and (not prev or prev[0] == sig): continue          # nothing showing, or already told to hide
        if s['on'] and prev and prev[0] == sig and now - prev[1] < HEARTBEAT: continue
        if push.send_data(uid, data): _last[uid] = (sig, now)

def start():
    global _started
    if _started or os.getenv('LIVE_NOTIF', '1') == '0' or not push.configured(): return
    _started = True
    def run():
        time.sleep(20)
        while True:
            try: tick()
            except Exception as e: print('[live] tick failed', str(e)[:160])
            time.sleep(PERIOD)
    threading.Thread(target=run, daemon=True).start()
