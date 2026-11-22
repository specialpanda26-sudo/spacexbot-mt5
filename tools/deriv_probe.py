"""Deriv probe: READ-ONLY. Shows what Deriv really answers, so the bot's guesses can be checked. It never buys or sells and writes nothing.
Run in Termux:  pip install requests websocket-client   then   python tools/deriv_probe.py
Paste your Deriv token when asked (it is not shown and not saved). Optional: set DERIV_APP_ID first if you use a personal token.
Send the printout back (it shows structure only; account ids are cut to 3 letters)."""
import os, sys, json, getpass

BASE = os.getenv('DERIV_BASE', 'https://api.derivws.com').rstrip('/')
APP = os.getenv('DERIV_APP_ID', '').strip()


def mask(v):
    s = str(v)
    return s[:3] + '***' if len(s) > 3 else '***'


def shape(o, depth=0):
    if isinstance(o, dict):
        return {k: (shape(v, depth + 1) if depth < 3 else type(v).__name__) for k, v in o.items()}
    if isinstance(o, list):
        return [shape(o[0], depth + 1)] if o else []
    return type(o).__name__


def main():
    try:
        import requests
        import websocket
    except ImportError:
        print('Install first:  pip install requests websocket-client')
        return 1
    tok = getpass.getpass('Deriv token (hidden): ').strip()
    if not tok:
        print('No token.')
        return 1
    h = {'Authorization': 'Bearer ' + tok, 'Accept': 'application/json'}
    if APP:
        h['Deriv-App-ID'] = APP
    print('\n[1] GET /trading/v1/options/accounts')
    r = requests.get(BASE + '/trading/v1/options/accounts', headers=h, timeout=15)
    print('    HTTP', r.status_code)
    try:
        j = r.json()
    except ValueError:
        j = {}
    print('    shape:', json.dumps(shape(j)))
    accts = j.get('data') if isinstance(j, dict) else None
    if not isinstance(accts, list) or not accts:
        print('    no accounts found. Stop here and send this printout.')
        return 0
    demo = None
    for a in accts:
        if not isinstance(a, dict):
            continue
        keep = {k: (mask(v) if 'id' in k.lower() else v) for k, v in a.items() if not isinstance(v, (dict, list))}
        print('    account:', json.dumps(keep))
        if demo is None and 'demo' in json.dumps(a).lower():
            demo = a
    if demo is None:
        print('    no demo account found. Make one on Deriv, then run again.')
        return 0
    aid = demo.get('account_id') or demo.get('id') or demo.get('loginid')
    print('\n[2] POST .../accounts/<demo id>/otp')
    r = requests.post('%s/trading/v1/options/accounts/%s/otp' % (BASE, aid), headers=h, data=b'', timeout=15)
    print('    HTTP', r.status_code)
    try:
        u = (r.json().get('data') or {}).get('url')
    except ValueError:
        u = None
    print('    url given:', bool(u), '| starts with wss://', str(u).startswith('wss://'))
    if not u:
        return 0
    ws = websocket.create_connection(u, timeout=15)
    n = [0]

    def ask(msg):
        n[0] += 1
        ws.send(json.dumps(dict(msg, req_id=n[0])))
        for _ in range(12):
            d = json.loads(ws.recv())
            if d.get('req_id') == n[0] or (d.get('echo_req') or {}).get('req_id') == n[0]:
                return d
        return {}

    def err(d):
        e = d.get('error') or {}
        return (e.get('code'), e.get('message')) if e else None

    print('\n[3] balance')
    d = ask({'balance': 1})
    print('    keys:', list(d.keys()), '| balance keys:', list((d.get('balance') or {}).keys()) if isinstance(d.get('balance'), dict) else d.get('balance'), '| error:', err(d))

    print('\n[4] candles for gold (M15, 5 candles), both spellings')
    for label, extra in (('ticks_history=frxXAUUSD', {}), ('+ underlying_symbol', {'underlying_symbol': 'frxXAUUSD'})):
        d = ask(dict({'ticks_history': 'frxXAUUSD', 'style': 'candles', 'granularity': 900, 'count': 5, 'end': 'latest'}, **extra))
        c = d.get('candles')
        print('    %-24s candles:%s first keys:%s error:%s' % (label, len(c) if isinstance(c, list) else None, list(c[0].keys()) if isinstance(c, list) and c else None, err(d)))

    print('\n[5] symbols that look like gold or forex')
    d = ask({'active_symbols': 'brief'})
    rows = d.get('active_symbols') if isinstance(d.get('active_symbols'), list) else []
    print('    total:', len(rows), '| error:', err(d))
    for x in rows:
        s = json.dumps(x)
        if 'XAU' in s.upper() or 'GOLD' in s.upper():
            print('    gold:', json.dumps({k: v for k, v in x.items() if not isinstance(v, (dict, list))})[:200])
    print('    has frxXAUUSD:', any('frxXAUUSD' in json.dumps(x) for x in rows))

    print('\n[6] quote only (NO buy): MULTUP on gold with stop and target')
    d = ask({'proposal': 1, 'contract_type': 'MULTUP', 'underlying_symbol': 'frxXAUUSD', 'currency': demo.get('currency') or 'USD', 'amount': 10, 'basis': 'stake', 'multiplier': 100,
             'limit_order': {'stop_loss': 5, 'take_profit': 10}})
    print('    proposal ok:', isinstance(d.get('proposal'), dict) and bool(d['proposal'].get('id')), '| error:', err(d))
    ws.close()
    print('\nDone. Nothing was bought, nothing was saved.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
