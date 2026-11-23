import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if new in s: print('already done:', path, old[:40]); return
    if old not in s: sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
B = 'backend/burst.py'
sub(B, "def view(uid='', now=None):\n    return {'settings': get(uid),",
'''def minlot(uid=''):
    """LOT3: {known, warn, message}. Words only."""
    out = {'known': False, 'warn': False, 'message': ''}
    try:
        from . import presets, bars, indicators
        a = st.acct(uid) or {}; bal = _balance(uid); sym = presets.clean_sym(a.get('sym'))
        if bal <= 0 or not sym: return out
        p = get(uid); n = max(2, p['quick_n']); base = links.risk(uid) if uid else st.fget('risk_pct'); total = bal * float(base) / 100.0
        mine = {x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()}; wide = automode.max_stop(); lines = []
        for name, f in sym.items():
            if mine and name not in mine: continue
            b = bars.get(name, 'M15', uid)
            if len(b) < 15: continue
            r = indicators.atr(b)[-1]
            if not r > 0: continue
            one = f['vol_min'] * (r * wide / f['tick_size']) * f['tick_value']
            if p['lot'] > 0:
                lot = max(p['lot'], f['vol_min']); each = one * lot / f['vol_min']
                lines.append('%s: %g lot each risks up to about $%.2f per entry, $%.2f for %d entries.%s' % (name, lot, each, each * n, n, ' (Your lot is under the broker minimum, so %g is used.)' % f['vol_min'] if p['lot'] < f['vol_min'] - 1e-12 else ''))
            elif one * n > total:
                fit = int(total // one) if one > 0 else n
                lines.append('%s: the smallest lot (%g) risks up to about $%.2f each, but your risk of $%.2f is shared by %d entries, so only %d would open. Raise Risk %%, or set Lot per entry, or use fewer entries.' % (name, f['vol_min'], one, total, n, max(fit, 0)))
        if not lines: return out
        out.update(known=True, warn=True, message=' '.join(lines[:3]))
    except Exception as e: print('[burst] minlot failed', repr(e)[:80])
    return out


def view(uid='', now=None):
    return {'minlot': minlot(uid), 'settings': get(uid),''')
H = 'static/index.html'
sub(H, '<p class="note" id="bswPrev">', '<p class="note" id="bswLotWarn" role="status"></p><p class="note" id="bswPrev">')
sub(H, 'function bswShow(j){var s=j.settings||{};', 'function bswShow(j){var s=j.settings||{};var ml=j.minlot||{};$("#bswLotWarn").textContent=ml.message||"";')
print('LOT3 done')
