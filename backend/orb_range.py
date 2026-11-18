"""Video 4 (Trade with Pat, 9:30 opening range breakout) - SECTION 4A: the New York open range and the displacement break.
Rules from the video: trade the NEW YORK session only | the range is the first 15-MINUTE candle of the New York Stock Exchange open (9:30-9:45 New York
time); its high and low are the trading range for the session | then watch the 5-minute chart for an IMPULSIVE move out of the top or the bottom of the
range, with big candles that create displacement | the candle must CLOSE outside the range: a candle that only wicks out does not count | no big strong
candles = it does not count | a valid push is THREE OR FOUR big same-direction candles in a row that break recent structure (price takes out the recent high / low).
This file only FINDS the range and the displacement. It fires no trade (the demand zone / fair value gap and the entry are section 4B), so it is not
registered in strategies.py. Works on 15-minute or 5-minute candles (any step that divides 15 minutes); a 1-hour chart gives None.
New York time is real New York time: 9:30 is 13:30 UTC in summer (daylight saving) and 14:30 UTC in winter. The video's indicator uses a fixed UTC-5, which
is wrong in summer; here daylight saving is handled. zoneinfo is used when the machine has it; if not, the US daylight-saving rule is used instead.
Candle 't' is the candle OPEN time in epoch seconds (UTC). The video gives no numbers for 'big': the tunables below are my assumptions."""
import calendar
from datetime import datetime, timedelta, timezone
from .indicators import atr

RANGE_H, RANGE_M = 9, 30        # the range candle opens at 9:30 New York time
RANGE_SEC = 900                 # ...and lasts 15 minutes
END_H, END_M = 16, 0            # assumption: displacement is only looked for until 16:00 New York time (the video says only 'New York session')
DISP_MIN = 3                    # video: three or four big same-direction candles in a row
BODY_ATR = 0.5                  # assumption: a 'big' candle has a body of at least this many ATR (ATR of the candles before it)
MIN_BARS = 20                   # candles needed on the chart (ATR warm-up)

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo('America/New_York')
    datetime.fromtimestamp(0, _TZ)
except Exception:
    _TZ = None

def _nth_sunday(year, month, n):
    d = datetime(year, month, 1)
    first = 1 + (6 - d.weekday()) % 7
    return datetime(year, month, first + 7 * (n - 1))

def _ny_local_rule(t):
    """New York local time from the US daylight-saving rule (2nd Sunday of March 02:00 to 1st Sunday of November 02:00). Used when zoneinfo is missing."""
    u = datetime.fromtimestamp(t, timezone.utc).replace(tzinfo=None)
    s = _nth_sunday(u.year, 3, 2) + timedelta(hours=7)        # 02:00 EST = 07:00 UTC
    e = _nth_sunday(u.year, 11, 1) + timedelta(hours=6)       # 02:00 EDT = 06:00 UTC
    return u - timedelta(hours=4 if s <= u < e else 5)

def ny_local(t):
    """Naive datetime of epoch second t in New York local time."""
    if _TZ is None: return _ny_local_rule(t)
    return datetime.fromtimestamp(t, _TZ).replace(tzinfo=None)

def ny_epoch(day, h, m=0):
    """Epoch second of h:m New York time on the New York date 'day' (a date)."""
    loc = datetime(day.year, day.month, day.day, h, m)
    base = calendar.timegm(loc.timetuple())
    for off in (4, 5):
        if ny_local(base + off * 3600) == loc: return base + off * 3600
    return base + 5 * 3600

def opening_range(c):
    """The range of the New York date of the LAST candle: {'hi','lo','mid','t0','t1','date'}. None when the range is not finished yet (9:45 not reached),
    when a candle of the 9:30-9:45 window is missing, on a Saturday or Sunday, or when the chart is above 15 minutes."""
    if len(c) < 2: return None
    step = c[-1]['t'] - c[-2]['t']
    if step <= 0 or step > RANGE_SEC or RANGE_SEC % step: return None
    d = ny_local(c[-1]['t']).date()
    if d.weekday() >= 5: return None                     # the exchange is shut on Saturday and Sunday (holidays are not handled)
    t0 = ny_epoch(d, RANGE_H, RANGE_M); t1 = t0 + RANGE_SEC
    if c[-1]['t'] < t1: return None
    w = [x for x in c if t0 <= x['t'] < t1]
    if len(w) != RANGE_SEC // step: return None
    hi = max(x['h'] for x in w); lo = min(x['l'] for x in w)
    return {'hi': hi, 'lo': lo, 'mid': (hi + lo) / 2.0, 't0': t0, 't1': t1, 'date': str(d)}

def displacement(c, r):
    """The first displacement break after the range r (from opening_range) and before the session end. None when there is none.
    Up: DISP_MIN or more candles in a row, each green with a body of at least BODY_ATR x ATR, and the highest CLOSE of the run is above the break level =
    the range high or the highest high (wicks included) seen since the range ended, whichever is higher. Down is the mirror image.
    Returns {'side': 'buy'|'sell', 'start', 'end' (candle indexes of the run; 'end' grows while the run goes on), 'n', 'level', 't_start', 't_end'}."""
    if not r or len(c) < MIN_BARS: return None
    day = datetime.strptime(r['date'], '%Y-%m-%d').date()
    stop = ny_epoch(day, END_H, END_M)
    ix = [i for i, x in enumerate(c) if r['t1'] <= x['t'] < stop]
    if len(ix) < DISP_MIN: return None
    a = atr(c)
    def big(i, up):
        x = c[i]; body = x['c'] - x['o'] if up else x['o'] - x['c']
        return i > 0 and body >= BODY_ATR * a[i - 1]
    for p, i in enumerate(ix):
        for up in (True, False):
            j = p
            while j < len(ix) and ix[j] == i + (j - p) and big(ix[j], up): j += 1
            n = j - p
            if n < DISP_MIN: continue
            before = [c[k] for k in ix[:p]]
            run = [c[k] for k in ix[p:j]]
            if up:
                lvl = max([r['hi']] + [x['h'] for x in before])
                ok = max(x['c'] for x in run) > lvl
            else:
                lvl = min([r['lo']] + [x['l'] for x in before])
                ok = min(x['c'] for x in run) < lvl
            if ok:
                return {'side': 'buy' if up else 'sell', 'start': i, 'end': ix[j - 1], 'n': n, 'level': lvl, 't_start': c[i]['t'], 't_end': c[ix[j - 1]]['t']}
    return None

def scan(c):
    """Range + displacement together. None = no finished range today (or not enough data). Else {'range': {...}, 'disp': {...} or None}."""
    r = opening_range(c)
    if r is None: return None
    return {'range': r, 'disp': displacement(c, r)}
