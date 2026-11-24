"""Share code: one person turns ALL their bot settings into a short code, another person pastes it and gets the same settings.
No server storage: the code IS the settings (JSON, compressed, base64, with a check at the end), so it works for anyone on this server and
survives a redeploy. Format:  SXB1.<payload>.<check>   (spaces and line breaks added by WhatsApp / email are ignored).

What is in a code (the same things the app's own cards save, nothing else):
  pref  Strategies & entries card   : strategies, alone, min_conf, entries, scale, fast, regime
  lim   My limits card              : daily loss, weekly loss, open trades, same-way trades, loss streak (+ rest hours), trades a day, wait minutes, news lock
  gcap  Group target / loss limit   : on, target USD, loss %
  burst Burst card                  : on, quiet minutes, quick / big entries and targets, give-back, stake, loss USD, lot, every-minute scan
  cycle Auto-cycle card             : on, new groups a day
  risk  Risk per trade (%)
NEVER in a code (private or unsafe to hand over): keys, broker logins, balances, email, profile, Demo/Real mode, whether the bot is ON, phone-mode
numbers, alert choices, plan or payment data. Loading a code never starts the bot and never switches Real mode on.

Rules:
 - Every value is checked again on the loading side. A code is only data: unknown parts are dropped, numbers are cut into the allowed range,
   the owner's ceilings win (entries / open trades / risk), strategies this server does not have are skipped. Nothing is trusted from the code.
 - Every value goes through the EXISTING validated save (prefs.save, userlim.save, groupcap.save, burst.save, cycle.save, links.set_risk).
 - check() shows what would change and warns about anything that gets looser, BEFORE anything is saved. load() saves.
 - A subscriber must be on Demo to load a code (same Demo-first rule as the small-account settings). The owner scope is allowed: the owner's own cards
   write the same settings; the risk per trade of the owner is a server-wide default, so the owner's load leaves it alone.
 - Undo: the first load keeps the person's old raw values; 'Back to my old settings' puts those exact values back. A failed load rolls back by itself.
Nothing here claims a setting makes money. It only copies choices from one account to another."""
import base64, hashlib, json, re, time, zlib
from . import store as st, prefs, limits, userlim, groupcap, burst, cycle, links, brokers as bk, strategy_info as si

VERSION = 1
PREFIX = 'SXB1.'
MAX_CODE = 6000          # characters accepted (a real code is about 300-500)
MAX_JSON = 20000         # bytes after unpacking (zip-bomb guard)
NAME_MAX = 24
SECTIONS = ('pref', 'lim', 'gcap', 'burst', 'cycle', 'risk')
PERSON_KV = ('pref:', 'ul:', 'lim:', 'gcap:', 'burst:', 'cycle:')          # per-scope raw rows the loader can write
OWNER_GLOBALS = ('max_daily_loss_pct', 'max_weekly_loss_pct', 'max_open', 'no_open_cap', 'max_ccy_exposure', 'max_losing_streak',
                 'streak_cooldown_h', 'max_trades_day', 'cooldown_min', 'news_lock', 'news_before_min', 'news_after_min')          # what userlim.save writes for the owner

LABEL = {
    'pref': {'strategies': 'Strategies allowed', 'alone': 'One strategy may trade alone', 'min_conf': 'Strategies that must agree',
             'entries': 'Entries per setup', 'scale': 'More entries while winning', 'fast': '5-minute scan', 'regime': 'Pause strategies that lose in this market'},
    'gcap': {'on': 'Group target / loss limit', 'target_usd': 'Group profit target (USD)', 'loss_pct': 'Group loss limit (% of balance)'},
    'burst': {'on': 'Burst mode', 'idle_min': 'Burst: quiet minutes first', 'quick_n': 'Quick burst entries', 'big_n': 'Big burst entries',
              'quick_usd': 'Quick burst target (USD)', 'big_usd': 'Big burst target (USD)', 'giveback': 'Give-back guard (%)',
              'stake_usd': 'Stake per entry (USD)', 'loss_usd': 'Most a burst group may lose (USD)', 'lot': 'Lot per burst entry',
              'minute': 'Every-minute scan', 'minute_n': 'Entries each minute'},
    'cycle': {'on': 'Auto-cycle', 'max_per_day': 'Auto-cycle: new groups a day'},
    'risk': {'risk_pct': 'Risk per trade (%)'},
}
PROTECT = ('daily_loss', 'weekly_loss', 'max_open', 'same_dir', 'streak')          # a limit that goes from a number to 0 = a protection switched off


# ---------------------------------------------------------------- small helpers
def _owner(uid): return (not uid) or limits._owner(uid)


def _num(v, lo, hi, whole=False, zero_ok=False):
    """-> (value, clamped?) or raises ValueError('bad'). Booleans and non-numbers are refused; out of range is cut into range."""
    if isinstance(v, bool) or not isinstance(v, (int, float, str)): raise ValueError('bad')
    try: f = float(v)
    except (TypeError, ValueError, OverflowError): raise ValueError('bad')
    if f != f or f in (float('inf'), float('-inf')): raise ValueError('bad')
    if whole: f = float(int(round(f)))
    if zero_ok and f == 0: return 0, False
    g = max(lo, min(hi, f))
    return (int(g) if whole else round(g, 2)), g != f


def _name(x):
    x = x if isinstance(x, str) else ''
    return re.sub(r'\s+', ' ', ''.join(ch for ch in x if ch.isprintable())).strip()[:NAME_MAX]


def _fmt(key, v):
    if v is None: return '-'
    if key == 'lot' and v == 0: return 'Automatic'
    if key == 'stake_usd' and v == 0: return 'Normal sizing'
    if isinstance(v, bool): return 'On' if v else 'Off'
    if isinstance(v, list): return ', '.join(si.name(x) for x in v) if v else 'All strategies'
    if v == 0 and key not in ('min_conf', 'entries'): return 'Off'
    if v == 0: return 'Default'
    if key.endswith('_usd') or key in ('lot',): return ('$%g' % v) if key != 'lot' else '%g' % v
    if key in ('risk_pct', 'loss_pct', 'giveback'): return '%g%%' % v
    return '%g' % v


# ---------------------------------------------------------------- collect (what this person has now)
def collect(sc, bsc=None):
    """The person's settings as plain data. sc = scope of prefs / limits / group / cycle / risk, bsc = scope of the burst card (see burst_scope)."""
    bsc = sc if bsc is None else bsc
    out = {'pref': prefs.get(sc), 'lim': {k: userlim.val(sc, k) for k in userlim.ORDER}, 'gcap': groupcap.get(sc),
           'burst': burst.get(bsc), 'cycle': cycle.get(sc)}
    out['lim'] = {k: (int(v) if v == int(v) else round(v, 2)) for k, v in out['lim'].items()}
    out['pref'].pop('ceiling', None)
    if _owner(sc):
        try: out['risk'] = {'risk_pct': round(st.fget('risk_pct'), 2)}
        except (TypeError, ValueError): pass
    elif links.get(sc): out['risk'] = {'risk_pct': round(links.risk(sc), 2)}
    return out


# ---------------------------------------------------------------- the code
def _check_digits(raw): return hashlib.sha256(raw).hexdigest()[:6]


def encode(sections, name=''):
    body = {'v': VERSION, 'n': _name(name), 't': int(time.time()), 's': {k: sections[k] for k in SECTIONS if k in sections}}
    raw = zlib.compress(json.dumps(body, separators=(',', ':'), sort_keys=True).encode('utf-8'), 9)
    return PREFIX + base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=') + '.' + _check_digits(raw)


def decode(code):
    """-> the payload dict, or ValueError with a plain message (this is what the person sees)."""
    if not isinstance(code, str): raise ValueError('Paste the code first')
    c = re.sub(r'[\s`"\'<>]', '', code)
    if not c: raise ValueError('Paste the code first')
    if len(c) > MAX_CODE: raise ValueError('That is too long to be a settings code')
    if not c.upper().startswith(PREFIX.upper()): raise ValueError('That is not a spaceXBot settings code. It starts with SXB1.')
    c = PREFIX + c[len(PREFIX):]
    try: data, chk = c[len(PREFIX):].rsplit('.', 1)
    except ValueError: raise ValueError('The code looks cut short. Copy the whole code again.')
    try: raw = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
    except (ValueError, TypeError): raise ValueError('The code has a wrong letter in it. Copy it again.')
    if _check_digits(raw) != chk.lower(): raise ValueError('The code has a wrong or missing part. Copy the whole code again.')
    try:
        d = zlib.decompressobj(); text = d.decompress(raw, MAX_JSON)
        if d.unconsumed_tail: raise ValueError('big')
        j = json.loads(text.decode('utf-8'))
    except (zlib.error, ValueError, UnicodeDecodeError): raise ValueError('The code could not be read. Copy it again.')
    if not isinstance(j, dict) or not isinstance(j.get('s'), dict): raise ValueError('The code could not be read. Copy it again.')
    if j.get('v') != VERSION: raise ValueError('This code is from a different version of the app. Ask your friend to make a new one.')
    return j


# ---------------------------------------------------------------- clean (never trust the code)
def clean(payload, owner=False):
    """-> (settings, notes). settings has only checked values, cut to what this server allows. notes = plain sentences about what was changed or skipped."""
    s = payload.get('s') or {}; notes = []; out = {}
    ceil = limits.ceiling()

    def note(t):
        if t not in notes: notes.append(t)

    # strategies & entries
    p = s.get('pref'); o = {}
    if isinstance(p, dict):
        if 'strategies' in p:
            sl = p['strategies']
            if isinstance(sl, list) and len(sl) <= 60 and all(isinstance(x, str) for x in sl):
                known = set(prefs._known()); keep = [x for x in dict.fromkeys(sl) if x in known]
                if len(keep) < len(set(sl)): note('%d strategy(ies) in the code are not on this server and were skipped.' % (len(set(sl)) - len(keep)))
                if keep or not sl: o['strategies'] = keep
                else: note('None of the strategies in the code exist here, so your strategy choice was left as it is.')
        for k, lo, hi in (('min_conf', 0, 5), ('entries', 0, min(10, ceil))):
            if k in p:
                try:
                    v, cut = _num(p[k], lo, hi, whole=True); o[k] = v
                    if cut: note('%s was cut to %d (the highest this server allows).' % (LABEL['pref'][k], v))
                except ValueError: pass
        for k in ('alone', 'scale', 'fast', 'regime'):
            if isinstance(p.get(k), bool): o[k] = p[k]
    if o: out['pref'] = o

    # limits
    l = s.get('lim'); o = {}
    if isinstance(l, dict):
        for k in userlim.ORDER:
            if k not in l: continue
            sp = userlim.SPEC[k]
            try: v, cut = _num(l[k], sp['lo'], sp['hi'], whole=sp['step'] >= 1, zero_ok=True)
            except ValueError: continue
            if k == 'max_open' and v and not owner and v > ceil: v, cut = ceil, True
            o[k] = v
            if cut: note('%s was cut into the allowed range (%g).' % (sp['label'], v))
    if o: out['lim'] = o

    # group target / loss limit
    g = s.get('gcap'); o = {}
    if isinstance(g, dict):
        if isinstance(g.get('on'), bool): o['on'] = g['on']
        for k, lo, hi in (('target_usd', groupcap.USD_LO, groupcap.USD_HI), ('loss_pct', groupcap.PCT_LO, groupcap.PCT_HI)):
            if k in g:
                try: o[k] = _num(g[k], lo, hi, zero_ok=True)[0]
                except ValueError: pass
    if o: out['gcap'] = o

    # burst
    b = s.get('burst'); o = {}
    if isinstance(b, dict):
        for k in ('on', 'minute'):
            if isinstance(b.get(k), bool): o[k] = b[k]
        for k, lo, hi in (('idle_min', 1, 60), ('quick_n', 1, ceil), ('big_n', 1, ceil), ('minute_n', 2, ceil), ('giveback', 0, 90)):
            if k in b and not (k == 'minute_n' and ceil < 2):          # burst.save refuses minute_n when the ceiling is below 2
                try:
                    v, cut = _num(b[k], lo, hi, whole=True); o[k] = v
                    if cut and k in ('quick_n', 'big_n', 'minute_n'): note('%s was cut to %d (the highest this server allows).' % (LABEL['burst'][k], v))
                except ValueError: pass
        for k, lo, hi, z in (('quick_usd', burst.USD_LO, burst.USD_HI, False), ('big_usd', burst.USD_LO, burst.USD_HI, False), ('stake_usd', 0.1, burst.USD_HI, True),
                             ('loss_usd', 0.1, burst.USD_HI, True), ('lot', 0.01, 100.0, True)):
            if k in b:
                try: o[k] = _num(b[k], lo, hi, zero_ok=z)[0]
                except ValueError: pass
    if o: out['burst'] = o

    # auto-cycle
    cy = s.get('cycle'); o = {}
    if isinstance(cy, dict):
        if isinstance(cy.get('on'), bool): o['on'] = cy['on']
        if 'max_per_day' in cy:
            try: o['max_per_day'] = _num(cy['max_per_day'], cycle.MAX_LO, cycle.MAX_HI, whole=True)[0]
            except ValueError: pass
    if o: out['cycle'] = o

    # risk per trade (a subscriber only; the owner's is a server-wide default and is left alone)
    r = s.get('risk')
    if isinstance(r, dict) and 'risk_pct' in r and not owner:
        try:
            v, cut = _num(r['risk_pct'], links.RISK_MIN, links.RISK_MAX)
            try: top = st.fget('risk_pct')
            except (TypeError, ValueError): top = links.RISK_MAX
            if v > top: v, cut = max(links.RISK_MIN, round(top, 2)), True
            out['risk'] = {'risk_pct': v}
            if cut: note('Risk per trade was cut to %g%% (the highest this server allows for you).' % v)
        except ValueError: pass
    elif isinstance(r, dict) and owner: note('Risk per trade is a server-wide setting for the owner, so it was not changed.')
    return out, notes


# ---------------------------------------------------------------- preview rows + warnings
def _rows(cur, new, owner):
    rows = []; same = 0
    def add(sec, key, label, a, b):
        nonlocal same
        if a == b: same += 1
        else: rows.append({'label': label, 'now': _fmt(key, a), 'new': _fmt(key, b), 'sec': sec})
    for sec in ('pref', 'gcap', 'burst', 'cycle'):
        for k, v in (new.get(sec) or {}).items():
            add(sec, k, LABEL[sec].get(k, k), (cur.get(sec) or {}).get(k), v)
    for k, v in (new.get('lim') or {}).items():
        add('lim', k, userlim.SPEC[k]['label'], (cur.get('lim') or {}).get(k), v)
    if new.get('risk'): add('risk', 'risk_pct', LABEL['risk']['risk_pct'], (cur.get('risk') or {}).get('risk_pct'), new['risk']['risk_pct'])
    return rows, same


def _warnings(cur, new):
    w = []
    cl = cur.get('lim') or {}
    for k, v in (new.get('lim') or {}).items():
        if k in PROTECT and v == 0 and (cl.get(k) or 0) != 0: w.append('%s will be switched OFF.' % userlim.SPEC[k]['label'])
    n = new.get('lim') or {}
    if n.get('daily_loss') == 0 and n.get('weekly_loss') == 0: w.append('There will be no daily or weekly loss stop. Only the stop loss on each trade protects the account.')
    if (new.get('burst') or {}).get('on') and not (cur.get('burst') or {}).get('on'): w.append('Burst mode will be ON. It opens several entries quickly.')
    if (new.get('burst') or {}).get('minute') and not (cur.get('burst') or {}).get('minute'): w.append('The every-minute scan will be ON.')
    if (new.get('cycle') or {}).get('on') and not (cur.get('cycle') or {}).get('on'): w.append('Auto-cycle will be ON. It repeats groups, so it also repeats losses.')
    nr = (new.get('risk') or {}).get('risk_pct'); cr = (cur.get('risk') or {}).get('risk_pct')
    if nr is not None and cr is not None and nr > cr: w.append('Risk per trade goes UP from %g%% to %g%%.' % (cr, nr))
    return w


# ---------------------------------------------------------------- undo snapshot
def _snap_key(sc): return 'sharecode_undo:' + ((sc or '') or 'owner')


def _keys(sc, bsc):
    ks = [p + (sc or '') for p in PERSON_KV if p != 'burst:'] + ['burst:' + (bsc or '')]
    if _owner(sc): ks += list(OWNER_GLOBALS)
    return list(dict.fromkeys(ks))


def _read_raw(sc, bsc):
    prev = {}
    for k in _keys(sc, bsc):
        r = st.q('SELECT v FROM kv WHERE k=?', (k,), True); prev[k] = r['v'] if r else None
    l = links.get(sc) if sc else None
    return {'kv': prev, 'has_link': bool(l), 'risk': (l or {}).get('risk')}


def _write_raw(sc, prev):
    for k, v in (prev.get('kv') or {}).items():
        if v is None: st.x('DELETE FROM kv WHERE k=?', (k,))
        else: st.put(k, v)
    if sc and links.get(sc): st.x('UPDATE links SET risk=? WHERE uid=?', (prev.get('risk'), sc))


def _snap(sc):
    try: j = json.loads(st.get(_snap_key(sc)) or 'null')
    except (TypeError, ValueError): j = None
    return j if isinstance(j, dict) and isinstance(j.get('prev'), dict) else None


# ---------------------------------------------------------------- public API
def status(sc, bsc=None):
    s = _snap(sc); own = _owner(sc)
    demo = True if own else (links.mode(sc) != 'real' and bk.mode(sc, 'Deriv') != 'real')
    return {'can_undo': bool(s), 'last': {'name': s.get('name', ''), 't': s.get('t', 0)} if s else None, 'owner': bool(own), 'demo': bool(demo)}


def make(sc, bsc=None, name=''):
    """-> {'code', 'rows': [{'label','value'}...]}  (rows are what the code holds, for the person to see before sharing)."""
    cur = collect(sc, bsc)
    rows = []
    for sec in ('pref', 'gcap', 'burst', 'cycle'):
        for k, v in cur[sec].items(): rows.append({'label': LABEL[sec].get(k, k), 'value': _fmt(k, v)})
    for k in userlim.ORDER: rows.append({'label': userlim.SPEC[k]['label'], 'value': _fmt(k, cur['lim'][k])})
    if cur.get('risk'): rows.append({'label': LABEL['risk']['risk_pct'], 'value': _fmt('risk_pct', cur['risk']['risk_pct'])})
    return {'code': encode(cur, name), 'rows': rows, 'count': len(rows)}


def check(sc, bsc, code):
    """What loading this code would do, saved nowhere. Raises ValueError (plain message) for a bad code."""
    pl = decode(code); new, notes = clean(pl, _owner(sc))
    if not new: raise ValueError('That code has no settings this server can use.')
    cur = collect(sc, bsc); rows, same = _rows(cur, new, _owner(sc))
    return {'name': _name(pl.get('n')), 'made': int(pl.get('t') or 0) if isinstance(pl.get('t'), (int, float)) and not isinstance(pl.get('t'), bool) else 0,
            'rows': rows, 'same': same, 'notes': notes, 'warnings': _warnings(cur, new)}


def load(sc, bsc, code):
    """Save the settings from the code for this person. Raises ValueError (nothing changed) when refused or a save fails. Returns check-style info + status."""
    pl = decode(code); own = _owner(sc)
    if not own and (links.mode(sc) == 'real' or bk.mode(sc, 'Deriv') == 'real'):
        raise ValueError('Load a friend\'s settings on a Demo account first. Switch to Demo, load the code, watch it work, then decide about Real.')
    new, notes = clean(pl, own)
    if not new: raise ValueError('That code has no settings this server can use.')
    cur = collect(sc, bsc); rows, same = _rows(cur, new, own); warn = _warnings(cur, new)
    old = _snap(sc); prev = old['prev'] if old else _read_raw(sc, bsc)          # a second load keeps the ORIGINAL values for undo
    snap = {'prev': prev, 'name': _name(pl.get('n')), 't': int(time.time())}
    st.put(_snap_key(sc), json.dumps(snap))
    try:
        if 'pref' in new: prefs.save(sc, new['pref'])
        if 'lim' in new: userlim.save(sc, new['lim'])
        if 'gcap' in new: groupcap.save(sc, new['gcap'])
        if 'burst' in new: burst.save(bsc, new['burst'])
        if 'cycle' in new: cycle.save(sc, new['cycle'])
        if 'risk' in new and not own and links.get(sc): links.set_risk(sc, new['risk']['risk_pct'])
        elif 'risk' in new and not own: notes.append('Make your MT5 key first (Connect tab), then load the code again to set the risk per trade.')
    except Exception:
        _write_raw(sc, prev)
        if old: st.put(_snap_key(sc), json.dumps(old))
        else: st.x('DELETE FROM kv WHERE k=?', (_snap_key(sc),))
        raise
    return {'name': snap['name'], 'rows': rows, 'same': same, 'notes': notes, 'warnings': warn, **status(sc, bsc)}


def undo(sc, bsc=None):
    s = _snap(sc)
    if not s: raise ValueError('There are no loaded settings to undo.')
    _write_raw(sc, s['prev'])
    st.x('DELETE FROM kv WHERE k=?', (_snap_key(sc),))
    return status(sc, bsc)
