"""Walk-forward test of the SAME strategies on MT5-exported candles.
Export in MT5: View > Symbols > Bars (M15) > Export. Then:
  python tools/backtest.py XAUUSD_M15.csv [XAUUSD_H1.csv]
Flags: --solo (each strategy alone)   --trail (ATR trailing-stop exit instead of the fixed 2R target, default 2.0 x ATR)   --trail=3 (3.0 x ATR)
CSV columns (tab/comma): date time open high low close [tickvol vol spread]. Prints win rate, expectancy, drawdown."""
import sys, csv, datetime as dt
sys.path.insert(0, '.')
from backend.brain import evaluate
from backend.indicators import atr
from backend.trail_exit import trail_exit

FMT = ['%Y.%m.%d %H:%M:%S', '%Y.%m.%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
def _t(s):
    for f in FMT:
        try: return dt.datetime.strptime(s, f)
        except ValueError: pass
    raise ValueError(s)

def load(path):
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        text = f.read()
    delim = '\t' if '\t' in text.splitlines()[0] else ','
    for r in csv.reader(text.splitlines(), delimiter=delim):
        try:
            if ':' in r[1]: t = _t(r[0] + ' ' + r[1]); o, h, l, c = map(float, r[2:6])   # MT5: date, time, o,h,l,c,...
            else: t = _t(r[0]); o, h, l, c = map(float, r[1:5])
        except Exception: continue                                                       # header / bad row
        rows.append({'t': int(t.replace(tzinfo=dt.timezone.utc).timestamp()), 'o': o, 'h': h, 'l': l, 'c': c, 'v': 0})
    return rows

def run(m15, h1=None, min_conf=2, rr=2.0, risk=1.0, cooldown=4, off=(), trail=0.0):
    """trail=0 keeps the fixed target (old behaviour). trail=2.0 exits with an ATR trailing stop of 2.0 x ATR instead (section 3D)."""
    eq, peak, mdd, trades, i, n = 100.0, 100.0, 0.0, [], 300, len(m15)
    while i < n - 1:
        w = m15[max(0, i - 400): i + 1]
        hh = [x for x in (h1 or []) if x['t'] <= m15[i]['t']][-300:]
        s = evaluate(w, hh, min_conf, rr, off)
        if not s: i += 1; continue
        side, sl, tp = s['side'], s['sl'], s['tp']; res = None
        if trail:
            out = trail_exit(side, s['entry'], sl, m15[i + 1: i + 201], atr(w)[-1], trail)
            if out is None: i += 1; continue
            res, used = out; j = i + used
        else:
            for j in range(i + 1, min(i + 200, n)):
                b = m15[j]
                hit_sl = b['l'] <= sl if side == 'buy' else b['h'] >= sl
                hit_tp = b['h'] >= tp if side == 'buy' else b['l'] <= tp
                if hit_sl: res = -1.0; break            # SL first when both hit (pessimistic)
                if hit_tp: res = abs(tp - s['entry']) / abs(s['entry'] - sl); break
            if res is None: i += 1; continue
        eq *= 1 + risk / 100 * res; peak = max(peak, eq); mdd = max(mdd, (peak - eq) / peak * 100)
        trades.append(res); i = j + cooldown
    w = sum(1 for x in trades if x > 0)
    return trades
    print(f'trades {len(trades)}  win% {100*w/max(1,len(trades)):.1f}  avgR {sum(trades)/max(1,len(trades)):+.2f}  equity {eq:.1f}  maxDD {mdd:.1f}%')

def trail_arg(argv):
    """--trail -> 2.0, --trail=3 -> 3.0, absent -> 0.0 (fixed target)."""
    for a in argv:
        if a == '--trail': return 2.0
        if a.startswith('--trail='):
            try: v = float(a.split('=', 1)[1])
            except ValueError: raise SystemExit('Use --trail or --trail=3 (a number of ATRs)')
            if v <= 0: raise SystemExit('--trail needs a number above 0')
            return v
    return 0.0

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]; m = load(args[0]); h = load(args[1]) if len(args) > 1 else None
    tr = trail_arg(sys.argv)
    print('Exit: ' + (f'ATR trailing stop {tr} x ATR' if tr else 'fixed 2R target'))
    def show(label, t):
        w = sum(1 for x in t if x > 0); n = max(1, len(t)); print(f'{label:<22} trades {len(t):>4}  win% {100*w/n:5.1f}  avgR {sum(t)/n:+.2f}')
    if '--solo' in sys.argv:        # each strategy alone: which ones have an edge on YOUR data?
        from backend.strategies import ALL
        names = [f.__name__ for f in ALL]
        for nme in names: show(nme, run(m, h, 1, 2.0, off=set(names) - {nme}, trail=tr))
    else:
        for mc in (1, 2, 3): show(f'min_confluence {mc}', run(m, h, mc, trail=tr))
    print('Note: this ignores the news lock, currency-exposure cap and loss limits, so live results will differ.')
