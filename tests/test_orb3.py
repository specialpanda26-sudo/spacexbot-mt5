"""Tests for backend/orb_session.py (video 4, section 4C: Asia range, London sweep, New York bias). Run: python tests/test_orb3.py
Chart is synthetic, 15-minute candles on Wednesday 2026-07-15 (UTC). Asia 00:00-07:00 builds the range 99.6 - 100.6. London 07:00-12:00 is quiet unless a test
sweeps the high (wick to 100.9) and/or the low (wick to 99.3). Then the 9:30 New York range and a push up with an order-block entry (the same shape as tests/test_orb2.py)."""
import os, sys, calendar
HERE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(HERE, 'orb3_test.db')
os.environ.update(DEV_AUTH='1', EA_KEY='k', ADMIN_EMAILS='boss@x.com', DB_PATH=DB, BASE_URL='http://t')
if os.path.exists(DB): os.remove(DB)
sys.path.insert(0, os.path.join(HERE, '..'))
from backend.app import app
from backend import alerts; alerts.stop()          # the app starts its alert loop at import (see HANDOFF N6e)
from backend import store as st
import backend.orb_session as osn
import backend.strategies as S
import backend.strategy_info as SI
from backend.orb_session import analyse, with_session, orb_session
from backend.orb_entry import orb_entry, entry

R = []
def T(name, ok): R.append((name, bool(ok)))
def utc(y, mo, d, h, mi): return calendar.timegm((y, mo, d, h, mi, 0))
D0 = utc(2026, 7, 15, 0, 0)                          # Wednesday 00:00 UTC
SUMMER = utc(2026, 7, 15, 13, 30)                    # 9:30 New York

def bar(t, o, c, w=0.1, hi=None, lo=None):
    return {'t': t, 'o': o, 'h': hi if hi is not None else max(o, c) + w, 'l': lo if lo is not None else min(o, c) - w, 'c': c, 'v': 1}
def quiet(t, k): return bar(t, 100.0, 100.3) if k % 2 == 0 else bar(t, 100.3, 100.0)
def mirror(c): return [{'t': x['t'], 'o': 200 - x['o'], 'h': 200 - x['l'], 'l': 200 - x['h'], 'c': 200 - x['c'], 'v': 1} for x in c]
def shift(c, secs): return [dict(x, t=x['t'] + secs) for x in c]

def asia_london(sh=False, sl=False, net=0, sh_k=4, sh_hi=100.9, sl_k=8):
    out = []
    for k in range(28):                                  # Asia 00:00-07:00: range 99.6 - 100.6 (a spike up at k=10, a spike down at k=20)
        t = D0 + k * 900
        out.append(bar(t, 100.1, 100.3, hi=100.6) if k == 10 else bar(t, 100.2, 100.0, lo=99.6) if k == 20 else quiet(t, k))
    for k in range(20):                                  # London 07:00-12:00
        t = D0 + 7 * 3600 + k * 900; b = quiet(t, k)
        if k == sh_k and sh: b = bar(t, 100.1, 100.3, hi=sh_hi)
        if k == sl_k and sl: b = bar(t, 100.2, 100.0, lo=99.3)
        if k == 19 and net: b = bar(t, 100.0, 100.0 + 0.35 * net)     # the London close against the London open: up (+1) or down (-1)
        out.append(b)
    return out
def ny(post, rng=((100.2, 100.7),), pre_n=6, step=900):
    out = []
    for k in range(pre_n):
        o = 100.0 if k % 2 == 0 else 100.3; c = 100.3 if k % 2 == 0 else 100.0
        out.append(bar(SUMMER - (pre_n - k) * step, o, c))
    t = SUMMER
    for p in rng: out.append(bar(t, p[0], p[1], 0.3)); t += step
    for p in post: out.append(bar(t, p[0], p[1], hi=p[2] if len(p) > 2 else None, lo=p[3] if len(p) > 3 else None)); t += step
    return out
PUSH = [(100.7, 100.3), (100.3, 101.3, 101.4, 100.2), (101.3, 102.3, 102.4, 100.9), (102.3, 103.3, 103.4, 101.3), (103.3, 102.0), (102.0, 101.0), (101.0, 100.6)]
GO = (100.5, 100.95)
def day(**kw): return asia_london(**kw) + ny(PUSH + [GO])            # a full day that ends on the ORB entry candle (a BUY)
def pre_ny(**kw): return asia_london(**kw) + ny([])                  # same day, no ORB setup

# ---------------------------------------------------------------- the ORB scenario itself is a valid BUY (the tests below rely on it)
c0 = day()
T('setup: the plain day gives an ORB buy', entry(c0) and entry(c0)['side'] == 'buy' and orb_entry(c0, []) is not None)

# ---------------------------------------------------------------- Asia range
r = analyse(day(sh=True))
T('asia: the range is the high and low of the 00:00-07:00 UTC candles', r and r['asia'] == (99.6, 100.6))
T('asia: the date is the UTC day of the last candle', r and r['date'] == '2026-07-15')
yest = [bar(D0 - 900, 100.0, 100.0, hi=105.0, lo=95.0)] + day(sh=True)
T('asia: yesterday\'s candles are not in the range', analyse(yest) and analyse(yest)['asia'] == (99.6, 100.6))
r7 = analyse(day(sh=True, sh_k=0))                   # the sweep candle opens at 07:00 sharp: it belongs to London, not to Asia
T('asia: the 07:00 candle is London (its high does not widen the range, it is the sweep)', r7 and r7['asia'] == (99.6, 100.6) and r7['swept_high'] is True)
asia_hi_late = asia_london(); asia_hi_late[27] = bar(D0 + 27 * 900, 100.1, 100.3, hi=100.6)       # the 06:45 candle is still Asia
T('asia: the 06:45 candle is still Asia', analyse(asia_hi_late + ny(PUSH + [GO]))['asia'][1] == 100.6)

# ---------------------------------------------------------------- the sweep and the bias
T('bias: no sweep = no opinion', analyse(c0) and analyse(c0)['bias'] is None and analyse(c0)['kind'] is None and not analyse(c0)['swept_high'] and not analyse(c0)['swept_low'])
a = analyse(day(sh=True))
T('bias: London swept the Asia HIGH = New York reverses = SELL', a['swept_high'] and not a['swept_low'] and a['kind'] == 'reversal' and a['bias'] == 'sell')
a = analyse(day(sl=True))
T('bias: London swept the Asia LOW = New York reverses = BUY', a['swept_low'] and not a['swept_high'] and a['kind'] == 'reversal' and a['bias'] == 'buy')
a = analyse(day(sh=True, sl=True, net=1))
T('bias: both sides swept and London closed UP = continuation = BUY', a['swept_high'] and a['swept_low'] and a['london_dir'] == 'up' and a['kind'] == 'continuation' and a['bias'] == 'buy')
a = analyse(day(sh=True, sl=True, net=-1))
T('bias: both sides swept and London closed DOWN = continuation = SELL', a['london_dir'] == 'down' and a['kind'] == 'continuation' and a['bias'] == 'sell')
a = analyse(day(sh=True, sl=True))
T('bias: both sides swept and London went nowhere = no opinion', a['swept_high'] and a['swept_low'] and a['london_dir'] is None and a['bias'] is None and a['kind'] is None)
T('bias: a single sweep ignores the London close direction (high swept, London closed up: still SELL)', analyse(day(sh=True, net=1))['bias'] == 'sell')
T('bias: a single sweep ignores the London close direction (low swept, London closed down: still BUY)', analyse(day(sl=True, net=-1))['bias'] == 'buy')
T('sweep: a wick that stays inside the margin (100.64, margin 0.05 above 100.6) is no sweep', analyse(day(sh=True, sh_hi=100.64))['swept_high'] is False)
T('sweep: a wick that just touches the Asia high is no sweep', analyse(day(sh=True, sh_hi=100.6))['swept_high'] is False)
T('sweep: a wick clearly beyond the margin (100.7) is a sweep', analyse(day(sh=True, sh_hi=100.7))['swept_high'] is True)
ax = asia_london(); ax.append(bar(D0 + 12 * 3600, 100.1, 100.3, hi=100.9)); cx = ax + ny([])[1:]     # the 12:00 candle (after London) pokes above the Asia high
cxm = mirror(cx); T('sweep: a poke below the Asia low at 12:00 does not count either', analyse(cxm) and analyse(cxm)['swept_low'] is False and analyse(cxm)['bias'] is None)
T('sweep: a poke at 12:00 is after London and does not count', analyse(cx) and analyse(cx)['swept_high'] is False and analyse(cx)['bias'] is None)
mi = asia_london(); mi[3] = bar(D0 + 3 * 900, 100.1, 100.3, hi=101.5); T('sweep: a spike during Asia just widens the Asia range (high 101.5), London no longer sweeps it', analyse(mi + ny(PUSH + [GO]))['asia'][1] == 101.5 and analyse(mi + ny(PUSH + [GO]))['swept_high'] is False)
T('sweep: the lowest wick beyond the Asia low sweeps it (the mirror)', analyse(mirror(day(sh=True)))['swept_low'] is True and analyse(mirror(day(sh=True)))['bias'] == 'buy')
T('sweep: both sides mirrored keep their meaning (up becomes down)', analyse(mirror(day(sh=True, sl=True, net=1)))['bias'] == 'sell')
vol = asia_london(sh=True, sh_hi=100.7) + ny([(100.0, 106.0, 107.0, 99.0), (106.0, 100.0, 107.0, 99.0)] * 8)     # wild candles after the sweep
T('sweep: the ATR is read at the end of Asia, so wild candles later never remove a sweep', analyse(vol)['swept_high'] is True and analyse(vol)['bias'] == 'sell')
T('sweep: the same day gives the same answer on every later candle', analyse(day(sh=True)[:-3]) == analyse(day(sh=True)) and analyse(day(sh=True)[:-3]) is not None)

# ---------------------------------------------------------------- when there is no opinion at all
T('timing: before London is over there is no read (last candle 11:45 UTC)', analyse([x for x in pre_ny(sh=True) if x['t'] < D0 + 12 * 3600]) is None)
T('timing: the first candle at 12:00 UTC makes the read available', analyse([x for x in pre_ny(sh=True) if x['t'] <= D0 + 12 * 3600]) is not None)
T('timing: a Saturday gives no read', analyse(shift(day(sh=True), 3 * 86400)) is None)
T('timing: a Sunday gives no read', analyse(shift(day(sh=True), 4 * 86400)) is None)
T('timing: a Friday does', analyse(shift(day(sh=True), 2 * 86400)) is not None)
T('timing: a Monday does', analyse(shift(day(sh=True), 5 * 86400)) is not None)
cd = day(sh=True)
T('data: a few missing Asia candles are fine (5 of 28 gone)', analyse([x for i, x in enumerate(cd) if not (2 <= i < 7)]) is not None)
T('data: too many Asia candles missing gives nothing (10 of 28 gone)', analyse([x for i, x in enumerate(cd) if not (2 <= i < 12)]) is None)
T('data: a few missing London candles are fine (3 of 20 gone)', analyse([x for i, x in enumerate(cd) if not (30 <= i < 33)]) is not None)
T('data: too many London candles missing gives nothing (5 of 20 gone)', analyse([x for i, x in enumerate(cd) if not (30 <= i < 35)]) is None)
T('data: a 1-hour chart gives nothing', analyse([{'t': D0 + k * 3600, 'o': 100.0, 'h': 100.5, 'l': 99.5, 'c': 100.2, 'v': 1} for k in range(40)]) is None)
T('data: fewer than 30 candles, or none, gives nothing', analyse(cd[:20]) is None and analyse([]) is None)
T('data: a chart with no movement at all (ATR 0) gives nothing', analyse([{'t': D0 + k * 900, 'o': 100.0, 'h': 100.0, 'l': 100.0, 'c': 100.0, 'v': 1} for k in range(60)]) is None)
five = []
for x in asia_london(sh=True):
    for j in range(3): five.append(dict(x, t=x['t'] + j * 300))
five += ny([], rng=((100.2, 100.8), (100.8, 100.4), (100.4, 100.7)), pre_n=18, step=300)
T('data: a 5-minute chart gives the same Asia range', analyse(five) is not None and analyse(five)['asia'] == (99.6, 100.6))

# ---------------------------------------------------------------- the filter wrapper
def fb(m, h): return {'side': 'buy', 'sl': 99.0, 'tp': 105.0, 'name': 'fake'}
def fs(m, h): return {'side': 'sell', 'sl': 101.0, 'name': 'fake'}
def fn(m, h): return None
T('filter: a buy is kept when the bias is buy, with its numbers and the new name', (lambda r: r and r['side'] == 'buy' and r['tp'] == 105.0 and r['sl'] == 99.0 and r['name'] == 'fb_session')(with_session(fb)(day(sl=True), [])))
T('filter: a buy is dropped when the bias is sell', with_session(fb)(day(sh=True), []) is None)
T('filter: a sell is kept when the bias is sell and dropped when it is buy', with_session(fs)(day(sh=True), []) and with_session(fs)(day(sl=True), []) is None)
T('filter: no bias drops everything', with_session(fb)(day(), []) is None and with_session(fs)(day(), []) is None)
T('filter: no session read (a weekend) drops everything', with_session(fb)(shift(day(sl=True), 3 * 86400), []) is None)
T('filter: a strategy with no signal stays silent', with_session(fn)(day(sl=True), []) is None)
T('filter: a custom name is used', with_session(fb, 'mine')(day(sl=True), [])['name'] == 'mine' and with_session(fb, 'mine').__name__ == 'mine')

# ---------------------------------------------------------------- the registered strategy (the switch is OFF by default)
T('switch: the store default is 0 (OFF)', st.get('orb_session') == '0')
SC = day(sl=True)                                   # London swept the low: bias BUY; the ORB push is up: a BUY
T('switch: OFF = silent even when everything agrees', orb_session(SC, []) is None)
st.put('orb_session', '1'); g = orb_session(SC, [])
T('switch: ON and the ORB buy agrees with the session = the trade, named orb_session', g and g['side'] == 'buy' and g['name'] == 'orb_session')
o = orb_entry(SC, [])
T('switch: same stop and target as orb_entry (it is the ORB trade, filtered)', g and o and abs(g['sl'] - o['sl']) < 1e-9 and abs(g['tp'] - o['tp']) < 1e-9)
T('switch: only side, stop, target and name (may not trade alone)', g and set(g) == {'side', 'sl', 'tp', 'name'} and osn.SOLO is False and 'solo' not in g)
T('switch: ON but London swept the HIGH (bias sell): the ORB buy is left to orb_entry alone', orb_session(day(sh=True), []) is None and orb_entry(day(sh=True), []) is not None)
T('switch: ON and no sweep: silent', orb_session(day(), []) is None)
T('switch: ON, both swept, London up: the buy agrees', orb_session(day(sh=True, sl=True, net=1), []) is not None)
T('switch: ON, both swept, London down: continuation is SELL, the ORB buy is not confirmed', orb_session(day(sh=True, sl=True, net=-1), []) is None)
T('switch: ON but no ORB setup: silent', orb_session(pre_ny(sl=True), []) is None)
MB = mirror(day(sl=True))                            # mirrored day: London swept the HIGH (bias SELL) and the push is DOWN (an ORB sell)
MS = mirror(day(sh=True))                            # mirrored day: London swept the LOW (bias BUY) and the push is DOWN (an ORB sell)
gs = orb_session(MB, [])
T('switch: a SELL works too (high swept, push down)', gs and gs['side'] == 'sell' and gs['name'] == 'orb_session')
T('switch: a SELL against the session (low swept, push down) is silent', orb_session(MS, []) is None and orb_entry(MS, []) is not None and orb_entry(MS, [])['side'] == 'sell')
st.put('orb_session', 'banana'); T('switch: a bad value counts as OFF', orb_session(SC, []) is None)
st.put('orb_session', '0'); T('switch: back to 0 silences it again', orb_session(SC, []) is None)
st.put('orb_session', '1'); bad = 0
for k in range(0, len(SC), 7):
    for ch in (SC[:k], SC[k:]):
        try: orb_session(ch, []); analyse(ch)
        except Exception: bad += 1
for junk in ([], [{}], [{'t': 1}], [{'t': 1}, {'t': 2}]):
    try: orb_session(junk, [])
    except Exception: bad += 1
T('strategy: never raises on odd data', bad == 0)
st.put('orb_session', '0')

# ---------------------------------------------------------------- registration
names = [f.__name__ for f in S.ALL]
T('registered once in strategies.ALL', names.count('orb_session') == 1 and names.count('orb_entry') == 1)
T('registered in the TREND group only', 'orb_session' in S.TREND and 'orb_session' not in S.REVERSION)
T('the function is named orb_session (the brain reads __name__)', orb_session.__name__ == 'orb_session')
T('has a name (1-32 chars) and a description (1-140 chars) in strategy_info', 'orb_session' in SI.INFO and 1 <= len(SI.INFO['orb_session'][0]) <= 32 and 1 <= len(SI.INFO['orb_session'][1]) <= 140)

# ---------------------------------------------------------------- the owner's switch over the API
C = app.test_client(); A = {'Authorization': 'Bearer dev:boss@x.com'}; U = {'Authorization': 'Bearer dev:joe@x.com'}
C.get('/api/me', headers=A); C.get('/api/me', headers=U)
x = C.post('/api/admin/settings', json={'orb_session': '1'}, headers=A)
T('the owner can switch it on (POST /api/admin/settings)', x.status_code == 200 and st.get('orb_session') == '1')
rp = st.get('risk_pct'); x = C.post('/api/admin/settings', json={'orb_session': '2', 'risk_pct': '0.37'}, headers=A)
T('a value other than 0 or 1 is refused with a plain message and nothing is saved', x.status_code == 400 and 'must be 0 or 1' in (x.get_json() or {}).get('error', '') and st.get('orb_session') == '1' and st.get('risk_pct') == rp and rp != '0.37')
x = C.post('/api/admin/settings', json={'orb_session': 'yes'}, headers=A); T('"yes" is refused too', x.status_code == 400 and st.get('orb_session') == '1')
x = C.post('/api/admin/settings', json={'btc_sunday_bounce': '3'}, headers=A); T('the 6B switches are still checked', x.status_code == 400)
x = C.post('/api/admin/settings', json={'orb_session': '0'}, headers=A); T('the owner can switch it off again', x.status_code == 200 and st.get('orb_session') == '0')
x = C.post('/api/admin/settings', json={'orb_session': '1'}, headers=U); T('a subscriber cannot touch it', x.status_code in (401, 403) and st.get('orb_session') == '0')
x = C.get('/api/admin/strategies', headers=A); T('the admin strategy list shows it', x.status_code == 200 and 'orb_session' in str(x.get_json()))

bad = [n for n, ok in R if not ok]
for n in bad: print('FAIL:', n)
print('%d checks, %d failed' % (len(R), len(bad)))
if os.path.exists(DB): os.remove(DB)
sys.exit(1 if bad else 0)
