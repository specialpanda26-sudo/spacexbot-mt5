"""The desktop app's brain: what the EA's OnTimer + OnTradeTransaction do, in Python. tick() is one pass (about every 5 s):
  1 report finished trades  2 send account + new candles  3 place the signal the server hands back, with the EA's safety checks.
Differences from the EA, all on the safe side: it refuses a signal while the bot is off in the app, queues reports on disk if the
internet drops (so a close is never lost), and tells the server whether a trade ended on TP or SL."""
import math, time
from . import config, basket
from .client import AuthError, ServerError
from .broker import BrokerError

DEFAULT_SYMBOLS = 'XAUUSD,EURUSD,GBPUSD,USDJPY'

class Engine:
    def __init__(self, cfg, broker, client, state_file=None, clock=time.time, log=print):
        self.cfg, self.b, self.c, self.clock, self._log, self.sf = cfg, broker, client, clock, log, state_file
        s = config.load_json(state_file) if state_file else {}
        self.known = {int(k): v for k, v in (s.get('known') or {}).items()}      # signal id -> MT5 position id, our open trades
        self.outbox = list(s.get('outbox') or []); self.done = list(s.get('done') or [])[-50:]
        self.groups = {int(k): v for k, v in (s.get('groups') or {}).items() if isinstance(v, dict)}          # DK2: open burst groups
        self.offset = cfg['utc_offset_min'] if cfg['utc_offset_min'] is not None else s.get('offset_min')     # broker server time minus UTC, minutes
        self.closing = {}; self.first_push = True; self.last_push = 0; self.server_symbols = ''
        self._prev = None; self._cand = None; self._cand_n = 0; self._names = {}; self.logs = []
        self.status = {'state': 'starting', 'msg': 'Starting...'}

    # ---------- helpers ----------
    def log(self, m):
        self.logs = (self.logs + ['%s  %s' % (time.strftime('%H:%M:%S'), m)])[-200:]; self._log(self.logs[-1])
    def _save(self):
        if self.sf: config.save_json(self.sf, {'known': self.known, 'outbox': self.outbox, 'done': self.done, 'offset_min': self.offset, 'groups': self.groups})
    def _symbols(self): return [s.strip() for s in (self.cfg['symbols'] or self.server_symbols or DEFAULT_SYMBOLS).split(',') if s.strip()]
    def _resolve(self, canon):
        if canon not in self._names:
            n = self.b.resolve(canon, self.cfg['suffix']); self._names[canon] = n
            if n is None: self.log('%s: not found at your broker (check the suffix setting)' % canon)
            elif n != canon + self.cfg['suffix']: self.log('%s is called %s at your broker' % (canon, n))
        return self._names[canon]
    def _queue(self, sid, status, **extra): self.outbox.append({'id': sid, 'status': status, 'extra': extra, 'n': 0}); self._save()

    def _flush(self):
        """Send queued reports in order. A failure keeps the rest for next time; an entry the server keeps refusing is dropped after 50 tries."""
        while self.outbox:
            e = self.outbox[0]
            try: self.c.report(e['id'], e['status'], **e['extra'])
            except AuthError: raise
            except ServerError:
                e['n'] += 1
                if e['n'] > 50: self.outbox.pop(0); continue
                break
            self.outbox.pop(0)
        self._save()

    # ---------- 1: finished trades ----------
    def _watch_closes(self):
        cur = {}
        for p in self.b.positions(self.cfg['magic']):             # BrokerError here means "unknown", never "closed"
            cm = p['comment'] or ''
            sid = basket.sid_of(cm)          # DK1: 'SXB12' and the burst form 'SXB12G5'
            if sid: cur[sid] = p['pid']
        for sid, pid in cur.items(): self.known.setdefault(sid, pid)       # also adopts trades opened before a restart
        for sid in [s for s in self.known if s not in cur]:
            info = self.b.close_info(self.known[sid])
            if info is None:                                       # MT5 history not ready yet: ask again next tick
                self.closing[sid] = self.closing.get(sid, 0) + 1
                if self.closing[sid] > 30: self.log('signal %d: could not read its result, gave up' % sid); del self.known[sid]
                continue
            self._queue(sid, 'closed', **basket.close_extra(self, sid, info)); del self.known[sid]; self.closing.pop(sid, None)
            self.log('signal %d closed: %s %+.2f' % (sid, info['reason'].upper(), info['pnl']))
        return len(cur)

    # ---------- 2: candles ----------
    def _observe_clock(self, syms):
        """Learn the broker's time zone (it changes with summer time) from LIVE ticks: server time must tick forward, and be a whole number
        of hours from this PC's UTC clock, three times in a row. Closed market = no change. The strategies use UTC hours, so this must be right."""
        if self.cfg['utc_offset_min'] is not None: self.offset = self.cfg['utc_offset_min']; return
        t = self.b.freshest_tick([n for n in map(self._resolve, syms) if n])
        prev, self._prev = self._prev, t
        if t is None or prev is None or t <= prev: return
        d = (t - self.clock()) / 3600.0; h = round(d)
        if abs(d - h) > 0.25 or abs(h) > 14: self.log('broker time does not match this PC\'s clock: fix the Windows date/time'); return
        self._cand, self._cand_n = (h * 60, self._cand_n + 1) if h * 60 == self._cand else (h * 60, 1)
        if self._cand_n >= 3 and self.offset != self._cand: self.offset = self._cand; self.log('broker time zone: UTC%+d' % h); self._save()

    def _bars(self, syms):
        out = {}; off = self.offset * 60
        for canon in syms:
            n = self._resolve(canon)
            if not n: continue
            try: m15, h1 = self.b.rates(n, 'M15', 450 if self.first_push else 6), self.b.rates(n, 'H1', 320 if self.first_push else 4)
            except Exception as e: self.log('%s candles: %s' % (canon, e)); continue
            if m15:
                out[canon] = {'M15': [[r[0] - off] + r[1:] for r in m15], 'H1': [[r[0] - off] + r[1:] for r in h1]}
                m5 = basket.rates_m5(self, n, off)          # DK3
                if m5: out[canon]['M5'] = m5
        return out or None

    # ---------- 3: placing a signal ----------
    @staticmethod
    def _lots(want, i, cap):
        step = i['vol_step'] or 0.01; nd = max(0, -int(math.floor(math.log10(step) + 1e-9)))
        lots = round(math.floor(min(want, i['vol_max'], cap) / step + 1e-9) * step, nd)
        return lots if lots >= i['vol_min'] - 1e-12 else None

    def cap_for(self, src, i):
        """LC2: the biggest lot for this trade = the smaller of the app's own cap and the person's max_lot from the server (0 or missing = no server cap).
        Returns (cap, None), or (None, why) when the person's biggest lot is below what the broker allows."""
        cap = self.cfg['max_lots']
        try: ml = float((src or {}).get('max_lot') or 0)
        except (TypeError, ValueError): ml = 0.0
        if ml != ml or ml < 0: ml = 0.0
        if ml > 0:
            if ml < i['vol_min'] - 1e-12: return None, 'your biggest lot is below the broker minimum lot'
            cap = min(cap, ml)
        return cap, None

    def _place(self, sid, sig, acct, bot):
        """None = order placed; text = why it was refused. Same checks as the EA, plus bot-off and algo-trading-off."""
        c = self.cfg
        if not bot: return 'bot is off in the app'
        if not acct['demo'] and not c['allow_live']: return 'live account blocked (allow_live is off)'
        if not acct['trade_allowed']: return 'Algo Trading is off in MetaTrader 5'
        side = sig.get('side'); canon = str(sig.get('symbol') or '').strip(); sym = self._resolve(canon) if canon else None
        try: sl, tp, risk = float(sig['sl']), float(sig['tp']), float(sig['risk_pct'])
        except (KeyError, TypeError, ValueError): return 'bad signal'
        if side not in ('buy', 'sell') or not (0 < risk <= 5): return 'bad signal'
        i = self.b.symbol(sym) if sym else None
        if not i or not i['tradable']: return 'symbol not found or not tradable'
        pt, ask, bid = i['point'], i['ask'], i['bid']
        if ask <= 0 or bid <= 0: return 'no price'
        if (ask - bid) / pt > c['max_spread_points']: return 'spread too wide'
        buy = side == 'buy'; price = ask if buy else bid; sl, tp = round(sl, i['digits']), round(tp, i['digits'])
        if not ((sl < price < tp) if buy else (tp < price < sl)): return 'SL/TP wrong side of price (stale signal)'
        lvl = i['stops_level'] * pt
        if abs(price - sl) < lvl or abs(price - tp) < lvl: return 'inside broker stop level'
        if i['tick_value'] <= 0 or i['tick_size'] <= 0: return 'no tick value'
        cap, why = self.cap_for(sig, i)          # LC2: obey the person's biggest lot
        if why: return why
        lots = self._lots(acct['balance'] * risk / 100.0 / ((abs(price - sl) / i['tick_size']) * i['tick_value']), i, cap)
        if lots is None: return 'min lot would risk more than allowed'
        r = self.b.send_market(sym, side, lots, sl, tp, 'SXB%d' % sid, c['deviation'], c['magic'], i['fill'])
        if not r['ok']: return 'order failed %s' % r['retcode']
        for p in self.b.positions(c['magic']):
            if p['comment'] == 'SXB%d' % sid: self.known[sid] = p['pid']
        self._queue(sid, 'open', ticket=r['ticket'], lots=lots, price=r['price']); self.log('signal %d: %s %s %.2f lots' % (sid, side.upper(), sym, lots))
        return None

    def _execute(self, sig, acct, bot):
        try: sid = int(sig.get('id'))
        except (TypeError, ValueError): return
        if sid in self.done: return                                 # never place the same signal twice
        self.done = (self.done + [sid])[-50:]
        try: why = self._place(sid, sig, acct, bot)
        except BrokerError as e: why = 'MetaTrader 5: %s' % e
        if why: self.log('signal %d refused: %s' % (sid, why)); self._queue(sid, 'rejected', reason=why[:120])

    # ---------- one pass ----------
    def _end(self, state, msg, acct=None, res=None):
        s = {'state': state, 'msg': msg, 'bot': (res or {}).get('bot'), 'open': len(self.known)}
        if acct: s.update(balance=acct['balance'], equity=acct['equity'], demo=acct['demo'])
        self.status = s; self._save(); return s

    def tick(self):
        try: acct = self.b.account()
        except BrokerError as e: return self._end('no_mt5', str(e))
        try: n_open = self._watch_closes()
        except BrokerError as e: n_open = len(self.known); self.log(str(e))
        try: self._flush()
        except AuthError: return self._end('bad_key', 'The server refused your key. Make a new one in the app (Connect tab).', acct)
        syms = self._symbols(); self._observe_clock(syms); bars = None
        if self.offset is not None and (self.first_push or self.clock() - self.last_push >= self.cfg['bars_push_seconds']): bars = self._bars(syms)
        payload = {'balance': round(acct['balance'], 2), 'equity': round(acct['equity'], 2), 'open': n_open, 'demo': acct['demo'],
                   'allow_live': self.cfg['allow_live'], 'login': acct['login']}
        try: res = self.c.sync(payload, bars)
        except AuthError: return self._end('bad_key', 'The server refused your key. Make a new one in the app (Connect tab).', acct)
        except ServerError as e: return self._end('offline', str(e) + ' (a sleeping free server needs about a minute)', acct)
        if bars is not None: self.first_push = False; self.last_push = self.clock()
        if res.get('symbols'): self.server_symbols = str(res['symbols'])
        if res.get('expired'): return self._end('expired', 'Your plan has ended. Renew it in the app.', acct, res)
        sig = res.get('signal')
        if isinstance(sig, dict): self._execute(sig, acct, res.get('bot') is True)
        bk = res.get('basket')          # DK1: a burst group arrives as one basket
        if isinstance(bk, dict): basket.run(self, bk, acct, res.get('bot') is True)
        basket.manage(self)          # DK2: close a group at its target / give-back / loss limit
        try: self._flush()
        except AuthError: pass
        msg = 'Waiting for the clock (a few seconds)...' if self.offset is None else 'Running. Bot is %s in the app.' % ('ON' if res.get('bot') else 'OFF')
        return self._end('ok', msg, acct, res)

    def run(self, stop, on_status=None):
        fails = 0
        while not stop.is_set():
            try: s = self.tick()
            except Exception as e: self.log('unexpected error: %s: %s' % (e.__class__.__name__, e)); s = self._end('error', 'Unexpected error, retrying.')
            if on_status: on_status(s)
            fails = 0 if s['state'] in ('ok', 'expired') else fails + 1
            basket.pause(self, stop, self.cfg['poll_seconds'] if not fails else min(60, self.cfg['poll_seconds'] * 2 ** min(fails, 5)))
