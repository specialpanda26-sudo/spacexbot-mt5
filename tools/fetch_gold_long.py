"""Downloads ~2 years of HOURLY gold futures (GC=F) candles from Yahoo into XAUUSD_1H_long.csv (UTC).
Futures differ slightly from broker spot XAUUSD, so use for a rough check only."""
import json, urllib.request, datetime as dt
url = 'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=60m&range=730d'
d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
r = d['chart']['result'][0]; q = r['indicators']['quote'][0]; n = 0
with open('XAUUSD_1H_long.csv', 'w') as f:
    for i, t in enumerate(r['timestamp']):
        o, h, l, c = q['open'][i], q['high'][i], q['low'][i], q['close'][i]
        if None in (o, h, l, c): continue
        x = dt.datetime.fromtimestamp(t, dt.timezone.utc)
        f.write(f"{x:%Y.%m.%d},{x:%H:%M},{o},{h},{l},{c}\n"); n += 1
print('XAUUSD_1H_long.csv', n, 'candles')
