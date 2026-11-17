# Video 2 - Brad Goh, "COMPLETE Price Action Trading Course" (Beginner to Pro)
Not a strategy video: he gives no exact entry/stop/target and no backtest, so treat every rule as UNTESTED until backtested.
Sections: S1 structure + BOS (backend/pa_structure.py, pa_bos) | S2 levels + candle pressure (pa_level) | S3 candle patterns (pa_candle) | S4 double top/bottom + H&S (pa_pattern) | S5 trendlines (pa_trendline)
1. Uptrend = higher highs + higher lows. Downtrend = lower highs + lower lows. Sideways = stay out.  [S1]
2. Trade with the trend.  [S1 structure(), reused by S2-S5]
3. Reversal: close through the last higher low (or lower high), retest it, make a lower high (or higher low). Do not trade the first break.  [S1]
4. Support/resistance needs 2+ touches. A broken level flips role.  [S2]
5. Only candles at a key level count. Big body = momentum. Long wick that closes back = rejection.  [S2]
6. Engulfing, three line strike, morning/evening star, only at a key level.  [S3]
7. Double top/bottom, head and shoulders (and inverted): enter on the neckline close, stop beyond the pattern, target the next key level.  [S4]
8. Trendline needs 2 touches (uptrend: join higher lows, downtrend: join lower highs). A break counts only with strong momentum, a wick over the line is a fake-out.  [S5]
My assumptions (tunable at the top of each file): swing = 3 candles each side, stop buffer 0.1 ATR, retest tolerance 0.5 ATR.
