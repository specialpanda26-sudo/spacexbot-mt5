"""Presets S3: minimum-lot check + the optional EA fields (vol_min, tick_value, tick_size per market).
Each old text must appear exactly once or NOTHING more is changed. Safe to run twice. Run from the repo folder."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:60]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')

P = 'backend/presets.py'; A = 'backend/app.py'; E = 'ea/SpaceXBridge.mq5'; T = 'tests/test_presets.py'

# 1) presets.py: imports
edit(P, 'import json, time\nfrom . import store as st, prefs, limits, groupcap, burst, links, brokers as bk\n',
     'import json, re, time\nfrom . import store as st, prefs, limits, groupcap, burst, links, brokers as bk, automode, bars, indicators\n', 'import json, re, time')

# 2) presets.py: clean_sym + min_lot
MINLOT = r'''

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
'''
edit(P, "\n\ndef apply(uid, tier):\n", MINLOT + "\n\ndef apply(uid, tier):\n", 'def min_lot(uid, tier)')
edit(P, "    tier = _tier(tier); _check_person(uid)\n    v = values(tier, uid)\n",
     "    tier = _tier(tier); _check_person(uid)\n    if min_lot(uid, tier)['blocked']: raise ValueError(WORDS)          # S3: no market could trade at this size, so say so now instead of skipping trades quietly\n    v = values(tier, uid)\n",
     "if min_lot(uid, tier)['blocked']")
edit(P, "            'not_included': NOT_INCLUDED, 'owner': bool(not uid or limits._owner(uid))}",
     "            'not_included': NOT_INCLUDED, 'owner': bool(not uid or limits._owner(uid)),\n            'minlot': {} if not uid or limits._owner(uid) else {str(k): min_lot(uid, k) for k in TIERS}}", "'minlot': {} if not uid")

# 3) app.py: keep the optional 'sym' facts (checked, size-limited) in the account snapshot; absent = nothing changes
edit(A, "bz = d.get('bars') if isinstance(d.get('bars'), dict) else {}\n    if who:\n        if not _paid(who)",
     "bz = d.get('bars') if isinstance(d.get('bars'), dict) else {}\n    sy = presets.clean_sym(a.get('sym'))          # S3: optional min-lot facts from a newer EA\n    if who:\n        if not _paid(who)", 'sy = presets.clean_sym')
edit(A, "    st.set_acct(a, who)\n    try:          # CY4", "    a.pop('sym', None)\n    if sy: a['sym'] = sy          # S3: only checked numbers are kept; an old EA sends none and nothing changes\n    st.set_acct(a, who)\n    try:          # CY4", "a.pop('sym', None)")
edit(A, "stake, envcheck\n", "stake, envcheck, presets\n", 'envcheck, presets')

# 4) EA: send the optional fields (a server that does not know them ignores them)
SYMJSON = r'''string SymJson()
{  // optional: the smallest lot, tick value and tick size of each market, so the server can warn BEFORE a group is refused for min lot
   string list[]; int n = StringSplit(Symbols, ',', list); string s = ""; int k = 0;
   for(int i = 0; i < n; i++)
   {
      StringTrimLeft(list[i]); StringTrimRight(list[i]);
      string sy = list[i] + SymbolSuffix;
      double mn = SymbolInfoDouble(sy, SYMBOL_VOLUME_MIN), tv = SymbolInfoDouble(sy, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(sy, SYMBOL_TRADE_TICK_SIZE);
      if(mn <= 0 || tv <= 0 || ts <= 0) continue;
      if(k++ > 0) s += ",";
      s += "\"" + list[i] + "\":{\"vol_min\":" + DoubleToString(mn, 4) + ",\"tick_value\":" + DoubleToString(tv, 8) + ",\"tick_size\":" + DoubleToString(ts, 8) + "}";
   }
   return (s == "") ? "" : ",\"sym\":{" + s + "}";
}
'''
edit(E, "void PollServer()\n{\n   string acct", SYMJSON + "void PollServer()\n{\n   string acct", 'string SymJson()')
edit(E, '(string)AccountInfoInteger(ACCOUNT_LOGIN) + "}";', '(string)AccountInfoInteger(ACCOUNT_LOGIN) + SymJson() + "}";', 'SymJson() + "}"')

# 5) tests
TESTS = r'''
# ---- S3: minimum-lot check ----
import time as _t
st.x("UPDATE users SET plan_until=? WHERE uid=?", (int(_t.time()) + 86400 * 30, A))
KEY = links.new_key(A); EH = {'X-EA-Key': KEY}
def candles(rng=2.0, n=40):
    t0 = int(_t.time()) - n * 900; return [[t0 + i * 900, 2000, 2000 + rng / 2, 2000 - rng / 2, 2000, 1] for i in range(n)]
GOLD = {'XAUUSD': {'vol_min': 0.01, 'tick_value': 1.0, 'tick_size': 0.01}}
def sync(bal, sym=None, bars=True):
    acct = {'balance': bal, 'equity': bal, 'open': 0, 'demo': True, 'allow_live': False, 'login': 1}
    if sym is not None: acct['sym'] = sym
    return c.post('/api/ea/sync', json={'account': acct, 'bars': {'XAUUSD': {'M15': candles()}} if bars else {}}, headers=EH)

T('clean_sym drops bad numbers, names and shapes', presets.clean_sym({'XAUUSD': {'vol_min': 0.01, 'tick_value': 1, 'tick_size': 0.01}, 'bad name': GOLD['XAUUSD'], 'X': {'vol_min': -1, 'tick_value': 1, 'tick_size': 1}, 'Y': {'vol_min': True, 'tick_value': 1, 'tick_size': 1}, 'Z': 5, 'W': {'vol_min': float('nan'), 'tick_value': 1, 'tick_size': 1}}).keys() == {'XAUUSD'})
T('clean_sym: not a dict gives nothing', presets.clean_sym(None) == {} and presets.clean_sym([1]) == {})
r = sync(1000)
a0 = st.acct(A)
T('OLD EA payload (no sym field): sync works exactly as before', r.status_code == 200 and 'sym' not in a0 and a0.get('balance') == 1000)
m = presets.min_lot(A, 20)
T('no min-lot facts: nothing is claimed, no warning, tap not blocked', m['known'] is False and not m['warn'] and not m['blocked'] and m['message'] == '')
presets.apply(A, 20); presets.undo(A)
T('new EA payload with sym is accepted and kept', sync(1000, GOLD).status_code == 200 and st.acct(A).get('sym') == GOLD)
T('garbage sym is dropped, the rest of the sync still works', sync(1000, {'XAUUSD': {'vol_min': 'x'}, 'q': 1}).status_code == 200 and 'sym' not in st.acct(A) and st.acct(A).get('balance') == 1000)
sync(1000, GOLD)
m = presets.min_lot(A, 20); row = m['rows'][0]
T('worst case = min lot x (3.5 ATR / tick size) x tick value (gold, range 2 -> 7 dollars)', abs(row['worst_usd'] - 7.0) < 0.2 and abs(row['best_usd'] - 1.0) < 0.1 and row['min_lot'] == 0.01)
T('1000 balance: limit 10 dollars, no warning', m['known'] and m['risk_usd'] == 10.0 and not m['warn'] and m['message'] == '')
sync(100, GOLD); m = presets.min_lot(A, 20)
T('100 balance: limit 1 dollar, worst case 7 -> the plain warning shows, but the tap is allowed (some setups still fit)', m['warn'] and m['message'] == presets.WORDS and not m['blocked'] and presets.status(A)['minlot']['20']['warn'])
sync(50, GOLD); b4 = raw(A)
T('50 balance: even the smallest stop is too big -> blocked with the plain message', presets.min_lot(A, 20)['blocked'] and 'cent account or a demo' in presets.WORDS)
try: presets.apply(A, 20); ok = False
except ValueError as e: ok = str(e) == presets.WORDS
T('blocked tap is refused with that message and NOTHING changes', ok and raw(A) == b4 and presets._snap(A) is None)
sync(1000, GOLD)
T('balance grows: the check clears and the tap works again', presets.apply(A, 20)['active'] == 20); presets.undo(A)
from backend import bars as _bars
_bars.merge('EURUSD', 'M15', candles(), uid=A); st.set_acct({'balance': 1000, 'equity': 1000, 'open': 0, 'demo': True, 'sym': dict(GOLD, EURUSD={'vol_min': 1.0, 'tick_value': 1.0, 'tick_size': 0.00001})}, A)
T('min-lot check only looks at markets the owner allows (EURUSD is not in Symbols, so it is ignored)', [x['symbol'] for x in presets.min_lot(A, 20)['rows']] == ['XAUUSD'])
'''
edit(T, "\nn = len(R); bad = [x for x, ok in R if not ok]", TESTS + "\nn = len(R); bad = [x for x, ok in R if not ok]", 'S3: minimum-lot check')
