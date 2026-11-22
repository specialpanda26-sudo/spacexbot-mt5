"""C4: the in-app cartoon how-to guide. One list of steps, used by the app screen (GET /api/guide) and later by the PDF guide (C5).
Plain words, no promise of profit. 'art' is the name of a cartoon in window.IL2 on the site."""

def S(i, t, art, intro, pts): return {'id': i, 'title': t, 'art': art, 'intro': intro, 'points': pts}

STEPS = [
    S('signup', 'Sign up', 'mail', 'Make your account in a minute.', [
        'Tap Log in, then Sign up. Use an email you can open.',
        'We send a link or a code. Open it to verify your email.',
        'Until your email is verified the bot stays locked.']),
    S('subscribe', 'Subscribe', 'coin', 'Pick a plan to use the bot.', [
        'Open Plans and choose weekly or monthly.',
        'Pay with M-Pesa or PayPal. Your plan shows how many days are left.',
        'Demo practice is open for everyone. Real trading needs an active plan.']),
    S('connect', 'Connect your broker', 'plug', 'Deriv, MT5 or Binance.', [
        'Open Connect and pick your broker.',
        'Deriv: paste your Deriv token. Binance: paste a key that can read, never one that can withdraw. Binance does not place trades yet.',
        'MT5: install the free bridge on your PC and paste your key.',
        'The tile says Connected only when the server really talks to your account.']),
    S('mode', 'Demo or real', 'shield', 'Start with demo. Real is your choice.', [
        'Demo uses practice money. Real uses your own money.',
        'To switch to Real you type the word REAL, and you must finish the learning path first.',
        'Any switch stops the bot, so you start it again on purpose.']),
    S('start', 'Start the bot', 'rocket', 'One tap on the Bot tab.', [
        'Choose which platform trades: MT5, Deriv or Binance. Only one trades at a time.',
        'Tap Start. The Bot status card says in plain words if it is trading or why not.',
        'Tap Stop any time. Stop always works.']),
    S('signal', 'Read a signal', 'doc', 'What a signal tells you.', [
        'A signal shows the market, buy or sell, the entry, the stop loss and the take profit.',
        'The strategy name tells you why the bot liked it.',
        'A signal is an idea, not a promise. Some trades lose.']),
    S('safety', 'Safety rules', 'lock', 'The bot has brakes.', [
        'Loss limits, a loss streak stop, a news lock and a cap on open trades.',
        'The bot also waits when the market is closed or big news is near.',
        'You can only make these stricter, never looser than the owner allows.']),
    S('alerts', 'Alerts', 'push', 'Know what happens without opening the app.', [
        'Allow notifications on your phone when asked.',
        'You get alerts for trades, plan days left and safety stops.',
        'You can set quiet hours so alerts do not wake you.']),
    S('help', 'Need help?', 'ok', 'Look here first.', [
        'The Bot status card names the reason when nothing trades.',
        'The Connect tab checks your broker and gives the first fix.',
        'Still stuck? Tell the owner exactly what the screen showed.'])]

def view(): return {'steps': STEPS, 'total': len(STEPS), 'brand': 'Powered by Ogola Tech'}
