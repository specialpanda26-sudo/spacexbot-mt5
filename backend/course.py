"""C2: the learning path. Six short lessons, three questions each, unlocked one after the other. Progress is kept per person in kv 'course:<uid>'.
The server grades: the right answers never leave it until a lesson is passed. Pass mark: 2 right out of 3. Owner switch: setting course_required (default on)."""
import json
from . import store as st

PASS = 2
def L(i, t, art, intro, pts, qs): return {'id': i, 'title': t, 'art': art, 'intro': intro, 'points': pts, 'quiz': [{'q': q[0], 'o': q[1], 'a': q[2], 'why': q[3]} for q in qs]}

LESSONS = [
 L('meet', 'Meet your bot', 'rocket', 'What the bot does, and what it does not do.',
   ['The bot reads the market and looks for set-ups. When two strategies agree, it makes a signal.',
    'A signal is a plan: where to enter, where to stop, where to take profit. It is not a promise.',
    'Nobody can promise profit. Losing trades are normal. The safety rules are there to keep losses small.'],
   [('How does the bot make a signal?', ['Two strategies agree', 'It guesses', 'It copies other users'], 0, 'A signal needs two strategies to agree, unless the owner lets one trade alone.'),
    ('Does a signal promise profit?', ['Yes, always', 'No, losses happen', 'Only on gold'], 1, 'No signal is a promise. Losses are part of trading.'),
    ('What keeps losses small?', ['Bigger trades', 'The safety rules', 'Turning the bot off and on'], 1, 'The safety rules (stop loss and loss limits) keep each loss small.')]),
 L('risk', 'Risk comes first', 'shield', 'How much you can lose on one trade and in one day.',
   ['Risk per trade is the share of your balance you accept to lose if the stop loss is hit. Small is safer, for example 1%.',
    'The stop loss closes a losing trade for you at a fixed price. Every trade has one.',
    'The daily loss limit stops the bot for the day when your losses reach that share of the balance.'],
   [('What is risk per trade?', ['What you win', 'What you accept to lose if the stop loss is hit', 'The broker fee'], 1, 'It is the share of the balance lost when the stop loss is hit.'),
    ('What does the stop loss do?', ['Closes a losing trade at a set price', 'Doubles the trade', 'Hides the loss'], 0, 'It closes a losing trade at a set price so one trade cannot hurt much.'),
    ('The daily loss limit is reached. What happens?', ['The bot keeps trading', 'The bot stops for the day', 'Your plan ends'], 1, 'The bot stops trading for the day.')]),
 L('strategies', 'The strategies', 'doc', 'Trend and pullback ideas in plain words.',
   ['Trend strategies join a move that is already running. Reversion strategies look for a move that went too far.',
    'The bot also reads levels, candles and moving averages. Each strategy is one vote.',
    'More votes agreeing means a stronger signal. News and weekends can switch the bot off on purpose.'],
   [('What does a trend strategy do?', ['Joins a move that is running', 'Always goes against the move', 'Ignores price'], 0, 'It follows a move that is already running.'),
    ('What is one strategy to the bot?', ['One vote', 'A trade', 'A fee'], 0, 'Each strategy is one vote.'),
    ('Why can the bot stay out of the market?', ['It is broken', 'Safety rules such as news and weekends', 'Nobody is online'], 1, 'The safety rules keep it out when the risk is high.')]),
 L('signal', 'Read a signal', 'phone', 'Entry, stop loss and take profit.',
   ['Entry is the price where the trade opens. Buy means you expect price to go up. Sell means down.',
    'Stop loss is where the trade closes if you are wrong. Take profit is where it closes if you are right.',
    'The take profit is usually about two times as far as the stop loss. So one win can cover about two losses.'],
   [('What is the entry?', ['The price where the trade opens', 'The price where it ends', 'Your balance'], 0, 'The entry is the price where the trade opens.'),
    ('A buy trade hits its stop loss. What happened?', ['Price fell and the trade closed with a loss', 'Price rose and you won', 'Nothing'], 0, 'A buy loses when price falls to the stop loss.'),
    ('Take profit is usually how far compared with the stop loss?', ['About half', 'About two times', 'The same, always'], 1, 'About two times as far, so wins are bigger than losses.')]),
 L('accounts', 'Demo and real accounts', 'plug', 'Practice money and real money.',
   ['A demo account uses practice money. A real account uses your own money. The bot works with both.',
    'Switching between demo and real stops the bot, so it never trades on the wrong account by accident.',
    'To switch to real, you type the word REAL. Take time to check which mode you are in before you start.'],
   [('What is a demo account?', ['Practice money', 'A free real account', 'A bonus'], 0, 'A demo account uses practice money.'),
    ('You switch from demo to real. What happens to the bot?', ['It stops until you start it', 'It trades double', 'Nothing'], 0, 'Switching mode stops the bot.'),
    ('What do you type to switch to real?', ['REAL', 'OK', 'Your password'], 0, 'You type the word REAL.')]),
 L('rules', 'Your safety rules', 'lock', 'The rules that protect your balance.',
   ['Loss streak stop: after a few losses in a row the bot rests. Max open trades: it never holds more than your limit at once.',
    'News lock: the bot stays out just before and after big news. Weekend rule: gold and forex rest on Saturday and Sunday.',
    'You can make the rules stricter, never looser than the owner allows.'],
   [('Why does the bot rest after several losses in a row?', ['To protect your balance', 'It is tired', 'A bug'], 0, 'The loss streak stop protects the balance.'),
    ('Why does it avoid big news?', ['Prices jump unpredictably', 'News is boring', 'Brokers close'], 0, 'Prices can jump unpredictably around big news.'),
    ('Can you make a rule looser than the owner allows?', ['No, only stricter', 'Yes', 'Only on weekends'], 0, 'You can only make rules stricter.')]),
]
IDX = {l['id']: i for i, l in enumerate(LESSONS)}

def _get(uid):
    try: d = json.loads(st.get('course:%s' % uid) or '{}')
    except ValueError: d = {}
    return d if isinstance(d, dict) else {}

def done(uid): return [l['id'] for l in LESSONS if _get(uid).get(l['id'], 0) >= PASS]

def required(): return str(st.get('course_required') or '1') != '0'

def complete(uid): return len(done(uid)) == len(LESSONS)

def view(uid):
    d = set(done(uid)); out = []; open_ = None
    for l in LESSONS:
        s = 'done' if l['id'] in d else ('open' if open_ is None else 'locked')
        if s == 'open': open_ = l['id']
        o = {'id': l['id'], 'title': l['title'], 'art': l['art'], 'intro': l['intro'], 'status': s, 'best': _get(uid).get(l['id'], 0)}
        if s != 'locked': o['points'] = l['points']; o['quiz'] = [{'q': q['q'], 'o': q['o']} for q in l['quiz']]
        out.append(o)
    return {'lessons': out, 'done': len(d), 'total': len(LESSONS), 'next': open_, 'complete': len(d) == len(LESSONS), 'required': required(), 'pass': PASS}

def grade(uid, lid, answers):
    """-> result. ValueError with a plain sentence for a wrong request. Right answers are revealed only after a pass."""
    if lid not in IDX: raise ValueError('That lesson does not exist.')
    i = IDX[lid]; d = set(done(uid))
    if i and LESSONS[i - 1]['id'] not in d: raise ValueError('Finish the lesson before this one first.')
    qs = LESSONS[i]['quiz']
    if not isinstance(answers, list) or len(answers) != len(qs) or any(type(a) is not int or not 0 <= a < len(qs[k]['o']) for k, a in enumerate(answers)):
        raise ValueError('Answer every question.')
    ok = [a == q['a'] for a, q in zip(answers, qs)]; n = sum(ok); passed = n >= PASS
    p = _get(uid)
    if n > p.get(lid, 0): p[lid] = n; st.put('course:%s' % uid, json.dumps(p))
    res = [{'ok': k, 'why': q['why']} for k, q in zip(ok, qs)]
    if passed:
        for r, q in zip(res, qs): r['right'] = q['a']
    return {'score': n, 'total': len(qs), 'passed': passed, 'results': res, 'view': view(uid)}
