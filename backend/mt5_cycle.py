"""CY4 (MT5): the auto-cycle for the MT5 bridge. The EA already closes a whole group at its target (Section 4) and reports every entry as closed with
reason 'basket', its closing price and the group profit. The server does the rest, so the EA code does not change:
  after_close(): called for every 'closed' report with reason 'basket'. When that was the LAST open entry of a normal multi-entry group (kind 'multi', group
     target above 0), the entries added up to a profit, the cycle is on and MT5 is the platform the person chose, it queues the next group with the same rules
     as the Deriv engine (deriv_group.reopen: same size, same symbol and side, same stop/target distances around the closing price, every risk gate, daily limit).
     A group that ended on a loss limit has a negative total and never starts the next one. One group can start the next only once (kv 'cyc_done:<grp>').
  retry(): called on every EA poll. Right after a close, the account snapshot the EA sent last may still show the old positions open, so the room check says no.
     That one refusal is tried again on the next polls for up to 90 seconds; any other refusal ends it at once.
Nothing here claims it makes more money: repeating trades also repeats losses."""
import json, time
from . import store as st, deriv_group as dg

WAIT = 90          # seconds a refusal for 'no room yet' is retried


def _transient(w): return w == 'max open positions' or str(w).startswith('not enough room')


def _first(g, uid): return st.q("SELECT * FROM signals WHERE grp=? AND COALESCE(uid,'')=? ORDER BY id LIMIT 1", (g, uid or ''), True)


def after_close(uid, sid, price, now=None):
    """-> ids of the new group, or None."""
    now = now or time.time(); uid = uid or ''
    s = st.q("SELECT * FROM signals WHERE id=? AND COALESCE(uid,'')=?", (sid, uid), True)
    g = (s or {}).get('grp'); m = dg._meta(g) if g else None
    if not m or m.get('k') != 'multi' or not (dg._f(m.get('tgt')) or 0) > 0: return None
    mem = st.q("SELECT * FROM signals WHERE grp=? AND COALESCE(uid,'')=? ORDER BY id", (g, uid))
    if not mem or any(r['status'] in ('open', 'pending', 'sent') for r in mem): return None          # an entry is still running: wait for its report
    closed = [r for r in mem if r['status'] == 'closed']
    total = round(sum(dg._f(r['pnl']) or 0 for r in closed), 2)
    if not closed or total <= 0: return None          # a loss limit or a stop loss never starts the next group
    if not st.x("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING", ('cyc_done:%d' % int(g), str(int(now))), True): return None          # this group already started its successor
    ids = dg.reopen(uid, g, m, mem[0], price, now)
    if not ids and _transient(dg.why(uid)): st.put('cyc_retry:' + uid, json.dumps({'parent': int(g), 'price': dg._f(price), 't': int(now)}))
    return ids


def retry(uid, now=None):
    """Try a waiting refusal again. -> ids of the new group, or None."""
    now = now or time.time(); uid = uid or ''
    try: j = json.loads(st.get('cyc_retry:' + uid) or 'null')
    except (TypeError, ValueError): j = None
    if not isinstance(j, dict): return None
    k = 'cyc_retry:' + uid
    m = dg._meta(j.get('parent')); first = _first(j.get('parent'), uid)
    if not m or not first: st.put(k, ''); return None
    if now - int(j.get('t') or 0) > WAIT:
        st.put(k, ''); dg._why(uid, 'no room for the next group: MT5 still showed the old positions open', None); return None
    ids = dg.reopen(uid, j['parent'], m, first, j.get('price'), now)
    if ids or not _transient(dg.why(uid)): st.put(k, '')
    return ids
