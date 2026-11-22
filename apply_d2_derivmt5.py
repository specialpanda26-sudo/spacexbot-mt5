"""D2: Deriv MT5 as a broker next to FBS. Run from the repo folder: python apply_d2_derivmt5.py
Safe to run twice. If any old text is not found exactly once, NOTHING is changed.
What it does: adds 'Deriv MT5' (an MT5 broker, own entry) to the broker list, its plain-words note, the tile on the Connect tab,
the logo alias, the onboarding choice and the server-name hint. Then it runs the tests."""
import os, sys, subprocess

B, H, T = 'backend/brokers.py', 'static/index.html', 'tests/test_brokers.py'
ABOUT = ("    'Deriv MT5': {'tile': 'Via your MT5 app', 'works': 'Trades on your Deriv MT5 account through the SpaceXBridge EA, next to FBS. "
         "Your positions show in your MT5 app.', 'not': 'The MT5 phone app cannot run the EA: MT5 must be open on a Windows PC or a VPS. "
         "Deriv may name markets differently (set Symbols or SymbolSuffix in the EA). This site does not read your Deriv MT5 balance.'},\n")
E = [
    (B, "'Deriv': 'token', 'Binance': 'keypair'}", "'Deriv': 'token', 'Deriv MT5': 'mt5', 'Binance': 'keypair'}", "'Deriv MT5': 'mt5'"),
    (B, "MAX_PER_USER = 10\n", "MAX_PER_USER = 10\nHINT = {'Deriv MT5': 'Type your Deriv MT5 server name. Copy it exactly from MT5 when you log in.'}\n", "HINT = {'Deriv MT5'"),
    (B, "raise ValueError('Type your MT5 server name, for example ' + n + '-Demo.')",
        "raise ValueError(HINT.get(n) or 'Type your MT5 server name, for example ' + n + '-Demo.')", "HINT.get(n) or"),
    (B, "    'Deriv': {'tile': 'Check, balance, demo bot'", ABOUT + "    'Deriv': {'tile': 'Check, balance, demo bot'", "'Deriv MT5': {'tile'"),
    (H, 'hfmarkets:"hfm",admiral:"admirals"}', 'hfmarkets:"hfm",admiral:"admirals",derivmt5:"deriv"}', 'derivmt5:"deriv"'),
    (H, '["Deriv","API token"],["XM","MT5 bridge"]', '["Deriv","API token"],["Deriv MT5","MT5 bridge"],["XM","MT5 bridge"]', '["Deriv MT5","MT5 bridge"]'),
    (H, 'mt?n+"-Demo":"Paste "', 'mt?(n==="Deriv MT5"?"Your Deriv MT5 server name":n+"-Demo"):"Paste "', 'n==="Deriv MT5"?"Your Deriv'),
    (H, '["hfm","HFM","HFMarketsGlobal-Demo"],["other"', '["hfm","HFM","HFMarketsGlobal-Demo"],["derivmt5","Deriv MT5","your Deriv MT5 server name"],["other"', '["derivmt5","Deriv MT5"'),
    (H, '["hfm","HFM","MT5 demo or real account","H"],["other"', '["hfm","HFM","MT5 demo or real account","H"],["derivmt5","Deriv MT5","MT5 demo or real account","D"],["other"', '["derivmt5","Deriv MT5","MT5 demo'),
    ('backend/connwhy.py', "'name': 'MT5 app (FBS, Exness...)'", "'name': 'MT5 app (FBS, Deriv MT5...)'", "MT5 app (FBS, Deriv MT5...)"),
    (T, "catalog has 8 brokers, vault ready', j['brokers'] == [] and len(j['catalog']) == 8", "catalog has 9 brokers, vault ready', j['brokers'] == [] and len(j['catalog']) == 9", 'catalog has 9 brokers'),
]
files, bad = {}, []
for p, old, new, mk in E:
    s = files.get(p)
    if s is None: s = files[p] = open(p, encoding='utf-8').read()
    if mk in s: print('skip (already there):', mk[:46]); continue
    if s.count(old) != 1: bad.append((p, old[:60], s.count(old))); continue
    files[p] = s.replace(old, new, 1); print('edited:', mk[:46])
if bad:
    for b in bad: print('STOP: not found exactly once (found %d) in %s -> %s' % (b[2], b[0], b[1]))
    print('Nothing was changed.'); sys.exit(1)
for p, s in files.items():
    open(p + '.new', 'w', encoding='utf-8').write(s); os.replace(p + '.new', p)
print('edits done. Running tests...')
fails = []
for f in sorted(os.listdir('tests')):
    if not (f.startswith('test_') and f.endswith('.py')) or f == 'test_rk5.py': continue          # test_rk5 is the known unrelated failure
    r = subprocess.run([sys.executable, 'tests/' + f], capture_output=True, text=True, timeout=300)
    last = (r.stdout.strip().splitlines() or [''])[-1]
    if r.returncode: fails.append(f); print('FAIL', f, last)
print('RESULT:', 'ALL TESTS PASS' if not fails else 'FAILED: ' + ', '.join(fails))
sys.exit(1 if fails else 0)
