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

## Sign-in emails (Supabase + Resend)
Sign-up and "forgot password" both email a **6-digit code**. Supabase sends it, Resend delivers it. Do this once, in this order:
1. **Resend:** add your domain, copy the DNS records (SPF, DKIM) into your domain's DNS, wait until it shows *Verified*. Create an API key.
2. **Supabase > Auth > SMTP Settings:** turn on custom SMTP. Host `smtp.resend.com`, port `465`, username `resend`, password = the Resend API key, sender = an address on the verified domain (e.g. `noreply@yourdomain.com`).
   Without this Supabase's built-in sender only emails your own team members and allows a handful of emails per hour, so real users get nothing.
3. **Supabase > Auth > Providers > Email:** *Confirm email* ON, email OTP length 6. If Confirm email is off, sign-up logs the user straight in and no code is sent.
4. **Supabase > Auth > Email Templates:** open **Confirm signup** and **Reset Password**. Each must contain `{{ .Token }}`, for example `<p>Your spaceXBot code is <b>{{ .Token }}</b>. It expires in 1 hour.</p>`.
   If a template only has `{{ .ConfirmationURL }}` the user gets a link, not a code, and the code screen cannot work. Magic Link and Change Email templates are not used.
5. **Supabase > Auth > URL Configuration:** Site URL = `BASE_URL`; add `BASE_URL/` to Redirect URLs (Google sign-in needs it).
6. **Test:** sign up with a new address, get the code, enter it. Then use *Forgot password* on that account: code, then new password.

Limits to know (check your dashboards, they change): Supabase allows one auth email per address every 60 seconds (the app's resend button waits 60 s to match) and caps emails per hour under *Auth > Rate Limits*; Resend's free plan has daily and monthly send caps.
What the app shows when something is wrong: "Too many emails sent" or "Please wait N seconds" = a rate limit; "We could not send the email" = the SMTP or sender-domain setup (step 1 or 2); "That code is wrong or has expired" = wrong, expired or already-used code (use Resend code).

## 3) Firebase, 4) MT5
Same as v1: Auth > Google, service-account JSON into `FIREBASE_SERVICE_ACCOUNT`, web config into `FIREBASE_WEB_CONFIG`, add your Render domain to Authorized domains.
Copy `ea/SpaceXBridge.mq5` to `MQL5/Experts/`, compile, allow WebRequest for your Render URL. Starts **demo-only** (`AllowLive=false`). MT5 must stay open.

## 5) Prove it before real money
    python tests/test_all.py                      # 30 offline checks
    python tests/test_sbauth.py                   # server-side token checks
    python tests/test_authjs.py                   # sign-up / code / reset flow in the browser code (needs node)
    python tools/backtest.py XAUUSD_M15.csv XAUUSD_H1.csv --solo
The backtest ignores news lock, exposure cap and loss limits.

## Known limits
- **SQLite on Render free is wiped on every redeploy.** Users, plans and payments reset. Move to Supabase Postgres before taking real money.
- If the ForexFactory feed is unreachable and was never loaded, the news lock fails open (shown in the app).
- Nothing here is proven profitable. Test on a demo account for weeks first.
