"""Section 4C: register backend/orb_session.py. Run from the project folder: python apply_orb3.py  (safe to run twice).
Needs apply_btc6b.py to have been run first (it edits the lines 6B added)."""
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
    ("from .orb_entry import orb_entry\n", "from .orb_entry import orb_entry\nfrom .orb_session import orb_session\n"),
    ("orb_entry, btc_range, btc_sunday_bounce,", "orb_entry, orb_session, btc_range, btc_sunday_bounce,"),
    ("'orb_entry', 'btc_range', 'btc_pullback_short'}", "'orb_entry', 'orb_session', 'btc_range', 'btc_pullback_short'}"),
])
edit('backend/store.py', [
    ("'btc_short_pullback': '0', 'plans': ''}", "'btc_short_pullback': '0', 'orb_session': '0', 'plans': ''}"),
])
edit('backend/app.py', [
    ("for k in ('btc_sunday_bounce', 'btc_short_pullback'):", "for k in ('btc_sunday_bounce', 'btc_short_pullback', 'orb_session'):"),
])
i = open('backend/strategy_info.py', encoding='utf-8').read()
k = i.index("    'orb_entry':"); e = i.index("\n", k) + 1
edit('backend/strategy_info.py', [(i[k:e], i[k:e] +
    "    'orb_session': ('ORB + session bias', 'The opening range trade, only when Asia and London agree: one side swept = New York reverses, both = continues. Off until on.'),\n")])

NOTE = """
## Section 4C (backend/orb_session.py, the session bias for the opening range trade) DONE (Nov 22)
- New: backend/orb_session.py, tests/test_orb3.py, apply_orb3.py (registers in strategies.py ALL + TREND, store DEFAULTS, strategy_info, and the 0/1 check in POST /api/admin/settings). No existing strategy file was edited.
- analyse(c) reads the UTC day of the last candle: Asia range = high/low of 00:00-07:00 UTC; London = 07:00-12:00 UTC; a sweep = a London WICK beyond the Asia high/low by at least 0.1 ATR (ATR read at the last Asia candle, so the answer for a day never changes later). Only the high swept = bias SELL (New York reverses), only the low swept = bias BUY, BOTH swept = continuation in London's direction (London close against London open; no direction = no bias), no sweep = no bias. Needs the London window to be over (last candle at or after 12:00 UTC), Monday to Friday, 15-minute or finer candles, and 80% of the Asia and London candles present.
- with_session(fn) wraps any strategy (kept only when its side equals the bias). orb_session = orb_entry wrapped in it, registered in TREND, NOT SOLO, behind its OWN setting orb_session (default 0 = OFF; POST /api/admin/settings {"orb_session": "1"}, owner only, any other value is refused). There is NO screen for the switch yet.
- What the switch does when ON: an ORB trade that agrees with the session bias gets a SECOND vote (orb_entry + orb_session), so it can reach min_confluence 2 on its own. An ORB trade against the bias, or with no bias, keeps one vote and needs another strategy as before. It does NOT veto other strategies (the brain was not touched).
- Honest limits: every number is an assumption (top of the file). Asia and London are fixed UTC hours (London daylight saving is not followed). A wick beyond the range counts as a sweep even if price stays beyond it (a real breakout). Strategies do not see the symbol, so the switch is global (Asia/London hours mean little for BTC). NOT backtested on real data.
- Next: N2 (backend/alerts.py leftovers), N6 kind 35 once decided, the backtest on real data, a screen for the three switches (optional).
"""
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if '## Section 4C' not in h:
    h = h.rstrip('\n') + '\n' + NOTE
    h = h.replace("- 4C  backend/orb_session.py: session analysis filter", "- 4C  DONE (Nov 22, see 'Section 4C' at the end of this file; backend/orb_session.py). Original spec: session analysis filter", 1)
    open('docs/HANDOFF.md', 'w', encoding='utf-8').write(h)
print('ok docs/HANDOFF.md')
