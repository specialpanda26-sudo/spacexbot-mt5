"""Small account presets ("smaller-risk settings") for $10 / $20 / $30 accounts.
One tap sets a person's EXISTING safety choices; nothing changes for anyone who never taps.
Rules (the tests check each one):
 - Per person only. The owner / admin scope is refused, because there the same save paths write GLOBAL settings.
 - Every value goes through the existing validated save: prefs.save, limits.save, groupcap.save, burst.save, links.set_risk.
   The owner's ceilings win: entries and positions are cut to limits.ceiling(), a looser pick never beats the owner's stricter
   streak (limits.streak), the risk is cut to the owner's risk_pct, burst is only ever switched OFF.
 - Demo first: refused while the person's MT5 or Deriv mode is Real. The Road to Real gate (roadmap.real_allowed) is not touched.
 - Undo: the first tap keeps the person's old raw values (kv pref:/lim:/gcap:/burst:<uid> and the link's risk). 'Back to my old settings'
   puts those exact values back (and removes keys that did not exist). This is the ONE place that writes raw values: they were valid when saved.
 - If any save fails halfway, everything is rolled back from that snapshot and nothing is left half-applied.
Not included (they have no per-person setting or no server rule today, so they are NOT set and the card says so): drawdown stop,
daily profit target + stop for the day, daily/weekly loss % (global owner settings). Kept in NOT_INCLUDED for the card text only.
Nothing here claims it makes money or keeps an account safe: it only makes the bot take smaller, fewer trades."""
import json, re, time
from . import store as st, prefs, limits, groupcap, burst, links, brokers as bk, automode, bars, indicators

# ---- the three tiers: change numbers here only ----
BASE = {'strategies': ['jg_pullback', 'heikin_flip', 'fvg_retrace'], 'alone': True, 'min_conf': 1, 'entries': 1,
        'burst_on': False, 'minute': False, 'max_open': 1, 'streak': 2, 'risk_pct': 1.0}
TIERS = {
    10: dict(BASE, loss_pct=2.0),
    20: dict(BASE, loss_pct=2.5),
    30: dict(BASE, loss_pct=3.0),
}
NOT_INCLUDED = ['Drawdown stop', 'Daily profit target', 'Daily and weekly loss limits (the owner sets these for everyone)']
KEYS = {'pref': 'pref:', 'lim': 'lim:', 'gcap': 'gcap:', 'burst': 'burst:'}          # kv prefixes, + the uid


def _tier(n):
    try: n = int(n)
    except (TypeError, ValueError): n = 0
    if n not in TIERS: raise ValueError('Pick the $10, $20 or $30 settings')
    return n


def _snap_key(uid): return 'preset:' + uid


def _snap(uid):
    try: j = json.loads(st.get(_snap_key(uid)) or 'null')
    except (TypeError, ValueError): j = None
    return j if isinstance(j, dict) and isinstance(j.get('prev'), dict) else None


def _read_raw(uid):
    """The person's current raw saved values (None = never saved)."""
    prev = {}
    for name, pre in KEYS.items():
        row = st.q('SELECT v FROM kv WHERE k=?', (pre + uid,), True); prev[name] = row['v'] if row else None
    l = links.get(uid); prev['has_link'] = bool(l); prev['risk'] = (l or {}).get('risk')
    return prev


def _write_raw(uid, prev):
    for name, pre in KEYS.items():
        if prev.get(name) is None: st.x('DELETE FROM kv WHERE k=?', (pre + uid,))
        else: st.put(pre + uid, prev[name])
    if links.get(uid): st.x('UPDATE links SET risk=? WHERE uid=?', (prev.get('risk'), uid))


def _check_person(uid):
    if not uid or limits._owner(uid):
        raise ValueError('Smaller-risk settings are for subscriber accounts. The owner bot is not changed.')
    if links.mode(uid) == 'real' or bk.mode(uid, 'Deriv') == 'real':
        raise ValueError('Try the smaller-risk settings on a demo account first. Switch to Demo, then pick a size.')


def values(tier, uid=''):
    """What the preset will write for this person, after the owner's ceilings (what the card shows)."""
    t = TIERS[_tier(tier)]
    ceil = limits.ceiling()
    risk = min(t['risk_pct'], links.RISK_MAX)
    try: risk = min(risk, st.fget('risk_pct'))          # never above the owner's own risk setting
    except (TypeError, ValueError): pass
    risk = max(links.RISK_MIN, round(risk, 2))
    return {'strategies': list(t['strategies']), 'alone': t['alone'], 'min_conf': t['min_conf'], 'entries': min(t['entries'], ceil),
            'max_open': min(t['max_open'], ceil), 'streak': t['streak'], 'risk_pct': risk, 'loss_pct': t['loss_pct'],
            'burst_on': False, 'minute': False}


# ---- S3: the minimum-lot check (before trading, not after) ----
WORDS = 'Your balance is too small for this market on this account type. Try a cent account or a demo.'
SYM_MAX = 12


def clean_sym(x):
    """The optional per-market facts the EA may send: {name: {vol_min, tick_value, tick_size}}. Anything odd is dropped. {} = nothing usable."""
    out = {}
    if not isinstance(x, dict): return out
    for k, v in list(x.items())[:SYM_MAX]:
        if not isinstance(k, str) or not re.fullmatch(r'[A-Za-z0-9._]{1,20}', k) or not isinstance(v, dict): continue
        row = {}
        for f in ('vol_min', 'tick_value', 'tick_size'):
            n = v.get(f)
            if isinstance(n, bool) or not isinstance(n, (int, float)) or n != n or n <= 0 or n > 1e9: break
            row[f] = float(n)
        else: out[k] = row
    return out


def min_lot(uid, tier):
    """Worst-case loss in dollars of the SMALLEST lot at the bot's widest stop (automode.max_stop ATR of the 15-minute candles; the bot
    never uses a wider one), against this tier's risk limit (balance x risk %). Same sum the EA does ('min lot would risk more than allowed').
    known False = the EA did not send min lots (old EA), or no balance / candles yet: nothing is claimed, the EA's own check still applies.
    warn = the worst case is above the limit for at least one market. blocked = even the smallest stop (0.5 ATR) is above it for EVERY market."""
    t = values(tier, uid); a = st.acct(uid) or {}
    try: bal = float(a.get('balance') or 0)
    except (TypeError, ValueError): bal = 0.0
    lim = round(bal * t['risk_pct'] / 100.0, 2)
    out = {'known': False, 'balance': round(bal, 2), 'risk_pct': t['risk_pct'], 'risk_usd': lim, 'rows': [], 'warn': False, 'blocked': False, 'message': ''}
    sym = clean_sym(a.get('sym')); mine = {x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()}
    if bal <= 0 or not sym: return out
    wide = automode.max_stop()
    for name, f in sym.items():
        if mine and name not in mine: continue
        b = bars.get(name, 'M15', uid)
        if len(b) < 15: continue
        r = indicators.atr(b)[-1]
        if not r > 0: continue
        per = lambda d: f['vol_min'] * (d / f['tick_size']) * f['tick_value']
        worst, best = per(r * wide), per(r * 0.5)
        out['rows'].append({'symbol': name, 'min_lot': f['vol_min'], 'worst_usd': round(worst, 2), 'best_usd': round(best, 2),
                            'too_small': worst > lim, 'all_skipped': best > lim})
    if not out['rows']: return out
    out['known'] = True; out['warn'] = any(x['too_small'] for x in out['rows']); out['blocked'] = all(x['all_skipped'] for x in out['rows'])
    if out['warn']: out['message'] = WORDS
    return out


def apply(uid, tier):
    """Apply a tier for this person. Raises ValueError (nothing changed) when refused or when a save fails. Returns status(uid)."""
    tier = _tier(tier); _check_person(uid)
    if min_lot(uid, tier)['blocked']: raise ValueError(WORDS)          # S3: no market could trade at this size, so say so now instead of skipping trades quietly
    v = values(tier, uid)
    old = _snap(uid); prev = old['prev'] if old else _read_raw(uid)          # a second tap keeps the ORIGINAL values for undo
    st.put(_snap_key(uid), json.dumps({'tier': tier, 'prev': prev, 't': int(time.time())}))
    try:
        prefs.save(uid, {'strategies': v['strategies'], 'alone': v['alone'], 'min_conf': v['min_conf'], 'entries': v['entries']})
        limits.save(uid, streak=v['streak'], max_open=v['max_open'])
        groupcap.save(uid, {'on': True, 'loss_pct': v['loss_pct']})
        burst.save(uid, {'on': v['burst_on'], 'minute': v['minute']})
        if links.get(uid): links.set_risk(uid, v['risk_pct'])
    except Exception:
        _write_raw(uid, prev)
        if old: st.put(_snap_key(uid), json.dumps(old))
        else: st.x('DELETE FROM kv WHERE k=?', (_snap_key(uid),))
        raise
    return status(uid)


def undo(uid):
    """Put the person's old values back exactly. Raises ValueError when there is nothing to undo."""
    s = _snap(uid)
    if not uid or not s: raise ValueError('There are no smaller-risk settings to undo')
    _write_raw(uid, s['prev'])
    st.x('DELETE FROM kv WHERE k=?', (_snap_key(uid),))
    return status(uid)


def status(uid):
    """What the card needs: the tiers (with this person's capped values), which one is on, whether undo is possible."""
    s = _snap(uid) if uid else None
    return {'tiers': {str(k): values(k, uid) for k in TIERS}, 'active': s['tier'] if s else None, 'can_undo': bool(s),
            'not_included': NOT_INCLUDED, 'owner': bool(not uid or limits._owner(uid)),
            'minlot': {} if not uid or limits._owner(uid) else {str(k): min_lot(uid, k) for k in TIERS}}
