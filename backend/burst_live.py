"""BT6: live profit of open groups on Deriv. Deriv has no floating figure of its own, so the Home card and the phone notification showed Floating P/L $0.00
even with trades open. deriv_group.check already reads the live profit of every open member of a group each round; this file saves that sum
(kv glive:<grp>: t, live, tot, n, tgt) and gives it back as (1) one plain sentence for the burst card and (2) the floating profit for Deriv's equity.
Only a figure read in the last FRESH seconds is used; an older one is ignored, never guessed. Words and numbers only: nothing here places or closes a trade."""
import json, time
from . import store as st

FRESH = 150          # seconds a saved live profit still counts


def _f(x):
    try: v = float(x)
    except (TypeError, ValueError): return None
    return v if v == v and abs(v) < 1e12 else None


def save(grp, live, tot, n, tgt, lim, now=None):
    st.put('glive:%d' % int(grp), json.dumps({'t': int(now or time.time()), 'live': round(float(live), 2), 'tot': round(float(tot), 2), 'n': int(n), 'tgt': round(float(tgt or 0), 2), 'lim': round(float(lim or 0), 2)}))


def _get(grp, now):
    try: j = json.loads(st.get('glive:%d' % int(grp)) or 'null')
    except (TypeError, ValueError): return None
    if not isinstance(j, dict) or _f(j.get('t')) is None or _f(j.get('live')) is None: return None
    return j if 0 <= now - float(j['t']) <= FRESH else None


def _open_groups(scopes):
    out = []
    for sc in dict.fromkeys(scopes):
        out += [r['grp'] for r in st.q("SELECT DISTINCT grp FROM signals WHERE grp IS NOT NULL AND status='open' AND COALESCE(uid,'')=? ORDER BY grp DESC LIMIT 20", (sc or '',))]
    return out


def floating(scopes, now=None):
    """Sum of the fresh live profit of the person's open groups (USD). 0.0 when there is none. scopes = the uids whose signals count, e.g. ('', 'u1')."""
    now = now or time.time(); tot = 0.0
    for g in _open_groups(scopes):
        j = _get(g, now)
        if j: tot += float(j['live'])
    return round(tot, 2)


def _usd(v): return '%s$%.2f' % ('+' if v >= 0 else '-', abs(v))


def group(uid='', now=None):
    """-> one sentence about the person's open BURST group, or None when no burst group is open."""
    now = now or time.time()
    for g in _open_groups((uid or '',)):
        try: m = json.loads(st.get('bg:%d' % int(g)) or 'null')
        except (TypeError, ValueError): m = None
        if not isinstance(m, dict) or m.get('k') == 'multi': continue
        n = (st.q("SELECT COUNT(*) n FROM signals WHERE grp=? AND status='open' AND COALESCE(uid,'')=?", (g, uid or ''), True) or {}).get('n') or 0
        j = _get(g, now)
        if not j: return '%d open, live profit not read yet.' % n
        tgt = _f(j.get('tgt')) or 0
        return '%d open, profit now %s%s (updated %s).' % (j['n'], _usd(float(j['tot'])), ' of %s target' % _usd(tgt) if tgt > 0 else '', 'just now' if now - float(j['t']) < 60 else '%d min ago' % ((now - float(j['t'])) // 60))
    return None
