"""BT8: the burst card's RESULTS line. Of the burst groups that are fully closed in the last DAYS days it counts how many won, lost or ended flat
(a group's result = the sum of the profit of its closed entries), the win and loss percent and the net USD, and says whether the loss rate is inside
the target (owner setting burst_loss_target, default 25 percent, 1 to 99). A group still open or closing is not counted. A normal multi-entry group is not a burst. Entries that never filled (rejected, expired) have no profit and are ignored.
Under MIN_GROUPS groups the line says it is only a rough guide. Words and numbers only: nothing here places or closes a trade."""
import json, time
from . import store as st

DAYS = 7
MIN_GROUPS = 10
EPS = 0.005          # a group within half a cent of zero ended flat


def target():
    try: v = int(float(st.get('burst_loss_target')))
    except (TypeError, ValueError): v = 25
    return max(1, min(99, v))


def _burst(grp):
    try: m = json.loads(st.get('bg:%d' % int(grp)) or 'null')
    except (TypeError, ValueError): return False
    return isinstance(m, dict) and m.get('k') != 'multi'


def stats(uid='', now=None, days=DAYS):
    """-> {n, won, lost, flat, net, win_pct, loss_pct, days, target}. Counts only fully closed burst groups whose last entry closed in the window."""
    now = now or time.time(); since = int(now - days * 86400)
    rows = st.q("SELECT grp, "
                "SUM(CASE WHEN status='closed' AND pnl IS NOT NULL THEN pnl ELSE 0 END) tot, "
                "SUM(CASE WHEN status='closed' AND pnl IS NOT NULL THEN 1 ELSE 0 END) k, "
                "SUM(CASE WHEN status IN('pending','sent','open','closing') THEN 1 ELSE 0 END) live, "
                "MAX(closed) c FROM signals WHERE grp IS NOT NULL AND COALESCE(uid,'')=? AND created>=? GROUP BY grp ORDER BY grp DESC LIMIT 500",
                (uid or '', since - 86400))
    won = lost = flat = 0; net = 0.0
    for r in rows:
        if int(r.get('live') or 0) > 0 or int(r.get('k') or 0) < 1: continue
        if int(r.get('c') or 0) < since or not _burst(r['grp']): continue
        t = float(r.get('tot') or 0); net += t
        if t > EPS: won += 1
        elif t < -EPS: lost += 1
        else: flat += 1
    n = won + lost + flat
    return {'n': n, 'won': won, 'lost': lost, 'flat': flat, 'net': round(net, 2), 'days': days, 'target': target(),
            'win_pct': round(won * 100.0 / n) if n else 0, 'loss_pct': round(lost * 100.0 / n) if n else 0}


def _usd(v): return '%s$%.2f' % ('+' if v >= 0 else '-', abs(v))


def line(uid='', now=None):
    """-> one plain sentence for the burst card."""
    s = stats(uid, now)
    if not s['n']: return 'Results: no closed burst groups in the last %d days yet.' % s['days']
    out = 'Results (last %d days): %d closed groups, %d won (%d%%), %d lost (%d%%)%s. Net %s. ' % (
        s['days'], s['n'], s['won'], s['win_pct'], s['lost'], s['loss_pct'], ', %d flat' % s['flat'] if s['flat'] else '', _usd(s['net']))
    out += 'Your target is %d%% losses or fewer: %s.' % (s['target'], 'you are inside it' if s['loss_pct'] <= s['target'] else 'you are above it')
    if s['n'] < MIN_GROUPS: out += ' Only %d groups so far, so treat it as a rough guide.' % s['n']
    return out
