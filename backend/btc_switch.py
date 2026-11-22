"""Bitcoin switch (Section B1, owner request Nov 22): one switch that puts BTCUSD in the markets list, so the bot can trade it at the weekend
while gold and forex rest (risk.py already lets a listed BTC market through the weekend rule, Section W9).
 - set_on(True): adds BTCUSD to the Symbols setting (unless a BTC spelling is already there), turns the weekend exemption on (crypto_weekend = 1)
   and sets the mode: 'weekend' = Bitcoin is scanned only from Friday 20:00 UTC to Sunday night (gold and forex trade on weekdays),
   'always' = Bitcoin is scanned every day like any other market.
 - set_on(False): takes every Bitcoin spelling out of Symbols. Nothing else is touched.
Nothing here claims Bitcoin trades well: the strategies were built around gold and are not tested on Bitcoin. Use a demo account first."""
from . import store as st, risk

BTC = 'BTCUSD'

def _list(): return [x.strip() for x in (st.get('symbols') or '').split(',') if x.strip()]

def mode(): return 'weekend' if st.get('btc_mode') == 'weekend' else 'always'

def status(now=None):
    listed = [x for x in _list() if risk.is_crypto(x)]
    return {'on': bool(listed) and st.get('crypto_weekend') != '0', 'listed': listed, 'mode': mode(), 'weekend_now': risk.weekend_shut(now), 'symbols': st.get('symbols')}

def set_on(on, weekend_only=True):
    syms = _list()
    if on:
        if not any(risk.is_crypto(x) for x in syms): syms.append(BTC)
        st.put('crypto_weekend', '1'); st.put('btc_mode', 'weekend' if weekend_only else 'always')
    else:
        syms = [x for x in syms if not risk.is_crypto(x)]
        if not syms: syms = [x for x in str(st.DEFAULTS.get('symbols') or 'XAUUSD').split(',') if x.strip() and not risk.is_crypto(x)] or ['XAUUSD']
    st.put('symbols', ','.join(syms))
    return status()
