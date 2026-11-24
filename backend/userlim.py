"""RS5: every person's OWN limits. The owner's admin-panel numbers now control the owner's own bot only.
A person's limit is, in this order: the number they saved (0 = off) -> the number they saved in the older Session limits card -> a start value
(safe values for a REAL-money account, off for a demo account). Whatever they set, the stop loss on every trade still protects the account.
One table below holds the numbers AND the plain-words guide the app shows ('What this does')."""
import json
from . import store as st

# key: label, lo, hi, step, owner's global setting, start value for a real account, guide texts
SPEC = {
 'daily_loss': dict(label='Daily loss limit (% of balance)', lo=0, hi=100, step=0.5, glob='max_daily_loss_pct', safe=3.0,
   on='When today\'s losses reach this share of your balance, the bot stops opening trades until the new day (00:00 UTC, 3:00 AM Kenya time). You can also restart the count in Trades > Journal.',
   ex='$1,000 balance and 3 = it stops for the day after $30 lost.', off='No daily stop. Only the stop loss on each trade protects you.'),
 'weekly_loss': dict(label='Weekly loss limit (% of balance)', lo=0, hi=100, step=0.5, glob='max_weekly_loss_pct', safe=6.0,
   on='When this week\'s losses (since Monday 00:00 UTC) reach this share of your balance, the bot stops until next week.',
   ex='$1,000 balance and 6 = it stops for the week after $60 lost.', off='No weekly stop.'),
 'max_open': dict(label='Most trades open at once', lo=0, hi=50, step=1, glob='max_open', safe=3,
   on='The bot will not open a new trade while this many are open. It waits for one to close.',
   ex='3 = a 4th trade waits until one of the 3 closes.', off='As many as the platform allows (the owner\'s server ceiling).'),
 'same_dir': dict(label='Most trades leaning the same way on one currency', lo=0, hi=10, step=1, glob='max_ccy_exposure', safe=2,
   on='Stops you piling many trades in one direction on the same currency. Gold SELL counts against both gold and the dollar.',
   ex='2 = a 3rd SELL on gold waits while two SELLs are open.', off='No cap. All your trades can lean the same way, so one bad move hits them all together.'),
 'streak': dict(label='Stop after this many losses in a row', lo=0, hi=20, step=1, glob='max_losing_streak', safe=3,
   on='After this many losing trades in a row the bot pauses (for the rest hours below).',
   ex='3 = three losses in a row pause the bot.', off='The bot keeps trading after any number of losses in a row.'),
 'streak_rest': dict(label='Rest hours after that stop', lo=0, hi=72, step=1, glob='streak_cooldown_h', safe=4,
   on='How long the bot rests after the losing-streak stop.', ex='4 = it rests 4 hours.', always=True, off='No rest. Only matters when the streak stop above is on.'),
 'max_trades': dict(label='Most trades a day', lo=0, hi=100, step=1, glob='max_trades_day', safe=0,
   on='After this many trades today the bot waits for tomorrow. A burst or several-entries setup counts as one.',
   ex='10 = the 11th trade waits until tomorrow.', off='No daily trade count limit.'),
 'cooldown': dict(label='Wait minutes before the same market trades again', lo=0, hi=1440, step=1, glob='cooldown_min', safe=60,
   on='After a trade on a market, the bot leaves that market alone for this many minutes.', ex='60 = gold waits an hour after its last trade.', off='The same market can trade again straight away.'),
 'news_min': dict(label='News lock (minutes before and after big news)', lo=0, hi=240, step=5, glob='news_before_min', safe=30,
   on='The bot opens no trade on a market from this many minutes before to this many minutes after a high-impact news release for its currencies.',
   ex='30 = no gold trades from 30 minutes before to 30 minutes after US news.', off='The bot trades through news, when prices jump and spreads widen.'),
}
ORDER = ['daily_loss', 'weekly_loss', 'max_open', 'same_dir', 'streak', 'streak_rest', 'max_trades', 'cooldown', 'news_min']
LEGACY = {'max_trades': 'mt', 'streak': 'ks', 'max_open': 'mo'}          # the older Session limits card kept these in lim:<uid>

def _owner(uid):
    from . import limits
    return (not uid) or limits._owner(uid)

def _real(uid):
    return st.acct(uid).get('demo') is not True

def _saved(uid):
    try: j = json.loads(st.get('ul:' + uid) or '{}')
    except ValueError: j = {}
    return j if isinstance(j, dict) else {}

def _glob(key):
    try:
        if key == 'news_min': return float(st.get('news_before_min') or 0) if st.get('news_lock') == '1' else 0.0
        if key == 'max_open':
            from . import limits
            return 0.0 if limits.no_cap('') else float(max(1, int(float(st.get('max_open') or 3))))
        return float(st.get(SPEC[key]['glob']) or 0)
    except (TypeError, ValueError): return 0.0

def val(uid, key):
    """The number the gates use for this person. 0 = off."""
    if _owner(uid): return _glob(key)
    sv = _saved(uid)
    if key in sv:
        try: return float(sv[key])
        except (TypeError, ValueError): pass
    if key in LEGACY:
        from . import limits
        n = limits._num(limits._mine(uid).get(LEGACY[key]))
        if n > 0: return float(n)
    return float(SPEC[key]['safe']) if (_real(uid) or SPEC[key].get('always')) else 0.0

def news(uid):
    """(minutes before, minutes after) for the news lock; (0, 0) = off."""
    if _owner(uid):
        return (float(st.get('news_before_min') or 0), float(st.get('news_after_min') or 0)) if st.get('news_lock') == '1' else (0.0, 0.0)
    n = val(uid, 'news_min'); return (n, n)

def view(uid):
    """What the app shows: every field with its value, start value and guide."""
    own = _owner(uid); sv = {} if own else _saved(uid); out = []
    for k in ORDER:
        s = SPEC[k]; v = val(uid, k)
        out.append({'key': k, 'label': s['label'], 'lo': s['lo'], 'hi': s['hi'], 'step': s['step'], 'value': int(v) if v == int(v) else v, 'safe': s['safe'],
                    'on': s['on'], 'example': s['ex'], 'off': s['off'], 'saved': k in sv})
    mode = 'owner' if own else ('real' if _real(uid) else 'demo')
    intro = {'owner': 'These are the limits of your own bot. Other people set their own.',
             'real': 'Real-money account: safe start values are filled in. Change any number, or put 0 to switch that limit off. It is your choice.',
             'demo': 'Demo account: every limit starts off. Put a number to switch one on. Real-money accounts start with safe values.'}[mode]
    return {'mode': mode, 'intro': intro, 'fields': out}

def save(uid, data):
    """data: {key: number}. Raises ValueError with a plain message. The owner's numbers go to the owner's own settings."""
    if not isinstance(data, dict): raise ValueError('Nothing to save')
    clean = {}
    for k, v in data.items():
        if k not in SPEC: continue
        s = SPEC[k]
        try: n = float('nan') if isinstance(v, bool) else float(v)
        except (TypeError, ValueError): n = float('nan')
        if n != n or not (s['lo'] <= n <= s['hi']): raise ValueError('%s must be from %s to %s (0 = off)' % (s['label'], s['lo'], s['hi']))
        clean[k] = round(n, 2) if s['step'] < 1 else int(round(n))
    if _owner(uid):
        for k, n in clean.items():
            if k == 'news_min':
                st.put('news_lock', '1' if n > 0 else '0')
                if n > 0: st.put('news_before_min', n); st.put('news_after_min', n)
            elif k == 'max_open':
                st.put('no_open_cap', '1' if n == 0 else '0')
                if n > 0: st.put('max_open', int(n))
            else: st.put(SPEC[k]['glob'], n)
    else:
        cur = _saved(uid); cur.update(clean); st.put('ul:' + uid, json.dumps(cur))
    return view(uid)

def reset(uid):
    """Back to the start values (a person only; the owner changes numbers in the boxes)."""
    if not _owner(uid): st.x('DELETE FROM kv WHERE k=?', ('ul:' + uid,)); st.x('DELETE FROM kv WHERE k=?', ('lim:' + uid,))
    return view(uid)
