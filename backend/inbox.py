"""TB1: the in-app notification inbox (the bell at the top of the app).
Every notification the bot would send to a person (push.send) is also kept here in plain words, newest first, so the person can read it in the app even if the phone banner was missed.
kv 'inbox:<uid>' = a list of {id, t, kind, cat, title, body, k}, at most MAX. kv 'inboxseen:<uid>' = the time the person last opened the bell (anything newer is 'new').
The same key is saved once, and the same words within DUP seconds are saved once, so a busy minute does not fill it. Words only: it never changes what the bot does. add() never raises."""
import json, time, threading
from . import store as st

MAX = 40
DUP = 120
_lock = threading.Lock()


def _k(uid): return 'inbox:' + (uid or '')
def _ks(uid): return 'inboxseen:' + (uid or '')


def _load(uid):
    try: j = json.loads(st.get(_k(uid)) or '[]')
    except (TypeError, ValueError): return []
    return [r for r in j if isinstance(r, dict) and r.get('title')] if isinstance(j, list) else []


def add(uid, kind, title, body, cat='', key=None, now=None):
    """Save one notification for one person. Returns True when it was saved, False when it was a repeat or could not be saved."""
    try:
        now = int(now or time.time()); title = ' '.join(str(title or '').split())[:80]; body = ' '.join(str(body or '').split())[:300]
        if not uid or not title: return False
        key = str(key)[:80] if key else None
        with _lock:
            rows = _load(uid)
            for r in rows[:MAX]:
                if key and r.get('k') == key: return False
                if r.get('kind') == kind and r.get('body') == body and now - int(r.get('t', 0)) < DUP: return False
            nid = (max([int(r.get('id', 0)) for r in rows] or [0]) + 1)
            rows.insert(0, {'id': nid, 't': now, 'kind': kind, 'cat': cat or '', 'title': title, 'body': body, 'k': key})
            st.put(_k(uid), json.dumps(rows[:MAX]))
        return True
    except Exception as e:
        print('[inbox] add failed', str(e)[:80]); return False


def _seen(uid):
    try: return int(st.get(_ks(uid)) or 0)
    except (TypeError, ValueError): return 0


def view(uid):
    """{items, unread, seen}: items newest first, each with 'new' (True when it came after the person last opened the bell)."""
    s = _seen(uid); items = []
    for r in _load(uid):
        d = dict(r); d.pop('k', None); d['new'] = int(r.get('t', 0)) > s; items.append(d)
    return {'items': items, 'unread': sum(1 for d in items if d['new']), 'seen': s}


def mark_seen(uid, now=None):
    st.put(_ks(uid), str(int(now or time.time())))


def clear(uid):
    with _lock: st.put(_k(uid), '[]')
