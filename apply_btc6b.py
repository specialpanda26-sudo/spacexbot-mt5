"""BTC Section 6B: register backend/btc_weekend.py. Run from the project folder: python apply_btc6b.py  (safe to run twice)."""
import os
def edit(path, pairs):
    s = open(path, encoding='utf-8').read(); o = s
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, path + ': need exactly one: ' + old[:60]
        s = s.replace(old, new, 1)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)

edit('backend/strategies.py', [
    ("from .btc_range import btc_range\n", "from .btc_range import btc_range\nfrom .btc_weekend import btc_sunday_bounce, btc_pullback_short\n"),
    ("orb_entry, btc_range, jg_pullback,", "orb_entry, btc_range, btc_sunday_bounce, btc_pullback_short, jg_pullback,"),
    ("'orb_entry', 'btc_range'}", "'orb_entry', 'btc_range', 'btc_pullback_short'}"),
])
edit('backend/store.py', [
    ("'auto_target_usd': os.getenv('AUTO_TARGET_USD', '0'), 'plans': ''}", "'auto_target_usd': os.getenv('AUTO_TARGET_USD', '0'), 'btc_sunday_bounce': '0', 'btc_short_pullback': '0', 'plans': ''}"),
])
edit('backend/app.py', [
    ("    for k, v in j.items():\n        if k in st.DEFAULTS and k != 'plans': st.put(k, v)",
     "    for k in ('btc_sunday_bounce', 'btc_short_pullback'):          # BTC 6B switches: 0 or 1 only, checked before anything is saved\n        if k in j and str(j[k]) not in ('0', '1'): return jsonify(error='%s must be 0 or 1' % k), 400\n    for k, v in j.items():\n        if k in st.DEFAULTS and k != 'plans': st.put(k, v)"),
])
i = open('backend/strategy_info.py', encoding='utf-8').read()
k = i.index("    'btc_range':"); e = i.index("\n", k) + 1
edit('backend/strategy_info.py', [(i[k:e], i[k:e] +
    "    'btc_sunday_bounce': ('BTC Sunday bounce', 'After a big Friday sell-off, buys the first bounce in the Sunday open window, target the 0.382 fib. Off until switched on (video 2).'),\n"
    "    'btc_pullback_short': ('BTC pullback short', 'With the 4h trend down, sells only after a pullback to the 4h 50 EMA or a bear-flag breakdown. Off until switched on (video 3).'),\n")])

NOTE = """
## BTC Section 6B (backend/btc_weekend.py, two optional weekend rules) DONE (Nov 22)
- New: backend/btc_weekend.py, tests/test_btc6b.py (98 checks, mutation-checked: 40 deliberate breaks, each went red), apply_btc6b.py (registers in strategies.py, store DEFAULTS, strategy_info, and a 0/1 check in POST /api/admin/settings). No existing strategy file was edited.
- Two strategies, each behind its OWN setting, both default 0 (OFF; silent until set to 1 with POST /api/admin/settings {"btc_sunday_bounce": "1"} / {"btc_short_pullback": "1"}, owner only, any other value is refused). There is NO screen for them yet. Neither is SOLO.
- btc_sunday_bounce (video 2, BUY only): after a Friday (UTC) H1 fall of 3%+ with the high before the low, buys the FIRST green real-body candle Sunday 22:00-24:00 UTC (the window cannot run into Monday); stand down if a Sunday candle closed under the Friday low, the 0.382 fib was already touched in the window, or an earlier candle of the window already qualified. Stop under the window low, TP = 0.382 (tp2 = 0.5 in setup()). Registered in NEITHER the TREND nor the REVERSION group on purpose (the regime filter would silence a bounce in a strong trend).
- btc_pullback_short (video 3, SELL only, in TREND): bias down = last closed 4h candle under its FALLING 4h 50 EMA (4h grouped from H1, needs 60 4h candles = 240 H1 candles). Deep pullback = first red real-body candle that touched the EMA zone and closed back under it (no own target, the brain gives 2R). Shallow = bear-flag breakdown: impulse of 8 candles (4+ ATR), flag of 3-12 candles (longest that fits is used) that gives back at most half, never makes a new low and drifts up, a red real-body candle closing under the flag low; target = impulse height from the entry (RR 1.5); skipped when any of the last 21 candles touched the EMA zone (that is the deep case). A straight waterfall fires nothing.
- Honest limits: every number is an assumption (top of the file). NOT coded: break-even after the first move, the order-book reading, the stock-market link, a sell version of the Sunday rule, and a veto of OTHER strategies' shorts (the brain was not touched). Strategies do not see the symbol, so the pullback switch also runs on gold/forex candles. The Sunday window is a guess: Bitcoin has no real Sunday open. Friday and Sunday are read in UTC. NOT backtested on real BTC candles.
- Next: 4C (backend/orb_session.py), N6 kind 35 once decided, the backtest on real data, a screen for the two switches (optional).
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## BTC Section 6B' not in h:
    h = h.rstrip('\n') + '\n' + NOTE
    h = h.replace("Status: 6A DONE (see 'BTC Section 6A' at the end of this file); 6B not started.", "Status: 6A DONE (see 'BTC Section 6A' at the end of this file); 6B DONE (see 'BTC Section 6B').")
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h)
print('ok docs/HANDOFF.md')
