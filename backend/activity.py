"""AC1: what the bot is doing, live, for the Journal tab. Words only: it never changes what the bot does.
Each check the bot makes (a market looked at, a wait, a setup found, a switch turned) leaves ONE plain sentence in kv 'act:<scope>' (newest first, at most MAX).
The same sentence seen again only moves up and refreshes its time (and is saved at most once every REFRESH seconds), so a quiet market does not flood it.
GET /api/activity = snapshot(): 'now' (the bot's state in words), 'markets' (the last look at each market), 'items' (the feed).
Scope: a normal person = their own uid. The owner = the owner's own EA ('' scope) + their own uid, the same as the Journal."""
import json, time, threading
from . import store as st

MAX = 80
REFRESH = 120
LOOK_BACK = 25          # a repeat is matched against this many newest rows
_lock = threading.Lock()


def _key(uid): return 'act:' + (uid or '')


def _load(uid):
    try: j = json.loads(st.get(_key(uid)) or '[]')
    except (TypeError, ValueError): return []
    return [r for r in j if isinstance(r, dict) and r.get('m')] if isinstance(j, list) else []


def log(uid, text, kind='check', now=None):
    """Save one sentence. kind: check | wait | trade | bot. Never raises (the bot must not stop because a note failed)."""
    text = ' '.join(str(text or '').split())[:240]
    if not text: return
    now = int(now or time.time())
    try:
        with _lock:
            rows = _load(uid); hit = next((i for i, r in enumerate(rows[:LOOK_BACK]) if r.get('m') == text and r.get('k') == kind), None)
            if hit is not None:
                r = rows[hit]
                if hit == 0 and now - int(r.get('t') or 0) < REFRESH: return          # same top sentence a moment ago: nothing to write
                rows.pop(hit); r['t'] = now; r['n'] = int(r.get('n') or 1) + 1; rows.insert(0, r)
            else: rows.insert(0, {'t': now, 'a': now, 'k': kind, 'm': text, 'n': 1})
            del rows[MAX:]
            st.put(_key(uid), json.dumps(rows))
    except Exception as e: print('activity log failed', str(e)[:80])


def scopes(uid, admin): return ['', uid] if admin and uid else [''] if admin else [uid]


def items(uid, admin, limit=60):
    out = []
    for sc in scopes(uid, admin):
        for r in _load(sc): out.append({'t': int(r.get('t') or 0), 'a': int(r.get('a') or r.get('t') or 0), 'k': r.get('k') or 'check', 'm': r['m'], 'n': int(r.get('n') or 1)})
    out.sort(key=lambda r: r['t'], reverse=True)
    return out[:max(1, int(limit))]


def markets(uid, admin, now=None, limit=8):
    """The last look at each market (the scanner note 'scan:<scope>:<symbol>'), newest first, nothing older than a day."""
    from . import botstate
    now = now or time.time(); best = {}
    for sc in scopes(uid, admin):
        pre = 'scan:%s:' % sc
        for r in st.q("SELECT k,v FROM kv WHERE k LIKE ?", (pre + '%',)) or []:
            if not str(r['k']).startswith(pre): continue
            try: j = json.loads(r['v'])
            except (TypeError, ValueError): continue
            if not isinstance(j, dict): continue
            t = int(j.get('t') or 0); sym = str(r['k'])[len(pre):]
            if not sym or now - t > 86400: continue
            if sym not in best or t > best[sym]['t']: best[sym] = {'symbol': sym, 't': t, 'm': botstate.scan_text(j)}
    return sorted(best.values(), key=lambda o: o['t'], reverse=True)[:limit]


def headline(ex):
    s = ex.get('state')
    return ('The bot is stopped' if s == 'stopped' else 'The bot is on and waiting' if s == 'waiting' else 'The bot is on and watching the market' if s == 'watching'
            else 'The bot is on' if ex.get('running') else 'The bot is stopped')


def snapshot(uid, admin=False, paid=True, now=None):
    from . import botstate
    now = int(now or time.time())
    try: ex = botstate.explain(uid, admin, paid, now) or {}
    except Exception as e: print('activity state failed', str(e)[:80]); ex = {}
    return {'now': {'running': bool(ex.get('running')), 'state': ex.get('state') or 'stopped', 'headline': headline(ex), 'detail': ex.get('why') or '', 'checked': ex.get('checked')},
            'markets': markets(uid, admin, now), 'items': items(uid, admin), 'ts': now}
