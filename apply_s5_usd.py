"""Section 5 (BTC plan): Auto settings get a profit target in USD per position (setting auto_target_usd, 0 = off, 0.1 to 1000).
 - backend/store.py: auto_target_usd in DEFAULTS (so the admin route can save it).
 - backend/automode.py: target_usd() (only while Auto mode is on) and mark(grp, uid, n): the setup goes to the EA as ONE basket (kv 'bg:<id>', kind 'multi')
   whose group target is USD x n. A single position is a group of one (grp = its own id; every counter already uses COALESCE(grp,id)).
 - backend/app.py: _scan_tf calls it after the signal is made (a person's OWN group target, when on, still wins); the group alert wording is right for a group of one;
   admin_set checks auto_target_usd 0 to 1000 before saving.
 - static/index.html: the Auto settings card gets a "USD target per position" box; the stop box is now called "Stop loss limit ATR".
The stop loss stays ATR based (the brain's 0.5 to max_stop_atr rule). The bot opens a new setup ONLY on a fresh signal on a new candle (lastbar guard): a closed target never reopens by itself.
Safe to run twice."""
import sys
def edit(path, old, new, marker):
    s = open(path, encoding='utf-8').read()
    if marker in s: print(path, ': already ok'); return
    if s.count(old) != 1: sys.exit('STOP: cannot find exactly once in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new)); print(path, ': edited')

edit('backend/store.py', "'plans': ''}", "'auto_target_usd': os.getenv('AUTO_TARGET_USD', '0'), 'plans': ''}", "'auto_target_usd'")

A = 'backend/automode.py'
edit(A, "from . import store as st\n", "import json, time\nfrom . import store as st\n", "import json, time")
edit(A, "def lock(off, solo, min_conf):", '''def target_usd():
    """Profit target in USD for EACH position (setting auto_target_usd). 0 = none (the normal take profit only). Only while Auto mode is on."""
    return round(_f('auto_target_usd', 0.0, 1000.0, 0.0), 4) if on() else 0.0

def mark(grp, uid, n, now=None):
    """Auto mode with a USD target: send this setup (n positions, group id = the first signal's id) to the EA as ONE basket that closes when the total reaches USD x n.
    A single position is a group of one. The normal stop loss and take profit stay on every position. Returns True when marked."""
    t = target_usd(); n = max(1, int(n or 1))
    if t <= 0: return False
    st.x('UPDATE signals SET grp=? WHERE id=? AND grp IS NULL', (int(grp), int(grp)))
    st.put('bg:%d' % int(grp), json.dumps({'k': 'multi', 'n': n, 'each': t, 'gb': 0, 'tgt': round(t * n, 4), 'loss': 0, 't': int(now or time.time())}))
    return True

def lock(off, solo, min_conf):''', "def target_usd")

P = 'backend/app.py'
edit(P, "    if n <= 1: stake.mark(sid, uid, s.get('score'), s.get('adx'))          # Section 1: bigger Deriv stake on strong setups\n",
        "    if n <= 1: stake.mark(sid, uid, s.get('score'), s.get('adx'))          # Section 1: bigger Deriv stake on strong setups\n    if n <= 1: automode.mark(sid, uid, 1)          # Section 5: Auto mode USD target on a single position (a group of one)\n", "automode.mark(sid, uid, 1)")
edit(P, "        groupcap.mark(sid, uid, n)          # group target / loss limit on: this setup goes to the EA as ONE basket\n",
        "        if not groupcap.mark(sid, uid, n): automode.mark(sid, uid, n)          # the person's own group target wins; else the Auto mode USD target (Section 5)\n", "automode.mark(sid, uid, n)")
edit(P, "body = body.replace('Burst ', 'Group ', 1)          # a normal group is not a burst",
        "body = body.replace('Burst ', 'Group ', 1)          # a normal group is not a burst\n            if bg and (burst.meta(bg) or {}).get('k') == 'multi' and int((burst.meta(bg) or {}).get('n') or 2) < 2: title = title.replace(' burst ', ' ').replace(' group ', ' '); body = body.replace('Group ', '', 1)          # a group of one reads as a plain trade", "a group of one reads")
edit(P, "('max_trades_day', 0, 100)):", "('max_trades_day', 0, 100), ('auto_target_usd', 0, 1000)):", "('auto_target_usd', 0, 1000)")

H = 'static/index.html'
s = open(H, encoding='utf-8').read()
if 'id="auUsd"' in s: print(H, ': already ok')
else:
    a = '<input class="inp" id="auPos" placeholder="Positions 1-5" inputmode="numeric" style="width:30%"></div>'
    b = '<input class="inp" id="auPos" placeholder="Positions 1-5" inputmode="numeric" style="width:30%"><input class="inp" id="auUsd" placeholder="USD target per position (0 = off)" inputmode="decimal" style="width:30%"></div>'
    if s.count(a) != 1: sys.exit('STOP: auto card inputs not found once')
    s = s.replace(a, b)
    for old, new in (('placeholder="Stop limit ATR"', 'placeholder="Stop loss limit ATR"'),
                     ('Stop limit: the widest stop allowed', 'Stop loss limit: the widest stop loss allowed'),
                     ('Positions: how many positions one trade opens (1 to 5); they share the same stop and target and split the trade amount between them.',
                      'Positions: how many positions one trade opens (1 to 5); they share the same stop and target and split the trade amount between them. USD target per position: the MT5 bridge closes the trade when its profit reaches this many dollars for each position (0 = off, the normal take profit only). With 3 positions and 2 dollars it closes all three when the total reaches 6. The stop loss stays in place. The bot opens a new trade only on a fresh signal, never straight after a close. Deriv and phone mode cannot close by dollars.')):
        if s.count(old) != 1: sys.exit('STOP: text not found once: ' + old[:50])
        s = s.replace(old, new)
    a = 'function auFill(j){$("#auOn").checked=j.auto_mode==="1";'
    if s.count(a) != 1: sys.exit('STOP: auFill not found once')
    s = s.replace(a, a + '$("#auUsd").value=j.auto_target_usd;')
    a = 'auto_positions:$("#auPos").value}'
    if s.count(a) != 1: sys.exit('STOP: auto save body not found once')
    s = s.replace(a, 'auto_positions:$("#auPos").value,auto_target_usd:$("#auUsd").value||"0"}')
    open(H, 'w', encoding='utf-8').write(s); print(H, ': edited')
print('done')
