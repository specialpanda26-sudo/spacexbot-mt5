"""The words and picture for every notification kind. Friendly like the app, but facts only: no promise of profit, no advice."""
import os
BASE = os.getenv('PUBLIC_URL', 'https://spacexbot-gn73.onrender.com').rstrip('/')

def img(name): return '%s/notif/%s.png' % (BASE, name) if name else None
def _n(v):
    try: return float(v)
    except (TypeError, ValueError): return None
def money(v, cur=''):
    x = _n(v)
    if x is None: return '--'
    return ('%s%s %s' % ('+' if x > 0 else '-' if x < 0 else '', format(abs(x), ',.2f'), cur or '')).strip()
class _F(dict):
    def __missing__(self, k): return ''
def _side(f): return str(f.get('side') or '').upper()
def _strat(f):
    """' Strategy: <readable name>.' for a signal text, or '' with no strategy. A failed name lookup must never stop the trade text."""
    s = f.get('strategy')
    if not s: return ''
    try:
        from . import strategy_info
        return ' Strategy: %s.' % strategy_info.label(s)
    except Exception: return ''


def _closed(f):
    p = _n(f.get('pnl')); sym = f.get('sym') or 'Trade'; m = money(p, f.get('cur'))
    if p is None or p == 0: return ('%s closed' % sym, 'Closed at about break-even (%s).' % m, 'even')
    if p > 0: return ('Hooray! %s closed in profit' % sym, 'You made %s on this one. Open the app to see it.' % m, 'win')
    return ('Oops, %s closed at a loss' % sym, 'This one finished at %s. Losses happen in trading; your stop-loss kept it limited.' % m, 'loss')

def _day(f):
    p = _n(f.get('pnl')); m = money(p, f.get('cur')); n = f.get('n', 0); wr = f.get('wr')
    tail = '%s trade%s' % (n, '' if str(n) == '1' else 's') + (', %s%% wins' % wr if wr not in (None, '') else '') + '.'
    if not n: return ('Quiet day', 'No trades closed today. The bot is still watching the market.', 'hi')
    if p is None or p == 0: return ('Today ended flat', tail, 'even')
    if p > 0: return ('Hooray! Today: %s' % m, tail, 'win')
    return ('Oops, today: %s' % m, tail + ' A tough day; tomorrow is a fresh start for the rules.', 'loss')

def _period(word):
    def f_(f):
        p = _n(f.get('pnl')); m = money(p, f.get('cur')); extra = ''
        if f.get('best'): extra = ' Best: %s.' % f['best']
        t = '%s trades, %s%% wins.%s' % (f.get('n', 0), f.get('wr', '--'), extra)
        if p is None or p == 0: return ('Your %s report' % word, t, 'even')
        return (('Hooray! %s report: %s' if p > 0 else 'Oops, %s report: %s') % (word.capitalize(), m), t, 'win' if p > 0 else 'loss')
    return f_

T = {
 1: lambda f: ('%s %s is live' % (_side(f), f['sym']), 'Entry %s, stop-loss %s, take-profit %s.%s Risking %s%% of the account.' % (f['entry'], f['sl'], f['tp'], _strat(f), f.get('risk', '--')), 'hi'),
 2: lambda f: ('Hooray! %s hit take-profit' % (f.get('sym') or 'Trade'), 'Closed in profit: %s. The plan played out.' % money(f.get('pnl'), f.get('cur')), 'win'),
 3: lambda f: ('Oops, %s hit stop-loss' % (f.get('sym') or 'Trade'), 'Closed at a loss: %s. It is part of trading, and the stop-loss capped it.' % money(f.get('pnl'), f.get('cur')), 'loss'),
 4: _closed,
 5: lambda f: ('%s stop moved to breakeven' % f['sym'], 'The stop-loss now sits at your entry price.', 'even'),
 6: lambda f: ('%s partly closed' % f['sym'], 'Part of the position was closed (%s). The rest is still open.' % money(f.get('pnl'), f.get('cur')), 'hi'),
 7: lambda f: ('Signal found on %s' % f['sym'], '%s at about %s, stop-loss %s, take-profit %s.%s%s Take or skip it in the app%s.' % (_side(f), f['entry'], f['sl'], f['tp'], _strat(f), (' About %.2f lots at your risk setting.' % f['lots']) if f.get('lots') else '', (' within %s min' % f['mins']) if f.get('mins') else ''), 'hi'),
 8: lambda f: ('Skipped %s' % f['sym'], 'Reason: %s.' % (f.get('reason') or 'it did not pass the rules'), 'even'),
 9: lambda f: ('%s pending order %s' % (f['sym'], f.get('state') or 'updated'), 'Open the app to see where it stands.', 'hi'),
 10: lambda f: ('%s is still open' % f['sym'], 'Open for %s. Floating P/L: %s.' % (f.get('dur') or 'a while', money(f.get('pnl'), f.get('cur'))), 'even'),
 11: lambda f: ('Daily loss limit reached', "Today's losses hit the %s%% limit. Trading is paused until tomorrow." % f.get('limit', '--'), 'risk'),
 12: lambda f: ('Weekly loss limit reached', "This week's losses hit the %s%% limit. Trading is paused until next week." % f.get('limit', '--'), 'risk'),
 13: lambda f: ('Losing-streak pause', '%s losses in a row. The bot is resting until %s.' % (f.get('n', '--'), f.get('until', 'later')), 'risk'),
 14: lambda f: ('Trading resumed', 'The pause is over and the bot is scanning again.', 'hi'),
 15: lambda f: ('Max open trades reached', '%s trades are open, so new signals wait.' % f.get('n', '--'), 'risk'),
 16: lambda f: ('Max trades for today reached', '%s trades taken today. New signals wait until tomorrow.' % f.get('n', '--'), 'risk'),
 17: lambda f: ('%s exposure limit' % (f.get('ccy') or 'Currency'), 'A %s trade was blocked so the same currency is not stacked too much.' % f.get('sym', 'new'), 'risk'),
 18: lambda f: ('Half of the daily limit used', "Today's loss is %s%% of the %s%% limit." % (f.get('used', '--'), f.get('limit', '--')), 'risk'),
 19: lambda f: ('%s in %s minutes' % (f.get('event') or 'High-impact news', f.get('mins') or 60), 'Big news for %s is coming. Trading may pause around it.' % (f.get('ccy') or 'the market'), 'news'),
 20: lambda f: ('News lock started', 'New trades are paused around %s.' % (f.get('event') or 'the news'), 'news'),
 21: lambda f: ('News lock ended', 'The bot can open trades again.', 'news'),
 22: lambda f: ('%s session is opening' % (f.get('session') or 'A'), 'The market is waking up. The bot is watching.', 'news'),
 23: lambda f: ('XAUUSD moved %s%%' % f.get('pct', '--'), 'Gold moved %s%% in %s minutes. Price now %s.' % (f.get('pct', '--'), f.get('mins', '--'), f.get('price', '--')), 'news'),
 24: lambda f: ('Market is closed', 'No trades until it opens again.', 'news'),
 25: lambda f: ('Spread too wide on %s' % f['sym'], 'Spread is %s, so the trade was skipped.' % f.get('spread', 'high'), 'even'),
 26: lambda f: ('MT5 connected', 'Your EA is online and talking to spaceXBot.', 'hi'),
 27: lambda f: ('MT5 is offline', 'No heartbeat from your EA for %s minutes. Check MT5 is open, the EA is running and AutoTrading is on.' % f.get('mins', '--'), 'off'),
 28: lambda f: ('MT5 is back online', 'Your EA is talking to spaceXBot again.', 'hi'),
 29: lambda f: ('spaceXBot was updated', 'The server restarted with the latest update. Nothing for you to do.', 'hi'),
 30: lambda f: ('Monitor mode %s' % ('on' if f.get('on') else 'off'), 'The bot will find signals and wait for you.' if f.get('on') else 'The bot will place trades by itself.', 'hi'),
 31: lambda f: ('Switched to %s account' % (f.get('acct') or 'another'), 'Trades now go to your %s account.' % (f.get('acct') or 'new'), 'risk'),
 32: _day,
 33: _period('weekly'),
 34: _period('monthly'),
 35: lambda f: ('The brain learned something', f.get('note') or 'New weekly lessons are ready in the app.', 'hi'),
 36: lambda f: ('Hooray! %s wins in a row' % f.get('n', '--'), 'A winning streak, nice. Open the app to see the trades.', 'win'),
 37: lambda f: ("Review today's trades", 'A minute in the journal helps you spot what is working.', 'hi'),
 38: lambda f: ('Payment received', 'Thank you! Your bot is unlocked until %s.' % f.get('until', 'your plan end date'), 'bill'),
 39: lambda f: ('M-Pesa prompt sent', 'Check your phone and enter your PIN to finish.', 'bill'),
 40: lambda f: ('Payment did not go through', 'It failed or expired. You can try again from Plans.', 'off'),
 41: lambda f: ('PayPal payment confirmed', 'Thank you! Your bot is unlocked until %s.' % f.get('until', 'your plan end date'), 'bill'),
 42: lambda f: ('Your plan ends in 3 days', 'Renew to keep the bot running.', 'bill'),
 43: lambda f: ('Your plan ends tomorrow', 'Renew to keep the bot running.', 'bill'),
 44: lambda f: ('Your plan has ended', 'The bot is paused. Renew any time to switch it back on.', 'off'),
 45: lambda f: ('Verify your email', 'It takes a few seconds and keeps your account safe.', 'hi'),
 46: lambda f: ('Connect your MT5', 'The bot can start once your MT5 is linked. Open Connect to see how.', 'hi'),
 47: lambda f: ('Set your risk', 'Pick your risk percent and max trades so the bot follows your limits.', 'hi'),
 48: lambda f: ('Choose your alerts', 'Pick which notifications you want in Profile.', 'hi'),
 49: lambda f: ('Finish your profile', 'Pick your symbols and add the last details.', 'hi'),
 50: lambda f: ('Security notice', '%s. If this was not you, change your password now.' % (f.get('what') or 'New sign-in on your account'), 'risk'),
}
def compose(kind, **facts):
    """-> (title, body, image_url). Missing facts never crash a send: they fall back to a plain wording."""
    f = _F(facts)
    try: t, b, i = T[kind](f)
    except Exception: t, b, i = 'spaceXBot', 'Open the app for details.', 'hi'
    return t, b, img(i)
