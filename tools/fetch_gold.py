"""Downloads ~60 days of gold futures (GC=F) candles from Yahoo into XAUUSD_M15.csv and XAUUSD_H1.csv (UTC).
Futures prices differ slightly from your broker's spot XAUUSD, so use this for a rough check only."""
import json, urllib.request, datetime as dt
def get(interval, out):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval={interval}&range=60d'
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
    r = d['chart']['result'][0]; q = r['indicators']['quote'][0]; n = 0
    with open(out, 'w') as f:
        for i, t in enumerate(r['timestamp']):
            o, h, l, c = q['open'][i], q['high'][i], q['low'][i], q['close'][i]
            if None in (o, h, l, c): continue
            x = dt.datetime.fromtimestamp(t, dt.timezone.utc)
            f.write(f"{x:%Y.%m.%d},{x:%H:%M},{o},{h},{l},{c}\n"); n += 1
    print(out, n, 'candles')
get('15m', 'XAUUSD_M15.csv'); get('60m', 'XAUUSD_H1.csv')
