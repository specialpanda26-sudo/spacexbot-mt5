"""R5 auto markets. Only adds: backend/automarkets.py, three settings (all off/empty by default), an owner route /api/admin/markets and a 10 minute loop. Run once from the repo root."""
import sys
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        if s.count(old) != 1: sys.exit('NOT FOUND exactly once in %s: %r' % (path, old[:70]))
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)

edit('backend/store.py', [
    ("'multi_entries': os.getenv('MULTI_ENTRIES', '1'), ", "'auto_markets': '0', 'symbols_pool': os.getenv('SYMBOLS_POOL', ''), 'auto_markets_max': '2', 'multi_entries': os.getenv('MULTI_ENTRIES', '1'), "),
])
edit('backend/app.py', [
    ("\nfrom . import lag, multi\n", "\nfrom . import lag, multi, automarkets\n"),
    ("@app.get('/api/plans')\n", "@app.get('/api/admin/markets')\n@need(admin=True)\ndef admin_markets(u): return jsonify(automarkets.status())\n\n@app.get('/api/plans')\n"),
    ("try: deriv.start(_scan, _paid)\n", "try: automarkets.start()\nexcept Exception as e: print('[markets] loop not started', e)\ntry: deriv.start(_scan, _paid)\n"),
])
print('R5 auto markets added')
