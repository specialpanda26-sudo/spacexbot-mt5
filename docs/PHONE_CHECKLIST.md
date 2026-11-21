# Final check on a real phone (Section 10)

Do these in order after a Render deploy. Tick each one. Nothing here claims the bot makes money: only a backtest on real data (tools/backtest.py --solo) can say that, and a demo account comes before real money.

## A. Before the phone (5 minutes, in a browser)
1. Render > your service > Environment. Open the site /admin > Health. Every red line in the Setup check must be fixed or understood (the check shows variable NAMES only, never values). Must be set: DATABASE_URL, BASE_URL (https://), EA_KEY, ADMIN_EMAILS, SUPABASE_URL + SUPABASE_ANON_KEY, PAYHERO or your payment keys, FCM_SERVICE_ACCOUNT (without it no push), BROKER_KEY + DERIV_APP_ID if you use Deriv.
2. GitHub > repo > Settings > Secrets and variables > Actions: these 5 must exist: ANDROID_KEYSTORE_BASE64, ANDROID_KEYSTORE_PASSWORD, ANDROID_KEY_ALIAS, ANDROID_KEY_PASSWORD, GOOGLE_SERVICES_JSON_BASE64 (the last one or the APK has no push). In Termux: `gh secret list`.
3. The repo is public (the update pop-up and the download links read the GitHub release). Actions > Build Android APK finished green and Releases has the newest app-<n>.
4. Open the site once so Render wakes up (free Render sleeps after 15 minutes idle; ping /healthz from a free uptime monitor if you want it awake).

## B. Install and sign in (phone)
5. Install the newest spacexbot.apk from Releases. Open it. Sign in with a test account. The chip must not say Offline for more than a few seconds.
6. Allow notifications when asked. Admin panel > Phone alerts > send the test push. It must arrive as a banner (app open) and as a notification (app closed). Tap it: the right screen opens.
7. Leave the app closed for a while, open it again: you must NOT be logged out. If you see "Your session ended", note the time and tell the next AI.

## C. Update pop-up
8. Push any small change so a new build number is released. Open the old app: "New build N - you have M" card, Update now and Maybe later work. The text must not say "fixes".
9. If no pop-up shows when you expect one: the app keeps the reason (Settings area / SXBUpdate.status()): "no release found", "up to date", "the app version cannot be read" or "the update check failed". Send that sentence.

## D. Home screen states (cartoon + speech bubble must say the same thing)
10. No plan: lock picture, bubble "The bot is locked. Choose a plan to switch it on."
11. With a plan, bot stopped: clock picture, bubble "The bot is stopped. Tap Start bot."
12. Loss limit hit (set a very small limit on a demo account): shield picture, bubble and grey line give the server sentence.
13. Profit at or above the Daily target (Bot tab box, default $3): party picture and the numbers. This only celebrates; it does not stop the bot.
14. Saturday/Sunday with only gold/forex listed: moon picture and the market-closed sentence.
15. Look at the animations once. If anything feels too busy, tell the next AI which one (the fix is one line).

## E. Trading path (demo account only, Real mode OFF)
16. Connect tab: Deriv or the MT5 bridge shows connected; "<broker> is connected" card appears once.
17. Account card shows Demo. Bot tab > Start. Bot status card says in plain words what it is doing or why it is not trading.
18. Wait for or force one demo trade. Check: it appears in Trades, Journal, Stats and the P&L card, a push arrives to the right phone (owner trades go to admin phones only), and tapping the trade opens its chart pop-up.
19. Stop the bot: it must stay stopped after you close and reopen the app.

## F. Money and plans
20. Pay for a plan with a real M-Pesa number that is NOT yours (the owner's own number is the case that already worked). The STK prompt must arrive, the plan must activate, a receipt email must arrive.
21. "Your plan ends soon" shows within 3 days of the end, "Your plan has ended" after it, each once.

Write down every item that failed with the exact text on the screen. Give that list to the next AI together with docs/HANDOFF.md.
