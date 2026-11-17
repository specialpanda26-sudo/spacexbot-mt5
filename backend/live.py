"""Live 'Bot running' phone notification. Every minute, while the bot is on and the EA is online, each phone gets a silent
data message; the app's native service shows it as one pinned notification that updates in place.
Admins see balance and floating profit. Subscribers see only what the app already shows them: bot status, today, open trades."""
import os, time, json, threading
from . import store as st, push

PERIOD, HEARTBEAT = 60, 170          # check every 60 s; resend an unchanged notification every 170 s so it never times out
CUR = os.getenv('LIVE_CUR', '$')
_last = {}                           # uid -> (signature, time sent)
_started = False

def _m(v, signed=False):
    try: x = float(v)
    except (TypeError, ValueError): return '--'
    s = format(abs(x), ',.2f')
    return ('+' if x > 0 and signed else '-' if x < 0 else '') + CUR + s

def snapshot(now=None):
    now = now or time.time(); a = st.acct()
    on = st.get('bot_enabled') == '1' and now - a.get('seen', 0) < 120
    t = st.q('SELECT COUNT(*) n, COALESCE(SUM(pnl),0) pnl FROM signals WHERE created>=?', (st.day_start(),), True) or {}
    opn = st.q("SELECT symbol,side,fill,entry FROM signals WHERE status='open' ORDER BY id DESC LIMIT 6") or []
    return {'on': on, 'a': a, 'today': t.get('pnl') or 0, 'open': list(opn), 'now': now}

def build(admin, s):
    a = s['a']; bal, eq = a.get('balance'), a.get('equity'); n = int(a.get('open') or len(s['open']) or 0)
    title = 'Bot running' + ('  |  ' + _m(bal) if admin and bal is not None else '')
    text = 'Today ' + _m(s['today'], True) + '  |  ' + (str(n) + ' open' if n else 'no open trades')
    lines = []
    if admin and bal is not None: lines.append('Balance ' + _m(bal) + ('   Equity ' + _m(eq) if eq is not None else ''))
    if admin and bal is not None and eq is not None: lines.append('Floating P/L ' + _m(float(eq) - float(bal), True))
    lines.append('Today ' + _m(s['today'], True))
    if s['open']:
        lines.append('Open trades:')
        for o in s['open']: lines.append('  ' + str(o['side']).upper() + ' ' + str(o['symbol']) + ' at ' + str(o.get('fill') or o.get('entry') or '--'))
    else: lines.append('No open trades right now')
    return {'type': 'live', 'title': title, 'text': text, 'big': '\n'.join(lines), 'ts': int(s['now'])}

def tick(now=None):
    s = snapshot(now); now = s['now']
    admins = {x.strip().lower() for x in os.getenv('ADMIN_EMAILS', '').split(',') if x.strip()}
    for r in st.q('SELECT DISTINCT u.uid AS uid,u.email AS email,u.plan_until AS pu,u.notif AS notif FROM users u JOIN push_tokens t ON t.uid=u.uid'):
        uid = r['uid']; admin = (r['email'] or '').lower() in admins
        if not (admin or (r['pu'] or 0) > now): continue
        try: pref = json.loads(r.get('notif') or '{}').get('live', 1) not in (0, False, '0')
        except ValueError: pref = True
        if not pref: continue
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
