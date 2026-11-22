"""Section R2: "my broker is connected but the app says Not connected". GET /api/connections says, for each way of connecting, whether it really is connected and,
if not, the first real check that fails and what to do. Nothing is made up: every check reads the same data the rest of the app reads.
Two ways exist and they are separate:
- MT5 bridge (FBS, Exness, HFM...): saving an MT5 broker only keeps its server name. It is connected when the SpaceXBridge EA (or the Windows app) reports to the
  server with THIS person's key (the owner's EA_KEY only reaches the owner) in the last OFFLINE seconds (bridge.describe, the same limit the whole app uses).
- Deriv: connected when the server is set up (DERIV_APP_ID + BROKER_KEY), a token is saved and checked, and a balance was read. The balance is read when the token is
  saved and then every round while Start bot is on, so an old balance shows as 'stale' (Offline), not as missing.
row.state: 'ok' connected | 'stale' connected but old numbers | 'problem' set up but a check fails | 'none' not set up. summary.state: 'connected' if any row is ok or stale, else 'none'.
ASSUMPTIONS (tunable): FRESH = seconds a Deriv balance counts as live (same as backend/livestats.py)."""
import os, time
from . import store as st, links, brokers as bk, bridge, deriv

FRESH = 180


def _ago(s): return bridge._ago(max(0, int(s)))


def _ck(t, ok, d=''): return {'t': t, 'ok': ok, 'd': '' if ok else d}


def _first_fail(checks):
    return next((c for c in checks if c['ok'] is False), None)


def mt5_row(uid, admin, paid, site, now):
    d = bridge.describe(uid, admin, paid, site, now)
    s = d['state']
    saved = [{'name': b['name'], 'label': b.get('label') or ''} for b in bk.view(uid) if bk.CATALOG.get(b['name']) == 'mt5']
    key_ok = True if admin else bool(links.get(uid))
    if admin and not os.getenv('EA_KEY', '').strip(): key_ok = False
    checks = [
        _ck('Plan active', s != 'expired', 'Your plan has ended, so the server ignores your bridge until you renew.'),
        _ck('Bridge key', key_ok, 'EA_KEY is not set on Render, so no bridge can connect.' if admin else 'Make your personal key in the Connect your MT5 card and paste it into the bridge as EAKey. The owner\'s key does not work for you.'),
        _ck('Bridge has reported', s in ('online', 'offline'), 'MT5 has not contacted the server yet. In MT5 allow WebRequest for this address, attach SpaceXBridge, set ServerUrl and EAKey, and turn Algo Trading on (green).'),
        _ck('Reported in the last 2 minutes', s == 'online', 'The bridge went quiet%s. Keep MT5 open, with internet, and Algo Trading on.' % ((', its last report was ' + _ago(d['age'])) if d.get('age') is not None else '')),
    ]
    f = _first_fail(checks)
    state = ('ok' if s == 'online' else 'stale' if s == 'offline' else ('problem' if saved else 'none') if s == 'nolink'
             else ('problem' if (saved or not admin) else 'none') if s == 'never' else 'problem')
    head = d['message'] if s != 'never' or not saved else 'Your MT5 broker is saved, but the bridge has not reported yet.'
    if saved and s != 'online': head += ' Saving a broker only records its server name; the connection comes from the bridge.'
    return {'id': 'MT5', 'name': 'MT5 app (FBS, Deriv MT5...)', 'state': state, 'headline': head, 'checks': checks, 'fix': f['d'] if f else '', 'saved': saved,
            'mode': d.get('mode'), 'login': d.get('login'), 'age': d.get('age'), 'balance': d.get('balance')}


def deriv_row(uid, admin, paid, now):
    link = st.q("SELECT status FROM broker_links WHERE uid=? AND broker='Deriv'", (uid,), True)
    row = next((r for r in bk.view(uid) if r['name'] == 'Deriv'), {})
    app, vault = bool(deriv.ON()), bk.ready()
    miss = [n for n, v in (('DERIV_APP_ID', app), ('BROKER_KEY', vault)) if not v]
    status = (link or {}).get('status') or ''
    bal, t = row.get('balance'), row.get('bal_t')
    age = None if not t else max(0, int(now - float(t)))
    fresh = age is not None and age < FRESH
    checks = [
        _ck('Server is set up for Deriv', not miss, ('Set %s on Render, then redeploy.' % ' and '.join(miss)) if admin else 'The owner has not finished the Deriv setup on the server yet.'),
        _ck('Token saved', bool(link), 'Open Deriv on the Connect tab and paste your token (Read and Trade scopes).'),
        _ck('Token checked', status == 'verified', 'Deriv refused this token. Make a new one with Read and Trade scopes and save it.' if status == 'rejected' else 'The token is saved but not checked yet. Save it again to check it.'),
        _ck('Balance read', bal is not None, 'No balance was read yet. Save the token again, or tap Start bot.'),
        _ck('Balance is fresh (3 minutes)', fresh, 'The balance was last read %s. It refreshes every minute while the bot is on. Tap Start bot, or save the token again.' % (_ago(age) if age is not None else 'never')),
    ]
    if not admin: checks.append(_ck('Plan active', bool(paid), 'Your plan has ended. Renew it to trade.'))
    f = _first_fail(checks)
    if not link: state, head = 'none', 'Deriv is not set up.'
    elif f is None: state, head = 'ok', 'Deriv connected (%s account), balance $%.2f.' % ('Demo' if row.get('acct_demo') is not False else 'Real', float(bal))
    elif f['t'].startswith('Balance is fresh') and status == 'verified' and bal is not None: state, head = 'stale', 'Deriv is connected but the balance is old, so it shows Offline.'
    else: state, head = 'problem', 'Deriv is saved but not connected: %s.' % f['t'].lower()
    return {'id': 'Deriv', 'name': 'Deriv', 'state': state, 'headline': head, 'checks': checks, 'fix': f['d'] if f else '', 'bot': bool(row.get('bot')), 'bot_why': row.get('why') or '',
            'mode': 'real' if row.get('acct_demo') is False else 'demo' if row.get('acct_demo') is True else row.get('mode'), 'age': age, 'balance': bal}


def snapshot(uid, admin, paid, site='', now=None):
    now = now or time.time()
    rows = [deriv_row(uid, admin, paid, now), mt5_row(uid, admin, paid, site, now)]
    up = [r['name'] for r in rows if r['state'] in ('ok', 'stale')]
    first = next((r for r in rows if r['state'] == 'problem'), None) or next((r for r in rows if r['state'] == 'none'), None)
    if up: msg = 'Connected: %s.' % ' and '.join(up)
    elif first: msg = 'Nothing is connected yet. %s %s' % (first['headline'], first['fix'])
    else: msg = 'Nothing is connected yet.'
    return {'state': 'connected' if up else 'none', 'connected': up, 'message': msg.strip(), 'rows': rows, 'ts': int(now)}
