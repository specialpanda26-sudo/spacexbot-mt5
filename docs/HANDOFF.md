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
- Video 5 section 5B: backend/gold_scalp.py + tests/test_gs2.py (liquidity-sweep entry in a 15m zone, aggressive version). Next: 5C.

- Admin test price (Nov 18 plan, section 1): backend/payments.py set_test_plan + POST /api/admin/testprice + Test price card in the admin panel + tests/test_testprice.py.

- Admin section 1: access pass. backend/adminpass.py + POST /api/admin/pass + X-Admin-Pass header (static/live.js) + pass box on #admin + tests/test_adminpass.py. Set ADMIN_PASS on Render.

## REMAINING (do in this order, one section per session)
### Video 3 (Data Trader - moving average strategy)  [3A, 3B, 3C, 3D done]
- 3B  DONE (backend/ma_bounce.py). Original spec: the 20 or 50 MA as dynamic support/resistance + STOCHASTIC. Needs a new `stoch(b, k=14, d=3)` in a NEW helper file (do not edit indicators.py). Rule: price has touched the MA several times and bounced (the MA acts as support/resistance); when price is back at the MA AND stochastic is oversold (<20) in an uptrend -> buy; overbought (>80) at the MA in a downtrend -> sell. Add to REVERSION or TREND as fits (it trades pullbacks WITH the trend -> TREND).
- 3C  DONE (backend/ema200_filter.py + tests/test_e200.py: with_ema200 wrapper, psar_raw, supertrend_flip; registered as psar_e200 and supertrend_e200 in TREND; psar_e200 stays silent when psar_flip fires so one SAR flip is never two votes). Original spec: the 200 EMA filter. Price above 200 EMA -> only buys, below -> only sells. Implement as a wrapper `with_ema200(fn)` and register filtered copies of psar_flip and a supertrend-style signal (video: parabolic SAR 38% -> 46%, supertrend 39% -> 48%). Test: a buy from the wrapped strategy is dropped when price is below the 200 EMA, sells likewise.
- 3D  DONE (backend/trail_exit.py + tools/backtest.py --trail + tests/test_trail.py; run: python tools/backtest.py M15.csv H1.csv --solo --trail=2). Original spec: ATR trailing-stop exit. The backtest and brain use a fixed 2R target. Add an OPTIONAL trailing-exit simulation to tools/backtest.py (flag --trail) only after 3A-3C pass. Low priority.

### Video 5 (Brad Goh - gold scalping, 5 steps)
- 5A  DONE (backend/gs_zones.py + tests/test_gs1.py: bias(m,h) = 1h and 15m structure must agree; find_zones / scan return demand or supply zones as order blocks or fair value gaps, with a touched flag; touching(bar, zone). Not registered, it fires no trade - 5B uses scan()). Original spec: step 1+2 - 1h AND 15m trend must agree (reuse structure() from backend/pa_structure.py), then mark demand zones (buys) / supply zones (sells): the last opposite candle before an impulsive move that broke structure (order block) or a fair value gap.
- 5B  DONE (backend/gold_scalp.py + tests/test_gs2.py: uses gs_zones.scan, trades only in 15m zones of the 5A bias; fires on the first candle that wicks through a recent swing low/high and closes back; stop beyond the sweep candle; target = nearest unbroken 15m swing high/low, at least 1R; registered as gold_scalp in TREND, SOLO=False). Original spec: steps 3+4+5 - aggressive entry right after the sweep candle.
- 5C  DONE (backend/gold_scalp_c.py + tests/test_gs3.py: sweep at a 15m zone, then a close beyond the last internal high = market shift, then the FIRST pullback into the last down/up candle before the shift; stop beyond the sweep candle, target nearest unbroken swing; registered as gold_scalp_c in TREND, SOLO=False). Original spec: conservative entry for 5B: after the sweep, wait for a market shift (close beyond the last internal high/low), then pullback into the zone that caused the shift; same stop and target. Skip when 1h and 15m disagree.

### Video 4 (Trade with Pat - 9:30 opening range breakout)
- 4A  DONE (backend/orb_range.py + tests/test_orb1.py: opening_range(c) = high/low of the 9:30-9:45 New York candles, daylight saving handled, weekdays only, final once 9:45 has started; displacement(c, r) = 3 or more big same-direction candles that CLOSE beyond the range and beyond any wick high/low seen since the range ended, 9:45 to 16:00 New York; scan(c) gives both. Not registered, it fires no trade - 4B uses it). Original spec: New York open range. Needs a NY session clock (9:30-9:45 America/New_York, handles daylight saving; use zoneinfo). Range = high/low of the first 15m candle at 9:30 NY. Then on 5m/15m: a DISPLACEMENT break = a candle that CLOSES outside the range with big bodies (3-4 same-direction candles, recent structure broken). Wick-only does not count.
- 4B  backend/orb_entry.py: after displacement, mark the demand/supply zone (last opposite candle before the push) or fair value gap; enter when price returns and the zone holds (engulfing candle is a bonus, not required); stop beyond the zone (or the range midline); target about 1.5-2.2R.
- 4C  backend/orb_session.py: session analysis filter - Asia range, London sweeps the Asia high/low, New York usually reverses London's direction; if London swept BOTH sides of the Asia range expect continuation, not reversal. Used to choose the ORB direction.

### Last
- Run tools/backtest.py --solo on real data (6-12 months). Remove or ignore anything with an unproven edge. Then demo account before real money.

## PHONE ALERTS (user request Nov 18; one section per session)
- N1  DONE (static/live.js, code between /*N1-start*/ and /*N1-end*/: the Android app asks for notification permission, gets its Firebase token, POSTs /api/push/token, unregisters on sign-out, tap opens the right screen; tests/test_push1.py). Before N1 nothing ever sent the token, so no push could reach a phone. Needs google-services.json in the APK build and FCM_SERVICE_ACCOUNT on Render.
- N2  backend/alerts.py: one background loop for timed alerts, daily cap raised (PUSH_DAILY_CAP default 12 -> 30), quiet hours adjustable, admin "send test alert" button.
- N3  billing alerts: kinds 38-41 from payments, 42/43/44 plan ends in 3 days / tomorrow / ended.
- N4  trade + risk alerts: new signal to every subscriber (kind 7/1), 9, 10, and 11-18 from the risk gates.
- N5  market alerts: 19-25 (news soon, news lock, session opening, large gold move, market closed, spread).
- N6  system, daily, tips: 26-31, 32-37 reports, 45-49 nudges, 50 security.
- Server route names #signals/#stats/#plans do not exist in the app; N1 maps them on the phone (signals,stats -> trades, plans -> profile).

## UI / BACKEND FEATURES for the strategies (one section per session, same rules as above)
- A1  DONE: backend/strategy_info.py (INFO = readable name + one line per strategy; label(); listing()) + GET /api/admin/strategies + tests/test_sinfo.py. The test FAILS when a strategy is registered without an INFO line, so add one whenever you add a strategy.
- A2  DONE (static/index.html admin panel: Strategies card with on/off switches + Results table, code between /*A2-start*/ and /*A2-end*/; tests/test_strui.py runs it in node). Original spec: admin panel "Strategies" card in static/index.html (function panel(), next to Test price / Packages): one row per strategy from GET /api/admin/strategies: name, description, trend/reversion tag, on/off switch (POST /api/admin/settings {strategies_off: "a,b"}), and a results table (n, win rate, average) with "no trades yet" when n = 0. Build from the site's own cards and inputs.
- A3  DONE (store DEFAULTS strategies_solo, brain.evaluate(..., solo=()), app._scan passes it, GET /api/admin/strategies returns solo, second switch per strategy in the Strategies card, tests/test_solo.py + test_strui.py; solo is a global setting, it also applies to subscribers' scans). Original spec: admin switch "may trade alone" per strategy: new setting strategies_solo in backend/store.py DEFAULTS, brain.evaluate(..., solo=()) treats a hit from a strategy in that set as solo (today only the SOLO constant inside the strategy file does), app._scan passes it, the list route returns it, a switch in the card. Tests: a solo strategy trades without a second vote, an off one never does.
- A4  DONE (strategy_info.alert_body for the scan alert; pushcopy kinds 1 and 7 get a "Strategy: <name>." line; assist feed + push and GET /api/signals send strategy_name; the Phone mode signal card shows the name, code between /*A4-start*/ and /*A4-end*/; tests/test_sigtext.py). Original spec: signals and alerts: show the readable name (strategy_info.label) and the target. backend/app.py _scan builds the notification text with the raw id today ("(gold_scalp)"); pushcopy kinds 1 and 7 have no strategy line; the signal card in the app should show name + entry/SL/TP.
