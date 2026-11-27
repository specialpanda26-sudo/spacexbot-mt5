"""PL6: per-account market choice + switch. The scanner skips markets the account did not choose (nothing chosen = every market, as before).
Needs backend/mt5_markets.py (created by the cat above). Patches backend/app.py. Safe to run twice."""
p = 'backend/app.py'; s = open(p, encoding='utf-8').read()
if 'mt5_markets' in s: print(p, 'already patched, skipping')
else:
    pairs = [
     ("from . import quickprofit          # QP1: take small profits\n", "from . import quickprofit          # QP1: take small profits\nfrom . import mt5_markets          # PL6: which markets this account's MT5 bot trades\n"),
     ("    for sym in bz:\n        try: _scan(sym, who)\n", "    for sym in bz:\n        if not mt5_markets.allowed(who, sym): continue          # PL6: a market this account did not choose gets no new signals (open trades are never touched)\n        try: _scan(sym, who)\n"),
     ("@app.get('/api/burst')\n", "@app.get('/api/markets')\n@need(verified=True)\ndef mk_get(u): return jsonify(mt5_markets.view('' if u.get('admin') else u['uid']))          # PL6: the owner's own MT5 EA runs under scope ''\n\n@app.post('/api/markets')\n@need(verified=True)\ndef mk_set(u):\n    j = _j(); sc = '' if u.get('admin') else u['uid']\n    if not isinstance(j, dict): return jsonify(error='Send the choice as an object'), 400\n    try: mt5_markets.switch(sc, j.get('to', ''), j.get('mode', 'only'))\n    except ValueError as e: return jsonify(error=str(e)), 400\n    return jsonify(mt5_markets.view(sc))\n\n@app.get('/api/burst')\n"),
    ]
    for old, new in pairs:
        assert s.count(old) == 1, 'anchor count %d: %s' % (s.count(old), old[:50])
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s); print(p, 'patched')
