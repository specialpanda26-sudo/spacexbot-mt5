"""Section SW1: the three OFF-by-default switches get check boxes in the admin 'Advanced' settings (static/index.html, the S4A list).
Run from the project folder: python apply_sw1.py  (safe to run twice). Needs apply_btc6b.py and apply_orb3.py to have been run first."""
def edit(path, pairs):
    s = open(path, encoding='utf-8').read(); o = s
    for old, new in pairs:
        if new in s: continue
        assert s.count(old) == 1, path + ': need exactly one: ' + old[:60]
        s = s.replace(old, new, 1)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)

OLD = '["max_trades_day","Max trades a day (0 = off)","n",0,100]];'
NEW = ('["max_trades_day","Max trades a day (0 = off)","n",0,100],'
       '["btc_sunday_bounce","BTC Sunday bounce (buys the first bounce after a big Friday sell-off; unproven)","c"],'
       '["btc_short_pullback","BTC pullback short (sells only after a pullback to the 4h 50 EMA; unproven)","c"],'
       '["orb_session","Opening range + session bias (second vote when Asia/London agree; unproven)","c"]];')
edit('static/index.html', [(OLD, NEW)])

NOTE = """
## Section SW1 (check boxes for the three OFF-by-default switches) DONE (Nov 22)
- static/index.html, the S4A list (Admin > Settings > Advanced, saved with 'Save advanced'): three check boxes, btc_sunday_bounce, btc_short_pullback and orb_session. Nothing else changed: the page already loads the values with POST /api/admin/settings {} and saves 0/1 strings, the server already refuses anything else. tests/test_sw1.py (reads the S4A list out of index.html, runs the page's own save/fill logic in node when node exists, and round-trips through the API). apply_sw1.py.
- Each switch is still OFF until ticked and saved. The three strategies are unproven: no backtest on real data yet.
- Next: the backtest on real data (needs the owner's M15 and H1 CSVs), N6 kind 35 once decided, and the fake-data clean-up (see 'Fake data scan' below if present).
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Section SW1' not in h:
    h = h.rstrip('\n') + '\n' + NOTE
    h = h.replace("- Next: N2 (backend/alerts.py leftovers), N6 kind 35 once decided, the backtest on real data, a screen for the three switches (optional).", "- Next: the backtest on real data, N6 kind 35 once decided (N2 was already done, see 'Progress Update - Section N2 DONE'; the switch check boxes are Section SW1).")
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h)
print('ok docs/HANDOFF.md')

SCAN = """
## Fake data scan (Nov 22, owner request; found only, NOT fixed; do not fix until the owner says which)
Clean: everything the backend serves (journal, P&L, stats, live account numbers, signals, push, mail) comes from real rows; backend/livestats.py, the Journal and the P&L card say so and the code agrees. A search found no random or invented numbers in backend/ or tools/. desktop/broker.py 'fake' is only a test seam.
All the fake data is the old demo layer in static/index.html (line numbers as of Nov 22):
1. Backtest card (about 1880-1945): runs on a RANDOM-WALK price series (series() with a seeded random generator) of the 8 pairs in the made-up price table P (line 1872; EURUSD 1.0842, XAUUSD 2041.6, BTCUSD 67420.5: old prices). The card title says 'sample data, not your bot', BUT its profit factor feeds the 'Run check' go-live verdict (line 1887, c4 = X.bt.pf > 1): a random result can print 'Backtest evidence: Profit factor 1.3, 6 of 8 pairs positive' and 'Conditions pass', and it writes a Journal note 'Backtest ran: profit factor ...' (line 1943). MOST MISLEADING item.
2. 'Focus pair now: XAUUSD (Buy setup, score 72)' (line 1936, #uFocus in Session limits): computed from the made-up table P by an(). Not live, not labelled.
3. News list (line 933 NEWS, shown by renderNews at 1011 in the News card): 5 fixed events (Core PCE, ECB speaks, ...) with fixed minutes-from-now. Not the real calendar (backend/news.py). Also drives nextHigh.
4. Weekly brief (line 1904): synthetic 7-day series, labelled 'Sample data'.
5. Home chart (CP table line 1449, nxt() random candles at 1241): random-walk chart, labelled with a 'Sample data' chip. The Autobot scan log (line 1513) is random text and is hidden when signed in.
6. Landing page phone mock-up (lines 610-615: equity $1,039.75, +$8.40, -$3.10): decorative, aria-hidden. Line 833 and 2344 already say 'sample data' while no broker is connected.
Suggested fix, one section each: (a) take the backtest out of the go-live verdict and out of the Journal, or replace it with the real tools/backtest.py result typed in by the owner; (b) hide or label Focus pair; (c) show the real news calendar (backend/news.py already loads it; check which endpoint can give the list) or hide the card until it loads; (d) label or remove 4 and 5 for signed-in users.
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Fake data scan' not in h:
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h.rstrip('\n') + '\n' + SCAN)
print('ok docs/HANDOFF.md (scan)')
