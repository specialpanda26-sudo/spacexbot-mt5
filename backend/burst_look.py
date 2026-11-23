"""BT5: the burst card's 'last look' line. Each time the burst scanner looks at a candle and does (or does not) open a group, it saves ONE plain sentence
for that person (kv blook:<uid>): what it saw and why it did or did not trade. The Bot tab shows it under the burst chip, with how long ago it was.
It only ever shows words the bot already decided; it never changes what the bot does."""
import json, time
from . import store as st, burst_free as bf

OLD = 6 * 3600          # a look older than this is not shown


def note(uid, text, now=None):
    st.put('blook:' + (uid or ''), json.dumps({'t': int(now or time.time()), 'why': str(text)[:240]}))
    try:
        from . import activity
        activity.log(uid, 'Burst: ' + str(text), 'check', now)          # AC1
    except Exception as e: print('activity note failed', str(e)[:80])


def ago(sec):
    sec = max(0, int(sec))
    return 'just now' if sec < 60 else '%d min ago' % (sec // 60) if sec < 3600 else '%d h ago' % (sec // 3600)


def last(uid='', now=None):
    """-> {'why': text, 'ago': 'N min ago'} or None (nothing saved, or older than 6 hours)."""
    now = now or time.time()
    try: j = json.loads(st.get('blook:' + (uid or '')) or 'null')
    except (TypeError, ValueError): return None
    if not isinstance(j, dict) or not j.get('why'): return None
    try: age = now - float(j.get('t') or 0)
    except (TypeError, ValueError): return None
    return None if age > OLD else {'why': str(j['why']), 'ago': ago(age)}


def free_words(uid, m, minute=False):
    """Why the no-strategy burst (BT4) did not open either. Empty text when it did not need to say anything."""
    n = bf.per_hour(minute)
    if n <= 0: return 'Burst without a strategy signal is off.'
    u = bf.used(uid, minute=minute)
    if u >= n: return 'Hourly cap reached (%d of %d groups).' % (u, n)
    need = bf.MIN_MINUTE if minute else 30          # FX1
    if len(m or []) < need: return 'Only %d candles so far; a chance without a strategy signal needs %d.' % (len(m or []), need)
    if bf.side(m) is None and not (minute and bf.side_any(m, bf.MIN_MINUTE)): return 'No clear price move either.'
    return ''
