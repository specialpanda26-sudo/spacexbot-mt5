# HANDOFF - what is built, what is left (give this file to the next AI)

Project: gold/forex signal bot (backend/*.py strategies, backend/brain.py confluence, tools/backtest.py, tests/*.py).
Rules for every new section (same as sections already done):
1. One new file per section in backend/, its own tests/test_*.py (plain python, prints PASS/FAIL, run with `python tests/test_xx.py`).
2. Each rule needs a test that fails if the rule is removed (mutation-check by hand: break each rule, a test must go red).
3. Register in backend/strategies.py (ALL, and TREND / REVERSION sets if it fits), then run: tests/test_pa1..pa5.py, test_jg.py, test_ma*.py, test_all.py - all must pass.
4. Never edit existing strategy files. The video's numbers are not given, so tunables are assumptions at the top of each file.
5. The brain only accepts stops 0.5 to 3.5 ATR (15-minute) from entry and uses a fixed 2R target.
6. Do not claim a strategy "works": only a backtest on real data (tools/backtest.py --solo) can say that. First results (2 months gold futures): roughly break-even.

## DONE
- Video 1 (jg_pullback etc.), Video 2 sections 1-5 (pa_level, pa_bos, pa_candle, pa_pattern, pa_trendline) - pushed to GitHub.
- Video 3 section 3A: backend/ma_cross.py + tests/test_ma1.py (20/50 EMA cross on the 1h candles, trending only via ADX, only markets that followed past crosses, fires on the 15m candle in which the hour closes, ATR-based stop).
- Video 3 section 3B: backend/stoch.py + backend/ma_bounce.py + tests/test_ma2.py (the 50 MA as support/resistance, needs earlier bounces, stochastic oversold/overbought, bullish/bearish rejection at the MA).

- Admin test price (Nov 18 plan, section 1): backend/payments.py set_test_plan + POST /api/admin/testprice + Test price card in the admin panel + tests/test_testprice.py.

- Admin section 1: access pass. backend/adminpass.py + POST /api/admin/pass + X-Admin-Pass header (static/live.js) + pass box on #admin + tests/test_adminpass.py. Set ADMIN_PASS on Render.

## REMAINING (do in this order, one section per session)
### Video 3 (Data Trader - moving average strategy)  [3A, 3B, 3C, 3D done]
- 3B  DONE (backend/ma_bounce.py). Original spec: the 20 or 50 MA as dynamic support/resistance + STOCHASTIC. Needs a new `stoch(b, k=14, d=3)` in a NEW helper file (do not edit indicators.py). Rule: price has touched the MA several times and bounced (the MA acts as support/resistance); when price is back at the MA AND stochastic is oversold (<20) in an uptrend -> buy; overbought (>80) at the MA in a downtrend -> sell. Add to REVERSION or TREND as fits (it trades pullbacks WITH the trend -> TREND).
- 3C  DONE (backend/ema200_filter.py + tests/test_e200.py: with_ema200 wrapper, psar_raw, supertrend_flip; registered as psar_e200 and supertrend_e200 in TREND; psar_e200 stays silent when psar_flip fires so one SAR flip is never two votes). Original spec: the 200 EMA filter. Price above 200 EMA -> only buys, below -> only sells. Implement as a wrapper `with_ema200(fn)` and register filtered copies of psar_flip and a supertrend-style signal (video: parabolic SAR 38% -> 46%, supertrend 39% -> 48%). Test: a buy from the wrapped strategy is dropped when price is below the 200 EMA, sells likewise.
- 3D  DONE (backend/trail_exit.py + tools/backtest.py --trail + tests/test_trail.py; run: python tools/backtest.py M15.csv H1.csv --solo --trail=2). Original spec: ATR trailing-stop exit. The backtest and brain use a fixed 2R target. Add an OPTIONAL trailing-exit simulation to tools/backtest.py (flag --trail) only after 3A-3C pass. Low priority.

### Video 5 (Brad Goh - gold scalping, 5 steps)
- 5A  DONE (backend/gs_zones.py + tests/test_gs1.py: bias(m,h) = 1h and 15m structure must agree; find_zones / scan return demand or supply zones as order blocks or fair value gaps, with a touched flag; touching(bar, zone). Not registered, it fires no trade - 5B uses scan()). Original spec: step 1+2 - 1h AND 15m trend must agree (reuse structure() from backend/pa_structure.py), then mark demand zones (buys) / supply zones (sells): the last opposite candle before an impulsive move that broke structure (order block) or a fair value gap.
- 5B  backend/gold_scalp.py: steps 3+4+5 - wait for price to come back into a 15m zone, then require a LIQUIDITY SWEEP (price takes out a recent swing low for buys / swing high for sells, wick through and close back). Aggressive entry: right after the sweep candle. Stop beyond the sweep candle (the protected low/high). Target: nearest 15m swing high (buys) / low (sells).
- 5C  conservative entry for 5B: after the sweep, wait for a market shift (close beyond the last internal high/low), then pullback into the zone that caused the shift; same stop and target. Skip when 1h and 15m disagree.

### Video 4 (Trade with Pat - 9:30 opening range breakout)
- 4A  backend/orb_range.py: New York open range. Needs a NY session clock (9:30-9:45 America/New_York, handles daylight saving; use zoneinfo). Range = high/low of the first 15m candle at 9:30 NY. Then on 5m/15m: a DISPLACEMENT break = a candle that CLOSES outside the range with big bodies (3-4 same-direction candles, recent structure broken). Wick-only does not count.
- 4B  backend/orb_entry.py: after displacement, mark the demand/supply zone (last opposite candle before the push) or fair value gap; enter when price returns and the zone holds (engulfing candle is a bonus, not required); stop beyond the zone (or the range midline); target about 1.5-2.2R.
- 4C  backend/orb_session.py: session analysis filter - Asia range, London sweeps the Asia high/low, New York usually reverses London's direction; if London swept BOTH sides of the Asia range expect continuation, not reversal. Used to choose the ORB direction.

### Last
- Run tools/backtest.py --solo on real data (6-12 months). Remove or ignore anything with an unproven edge. Then demo account before real money.
