"""Desktop app core against the REAL server code (Flask test client) and a fake MT5. No network, no MetaTrader needed.
Run:  python tests/test_desktop.py   (exit code 1 on any failure)"""
import os, sys, json, time, random, types, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, ROOT)
WORK = os.path.join(ROOT, 'data', 'desktop_test'); os.makedirs(WORK, exist_ok=True)
os.environ.update(DEV_AUTH='1', EA_KEY='ownerkey', ADMIN_EMAILS='boss@x.com', DB_PATH=os.path.join(WORK, 'srv.db'), BASE_URL='http://t')
if os.path.exists(os.environ['DB_PATH']): os.remove(os.environ['DB_PATH'])
from backend.app import app
from backend import store as st, bars, links
from desktop import config
from desktop.client import Client, AuthError, ServerError
from desktop.broker import BrokerError
from desktop.engine import Engine

R = []
def T(name):
    def deco(f):
        try: f(); R.append((name, True, ''))
        except Exception as e: R.append((name, False, repr(e)[:200]))
        return f
    return deco

# ---------- fakes ----------
class Clock:
    def __init__(self): self.now = time.time()
    def __call__(self): return self.now

class Flask:           # makes the Flask test client look like a `requests` session
    def __init__(self): self.c = app.test_client(); self.fail = False
    def post(self, url, json=None, headers=None, timeout=None):
        if self.fail: raise ConnectionError('down')
        r = self.c.post('/' + url.split('/', 3)[3], json=json, headers=headers)
        return types.SimpleNamespace(status_code=r.status_code, json=lambda: r.get_json(silent=True))

INFO = {'point': 0.01, 'digits': 2, 'ask': 2300.10, 'bid': 2300.00, 'stops_level': 10, 'tick_value': 1.0, 'tick_size': 0.01,
        'vol_min': 0.01, 'vol_max': 100.0, 'vol_step': 0.01, 'fill': 1, 'tradable': True}
class Fake:
    def __init__(self, clock, off=180, names=('XAUUSD', 'EURUSD')):
        self.clock, self.off, self.live, self.frozen = clock, off, True, 0
        self.info = {n: dict(INFO) for n in names}; self.acct = {'balance': 10000.0, 'equity': 10000.0, 'login': 7, 'demo': True, 'trade_allowed': True}
        self.pos, self.closed, self.orders, self.down, self.pos_err, self.refuse = [], {}, [], False, False, False
    def account(self):
        if self.down: raise BrokerError('MetaTrader 5 has no connection to the broker.')
        return dict(self.acct)
    def resolve(self, canon, suffix=''):
        for n in self.info:
            if n == canon + suffix: return n
        c = sorted((n for n in self.info if n.startswith(canon)), key=len); return c[0] if c else None
    def symbol(self, n): return dict(self.info[n]) if n in self.info else None
    def freshest_tick(self, syms): return int(self.clock.now) + self.off * 60 if self.live else self.frozen
    def rates(self, sym, tf, count):
        step = 900 if tf == 'M15' else 3600; last = int(self.clock.now // step) * step - step; rnd = random.Random(5); p = 2300.0; out = []
        for k in range(count):
            o = p; p += rnd.gauss(0, 1); out.append([last - (count - 1 - k) * step + self.off * 60, o, max(o, p) + .3, min(o, p) - .3, p, 10])
        self.last_utc = getattr(self, 'last_utc', {}); self.last_utc[tf] = last; return out
    def positions(self, magic):
        if self.pos_err: raise BrokerError('could not read open positions')
        return [dict(p) for p in self.pos]
    def close_info(self, pid): return self.closed.get(pid)
    def send_market(self, sym, side, lots, sl, tp, comment, deviation, magic, fill):
        if self.refuse: return {'ok': False, 'retcode': 10006, 'ticket': 0, 'price': 0, 'comment': 'rejected'}
        i = 1000 + len(self.orders); self.orders.append(dict(sym=sym, side=side, lots=lots, sl=sl, tp=tp, comment=comment))
        self.pos.append({'pid': i, 'ticket': i, 'comment': comment, 'symbol': sym}); return {'ok': True, 'retcode': 10009, 'ticket': i, 'price': 2300.10, 'comment': ''}
    def close(self, pid, pnl, reason='sl'): self.pos = [p for p in self.pos if p['pid'] != pid]; self.closed[pid] = {'pnl': pnl, 'reason': reason}

def rig(off=180, key='ownerkey', names=('XAUUSD', 'EURUSD'), **cfg):
    clock = Clock(); fb = Fake(clock, off, names); web = Flask()
    c = config.clean(dict(server_url='http://t', key=key, symbols='XAUUSD,EURUSD', **cfg))
    sf = os.path.join(WORK, 'state_%d.json' % random.randint(0, 10 ** 9))
    return clock, fb, web, Engine(c, fb, Client('http://t', key, web), sf, clock, lambda m: None), sf
def go(e, clock, n=1):
    for _ in range(n): clock.now += 5; s = e.tick()
    return s
def new_signal(sym='XAUUSD', side='buy', sl=2295.0, tp=2310.0, uid=None, risk=1.0, age=0):
    return st.x('INSERT INTO signals(symbol,side,entry,sl,tp,risk_pct,strategy,score,status,created,uid) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (sym, side, 2300.0, sl, tp, risk, 't', 2, 'pending', int(time.time()) - age, uid))
def sig(i): return st.q('SELECT * FROM signals WHERE id=?', (i,), True)
st.put('min_confluence', 99); st.put('bot_enabled', '1')      # the server's own scan never makes a signal; tests insert them

# ---------- config ----------
@T('config: junk in, safe values out')
def _():
    c = config.clean({'server_url': ' https://a.com/ ', 'poll_seconds': 'x', 'max_lots': -5, 'allow_live': 'yes', 'deviation': 9999, 'utc_offset_min': 'abc', 'evil': 1})
    assert c['server_url'] == 'https://a.com' and c['poll_seconds'] == 5 and c['max_lots'] == 0.01 and c['allow_live'] is False
    assert c['deviation'] == 500 and c['utc_offset_min'] is None and 'evil' not in c
@T('config: problems are told in plain words')
def _():
    assert len(config.problems(config.clean({}))) == 2 and not config.problems(config.clean({'server_url': 'https://x.com', 'key': 'k'}))
    assert config.problems(config.clean({'server_url': 'http://evil.com', 'key': 'k'}))
@T('config: save and load round trip')
def _():
    p = os.path.join(WORK, 'c.json'); config.save({'server_url': 'https://x.com', 'key': 'sxb_1', 'max_lots': 0.5}, p)
    c = config.load(p); assert c['key'] == 'sxb_1' and c['max_lots'] == 0.5 and config.load(os.path.join(WORK, 'none.json'))['poll_seconds'] == 5

# ---------- client ----------
@T('client: bad key -> AuthError, network down -> ServerError, good key works')
def _():
    w = Flask()
    try: Client('http://t', 'wrong', w).sync({}); assert 0
    except AuthError: pass
    w.fail = True
    try: Client('http://t', 'ownerkey', w).sync({}); assert 0
    except ServerError: pass
    w.fail = False; assert Client('http://t', 'ownerkey', w).sync({'balance': 1})['bot'] is True

# ---------- candles + time zone ----------
@T('time zone: learned from live ticks, candles reach the server in UTC (broker at UTC+3)')
def _():
    clock, fb, web, e, sf = rig(off=180); bars._d.clear()
    s = go(e, clock, 3); assert e.offset is None and not bars.get('XAUUSD', 'M15'), 'must not push candles before the time zone is known'
    s = go(e, clock, 2); assert e.offset == 180, e.offset
    m = bars.get('XAUUSD', 'M15'); assert len(m) == 450 and m[-1]['t'] == fb.last_utc['M15'] and m[-1]['t'] - m[-2]['t'] == 900
    assert len(bars.get('XAUUSD', 'H1')) == 320 and s['state'] == 'ok'
@T('time zone: broker at UTC-5 and UTC+0 are both right')
def _():
    for off in (-300, 0):
        clock, fb, web, e, sf = rig(off=off); bars._d.clear(); go(e, clock, 6); assert e.offset == off and bars.get('EURUSD', 'M15')[-1]['t'] == fb.last_utc['M15'], off
@T('time zone: closed market and no saved value -> no candles pushed (weekend start)')
def _():
    clock, fb, web, e, sf = rig(); fb.live = False; fb.frozen = int(clock.now) - 3 * 86400; bars._d.clear(); s = go(e, clock, 8)
    assert e.offset is None and not bars.get('XAUUSD', 'M15') and s['state'] == 'ok'
@T('time zone: saved value survives a restart, so a Monday-morning start pushes at once')
def _():
    clock, fb, web, e, sf = rig(off=120); go(e, clock, 6); assert e.offset == 120
    c2 = Clock(); f2 = Fake(c2, 120); f2.live = False; f2.frozen = 1; bars._d.clear()
    e2 = Engine(e.cfg, f2, Client('http://t', 'ownerkey', Flask()), sf, c2, lambda m: None); c2.now += 5; e2.tick()
    assert e2.offset == 120 and len(bars.get('XAUUSD', 'M15')) == 450
@T('time zone: a wrong PC clock is refused, not guessed')
def _():
    clock, fb, web, e, sf = rig(); e.clock = lambda: clock.now + 1800; bars._d.clear(); go(e, clock, 8); assert e.offset is None and not bars.get('XAUUSD', 'M15')
@T('time zone: manual override in the settings wins')
def _():
    clock, fb, web, e, sf = rig(off=180, utc_offset_min=240); bars._d.clear(); go(e, clock, 1); assert e.offset == 240
@T('candles: after the first push only the newest few are sent')
def _():
    clock, fb, web, e, sf = rig(); go(e, clock, 5); sent = []; orig = e.c.sync
    e.c.sync = lambda a, b=None: (sent.append(b), orig(a, b))[1]; clock.now += 61; go(e, clock, 1)
    assert sent[-1] and len(sent[-1]['XAUUSD']['M15']) == 6 and len(sent[-1]['XAUUSD']['H1']) == 4
@T('symbols: suffix found automatically, server symbol list used when none set')
def _():
    clock, fb, web, e, sf = rig(names=('XAUUSDm', 'EURUSDm')); e.cfg['symbols'] = ''; bars._d.clear(); go(e, clock, 6)
    assert fb.resolve('XAUUSD') == 'XAUUSDm' and bars.get('XAUUSD', 'M15') and not bars.get('GBPUSD', 'M15')

# ---------- placing trades ----------
@T('trade: 1% of 10000, buy at 2300.10 with SL 2295.10 (5.00 away) = 0.20 lots, server sees it open')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(sl=2295.10); go(e, clock, 1)
    o = fb.orders[-1]; assert o['lots'] == 0.2 and o['side'] == 'buy' and o['sl'] == 2295.1 and o['tp'] == 2310.0 and o['comment'] == 'SXB%d' % i, o
    s = sig(i); assert s['status'] == 'open' and s['lots'] == 0.2 and s['ticket'] and e.known[i] == fb.pos[-1]['pid']
@T('trade: a sell works and risk scales (0.5% -> 0.10 lots)')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(side='sell', sl=2305.0, tp=2290.0, risk=0.5); go(e, clock, 1)
    assert fb.orders[-1]['lots'] == 0.1 and fb.orders[-1]['side'] == 'sell', fb.orders[-1]
@T('trade: lots are capped by max_lots and floored to the broker step')
def _():
    clock, fb, web, e, sf = rig(max_lots=0.15); new_signal(); go(e, clock, 1); assert fb.orders[-1]['lots'] == 0.15
    clock, fb, web, e, sf = rig(); fb.info['XAUUSD']['vol_step'] = 0.1; new_signal(sl=2294.0); go(e, clock, 1); assert fb.orders[-1]['lots'] == 0.1, fb.orders[-1]
def refused(fix, why, **kw):
    clock, fb, web, e, sf = rig(**kw); fix(fb); i = new_signal(**({'sl': 2295.0})); go(e, clock, 1)
    s = sig(i); assert not fb.orders and s['status'] == 'rejected' and why in (s['note'] or ''), (s['status'], s['note'])
@T('refused: live account without allow_live')
def _(): refused(lambda f: f.acct.update(demo=False), 'live account blocked')
@T('refused: Algo Trading button off')
def _(): refused(lambda f: f.acct.update(trade_allowed=False), 'Algo Trading')
@T('refused: spread too wide')
def _(): refused(lambda f: f.info['XAUUSD'].update(ask=2301.0), 'spread')
@T('refused: stale signal (price already past TP)')
def _(): refused(lambda f: f.info['XAUUSD'].update(ask=2311.0, bid=2310.9), 'stale')
@T('refused: inside the broker stop level')
def _(): refused(lambda f: f.info['XAUUSD'].update(stops_level=900), 'stop level')
@T('refused: the minimum lot would risk too much')
def _(): refused(lambda f: f.info['XAUUSD'].update(vol_min=1.0), 'min lot')
@T('refused: symbol the broker does not have')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(sym='GBPJPY'); go(e, clock, 1); assert sig(i)['status'] == 'rejected' and not fb.orders
@T('refused: broker says no -> reported with the code')
def _(): refused(lambda f: setattr(f, 'refuse', True), 'order failed 10006')
@T('live account IS traded when allow_live is on')
def _():
    clock, fb, web, e, sf = rig(allow_live=True); fb.acct['demo'] = False; i = new_signal(); go(e, clock, 1); assert fb.orders and sig(i)['status'] == 'open'
@T('bot off in the app: signal handed over is refused, not traded')
def _():
    st.put('bot_enabled', '0')
    try: clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1); assert not fb.orders and sig(i)['status'] == 'rejected' and 'bot is off' in sig(i)['note']
    finally: st.put('bot_enabled', '1')
@T('the same signal is never placed twice')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1); e.c.sync = lambda a, b=None: {'signal': {'id': i, 'symbol': 'XAUUSD', 'side': 'buy', 'sl': 2295, 'tp': 2310, 'risk_pct': 1}, 'bot': True}
    go(e, clock, 3); assert len(fb.orders) == 1
@T('garbage signals from the server cannot crash or trade')
def _():
    clock, fb, web, e, sf = rig(); go(e, clock, 1)
    for bad in ({'id': 'x'}, {'id': 9001}, {'id': 9002, 'symbol': 'XAUUSD', 'side': 'buy', 'sl': 'a', 'tp': 1, 'risk_pct': 1}, {'id': 9003, 'symbol': 'XAUUSD', 'side': 'buy', 'sl': 2295, 'tp': 2310, 'risk_pct': 50}):
        e.c.sync = lambda a, b=None, bad=bad: {'signal': bad, 'bot': True}; assert go(e, clock, 1)['state'] == 'ok'
    assert not fb.orders

# ---------- closes ----------
@T('close: result (P/L and TP/SL) reaches the server and the loss counts')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1); fb.close(fb.pos[-1]['pid'], -12.5, 'sl'); go(e, clock, 1)
    s = sig(i); assert s['status'] == 'closed' and s['pnl'] == -12.5 and s['closed'] and not e.known
@T('close: unreadable position list is NOT treated as closed')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1); fb.pos_err = True; go(e, clock, 3)
    assert sig(i)['status'] == 'open' and e.known; fb.pos_err = False; go(e, clock, 1); assert sig(i)['status'] == 'open'
@T('close: MT5 history slow to appear -> retried, then reported')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1); pid = fb.pos[-1]['pid']; fb.pos = []; go(e, clock, 3)
    assert sig(i)['status'] == 'open'; fb.closed[pid] = {'pnl': 20.0, 'reason': 'tp'}; go(e, clock, 1); assert sig(i)['status'] == 'closed' and sig(i)['pnl'] == 20.0
@T('close: internet down when it closed -> kept on disk, sent when back')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1); fb.close(fb.pos[-1]['pid'], 33.0, 'tp'); web.fail = True; s = go(e, clock, 3)
    assert s['state'] == 'offline' and sig(i)['status'] == 'open' and len(e.outbox) == 1
    web.fail = False; go(e, clock, 1); assert sig(i)['status'] == 'closed' and sig(i)['pnl'] == 33.0 and not e.outbox
@T('close: app closed while the trade ended -> reported after restart')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1); fb.close(fb.pos[-1]['pid'], -7.0, 'sl')
    e2 = Engine(e.cfg, fb, Client('http://t', 'ownerkey', web), sf, clock, lambda m: None); go(e2, clock, 1); assert sig(i)['status'] == 'closed' and sig(i)['pnl'] == -7.0
@T('restart with a still-open trade keeps tracking it')
def _():
    clock, fb, web, e, sf = rig(); i = new_signal(); go(e, clock, 1)
    e2 = Engine(e.cfg, fb, Client('http://t', 'ownerkey', web), sf, clock, lambda m: None); go(e2, clock, 1); assert e2.known == e.known and sig(i)['status'] == 'open'

# ---------- failures ----------
@T('MT5 closed: clear message, no crash, recovers')
def _():
    clock, fb, web, e, sf = rig(); fb.down = True; s = go(e, clock, 2); assert s['state'] == 'no_mt5' and 'no connection' in s['msg']
    fb.down = False; assert go(e, clock, 1)['state'] == 'ok'
@T('wrong key: says so in plain words')
def _():
    clock, fb, web, e, sf = rig(key='sxb_nope'); s = go(e, clock, 1); assert s['state'] == 'bad_key' and 'key' in s['msg']
@T('run loop survives an unexpected crash and stops on request')
def _():
    import threading
    clock, fb, web, e, sf = rig(); e.cfg['poll_seconds'] = 2; n = [0]; stop = threading.Event()
    def boom():
        n[0] += 1
        if n[0] >= 3: stop.set()
        raise ValueError('x')
    e.tick = boom; e.cfg['poll_seconds'] = 2; orig = stop.wait; stop.wait = lambda s: None; e.run(stop); assert n[0] == 3 and e.status['state'] == 'error'

# ---------- a subscriber's own key (not the owner's) ----------
@T('subscriber key: sync, trade and close work and stay in their own data')
def _():
    uid = 'sub1'; st.x('INSERT INTO users(uid,email,name,created,plan_until,onboarded) VALUES(?,?,?,?,?,1)', (uid, 's@x.com', 's', int(time.time()), int(time.time()) + 86400))
    key = links.new_key(uid); links.set_bot(uid, True); bars._d.clear()
    clock, fb, web, e, sf = rig(key=key); i = new_signal(uid=uid); j = new_signal(); go(e, clock, 6)
    assert len(bars.get('XAUUSD', 'M15', uid)) == 450 and not bars.get('XAUUSD', 'M15', '')
    assert len(fb.orders) == 1 and fb.orders[0]['comment'] == 'SXB%d' % i and sig(i)['status'] == 'open' and sig(j)['status'] == 'pending'
    fb.close(fb.pos[-1]['pid'], 5.0, 'tp'); go(e, clock, 1); assert sig(i)['status'] == 'closed' and sig(j)['status'] != 'closed'
@T('subscriber key: ended plan -> told so, nothing traded')
def _():
    uid = 'sub2'; st.x('INSERT INTO users(uid,email,name,created,plan_until,onboarded) VALUES(?,?,?,?,?,1)', (uid, 't@x.com', 't', int(time.time()), int(time.time()) - 10))
    key = links.new_key(uid); clock, fb, web, e, sf = rig(key=key); i = new_signal(uid=uid); s = go(e, clock, 6); assert s['state'] == 'expired' and not fb.orders

w = max(len(n) for n, _, _ in R)
for n, ok, err in R: print(('PASS ' if ok else 'FAIL ') + n.ljust(w), '' if ok else ' <- ' + err)
bad = [n for n, ok, _ in R if not ok]; print(f'\n{len(R) - len(bad)}/{len(R)} passed'); sys.exit(1 if bad else 0)
