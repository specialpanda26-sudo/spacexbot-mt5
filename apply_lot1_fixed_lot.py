import sys
def sub(path, old, new):
    s = open(path, encoding='utf-8').read()
    if old not in s:
        if new in s: print('already done:', path, old[:40]); return
        sys.exit('NOT FOUND in %s: %s' % (path, old[:70]))
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1)); print('patched', path)
B = 'backend/burst.py'
sub(B, "'loss_usd': round(_clamp(j.get('loss_usd'), 0, USD_HI, 0.0, float), 2),",
       "'loss_usd': round(_clamp(j.get('loss_usd'), 0, USD_HI, 0.0, float), 2), 'lot': round(_clamp(j.get('lot'), 0, 100.0, 0.0, float), 2),          # LOT1\n            ")
sub(B, "    cur.update(new)\n",
       "    if 'lot' in d:          # LOT1: lots for each burst entry on MT5 (0 = automatic)\n        try: tv = float('nan') if isinstance(d['lot'], bool) else float(d['lot'])\n        except (TypeError, ValueError): tv = float('nan')\n        if tv != tv or not (tv == 0 or 0.01 <= tv <= 100): raise ValueError('Lot per entry must be 0 (automatic) or from 0.01 to 100')\n        new['lot'] = round(tv, 2)\n    cur.update(new)\n")
sub(B, "gm = {'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now, 'stake': pl.get('stake', 0)}",
       "gm = {'k': pl['kind'], 'n': n, 'each': pl['each'], 'gb': pl['giveback'], 't': now, 'stake': pl.get('stake', 0), 'lot': get(uid)['lot']}")
sub(B, "'tgt': float(m.get('tgt') or 0), 'loss': float(m.get('loss') or 0), 'kind': m.get('k'),",
       "'tgt': float(m.get('tgt') or 0), 'loss': float(m.get('loss') or 0), 'lot': float(m.get('lot') or 0), 'kind': m.get('k'),")
D = 'desktop/basket.py'
sub(D, "    lots = math.floor(raw / step + 1e-9) * step; want = n\n",
       "    try: fl = float(bk.get('lot') or 0)          # LOT1: the person chose the lot of each entry\n    except (TypeError, ValueError): fl = 0.0\n    if fl > 0: raw = max(fl, i['vol_min'])\n    lots = math.floor(raw / step + 1e-9) * step; want = n\n")
H = 'static/index.html'
sub(H, 'Stake per entry ($, Deriv needs 1 or more)', 'Stake per entry ($) - Deriv only, needs 1 or more')
sub(H, '<input class="inp" id="bswStake" type="number" min="0" step="0.05" inputmode="decimal" placeholder="0.5"></div>',
       '<input class="inp" id="bswStake" type="number" min="0" step="0.05" inputmode="decimal" placeholder="0.5"></div><div class="field"><label for="bswLot">Lot per entry - FBS / MT5 only (empty = automatic)</label><input class="inp" id="bswLot" type="number" min="0" step="0.01" inputmode="decimal" placeholder="0.01"></div>')
sub(H, '$("#bswLoss").value=s.loss_usd>0?s.loss_usd:"";', '$("#bswLoss").value=s.loss_usd>0?s.loss_usd:"";$("#bswLot").value=s.lot>0?s.lot:"";')
sub(H, 'var ls=$("#bswLoss").value.trim();', 'var lt=$("#bswLot").value.trim();body.lot=lt===""?0:parseFloat(lt);var ls=$("#bswLoss").value.trim();')
sub('tests/test_burst1.py', "'minute_n': 2, 'loss_usd': 0.0})", "'minute_n': 2, 'loss_usd': 0.0, 'lot': 0.0})")
print('LOT1 done')
