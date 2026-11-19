# spaceXBot MT5 v2

MT5 terminal (PC/VPS) <-> **EA** <-> Render backend (Flask) <-> app (Supabase sign-in with Google or an email code, M-Pesa via FinoQ, PayPal, email receipts and alerts via Resend).
The backend does the thinking (11 rule-based strategies, regime filter, safety gates). The EA only fetches signals and places orders.

## What changed from v1
- **FinoQ = PayHero.** One gateway, not two. Ported from Comrade Connect: webhook secret required, a success must name an amount >= the price and the same phone, repeats are harmless, late success after expiry still credits, a missed webhook is recovered by the status API; STK prompts are not rate-limited.
- **PayPal** now checks the captured amount and currency before crediting.
- **11 strategies** (was 5): added MACD cross, Heikin-Ashi flip, Parabolic SAR flip, Awesome Oscillator, Dual Thrust, shooting-star/hammer (from quant-trading).
- **Regime filter:** reversion setups skipped when ADX > 28, trend setups skipped when ADX < 18.
- **Gates:** news lock (ForexFactory feed), daily + weekly loss limits, losing-streak cooldown, max same-currency exposure, per-symbol cooldown.
- **Stats:** `/api/stats` shows results per strategy; `python tools/backtest.py M15.csv H1.csv --solo` tests each strategy alone on your own data.
- Plans are editable by the admin (`/api/admin/plans`), `/api/admin/grant` gives a user days.

## Per-user MT5 link (each subscriber's own broker)
Every subscriber connects **their own** MT5 (Exness or any MT5 broker). Nothing is shared and no paid service is used.
- The app makes a personal key (`sxb_...`), shown **once**. Only its hash is stored. A new key replaces the old one and starts in Demo mode with the bot off.
- The user puts that key in the EA's `EAKey` (the owner's own EA keeps using `EA_KEY`). Their candles, signals, limits, alerts and results stay separate; one user can never read or change another's.
- **Demo / Real:** Demo is the default. Real needs the user to type `REAL`, and the server refuses to trade a non-demo account unless Real mode is on **and** the EA reports `AllowLive=true`. Switching mode stops the bot.
- When a plan ends, the EA is told to stop and nothing new is stored. Only symbols in the admin's `symbols` setting are accepted from user EAs (max 12, 500 candles each).
- Routes: `GET /api/link`, `POST /api/link/key`, `/api/link/mode`, `/api/link/bot`, `/api/link/risk`, `DELETE /api/link`. The **Connect** tab has a Connect MT5 card wired to these routes: make or replace the key (shown once, with Copy), Demo/Real switch (Real asks to type `REAL`), Start/Stop bot and risk per trade. For a subscriber with a link, the Home Start/Stop button controls the real bot. Charts and sample numbers elsewhere are still demo.
- Memory: candles are kept in server memory per user. Watch Render's memory as users grow (the free plan is small).
- Existing data: old trades have no owner and belong to the owner's EA. After this update subscribers see their own bot, not the owner's.

## Phone mode (no PC needed)
For subscribers who only have a phone. Free, nothing to install. The owner's bot finds a signal; the server sends each phone-mode person a notification, and the **Connect** tab shows it with a lot size worked out from *their* balance and risk. They tap **Take it** or **Skip**, place the trade by hand in their MT5 phone app, then log **Won / Lost / Even** (money amount optional). Nothing here places a trade for them.
- **Needs your own feed running.** Signals come from the owner's EA or desktop app. If it is off, there are no signals to hand out.
- Switch on: Connect tab > Phone mode > enter balance and risk > Turn on. Not allowed together with the person's own MT5 bot (it would trade the same idea twice).
- A signal can be taken for 15 minutes. After that the price has probably moved. Sizes assume a USD account and standard lots (gold 100 oz, FX 100,000 units); symbols the server cannot size (for example EURGBP) show no size instead of a guess. The size is rounded down and never risks more than the person asked for; if even 0.01 lot is too much for their balance, the card says so.
- Routes: `GET /api/assist`, `POST /api/assist/settings`, `/take`, `/skip`, `/result`. Data: tables `assist` and `assist_log`, created on boot (SQLite or Postgres). Deleting an account removes both, and its push devices.
- The push (kind 7) obeys each person's alert settings and quiet hours (22:00 to 06:00 East Africa time); the signal is still in the app.

## Phone only (no PC): the server price feed
If you only have a phone, the server can get gold candles by itself, so phone mode has signals without an EA or the Windows app. Free, off by default.
- **Switch on:** sign in as admin, open `#admin`, **Price feed** card: press **Check** (it only tests the download from your server), then **Turn on**, then start the bot on Home (with no EA this only means "look for signals"). Or set the Render variable `FEED_ON=1`.
- **What you get:** about once a minute the server downloads closed 15-minute and 1-hour candles (Yahoo, `FEED_MAP`, default `XAUUSD:GC=F`), runs the same strategies and gates, and sends phone-mode people the signal with their lot size. **It never places a trade.** You place it by hand in the FBS / MT5 phone app.
- **Honest limits:** Yahoo gold is the *futures* price, usually a few dollars from FBS spot, with small jumps when the contract rolls. Check entry, stop and target on your MT5 chart first. Yahoo is unofficial and may refuse a cloud server; the card shows the exact reason. It pauses by itself while your own EA is online (two price sources would mix). Render free sleeps: ping `/healthz` every 10 minutes (UptimeRobot) while you want signals. Not tested against live Yahoo from Render yet: use **Check** first.
- **Prove it:** `python tests/test_feed.py` (Yahoo is faked there).

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

## Email alerts and receipts (Resend API)
Separate from sign-in codes. In Render add `RESEND_API_KEY` and `MAIL_FROM` (an address on your verified Resend domain, for example `spaceXBot <alerts@yourdomain.com>`).
- **Receipt:** one email to the buyer when a plan is credited (M-Pesa or PayPal). A repeat callback never sends a second one.
- **Trade alerts:** a new signal, a trade opened and a trade closed are emailed to active subscribers and admins who kept *Trade alerts* on in Profile. Turned off people get nothing.
- **Daily cap:** `MAIL_ALERT_CAP` (default 60) stops alerts for the day; receipts can go on to `MAIL_HARD_CAP` (default 90). Sign-in codes share your Resend quota, so keep alerts below it.
- **Check it:** `python3 tools/check_resend.py you@example.com` sends one test email and says what is wrong in plain words. The admin health check also lists a missing key.
- Until the domain is verified Resend only lets you send to your own address.

## 3) Google sign-in, 4) MT5
Google sign-in is switched on in Supabase > Auth > Providers > Google: paste the client ID and secret from Google Cloud, and add the callback URL Supabase shows to your Google OAuth client. Your Render address goes under Redirect URLs (step 5 above). Firebase is no longer used.
Copy `ea/SpaceXBridge.mq5` to `MQL5/Experts/`, compile, allow WebRequest for your Render URL. Starts **demo-only** (`AllowLive=false`). MT5 must stay open.

## 5) Prove it before real money
    python tests/test_all.py                      # offline checks: strategies, gates, payments, API
    python tests/test_sbauth.py                   # server-side token checks
    python tests/test_authjs.py                   # sign-up / code / reset flow in the browser code (needs node)
    python tests/test_admin.py                    # admin user list, grant, revoke
    python tests/test_mail.py                     # Resend receipts and trade alerts (no network)
    python tests/test_locked.py                   # bot lock follows the server plan (needs node)
    python tests/test_assist.py                   # phone mode: lot sizes, take / skip / result, who gets the push
    python tools/backtest.py XAUUSD_M15.csv XAUUSD_H1.csv --solo
The backtest ignores news lock, exposure cap and loss limits.

## Windows app (laptop mode)
A small window for a Windows PC that runs the same bot as the EA, with no MQL5 needed. It uses your own MetaTrader 5 and your personal key. Free.
- **Get the .exe:** GitHub > Actions > Build Windows app > Run workflow (it also builds by itself when `desktop/` changes on main). The file appears under Releases as **desktop-latest > spacexbot-desktop.exe**. The Connect tab has a **Download for Windows** card, shown only on a Windows PC. The repo must be public for visitors to download. The Android release stays the "latest" one; this one is kept apart on purpose so both links keep working.
- **Use it:** open MetaTrader 5 on the PC, log in to a **demo** account, switch **Algo Trading** on. Open the app, paste your server address and personal key (Connect tab > Make my key), press **Start**. Leave "Allow REAL-money accounts" off until you have watched it on demo for weeks.
- **Windows SmartScreen:** the first run may say *Windows protected your PC*. That is because the .exe has no paid code-signing certificate (they cost money, and this project stays free) and it is new, so Windows has no reputation for it yet. It does not mean the file is infected. Choose **More info > Run anyway**, but only for a file you downloaded from your own spaceXBot site or Releases page. You can compare the SHA-256 printed in the release notes with `Get-FileHash .\spacexbot-desktop.exe` in PowerShell.
- **Antivirus:** apps made with PyInstaller are sometimes flagged by antivirus programs even when harmless. If yours blocks it, do not turn your antivirus off. Run from source instead: install Python 3.12 from python.org (tick "Add to PATH"), then in the project folder `pip install requests MetaTrader5` and `python -m desktop.gui`.
- **If the window will not open:** look for `crash.log` in the `.spacexbot` folder inside your Windows user folder and send it to support.
- **Not tested on a live terminal.** The window logic is tested with fakes. The connection to a real MetaTrader 5 has not been run yet. Start on a demo account.

## Android app
GitHub > Actions > Build Android APK > Run workflow builds `spacexbot.apk` (see Releases). It is a thin wrapper that opens your Render site, so `android-wrapper/capacitor.config.json` must point at your own Render address (it is set to `spacexbot-gn73.onrender.com`). Signing needs the four `ANDROID_*` secrets (see `android-wrapper/setup-signing.sh`).
PayPal opens in the phone's browser; when the person returns to the app it checks the order and credits the plan. This has only been tested against a fake server, so try both M-Pesa and PayPal on a real phone before taking real money.
The landing page footer has a green **Download Android app** button. It points to `releases/latest/download/spacexbot.apk` of this repo, so it always gives the newest build from the "Build Android APK" workflow. It is hidden inside the Android app and on iPhone. The repo must be public for visitors to download. If you rename or move the repo, run the patch again or edit the link in `static/index.html` (id `apkDl`).

**App icon:** `android-wrapper/branding/logo.png` (1024x1024, transparent) is the source of the app icon, splash and notification icon. Replace it with your own PNG to change them; a new APK build is needed to see the change.
**Card tab:** the plan screen has M-Pesa, PayPal and Card. Card is PayPal's pay-by-card page (no PayPal account needed, if PayPal allows it for your account and the buyer's country). It is not FinoQ cards: FinoQ has not confirmed cards. A plan is credited only after the server confirms the capture with PayPal, same as the PayPal tab. If you ever publish on Google Play, its billing rules apply to digital subscriptions: check them first.

If PayPal fails, the app now shows a short code, e.g. `PayPal is unavailable right now (http401-invalid_client)`. `http401` = keys do not match `PAYPAL_ENV`; `http403` or `PAYEE_ACCOUNT_RESTRICTED` = the PayPal account is not approved for live payments; `net-...` = PayPal could not be reached. The Render log line `paypal create failed:` has the same code. A code ending in `@field` names the field PayPal refused, e.g. `http400-INVALID_PARAMETER_VALUE@landing_page` (fixed: Orders v2 has no `GUEST_CHECKOUT`; the order now sends `BILLING`, which opens PayPal's pay-by-card form).

## Phone alerts (Firebase)
Alerts reach the Android app even when it is closed. Three things must all be in place, or nothing arrives:
1. **Render:** variable `FCM_SERVICE_ACCOUNT` = the Firebase service-account JSON (Firebase console > Project settings > Service accounts > Generate new private key; paste the file's text, or its base64). Also set `PUBLIC_URL` to your server address (alert pictures load from it). Optional `PUSH_DAILY_CAP` (alerts per person per day, default 12).
2. **GitHub:** repository secret `GOOGLE_SERVICES_JSON_BASE64` = `base64 -w0 google-services.json` (Firebase > Project settings > Your apps > Android, package `com.spacexbot.app`). It is a GitHub secret, not a Render variable. Then run the Android build again: an APK built without it has no phone alerts.
3. **Phone:** install that APK, sign in, tap Allow on the notification question.
Check it: sign in as admin, open `#admin`, press **Send test alert**. It reports how many phones it reached, or why not. It works with the app open or closed.
- Who gets what: the owner's own trades (opened, take-profit, stop-loss, closed, skipped) go to the admins' phones only. A subscriber gets alerts for the trades of their own EA key, and phone-mode signals (kind 7).
- Free Render sleeps after 15 minutes without a request. Alerts that fire on a timer need the server awake: ping `/healthz` every 10 minutes from a free uptime monitor, or use a paid plan.
- Tests: `python tests/test_push1.py` (phone side), `python tests/test_push2.py` (delivery path).

## Known limits
- **SQLite on Render free is wiped on every redeploy.** Users, plans and payments reset. Move to Supabase Postgres before taking real money.
- If the ForexFactory feed is unreachable and was never loaded, the news lock fails open (shown in the app).
- Nothing here is proven profitable. Test on a demo account for weeks first.


### Render Free Tier Hosting Note
Render free instances spin down after 15 minutes of inactivity. The background alert timer loop runs only while the server is awake. To maintain continuous operation, configure an external free uptime monitor to ping `/healthz` every 10 minutes, or upgrade to a paid Render plan.

## Deriv bot: what must be set on Render
`BROKER_KEY` (16+ characters) and `DERIV_APP_ID` (your Deriv app id). Without them nothing is saved or traded, and the Platforms tile and the admin health card say so in plain words. Start/Stop the bot from the Deriv tile (Connect tab): no MT5 key is needed. Real Deriv accounts also need `DERIV_REAL=1` on Render AND Real mode chosen by the customer.
