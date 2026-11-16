# spaceXBot MT5 v2

MT5 terminal (PC/VPS) <-> **EA** <-> Render backend (Flask) <-> app (Google sign-in, push, M-Pesa via FinoQ, PayPal).
The backend does the thinking (11 rule-based strategies, regime filter, safety gates). The EA only fetches signals and places orders.

## What changed from v1
- **FinoQ = PayHero.** One gateway, not two. Ported from Comrade Connect: webhook secret required, a success must name an amount >= the price and the same phone, repeats are harmless, late success after expiry still credits, a missed webhook is recovered by the status API, STK prompts are rate-limited per account and phone.
- **PayPal** now checks the captured amount and currency before crediting.
- **11 strategies** (was 5): added MACD cross, Heikin-Ashi flip, Parabolic SAR flip, Awesome Oscillator, Dual Thrust, shooting-star/hammer (from quant-trading).
- **Regime filter:** reversion setups skipped when ADX > 28, trend setups skipped when ADX < 18.
- **Gates:** news lock (ForexFactory feed), daily + weekly loss limits, losing-streak cooldown, max same-currency exposure, per-symbol cooldown.
- **Stats:** `/api/stats` shows results per strategy; `python tools/backtest.py M15.csv H1.csv --solo` tests each strategy alone on your own data.
- Plans are editable by the admin (`/api/admin/plans`), `/api/admin/grant` gives a user days.

## 1) Deploy (Termux)
    unzip spacexbot-mt5-v2.zip && cd spacexbot-mt5
    git init && git add . && git commit -m "spacexbot mt5 v2" && git branch -M main
    git remote add origin https://github.com/<you>/<new-repo>.git && git push -u origin main
Render > New Web Service > that repo (render.yaml is read). Add the variables from `.env.example`.
Keep **1 worker**: candles live in memory. Free Render sleeps: ping `/healthz` every 10 min (UptimeRobot) while trading.

## 2) FinoQ webhook
Nothing to paste: the app sends `{BASE_URL}/api/webhooks/payhero?s={PAYHERO_CALLBACK_SECRET}` with every prompt.
Test with a KES 1-style small plan first. If prompts are refused, check `PAYHERO_BASE_URL` (Comrade Connect's code uses `https://api.finoq.africa`; older PayHero used `https://backend.payhero.co.ke`).

## 3) Firebase, 4) MT5
Same as v1: Auth > Google, service-account JSON into `FIREBASE_SERVICE_ACCOUNT`, web config into `FIREBASE_WEB_CONFIG`, add your Render domain to Authorized domains.
Copy `ea/SpaceXBridge.mq5` to `MQL5/Experts/`, compile, allow WebRequest for your Render URL. Starts **demo-only** (`AllowLive=false`). MT5 must stay open.

## 5) Prove it before real money
    python tests/test_all.py                      # 30 offline checks
    python tools/backtest.py XAUUSD_M15.csv XAUUSD_H1.csv --solo
The backtest ignores news lock, exposure cap and loss limits.

## Known limits
- **SQLite on Render free is wiped on every redeploy.** Users, plans and payments reset. Move to Supabase Postgres before taking real money.
- If the ForexFactory feed is unreachable and was never loaded, the news lock fails open (shown in the app).
- Nothing here is proven profitable. Test on a demo account for weeks first.
