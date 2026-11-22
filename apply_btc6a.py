"""BTC Section 6A: register backend/btc_range.py. Run from the project folder: python apply_btc6a.py  (safe to run twice)."""
import os
def edit(path, pairs):
    s = open(path, encoding='utf-8').read(); o = s
    for old, new in pairs:
        if new in s: continue
        assert old in s, path + ': text not found: ' + old[:60]
        s = s.replace(old, new, 1)
    if s != o: open(path, 'w', encoding='utf-8').write(s)
    print('ok', path)

edit('backend/strategies.py', [
    ("from .orb_entry import orb_entry\n", "from .orb_entry import orb_entry\nfrom .btc_range import btc_range\n"),
    ("gold_scalp_c, orb_entry, jg_pullback,", "gold_scalp_c, orb_entry, btc_range, jg_pullback,"),
    ("'gold_scalp_c', 'orb_entry'}", "'gold_scalp_c', 'orb_entry', 'btc_range'}"),
])
i = open('backend/strategy_info.py', encoding='utf-8').read()
a = "    'orb_entry':"; k = i.index(a); e = i.index("\n", k) + 1
edit('backend/strategy_info.py', [(i[k:e], i[k:e] + "    'btc_range': ('BTC range reaction', 'Range break, price falls back inside, a candle reacts in the discount (buy) or premium (sell) quarter; 8h to 30m (BTC video).'),\n")])

NOTE = """
## BTC Section 6A (backend/btc_range.py, the range / discount-premium entry) DONE (Nov 22)
- New: backend/btc_range.py, tests/test_btc6a.py (51 checks, mutation-checked: zone, reaction candle, body size, first reaction only, bottom broken, came back inside, break required, min range, stop fit, RR, stay on the frame, closed candles, complete groups, min bars, wick-aware stop, bearish side, 15m-only each went red). apply_btc6a.py registers it: strategies.py (ALL, TREND, NOT SOLO) and strategy_info.py. No existing strategy file was edited.
- Frames: 8h, 4h, 1h, 30m tried in that order. 4h/8h are GROUPED from the 1h candles (UTC boundaries), 30m from the 15m candles; a group counts only when all its small candles exist and it is closed. Fewer than MIN_BARS (12) candles = no structure = one frame lower. 8h needs about 100 hours of H1 history (the Section 2 feed downloads 60 days, enough).
- Range: swing high broken by a CLOSE, top = highest high since, bottom = last swing low before the break; valid only after a close back below the broken high and while nothing has closed under the bottom. Entry = first green candle with a real body (0.3 ATR) that touches the bottom quarter; stop under the bottom swing (or the candle wick); target TP1 = the top. If a valid range exists on a frame, that frame is traded or nothing (it never drops lower to find another trade). Bearish = mirror.
- setup(m, h) returns more than the signal: tp2 (top + 0.25 range), half flag, range, rr, frame. The 50% trade is the HALF_OK switch (default False); at the 0.5 level the reward is only about 1R with that stop, so it needs a lower RR_MIN and usually a wider SL_MAX to ever fire.
- Honest limits: with BTC's 15m ATR, 8h and 4h ranges are usually far too wide for the brain's 0.5-3.5 ATR stop, so the trades will mostly come from the 1h and 30m frames (skipped, never reshaped). 'Consolidating after the reaction' (video) cannot be read at entry: a doji-like reaction candle (body under 0.3 ATR) is skipped instead. Break-even after TP1 is not coded. It is generic (it also runs on gold and forex candles). NOT backtested on real BTC candles: run tools/backtest.py --solo on real data before trusting it. Test chart is synthetic.
- Next: Section 6B (optional weekend filters, each behind its own setting, default OFF), then 4C, N2, N6 and the S2-S6 list above.
"""
edit('docs/HANDOFF.md', [("Status: 6A and 6B not started. Order: 2, 3, 4, 5, then 6A, then 6B.", "Status: 6A DONE (see 'BTC Section 6A' at the end of this file); 6B not started. Order was: 2, 3, 4, 5, then 6A, then 6B.")])
h = open('docs/HANDOFF.md', encoding='utf-8').read()
if 'BTC Section 6A (backend/btc_range.py' not in h: open('docs/HANDOFF.md', 'a', encoding='utf-8').write(NOTE)
print('done: now run  python tests/test_btc6a.py  and  python tests/test_sinfo.py')
