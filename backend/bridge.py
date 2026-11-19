"""Section 7: what the MT5 bridge (ea/SpaceXBridge.mq5 or the Windows app) is really doing, in plain words. GET /api/bridge.
Nothing here is made up: it reads the account snapshot the EA last posted to /api/ea/sync (st.acct) and the real bot switch.
state: 'nolink'  a subscriber who has not made a personal key yet | 'expired' plan ended, the server ignores the EA | 'never' the EA has not reported yet
       'offline' it reported before but not in the last OFFLINE seconds | 'online'
Same limit as the rest of the app for 'EA online': OFFLINE = 120 s (risk.global_gate, /api/status)."""
import time
from . import store as st, links, risk

OFFLINE = 120


def _f(v):
    try: x = float(v)
    except (TypeError, ValueError): return None
    return x if x == x and abs(x) != float('inf') else None


def _checklist(site, owner):
    key = 'the EA_KEY you set on Render' if owner else 'your personal key from the Connect your MT5 card'
    return [
        {'t': 'Allow the web address', 'd': 'In MT5 open Tools, Options, Expert Advisors, tick Allow WebRequest and add %s (no slash at the end).' % site},
        {'t': 'Attach the bridge', 'd': 'Drag SpaceXBridge onto the XAUUSD chart. Press F7 and set ServerUrl to %s and EAKey to %s.' % (site, key)},
        {'t': 'Turn Algo Trading on', 'd': 'The Algo Trading button at the top of MT5 must be green, and the chart corner must show a smiling face.'},
        {'t': 'Read the Experts tab', 'd': 'At the bottom of MT5 open Experts. Error 4014 or 4060 means the web address is not allowed. 401 or bad key means the key is wrong.'},
    ]


def describe(uid, admin, paid, site, now=None):
    """uid: the person's uid. admin: the owner (their own EA, scope ''). paid: plan active. site: this server's address (no slash)."""
    now = now or time.time(); scope = '' if admin else uid; site = (site or '').rstrip('/')
    out = {'state': 'never', 'message': '', 'login': None, 'balance': None, 'equity': None, 'open': None, 'mode': None, 'allow_live': None,
           'age': None, 'bot': False, 'can_trade': False, 'why': '', 'warn': '', 'help': [], 'site': site}
    if not admin and not links.get(uid):
        out.update(state='nolink', message='No bridge key yet.', help=[{'t': 'Make your key', 'd': 'In the Connect your MT5 card on this tab, make your personal key, then paste it into the bridge as EAKey.'}] + _checklist(site, False)[:2])
        return out
    if not admin and not paid:
        out.update(state='expired', message='Your plan has ended, so the server ignores your bridge until you renew.')
        return out
    a = st.acct(scope) or {}; seen = _f(a.get('seen')) or 0
    out.update(login=str(a.get('login')) if a.get('login') not in (None, '') else None, balance=_f(a.get('balance')), equity=_f(a.get('equity')),
               open=int(_f(a.get('open')) or 0), mode='demo' if a.get('demo') is True else 'real' if a.get('demo') is False else None,
               allow_live=a.get('allow_live') if isinstance(a.get('allow_live'), bool) else None, bot=bool(links.bot_on(scope)))
    ok, why = risk.global_gate(now, uid=scope); out['can_trade'] = bool(ok); out['why'] = str(why or '')
    if not seen:
        out.update(state='never', message='The bridge has not reported yet. MT5 has not contacted this server.', help=_checklist(site, admin))
        return out
    age = max(0, int(now - seen)); out['age'] = age
    if age >= OFFLINE:
        out.update(state='offline', message='The bridge went quiet. Its last report was %s.' % _ago(age),
                   help=[{'t': 'Is MT5 open?', 'd': 'MT5 must stay open on your PC or VPS, with internet.'}, _checklist(site, admin)[2], _checklist(site, admin)[3]])
        return out
    kind = 'Demo' if out['mode'] == 'demo' else 'Real' if out['mode'] == 'real' else 'MT5'
    out.update(state='online', message='Bridge online. %s account%s.' % (kind, ' ' + out['login'] if out['login'] else ''))
    if out['mode'] == 'real' and out['allow_live'] is False: out['warn'] = 'This is a real account but the bridge setting AllowLive is false, so no real orders will be placed.'
    elif out['mode'] == 'real': out['warn'] = 'This is a real account and live trading is allowed in the bridge. Real money is at risk.'
    elif out['mode'] == 'demo' and out['allow_live'] is False: out['warn'] = 'Demo account. Live trading is blocked in the bridge, which is the safe setting.'
    return out


def _ago(s):
    return 'just now' if s < 10 else '%d s ago' % s if s < 90 else '%d min ago' % round(s / 60) if s < 5400 else '%d h ago' % round(s / 3600) if s < 129600 else '%d days ago' % round(s / 86400)
