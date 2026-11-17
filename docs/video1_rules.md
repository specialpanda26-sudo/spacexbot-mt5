# Video 1 rules: Jason Graystone, "Trading for Beginners Part 1" (daily-chart trend pullback)
Source: transcript analysed 17 Nov 2026. Code: backend/jg_pullback.py. Tests: tests/test_jg.py.
He says himself this is a demo setup, not a proven edge. Backtest before trusting it.

## Rules
1. Condition: trend (lower highs + lower lows for a sell). Choppy/indecisive market: stay out (the bot's ADX gate does this).
2. Phase: run, then pullback. Never enter in the middle of a run.
3. Trigger: first candle in the pullback that makes a lower low AND closes below the previous candle's low.
4. Entry: sell stop 2 pips below the trigger low. Stop: 2 pips above the highest high. Target: 2 pips above the lowest close of the previous run.
5. Risk 1% per trade. $/pip = risk $ / stop pips. Order of thinking: entry, stop, target.
6. No new trade until price makes a new low (one trade per pullback).
7. Never use an at-market order as a stop loss.
8. Buy side = mirror image.

## Optional filters he says to test (logged, not required)
Old support/resistance flip and touch count; angled trendline; Fib 38.2% / 61.8%; round numbers (.00/.50); shrinking candles, shooting star, doji.

## Candle reading
Close near the low = sellers won. Long upper wick = rejection. No-wick candle = strong momentum.

## Edge check
(1 + avg win / avg loss) x win rate - 1 must be above 0. His example: avg win 200, avg loss 170, win rate 55% -> about +0.2.

## What the bot cannot do exactly, and what it does instead
- Pending sell-stop entry -> enters at the trigger candle's close (already below the previous low).
- "2 pips" -> 0.1 x ATR, so it works on gold and FX.
- Daily timeframe -> uses whatever candles the bot feeds it (M15 now). Needs a daily feed to match the video.
- My own assumptions, not in the video (tunable at the top of jg_pullback.py): MIN_DEPTH 1 ATR, MIN_RR 1.5, MIN_BARS 2.
- SOLO = False: it only trades when another strategy agrees. Set True only after a backtest.

## Open questions for the owner
Close below previous close or previous low? Which "highest high" for the stop? How to define the run? Pending-order expiry? Filters required or only logged?
